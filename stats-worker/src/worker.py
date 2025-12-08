"""
Stats Worker - Main Worker Process

Processes statistical analysis jobs from Redis queue:
- EDA reports using ydata-profiling
- Table 1 using tableone
- Auto-analyze: intelligent statistical analysis
"""
import json
import logging
import os
import signal
import sys
import time
import traceback
from datetime import datetime
from io import BytesIO
from pathlib import Path

import pandas as pd
import redis
from minio import Minio

from .config import (
    REDIS_HOST, REDIS_PORT, REDIS_DB,
    STATS_JOBS_PENDING, STATS_JOBS_PREFIX,
    MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY,
    MINIO_SECURE, MINIO_DATASET_BUCKET, MINIO_REPORTS_BUCKET,
    WORKER_POLL_INTERVAL, TEMP_DIR,
)

# Configure logging
log_level = os.environ.get("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
running = True


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    global running
    logger.info(f"Received signal {signum}, shutting down...")
    running = False


class StatsWorker:
    """Worker for processing statistical analysis jobs"""
    
    def __init__(self):
        self.redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            decode_responses=True
        )
        
        self.minio_client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=MINIO_SECURE
        )
        
        # Ensure temp directory exists
        Path(TEMP_DIR).mkdir(parents=True, exist_ok=True)
        
        # Ensure reports bucket exists
        if not self.minio_client.bucket_exists(MINIO_REPORTS_BUCKET):
            self.minio_client.make_bucket(MINIO_REPORTS_BUCKET)
            logger.info(f"Created bucket: {MINIO_REPORTS_BUCKET}")
        
        logger.info("Stats Worker initialized")
    
    def update_job_status(self, job_id: str, status: str, **kwargs):
        """Update job status in Redis"""
        key = f"{STATS_JOBS_PREFIX}{job_id}"
        data = self.redis_client.get(key)
        
        if data:
            job = json.loads(data)
            job["status"] = status
            job["updated_at"] = datetime.utcnow().isoformat()
            job.update(kwargs)
            self.redis_client.set(key, json.dumps(job))
    
    def load_dataset_by_path(self, minio_path: str) -> pd.DataFrame:
        """Load dataset from MinIO by path (bucket/object format)"""
        try:
            # Parse path: could be 'bucket/path' or just 'path'
            if '/' in minio_path:
                parts = minio_path.split('/', 1)
                # Check if first part is a bucket name
                if self.minio_client.bucket_exists(parts[0]):
                    bucket = parts[0]
                    object_name = parts[1]
                else:
                    bucket = MINIO_DATASET_BUCKET
                    object_name = minio_path
            else:
                bucket = MINIO_DATASET_BUCKET
                object_name = minio_path
            
            logger.info(f"Loading dataset from {bucket}/{object_name}")
            
            response = self.minio_client.get_object(bucket, object_name)
            data = response.read()
            response.close()
            response.release_conn()
            
            return pd.read_csv(BytesIO(data))
            
        except Exception as e:
            logger.error(f"Failed to load dataset from {minio_path}: {e}")
            raise FileNotFoundError(f"Dataset not found at {minio_path}")
    
    def load_dataset(self, dataset_id: str) -> pd.DataFrame:
        """Load dataset from MinIO"""
        # Try to find the dataset file
        # Convention: datasets are stored as {dataset_id}.csv or in a path stored in metadata
        
        try:
            # First try direct path
            response = self.minio_client.get_object(
                MINIO_DATASET_BUCKET,
                f"{dataset_id}.csv"
            )
            data = response.read()
            response.close()
            response.release_conn()
            
            return pd.read_csv(BytesIO(data))
        except Exception as e:
            logger.warning(f"Could not load {dataset_id}.csv: {e}")
            
            # Try to find by listing objects
            objects = list(self.minio_client.list_objects(
                MINIO_DATASET_BUCKET,
                prefix=dataset_id,
                recursive=True
            ))
            
            for obj in objects:
                if obj.object_name.endswith('.csv'):
                    response = self.minio_client.get_object(
                        MINIO_DATASET_BUCKET,
                        obj.object_name
                    )
                    data = response.read()
                    response.close()
                    response.release_conn()
                    return pd.read_csv(BytesIO(data))
            
            raise FileNotFoundError(f"Dataset {dataset_id} not found in MinIO")
    
    def save_report(self, job_id: str, report_data: dict, format: str = "json") -> str:
        """Save report to MinIO"""
        if format == "json":
            content = json.dumps(report_data, indent=2, default=str)
            content_type = "application/json"
            ext = "json"
        elif format == "html":
            content = report_data.get("html", str(report_data))
            content_type = "text/html"
            ext = "html"
        else:
            content = str(report_data)
            content_type = "text/plain"
            ext = "txt"
        
        object_name = f"{job_id}.{ext}"
        content_bytes = content.encode('utf-8')
        
        self.minio_client.put_object(
            MINIO_REPORTS_BUCKET,
            object_name,
            BytesIO(content_bytes),
            length=len(content_bytes),
            content_type=content_type
        )
        
        return f"{MINIO_REPORTS_BUCKET}/{object_name}"
    
    def process_eda_job(self, job: dict):
        """Process EDA job using ydata-profiling"""
        from ydata_profiling import ProfileReport
        
        job_id = job["job_id"]
        params = job["params"]
        
        logger.info(f"Processing EDA job {job_id}")
        
        self.update_job_status(job_id, "running", progress=0.1, message="Loading dataset...")
        
        # Load dataset - prefer minio_path, then dataset_id from job level
        minio_path = job.get("minio_path") or params.get("minio_path")
        dataset_id = job.get("dataset_id") or params.get("dataset_id")
        
        if minio_path:
            df = self.load_dataset_by_path(minio_path)
        elif dataset_id:
            df = self.load_dataset(dataset_id)
        else:
            raise ValueError("No dataset_id or minio_path provided")
        logger.info(f"Loaded dataset with shape {df.shape}")
        
        self.update_job_status(job_id, "running", progress=0.3, message="Generating profile...")
        
        # Generate profile
        profile = ProfileReport(
            df,
            title=params.get("title", "EDA Report"),
            minimal=params.get("minimal", True),
            explorative=True,
        )
        
        self.update_job_status(job_id, "running", progress=0.7, message="Saving report...")
        
        # Get JSON output
        report_json = json.loads(profile.to_json())
        
        # Also get HTML for viewing
        html_report = profile.to_html()
        
        # Save both formats
        json_path = self.save_report(job_id, report_json, format="json")
        html_path = self.save_report(f"{job_id}_html", {"html": html_report}, format="html")
        
        self.update_job_status(
            job_id, "completed",
            progress=1.0,
            message="EDA report generated successfully",
            result_path=json_path,
            html_path=html_path.replace("_html.", "."),
        )
        
        logger.info(f"EDA job {job_id} completed")
    
    def process_tableone_job(self, job: dict):
        """Process TableOne job"""
        from tableone import TableOne
        
        job_id = job["job_id"]
        params = job["params"]
        
        logger.info(f"Processing TableOne job {job_id}")
        
        self.update_job_status(job_id, "running", progress=0.1, message="Loading dataset...")
        
        # Load dataset - prefer minio_path, then dataset_id from job level
        minio_path = job.get("minio_path") or params.get("minio_path")
        dataset_id = job.get("dataset_id") or params.get("dataset_id")
        
        if minio_path:
            df = self.load_dataset_by_path(minio_path)
        elif dataset_id:
            df = self.load_dataset(dataset_id)
        else:
            raise ValueError("No dataset_id or minio_path provided")
        logger.info(f"Loaded dataset with shape {df.shape}")
        
        self.update_job_status(job_id, "running", progress=0.3, message="Generating Table 1...")
        
        # Prepare TableOne parameters
        tableone_params = {
            "data": df,
        }
        
        if params.get("columns"):
            tableone_params["columns"] = params["columns"]
        if params.get("categorical"):
            tableone_params["categorical"] = params["categorical"]
        if params.get("continuous"):
            tableone_params["continuous"] = params["continuous"]
        if params.get("groupby"):
            tableone_params["groupby"] = params["groupby"]
        if params.get("nonnormal"):
            tableone_params["nonnormal"] = params["nonnormal"]
        if params.get("pval"):
            tableone_params["pval"] = params["pval"]
        
        # Generate Table 1
        table = TableOne(**tableone_params)
        
        self.update_job_status(job_id, "running", progress=0.7, message="Saving report...")
        
        # Get outputs - handle tuple keys in tableone dict
        tableone_dict = table.tableone.to_dict()
        # Convert tuple keys to strings for JSON serialization
        tableone_serializable = {}
        for col_key, col_data in tableone_dict.items():
            col_key_str = str(col_key) if isinstance(col_key, tuple) else col_key
            tableone_serializable[col_key_str] = {
                str(k) if isinstance(k, tuple) else k: v 
                for k, v in col_data.items()
            }
        
        report = {
            "tableone": tableone_serializable,
            "tabulate_text": table.tabulate(tablefmt="grid"),
            "tabulate_html": table.tabulate(tablefmt="html"),
            "tabulate_latex": table.tabulate(tablefmt="latex"),
            "n_rows": len(df),
            "n_cols": len(df.columns),
            "groupby": params.get("groupby"),
        }
        
        # Save report
        result_path = self.save_report(job_id, report, format="json")
        
        self.update_job_status(
            job_id, "completed",
            progress=1.0,
            message="Table 1 generated successfully",
            result_path=result_path,
        )
        
        logger.info(f"TableOne job {job_id} completed")
    
    def process_auto_analyze_job(self, job: dict):
        """Process auto-analyze job - intelligent statistical analysis"""
        from .tasks.auto_analyze_task import run_auto_analyze
        
        job_id = job["job_id"]
        params = job["params"]
        
        logger.info(f"Processing auto-analyze job {job_id}")
        
        self.update_job_status(job_id, "running", progress=0.1, message="Loading dataset...")
        
        # Load dataset - prefer minio_path, then dataset_id from job level
        minio_path = job.get("minio_path") or params.get("minio_path")
        dataset_id = job.get("dataset_id") or params.get("dataset_id")
        
        if minio_path:
            df = self.load_dataset_by_path(minio_path)
        elif dataset_id:
            df = self.load_dataset(dataset_id)
        else:
            raise ValueError("No dataset_id or minio_path provided")
        logger.info(f"Loaded dataset with shape {df.shape}")
        
        self.update_job_status(job_id, "running", progress=0.2, message="Analyzing data quality...")
        
        # Run auto-analysis
        target_column = params.get("target_column")
        
        self.update_job_status(job_id, "running", progress=0.4, message="Profiling columns...")
        
        result = run_auto_analyze(df, target_column=target_column)
        
        self.update_job_status(job_id, "running", progress=0.8, message="Saving analysis report...")
        
        # Add summary for easy reading
        result["summary"] = self._generate_summary(result)
        
        # Save report
        result_path = self.save_report(job_id, result, format="json")
        
        self.update_job_status(
            job_id, "completed",
            progress=1.0,
            message="Auto-analysis completed successfully",
            result_path=result_path,
        )
        
        logger.info(f"Auto-analyze job {job_id} completed")
    
    def _generate_summary(self, result: dict) -> dict:
        """Generate human-readable summary from analysis result"""
        summary = {
            "overview": f"Dataset has {result['metadata']['n_rows']} rows and {result['metadata']['n_cols']} columns",
            "quality": f"Data quality score: {result['data_quality']['score']}/100",
        }
        
        # Column summary
        col_summary = result.get("column_summary", {})
        summary["columns"] = {
            "numeric": len(col_summary.get("numeric", [])),
            "categorical": len(col_summary.get("categorical", [])),
            "datetime": len(col_summary.get("datetime", [])),
            "excluded": len(col_summary.get("id_columns", [])) + len(col_summary.get("constant", [])),
        }
        
        # Top issues
        issues = result.get("data_quality", {}).get("issues", [])
        if issues:
            summary["top_issues"] = issues[:3]
        
        # Target analysis summary
        if result.get("target_analysis") and result["target_analysis"].get("associations"):
            assocs = result["target_analysis"]["associations"]
            significant = [a for a in assocs if a.get("p_value", 1) < 0.05]
            summary["target_analysis"] = {
                "total_features_tested": len(assocs),
                "significant_associations": len(significant),
                "top_predictors": [a["variable"] for a in significant[:5]],
            }
        
        # Top recommendations
        recs = result.get("recommendations", [])
        if recs:
            summary["key_recommendations"] = [
                {"category": r["category"], "suggestion": r["suggestion"]}
                for r in recs[:3]
            ]
        
        return summary
    
    def process_auto_analyze_direct_job(self, job: dict):
        """Process auto-analyze job with direct CSV content (no MinIO)"""
        from .tasks.auto_analyze_task import run_auto_analyze
        
        job_id = job["job_id"]
        params = job["params"]
        
        logger.info(f"Processing direct auto-analyze job {job_id}")
        
        self.update_job_status(job_id, "running", progress=0.1, message="Parsing CSV content...")
        
        # Load dataset from CSV content
        csv_content = params.get("csv_content")
        if not csv_content:
            raise ValueError("No CSV content provided")
        
        df = pd.read_csv(BytesIO(csv_content.encode('utf-8')))
        logger.info(f"Loaded direct CSV with shape {df.shape}")
        
        self.update_job_status(job_id, "running", progress=0.2, message="Analyzing data quality...")
        
        # Run auto-analysis
        target_column = params.get("target_column")
        
        self.update_job_status(job_id, "running", progress=0.4, message="Profiling columns...")
        
        result = run_auto_analyze(df, target_column=target_column)
        
        self.update_job_status(job_id, "running", progress=0.8, message="Saving analysis report...")
        
        # Add summary
        result["summary"] = self._generate_summary(result)
        result["is_direct"] = True  # Mark as direct analysis
        
        # Save report
        result_path = self.save_report(job_id, result, format="json")
        
        self.update_job_status(
            job_id, "completed",
            progress=1.0,
            message="Direct auto-analysis completed successfully",
            result_path=result_path,
        )
        
        logger.info(f"Direct auto-analyze job {job_id} completed")
    
    def process_job(self, job: dict):
        """Process a single job"""
        job_type = job.get("job_type")
        job_id = job.get("job_id")
        
        try:
            if job_type == "eda":
                self.process_eda_job(job)
            elif job_type == "tableone":
                self.process_tableone_job(job)
            elif job_type == "auto_analyze":
                self.process_auto_analyze_job(job)
            elif job_type == "auto_analyze_direct":
                self.process_auto_analyze_direct_job(job)
            else:
                raise ValueError(f"Unknown job type: {job_type}")
                
        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}")
            logger.error(traceback.format_exc())
            
            self.update_job_status(
                job_id, "failed",
                error=str(e),
                message=f"Job failed: {str(e)[:200]}"
            )
    
    def run(self):
        """Main worker loop"""
        global running
        
        logger.info("Stats Worker starting...")
        logger.info(f"Listening on queue: {STATS_JOBS_PENDING}")
        
        while running:
            try:
                # Block waiting for job (with timeout for graceful shutdown)
                result = self.redis_client.brpop(STATS_JOBS_PENDING, timeout=WORKER_POLL_INTERVAL)
                
                if result:
                    _, job_data = result
                    job = json.loads(job_data)
                    
                    logger.info(f"Received job: {job.get('job_id')} (type: {job.get('job_type')})")
                    self.process_job(job)
                    
            except redis.ConnectionError as e:
                logger.error(f"Redis connection error: {e}")
                time.sleep(5)  # Wait before retry
                
            except Exception as e:
                logger.error(f"Worker error: {e}")
                logger.error(traceback.format_exc())
                time.sleep(1)
        
        logger.info("Stats Worker stopped")


def main():
    """Entry point"""
    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    worker = StatsWorker()
    worker.run()


if __name__ == "__main__":
    main()
