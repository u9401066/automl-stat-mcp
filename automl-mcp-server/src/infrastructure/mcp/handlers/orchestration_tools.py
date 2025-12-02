"""
Smart Orchestration Tools for MCP

High-level convenience tools that combine multiple operations.
These provide better UX for AI Agents by reducing the number of calls needed.
"""
from typing import Annotated, Any, Dict, List, Literal, Optional
import time

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from ..client import AutoMLClient
from .base import wait_for_completion


def register_orchestration_tools(mcp: FastMCP, client: AutoMLClient) -> None:
    """Register smart orchestration tools"""

    @mcp.tool()
    async def wait_for_job(
        job_id: Annotated[str, Field(description="Job ID to wait for")],
        user_id: Annotated[str, Field(description="User ID")],
        poll_interval: Annotated[int, Field(description="Seconds between status checks")] = 10,
        timeout: Annotated[int, Field(description="Maximum seconds to wait (0 = no timeout)")] = 3600,
    ) -> Dict[str, Any]:
        """
        Wait for a training job to complete.
        
        This polls the job status until it reaches a terminal state
        (completed, failed, or cancelled) or times out.
        
        ⚠️ Use this for jobs expected to finish within the timeout.
        For very long training, use get_job_status manually.
        
        Returns:
            job_id: Job identifier
            status: Final status (completed/failed/cancelled/timeout)
            model_id: (if completed) The trained model ID
            result: (if completed) Training results with leaderboard
            error_message: (if failed) Error description
            elapsed_seconds: Time waited
        """
        async def check_status():
            return await client.get_job_status(job_id, user_id)
        
        result = await wait_for_completion(
            check_status=check_status,
            poll_interval=poll_interval,
            timeout=timeout,
        )
        result["job_id"] = job_id
        return result

    @mcp.tool()
    async def train_and_wait(
        dataset_id: Annotated[str, Field(description="Dataset ID to train on")],
        target_column: Annotated[str, Field(description="Name of the target/label column")],
        problem_type: Annotated[
            Literal["binary", "multiclass", "regression"],
            Field(description="Type of ML problem")
        ],
        user_id: Annotated[str, Field(description="User ID")],
        session_id: Annotated[Optional[str], Field(description="Optional session ID")] = None,
        time_limit: Annotated[int, Field(description="Training time limit in seconds")] = 300,
        presets: Annotated[
            Literal["best_quality", "high_quality", "good_quality", "medium_quality", "optimize_for_deployment"],
            Field(description="AutoGluon quality preset")
        ] = "medium_quality",
        wait_timeout: Annotated[int, Field(description="Max seconds to wait for completion")] = 3600,
    ) -> Dict[str, Any]:
        """
        🚀 One-shot AutoML: Submit training and wait for results.
        
        This is a convenience tool that:
        1. Submits an AutoML training job
        2. Waits for it to complete
        3. Returns the full results including model_id and leaderboard
        
        ⚠️ This call blocks until training completes or times out!
        For time_limit=300 (5 min), actual training may take 5-10 minutes.
        
        Returns:
            job_id: Job identifier
            status: "completed" | "failed" | "timeout"
            model_id: (if completed) Ready-to-use model ID
            result: (if completed) Full training results
                - best_model: Name of best model
                - best_score: Best validation score
                - leaderboard: All models ranked by score
            error_message: (if failed) What went wrong
            
        Next step (if completed):
            Use predict(model_id, test_dataset_id) to make predictions
        """
        start_time = time.time()
        
        # 1. Submit the job
        job = await client.submit_automl_job(
            dataset_id=dataset_id,
            target_column=target_column,
            problem_type=problem_type,
            user_id=user_id,
            session_id=session_id,
            time_limit=time_limit,
            presets=presets,
        )
        job_id = job["job_id"]
        
        # 2. Wait for completion
        async def check_status():
            return await client.get_job_status(job_id, user_id)
        
        result = await wait_for_completion(
            check_status=check_status,
            poll_interval=10,
            timeout=wait_timeout,
        )
        
        # 3. Enrich result
        result["job_id"] = job_id
        elapsed = time.time() - start_time
        
        if result["status"] == "completed":
            model_id = result.get("model_id")
            if model_id:
                try:
                    leaderboard = await client.get_model_leaderboard(model_id, user_id)
                    result["leaderboard"] = leaderboard
                except Exception:
                    pass
            result["summary"] = f"✅ Training completed in {round(elapsed/60, 1)} minutes. Best model: {result.get('result', {}).get('best_model', 'N/A')}"
        elif result["status"] == "failed":
            result["summary"] = f"❌ Training failed: {result.get('error_message', 'Unknown error')}"
        elif result["status"] == "timeout":
            result["summary"] = f"⏱️ Timeout after {round(elapsed/60, 1)} minutes. Use get_job_status('{job_id}') to check later."
        
        return result

    @mcp.tool()
    async def quick_train(
        minio_path: Annotated[str, Field(description="Path to CSV file in MinIO (e.g., 'bucket/data.csv')")],
        target_column: Annotated[str, Field(description="Name of the target/label column")],
        problem_type: Annotated[
            Literal["binary", "multiclass", "regression"],
            Field(description="Type of ML problem")
        ],
        user_id: Annotated[str, Field(description="User ID")],
        dataset_name: Annotated[Optional[str], Field(description="Name for the dataset (auto-generated if not provided)")] = None,
        time_limit: Annotated[int, Field(description="Training time limit in seconds")] = 300,
        wait_timeout: Annotated[int, Field(description="Max seconds to wait for completion")] = 3600,
    ) -> Dict[str, Any]:
        """
        🎯 Fastest path from data to model!
        
        This is the ultimate convenience tool that:
        1. Registers your dataset from MinIO
        2. Submits AutoML training
        3. Waits for completion
        4. Returns ready-to-use model
        
        Just provide your CSV path and target column!
        
        Returns:
            dataset_id: Registered dataset ID
            job_id: Training job ID
            model_id: (if completed) Ready-to-use model ID
            status: "completed" | "failed" | "timeout"
            result: Training results with leaderboard
            
        Example:
            quick_train(
                minio_path="my-bucket/sales_data.csv",
                target_column="revenue",
                problem_type="regression",
                user_id="user123"
            )
        """
        start_time = time.time()
        
        # 1. Register dataset
        if not dataset_name:
            dataset_name = minio_path.split("/")[-1].replace(".csv", "")
        
        dataset = await client.register_dataset(
            name=dataset_name,
            minio_path=minio_path,
            user_id=user_id,
        )
        dataset_id = dataset["dataset_id"]
        
        # 2. Submit training
        job = await client.submit_automl_job(
            dataset_id=dataset_id,
            target_column=target_column,
            problem_type=problem_type,
            user_id=user_id,
            time_limit=time_limit,
            presets="medium_quality",
        )
        job_id = job["job_id"]
        
        # 3. Wait for completion
        async def check_status():
            return await client.get_job_status(job_id, user_id)
        
        result = await wait_for_completion(
            check_status=check_status,
            poll_interval=10,
            timeout=wait_timeout,
        )
        
        elapsed = time.time() - start_time
        
        # 4. Build response
        response = {
            "dataset_id": dataset_id,
            "job_id": job_id,
            "status": result["status"],
            "elapsed_seconds": round(elapsed, 1),
        }
        
        if result["status"] == "completed":
            model_id = result.get("model_id")
            response["model_id"] = model_id
            response["result"] = result.get("result")
            
            if model_id:
                try:
                    leaderboard = await client.get_model_leaderboard(model_id, user_id)
                    response["leaderboard"] = leaderboard
                except Exception:
                    pass
            
            response["summary"] = f"✅ Model ready! Dataset '{dataset_name}' → Model '{model_id}' in {round(elapsed/60, 1)} min"
        elif result["status"] == "failed":
            response["error_message"] = result.get("error_message")
            response["summary"] = f"❌ Training failed: {result.get('error_message')}"
        else:
            response["summary"] = f"⏱️ Timeout. Use get_job_status('{job_id}') to check later."
        
        return response

    @mcp.tool()
    async def analyze_dataset(
        dataset_id: Annotated[str, Field(description="Dataset ID to analyze")],
        target_column: Annotated[str, Field(description="Target column for analysis")],
        user_id: Annotated[str, Field(description="User ID")],
    ) -> Dict[str, Any]:
        """
        📊 Analyze a dataset and get training recommendations.
        
        This tool examines your dataset and suggests:
        - Problem type (binary/multiclass/regression)
        - Recommended presets based on dataset size
        - Estimated training time
        - Potential issues (missing values, imbalance, etc.)
        
        Use this before training to optimize your settings!
        
        Returns:
            dataset_info: Basic dataset statistics
            target_analysis: Target column analysis
            recommended_problem_type: Suggested problem type
            recommended_presets: Suggested quality presets
            recommended_time_limit: Suggested training time
            warnings: Potential issues found
        """
        # Get dataset info
        datasets = await client.list_datasets(user_id)
        dataset = next((d for d in datasets if d["dataset_id"] == dataset_id), None)
        
        if not dataset:
            return {"error": f"Dataset {dataset_id} not found"}
        
        row_count = dataset.get("row_count", 0)
        columns = dataset.get("columns", [])
        
        if target_column not in columns:
            return {"error": f"Target column '{target_column}' not in dataset. Available: {columns}"}
        
        # Build recommendations based on dataset size
        recommendations = _get_recommendations(row_count, columns, target_column, dataset)
        return recommendations

    @mcp.tool()
    async def get_training_summary(
        user_id: Annotated[str, Field(description="User ID")],
        session_id: Annotated[Optional[str], Field(description="Optional session ID")] = None,
    ) -> Dict[str, Any]:
        """
        📋 Get a summary of all your AutoML resources.
        
        Shows:
        - All datasets with their info
        - All jobs with their status
        - All models with their performance
        
        Great for getting an overview of your ML workspace!
        """
        datasets = await client.list_datasets(user_id, session_id)
        jobs = await client.list_jobs(user_id, session_id)
        models = await client.list_models(user_id, session_id)
        
        # Categorize jobs
        pending_jobs = [j for j in jobs if j["status"] == "pending"]
        running_jobs = [j for j in jobs if j["status"] == "running"]
        completed_jobs = [j for j in jobs if j["status"] == "completed"]
        failed_jobs = [j for j in jobs if j["status"] == "failed"]
        
        return {
            "summary": {
                "total_datasets": len(datasets),
                "total_jobs": len(jobs),
                "total_models": len(models),
                "jobs_pending": len(pending_jobs),
                "jobs_running": len(running_jobs),
                "jobs_completed": len(completed_jobs),
                "jobs_failed": len(failed_jobs),
            },
            "datasets": [
                {"id": d["dataset_id"], "name": d["name"], "rows": d.get("row_count")}
                for d in datasets
            ],
            "active_jobs": [
                {"id": j["job_id"], "type": j["job_type"], "status": j["status"], "progress": j.get("progress")}
                for j in (pending_jobs + running_jobs)
            ],
            "recent_models": [
                {"id": m["model_id"], "name": m.get("name"), "best_model": m.get("best_model_name"), "score": m.get("best_score")}
                for m in models[:5]
            ],
            "tips": [
                "Use quick_train() for fastest path from data to model",
                "Use analyze_dataset() before training to optimize settings",
                "Use train_and_wait() for full control with blocking wait",
            ],
        }


