"""
Stats Worker - Main Worker Process

Processes statistical analysis jobs from Redis queue:
- EDA reports using ydata-profiling
- Table 1 using tableone
- Auto-analyze: intelligent statistical analysis
- ROC/PR analysis with visualizations
- Survival analysis with Kaplan-Meier and Cox regression
"""
import json
import logging
import math
import os
import signal
import time
import traceback
from datetime import datetime
from io import BytesIO
from pathlib import Path

import numpy as np
import pandas as pd
import redis
from minio import Minio

from .config import (
    MINIO_ACCESS_KEY,
    MINIO_DATASET_BUCKET,
    MINIO_ENDPOINT,
    MINIO_REPORTS_BUCKET,
    MINIO_SECRET_KEY,
    MINIO_SECURE,
    REDIS_DB,
    REDIS_HOST,
    REDIS_JOB_TTL,
    REDIS_PORT,
    STATS_JOBS_PENDING,
    STATS_JOBS_PREFIX,
    TEMP_DIR,
    WORKER_POLL_INTERVAL,
)

# Configure logging
log_level = os.environ.get("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def sanitize_for_json(obj):
    """
    Recursively sanitize object for JSON serialization.
    Handles NaN, Infinity, -Infinity which are not valid JSON.
    """
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_json(item) for item in obj]
    elif isinstance(obj, tuple):
        return [sanitize_for_json(item) for item in obj]
    elif isinstance(obj, float):
        if math.isnan(obj):
            return None
        elif math.isinf(obj):
            return "Infinity" if obj > 0 else "-Infinity"
        return obj
    elif isinstance(obj, (np.floating, np.integer)):
        if np.isnan(obj):
            return None
        elif np.isinf(obj):
            return "Infinity" if obj > 0 else "-Infinity"
        return float(obj) if isinstance(obj, np.floating) else int(obj)
    elif isinstance(obj, np.ndarray):
        return sanitize_for_json(obj.tolist())
    elif isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    elif pd.isna(obj):
        return None
    return obj

# Global flag for graceful shutdown
running = True


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    global running
    logger.info(f"Received signal {signum}, shutting down...")
    running = False


class StatsWorker:
    """Worker for processing statistical analysis jobs.

    All results are stored in:
    - Redis (temp storage with TTL) for job status and quick results
    - MinIO (permanent storage) for reports and visualizations
    """

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
        """Update job status in Redis with TTL"""
        key = f"{STATS_JOBS_PREFIX}{job_id}"
        data = self.redis_client.get(key)

        if data:
            job = json.loads(data)
            job["status"] = status
            job["updated_at"] = datetime.utcnow().isoformat()
            job.update(kwargs)
            # Set with TTL - job data expires after 24 hours
            self.redis_client.setex(key, REDIS_JOB_TTL, json.dumps(job))

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
            raise FileNotFoundError(f"Dataset not found at {minio_path}") from e

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

            raise FileNotFoundError(f"Dataset {dataset_id} not found in MinIO") from e

    def save_report(self, job_id: str, report_data: dict, format: str = "json") -> str:
        """Save report to MinIO"""
        if format == "json":
            # Sanitize data to handle NaN, Infinity values
            sanitized_data = sanitize_for_json(report_data)
            content = json.dumps(sanitized_data, indent=2, default=str)
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

    # =========================================================================
    # Propensity Score Analysis Jobs
    # =========================================================================

    def process_propensity_estimate_job(self, job: dict):
        """Process propensity score estimation job"""
        from .tasks.propensity_score import estimate_propensity_scores

        job_id = job["job_id"]
        params = job["params"]

        logger.info(f"Processing propensity estimate job {job_id}")
        self.update_job_status(job_id, "running", progress=0.1, message="Loading dataset...")

        df = self._load_dataset_from_job(job)

        self.update_job_status(job_id, "running", progress=0.4, message="Estimating propensity scores...")

        result = estimate_propensity_scores(
            df=df,
            treatment_col=params["treatment_col"],
            covariates=params["covariates"],
            regularization=params.get("regularization", 0.0),
        )

        self.update_job_status(job_id, "running", progress=0.8, message="Saving results...")

        result_path = self.save_report(job_id, result.to_dict() if hasattr(result, 'to_dict') else result, format="json")

        self.update_job_status(job_id, "completed", progress=1.0, message="Propensity score estimation completed", result_path=result_path)
        logger.info(f"Propensity estimate job {job_id} completed")

    def process_propensity_match_job(self, job: dict):
        """Process propensity score matching job"""
        from .tasks.propensity_score import match_propensity_scores

        job_id = job["job_id"]
        params = job["params"]

        logger.info(f"Processing propensity match job {job_id}")
        self.update_job_status(job_id, "running", progress=0.1, message="Loading dataset...")

        df = self._load_dataset_from_job(job)

        self.update_job_status(job_id, "running", progress=0.4, message="Matching propensity scores...")

        result = match_propensity_scores(
            df=df,
            treatment_col=params["treatment_col"],
            score_col=params.get("score_col"),
            covariates=params.get("covariates"),
            method=params.get("method", "nearest"),
            caliper=params.get("caliper", 0.2),
            caliper_scale=params.get("caliper_scale", "std"),
            replacement=params.get("replacement", False),
        )

        self.update_job_status(job_id, "running", progress=0.8, message="Saving results...")

        result_path = self.save_report(job_id, result.to_dict() if hasattr(result, 'to_dict') else result, format="json")

        self.update_job_status(job_id, "completed", progress=1.0, message="Propensity score matching completed", result_path=result_path)
        logger.info(f"Propensity match job {job_id} completed")

    def process_propensity_effect_job(self, job: dict):
        """Process treatment effect estimation job"""
        from .tasks.propensity_score import estimate_treatment_effect

        job_id = job["job_id"]
        params = job["params"]

        logger.info(f"Processing propensity effect job {job_id}")
        self.update_job_status(job_id, "running", progress=0.1, message="Loading dataset...")

        df = self._load_dataset_from_job(job)

        self.update_job_status(job_id, "running", progress=0.4, message="Estimating treatment effect...")

        result = estimate_treatment_effect(
            df=df,
            outcome_col=params["outcome_col"],
            treatment_col=params["treatment_col"],
            score_col=params.get("score_col"),
            covariates=params.get("covariates"),
            method=params.get("method", "ipw"),
            target=params.get("target", "ate"),
            stabilized=params.get("stabilized", True),
        )

        self.update_job_status(job_id, "running", progress=0.8, message="Saving results...")

        result_path = self.save_report(job_id, result.to_dict() if hasattr(result, 'to_dict') else result, format="json")

        self.update_job_status(job_id, "completed", progress=1.0, message="Treatment effect estimation completed", result_path=result_path)
        logger.info(f"Propensity effect job {job_id} completed")

    def process_propensity_balance_job(self, job: dict):
        """Process covariate balance assessment job"""
        from .tasks.propensity_score import assess_balance

        job_id = job["job_id"]
        params = job["params"]

        logger.info(f"Processing propensity balance job {job_id}")
        self.update_job_status(job_id, "running", progress=0.1, message="Loading dataset...")

        df = self._load_dataset_from_job(job)

        self.update_job_status(job_id, "running", progress=0.4, message="Assessing covariate balance...")

        weights = np.array(params["weights"]) if params.get("weights") else None

        result = assess_balance(
            df=df,
            treatment_col=params["treatment_col"],
            covariates=params["covariates"],
            weights=weights,
            smd_threshold=params.get("smd_threshold", 0.1),
        )

        self.update_job_status(job_id, "running", progress=0.8, message="Saving results...")

        result_path = self.save_report(job_id, result.to_dict() if hasattr(result, 'to_dict') else result, format="json")

        self.update_job_status(job_id, "completed", progress=1.0, message="Balance assessment completed", result_path=result_path)
        logger.info(f"Propensity balance job {job_id} completed")

    def process_propensity_full_job(self, job: dict):
        """Process complete propensity score analysis job"""
        from .tasks.propensity_score import propensity_score_analysis

        job_id = job["job_id"]
        params = job["params"]

        logger.info(f"Processing propensity full analysis job {job_id}")
        self.update_job_status(job_id, "running", progress=0.1, message="Loading dataset...")

        df = self._load_dataset_from_job(job)

        self.update_job_status(job_id, "running", progress=0.3, message="Running full propensity score analysis...")

        result = propensity_score_analysis(
            df=df,
            outcome_col=params["outcome_col"],
            treatment_col=params["treatment_col"],
            covariates=params["covariates"],
            method=params.get("method", "matching"),
            target=params.get("target", "ate"),
            caliper=params.get("caliper", 0.2),
        )

        self.update_job_status(job_id, "running", progress=0.8, message="Saving results...")

        result_path = self.save_report(job_id, result if isinstance(result, dict) else result.to_dict(), format="json")

        self.update_job_status(job_id, "completed", progress=1.0, message="Propensity score analysis completed", result_path=result_path)
        logger.info(f"Propensity full job {job_id} completed")

    # =========================================================================
    # Survival Analysis Jobs
    # =========================================================================

    def process_kaplan_meier_job(self, job: dict):
        """Process Kaplan-Meier survival analysis job with visualization support"""
        from .tasks.survival_analysis import kaplan_meier_analysis, survival_summary

        job_id = job["job_id"]
        params = job["params"]
        user_id = job.get("user_id") or params.get("user_id", "anonymous")

        logger.info(f"Processing Kaplan-Meier job {job_id}")
        self.update_job_status(job_id, "running", progress=0.1, message="Loading dataset...")

        df = self._load_dataset_from_job(job)

        self.update_job_status(job_id, "running", progress=0.4, message="Computing Kaplan-Meier curves...")

        # Check if visualizations are requested (default True for MCP calls)
        generate_visualizations = params.get("generate_visualizations", True)

        km_result = kaplan_meier_analysis(
            df=df,
            time_col=params["time_col"],
            event_col=params["event_col"],
            group_col=params.get("group_col"),
            alpha=params.get("alpha", 0.05),
            generate_visualizations=generate_visualizations,
            user_id=user_id,
            job_id=job_id,
        )

        summary = survival_summary(
            df=df,
            time_col=params["time_col"],
            event_col=params["event_col"],
            group_col=params.get("group_col"),
            time_points=params.get("time_points"),
        )

        result = {
            "status": "success",
            **km_result,
            "summary": summary,
        }

        self.update_job_status(job_id, "running", progress=0.8, message="Saving results...")

        result_path = self.save_report(job_id, result, format="json")

        self.update_job_status(job_id, "completed", progress=1.0, message="Kaplan-Meier analysis completed", result_path=result_path)
        logger.info(f"Kaplan-Meier job {job_id} completed")

    def process_cox_regression_job(self, job: dict):
        """Process Cox proportional hazards regression job with visualization support"""
        from .tasks.survival_analysis import cox_regression

        job_id = job["job_id"]
        params = job["params"]
        user_id = job.get("user_id") or params.get("user_id", "anonymous")

        logger.info(f"Processing Cox regression job {job_id}")
        self.update_job_status(job_id, "running", progress=0.1, message="Loading dataset...")

        df = self._load_dataset_from_job(job)

        self.update_job_status(job_id, "running", progress=0.4, message="Fitting Cox model...")

        # Check if visualizations are requested (default True for MCP calls)
        generate_visualizations = params.get("generate_visualizations", True)

        result = cox_regression(
            df=df,
            time_col=params["time_col"],
            event_col=params["event_col"],
            covariates=params.get("covariates"),
            alpha=params.get("alpha", 0.05),
            generate_visualizations=generate_visualizations,
            user_id=user_id,
            job_id=job_id,
        )

        self.update_job_status(job_id, "running", progress=0.8, message="Saving results...")

        result_path = self.save_report(job_id, {"status": "success", **result}, format="json")

        self.update_job_status(job_id, "completed", progress=1.0, message="Cox regression completed", result_path=result_path)
        logger.info(f"Cox regression job {job_id} completed")

    def process_survival_compare_job(self, job: dict):
        """Process survival curves comparison job with visualization support"""
        from .tasks.survival_analysis import compare_survival_curves

        job_id = job["job_id"]
        params = job["params"]
        user_id = job.get("user_id") or params.get("user_id", "anonymous")

        logger.info(f"Processing survival compare job {job_id}")
        self.update_job_status(job_id, "running", progress=0.1, message="Loading dataset...")

        df = self._load_dataset_from_job(job)

        self.update_job_status(job_id, "running", progress=0.4, message="Comparing survival curves...")

        # Check if visualizations are requested (default True for MCP calls)
        generate_visualizations = params.get("generate_visualizations", True)

        result = compare_survival_curves(
            df=df,
            time_col=params["time_col"],
            event_col=params["event_col"],
            group_col=params["group_col"],
            generate_visualizations=generate_visualizations,
            user_id=user_id,
            job_id=job_id,
        )

        self.update_job_status(job_id, "running", progress=0.8, message="Saving results...")

        result_path = self.save_report(job_id, {"status": "success", **result}, format="json")

        self.update_job_status(job_id, "completed", progress=1.0, message="Survival comparison completed", result_path=result_path)
        logger.info(f"Survival compare job {job_id} completed")

    def process_survival_summary_job(self, job: dict):
        """Process survival data summary job"""
        from .tasks.survival_analysis import survival_summary

        job_id = job["job_id"]
        params = job["params"]

        logger.info(f"Processing survival summary job {job_id}")
        self.update_job_status(job_id, "running", progress=0.1, message="Loading dataset...")

        df = self._load_dataset_from_job(job)

        self.update_job_status(job_id, "running", progress=0.4, message="Summarizing survival data...")

        result = survival_summary(
            df=df,
            time_col=params["time_col"],
            event_col=params["event_col"],
            group_col=params.get("group_col"),
            time_points=params.get("time_points"),
        )

        self.update_job_status(job_id, "running", progress=0.8, message="Saving results...")

        result_path = self.save_report(job_id, {"status": "success", **result}, format="json")

        self.update_job_status(job_id, "completed", progress=1.0, message="Survival summary completed", result_path=result_path)
        logger.info(f"Survival summary job {job_id} completed")

    # =========================================================================
    # ROC Analysis Jobs
    # =========================================================================

    def process_roc_compute_job(self, job: dict):
        """Process ROC curve computation job with visualization support"""
        from .tasks.roc_analysis import compute_roc_curve

        job_id = job["job_id"]
        params = job["params"]
        user_id = job.get("user_id") or params.get("user_id", "anonymous")

        logger.info(f"Processing ROC compute job {job_id}")
        self.update_job_status(job_id, "running", progress=0.1, message="Loading dataset...")

        df = self._load_dataset_from_job(job)

        self.update_job_status(job_id, "running", progress=0.4, message="Computing ROC curve...")

        y_true = df[params["y_true_col"]].values
        y_scores = df[params["y_score_col"]].values

        # Convert confidence_level to alpha (e.g., 0.95 -> 0.05)
        confidence_level = params.get("confidence_level", 0.95)
        alpha = 1.0 - confidence_level

        # Check if visualizations are requested (default True for MCP calls)
        generate_visualizations = params.get("generate_visualizations", True)

        result = compute_roc_curve(
            y_true=y_true,
            y_scores=y_scores,
            threshold_method=params.get("threshold_method", "youden"),
            alpha=alpha,
            generate_visualizations=generate_visualizations,
            user_id=user_id,
            job_id=job_id,
            model_name=params.get("model_name", "Model"),
        )

        self.update_job_status(job_id, "running", progress=0.8, message="Saving results...")

        result_path = self.save_report(job_id, result, format="json")

        self.update_job_status(job_id, "completed", progress=1.0, message="ROC curve computed", result_path=result_path)
        logger.info(f"ROC compute job {job_id} completed")

    def process_roc_compare_job(self, job: dict):
        """Process ROC curves comparison job (two models) with visualization support"""
        from .tasks.roc_analysis import compare_roc_curves

        job_id = job["job_id"]
        params = job["params"]
        user_id = job.get("user_id") or params.get("user_id", "anonymous")

        logger.info(f"Processing ROC compare job {job_id}")
        self.update_job_status(job_id, "running", progress=0.1, message="Loading dataset...")

        df = self._load_dataset_from_job(job)

        self.update_job_status(job_id, "running", progress=0.4, message="Comparing ROC curves...")

        y_true = df[params["y_true_col"]].values
        model_score_cols = params["model_score_cols"]
        model_names = params.get("model_names") or model_score_cols

        # compare_roc_curves takes two models at a time
        if len(model_score_cols) != 2:
            raise ValueError("compare_roc_curves requires exactly 2 models. Use compare_multiple_models for 3+ models.")

        scores1 = df[model_score_cols[0]].values
        scores2 = df[model_score_cols[1]].values

        # Check if visualizations are requested (default True for MCP calls)
        generate_visualizations = params.get("generate_visualizations", True)

        result = compare_roc_curves(
            y_true=y_true,
            scores1=scores1,
            scores2=scores2,
            model1_name=model_names[0],
            model2_name=model_names[1],
            alpha=params.get("alpha", 0.05),
            generate_visualizations=generate_visualizations,
            user_id=user_id,
            job_id=job_id,
        )

        self.update_job_status(job_id, "running", progress=0.8, message="Saving results...")

        result_path = self.save_report(job_id, result, format="json")

        self.update_job_status(job_id, "completed", progress=1.0, message="ROC comparison completed", result_path=result_path)
        logger.info(f"ROC compare job {job_id} completed")

    def process_roc_threshold_job(self, job: dict):
        """Process optimal threshold finding job"""
        from .tasks.roc_analysis import find_optimal_threshold

        job_id = job["job_id"]
        params = job["params"]

        logger.info(f"Processing ROC threshold job {job_id}")
        self.update_job_status(job_id, "running", progress=0.1, message="Loading dataset...")

        df = self._load_dataset_from_job(job)

        self.update_job_status(job_id, "running", progress=0.4, message="Finding optimal threshold...")

        y_true = df[params["y_true_col"]].values
        y_scores = df[params["y_score_col"]].values

        # Map target_sensitivity/target_specificity to target_metric/target_value
        method = params.get("method", "youden")
        target_metric = None
        target_value = None

        if params.get("target_sensitivity"):
            method = "target_sensitivity"
            target_metric = "sensitivity"
            target_value = params["target_sensitivity"]
        elif params.get("target_specificity"):
            method = "target_specificity"
            target_metric = "specificity"
            target_value = params["target_specificity"]

        result = find_optimal_threshold(
            y_true=y_true,
            y_scores=y_scores,
            method=method,
            target_metric=target_metric,
            target_value=target_value,
        )

        self.update_job_status(job_id, "running", progress=0.8, message="Saving results...")

        result_path = self.save_report(job_id, result, format="json")

        self.update_job_status(job_id, "completed", progress=1.0, message="Threshold analysis completed", result_path=result_path)
        logger.info(f"ROC threshold job {job_id} completed")

    def process_roc_calibration_job(self, job: dict):
        """Process calibration analysis job"""
        from .tasks.roc_analysis import analyze_calibration

        job_id = job["job_id"]
        params = job["params"]

        logger.info(f"Processing ROC calibration job {job_id}")
        self.update_job_status(job_id, "running", progress=0.1, message="Loading dataset...")

        df = self._load_dataset_from_job(job)

        self.update_job_status(job_id, "running", progress=0.4, message="Analyzing calibration...")

        y_true = df[params["y_true_col"]].values
        y_prob = df[params["y_score_col"]].values

        result = analyze_calibration(
            y_true=y_true,
            y_prob=y_prob,
            n_bins=params.get("n_bins", 10),
        )

        self.update_job_status(job_id, "running", progress=0.8, message="Saving results...")

        result_path = self.save_report(job_id, result, format="json")

        self.update_job_status(job_id, "completed", progress=1.0, message="Calibration analysis completed", result_path=result_path)
        logger.info(f"ROC calibration job {job_id} completed")

    def process_roc_full_eval_job(self, job: dict):
        """Process full classifier evaluation job - results to MinIO only"""
        from .tasks.roc_analysis import full_classifier_evaluation

        job_id = job["job_id"]
        params = job["params"]
        user_id = job.get("user_id") or params.get("user_id", "anonymous")

        logger.info(f"Processing ROC full eval job {job_id}")
        self.update_job_status(job_id, "running", progress=0.1, message="Loading dataset...")

        df = self._load_dataset_from_job(job)

        self.update_job_status(job_id, "running", progress=0.3, message="Running full classifier evaluation...")

        y_true = df[params["y_true_col"]].values
        y_scores = df[params["y_score_col"]].values

        # Run evaluation with visualizations
        result = full_classifier_evaluation(
            y_true=y_true,
            y_scores=y_scores,
            model_name=params.get("model_name", "Model"),
            generate_visualizations=params.get("generate_visualizations", True),
            user_id=user_id,
            job_id=job_id,
        )

        self.update_job_status(job_id, "running", progress=0.8, message="Saving results to MinIO...")

        # Save to MinIO (permanent storage)
        result_path = self.save_report(job_id, result, format="json")

        self.update_job_status(
            job_id, "completed",
            progress=1.0,
            message="Full evaluation completed",
            result_path=result_path,
        )
        logger.info(f"ROC full eval job {job_id} completed, results saved to MinIO: {result_path}")

    def process_roc_compare_multiple_job(self, job: dict):
        """Process multiple models comparison job"""
        from .tasks.roc_analysis import compare_multiple_models

        job_id = job["job_id"]
        params = job["params"]

        logger.info(f"Processing ROC compare multiple job {job_id}")
        self.update_job_status(job_id, "running", progress=0.1, message="Loading dataset...")

        df = self._load_dataset_from_job(job)

        self.update_job_status(job_id, "running", progress=0.4, message="Comparing multiple models...")

        y_true = df[params["y_true_col"]].values
        model_columns = params["model_columns"]
        models = {name: df[col].values for name, col in model_columns.items()}

        result = compare_multiple_models(
            y_true=y_true,
            models=models,
            correction=params.get("correction", "bonferroni"),
            alpha=params.get("alpha", 0.05),
        )

        self.update_job_status(job_id, "running", progress=0.8, message="Saving results...")

        result_path = self.save_report(job_id, result, format="json")

        self.update_job_status(job_id, "completed", progress=1.0, message="Multi-model comparison completed", result_path=result_path)
        logger.info(f"ROC compare multiple job {job_id} completed")

    def process_roc_threshold_analysis_job(self, job: dict):
        """Process interactive threshold analysis job"""
        from .tasks.roc_analysis import threshold_analysis

        job_id = job["job_id"]
        params = job["params"]

        logger.info(f"Processing ROC threshold analysis job {job_id}")
        self.update_job_status(job_id, "running", progress=0.1, message="Loading dataset...")

        df = self._load_dataset_from_job(job)

        self.update_job_status(job_id, "running", progress=0.4, message="Analyzing thresholds...")

        y_true = df[params["y_true_col"]].values
        y_scores = df[params["y_score_col"]].values

        result = threshold_analysis(
            y_true=y_true,
            y_scores=y_scores,
            target_metric=params.get("target_metric"),
            target_value=params.get("target_value"),
            n_thresholds=params.get("n_thresholds", 21),
        )

        self.update_job_status(job_id, "running", progress=0.8, message="Saving results...")

        result_path = self.save_report(job_id, result, format="json")

        self.update_job_status(job_id, "completed", progress=1.0, message="Threshold analysis completed", result_path=result_path)
        logger.info(f"ROC threshold analysis job {job_id} completed")

    def process_roc_publication_report_job(self, job: dict):
        """Process publication report generation job"""
        from .tasks.roc_analysis import generate_publication_report

        job_id = job["job_id"]
        params = job["params"]

        logger.info(f"Processing ROC publication report job {job_id}")
        self.update_job_status(job_id, "running", progress=0.1, message="Loading dataset...")

        df = self._load_dataset_from_job(job)

        self.update_job_status(job_id, "running", progress=0.4, message="Generating publication report...")

        y_true = df[params["y_true_col"]].values
        y_scores = df[params["y_score_col"]].values

        result = generate_publication_report(
            y_true=y_true,
            y_scores=y_scores,
            model_name=params.get("model_name", "The prediction model"),
            outcome_name=params.get("outcome_name", "the outcome"),
            threshold_method=params.get("threshold_method", "youden"),
            decimal_places=params.get("decimal_places", 2),
        )

        self.update_job_status(job_id, "running", progress=0.8, message="Saving results...")

        result_path = self.save_report(job_id, result, format="json")

        self.update_job_status(job_id, "completed", progress=1.0, message="Publication report generated", result_path=result_path)
        logger.info(f"ROC publication report job {job_id} completed")

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _load_dataset_from_job(self, job: dict) -> pd.DataFrame:
        """Load dataset from job - handles CSV content or MinIO path"""
        params = job.get("params", {})

        # Check for direct CSV content first
        csv_content = params.get("csv_content")
        if csv_content:
            return pd.read_csv(BytesIO(csv_content.encode('utf-8')))

        # Then check for MinIO path
        minio_path = job.get("minio_path") or params.get("minio_path")
        if minio_path:
            return self.load_dataset_by_path(minio_path)

        # Finally check for dataset_id
        dataset_id = job.get("dataset_id") or params.get("dataset_id")
        if dataset_id:
            return self.load_dataset(dataset_id)

        raise ValueError("No csv_content, minio_path, or dataset_id provided")

    def process_job(self, job: dict):
        """Process a single job"""
        job_type = job.get("job_type")
        job_id = job.get("job_id")

        try:
            # Core analysis jobs
            if job_type == "eda":
                self.process_eda_job(job)
            elif job_type == "tableone":
                self.process_tableone_job(job)
            elif job_type == "auto_analyze":
                self.process_auto_analyze_job(job)
            elif job_type == "auto_analyze_direct":
                self.process_auto_analyze_direct_job(job)

            # Propensity score analysis jobs
            elif job_type == "propensity_estimate":
                self.process_propensity_estimate_job(job)
            elif job_type == "propensity_match":
                self.process_propensity_match_job(job)
            elif job_type == "propensity_effect":
                self.process_propensity_effect_job(job)
            elif job_type == "propensity_balance":
                self.process_propensity_balance_job(job)
            elif job_type == "propensity_full":
                self.process_propensity_full_job(job)

            # Survival analysis jobs
            elif job_type == "kaplan_meier":
                self.process_kaplan_meier_job(job)
            elif job_type == "cox_regression":
                self.process_cox_regression_job(job)
            elif job_type == "survival_compare":
                self.process_survival_compare_job(job)
            elif job_type == "survival_summary":
                self.process_survival_summary_job(job)

            # ROC analysis jobs
            elif job_type == "roc_compute":
                self.process_roc_compute_job(job)
            elif job_type == "roc_compare":
                self.process_roc_compare_job(job)
            elif job_type == "roc_threshold":
                self.process_roc_threshold_job(job)
            elif job_type == "roc_calibration":
                self.process_roc_calibration_job(job)
            elif job_type == "roc_full_eval":
                self.process_roc_full_eval_job(job)
            elif job_type == "roc_compare_multiple":
                self.process_roc_compare_multiple_job(job)
            elif job_type == "roc_threshold_analysis":
                self.process_roc_threshold_analysis_job(job)
            elif job_type == "roc_publication_report":
                self.process_roc_publication_report_job(job)

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