def _get_recommendations(row_count: int, columns: list, target_column: str, dataset: dict) -> dict:
    """Generate training recommendations based on dataset characteristics"""
    recommendations = {
        "dataset_info": {
            "name": dataset.get("name"),
            "rows": row_count,
            "columns": len(columns),
            "features": [c for c in columns if c != target_column],
            "target": target_column,
        },
        "recommendations": {},
        "warnings": [],
    }
    
    # Recommend presets based on size
    if row_count < 1000:
        recommendations["recommendations"]["presets"] = "best_quality"
        recommendations["recommendations"]["time_limit"] = 300
        recommendations["recommendations"]["reason"] = "Small dataset - can afford thorough search"
    elif row_count < 10000:
        recommendations["recommendations"]["presets"] = "high_quality"
        recommendations["recommendations"]["time_limit"] = 600
        recommendations["recommendations"]["reason"] = "Medium dataset - balanced approach"
    elif row_count < 100000:
        recommendations["recommendations"]["presets"] = "good_quality"
        recommendations["recommendations"]["time_limit"] = 900
        recommendations["recommendations"]["reason"] = "Large dataset - optimize for speed"
    else:
        recommendations["recommendations"]["presets"] = "medium_quality"
        recommendations["recommendations"]["time_limit"] = 1200
        recommendations["recommendations"]["reason"] = "Very large dataset - faster presets recommended"
        recommendations["warnings"].append("Large dataset may require significant training time")
    
    # Check for few features
    if len(columns) < 3:
        recommendations["warnings"].append("Very few features - model may have limited performance")
    
    # Estimate
    time_limit = recommendations["recommendations"]["time_limit"]
    recommendations["estimated_training_time"] = f"{time_limit // 60}-{time_limit * 2 // 60} minutes"
    recommendations["next_step"] = f"Run: train_and_wait(dataset_id='{dataset.get('dataset_id')}', target_column='{target_column}', problem_type='<your_type>', ...)"
    
    return recommendations
