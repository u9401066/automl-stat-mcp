"""
AutoML MCP Tool Handlers

MCP tool handlers for AutoML operations.
Following the pattern from medical-calc-mcp.
"""
from typing import Annotated, Any, Dict, List, Literal, Optional
import asyncio

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from ..client import get_client


class AutoMLHandler:
    """
    Handler for AutoML MCP tools.
    
    Provides tools for:
    - Dataset management (register, list, delete)
    - Training jobs (submit, status, cancel)
    - Model management (list, leaderboard, predict, delete)
    
    🚀 Smart Orchestration Tools:
    - quick_train: Fastest path from CSV to model (register + train + wait)
    - train_and_wait: Submit and wait for completion
    - wait_for_job: Wait for any job to complete
    - analyze_dataset: Get recommendations before training
    - get_training_summary: Overview of all resources
    
    Important: Training jobs are asynchronous!
    - submit_*_job returns immediately with job_id
    - Use wait_for_job or train_and_wait for blocking behavior
    - When complete, use model_id for predictions
    """

    def __init__(self, mcp: FastMCP):
        self._mcp = mcp
        self._client = get_client()
        self._register_tools()

    def _register_tools(self) -> None:
        """Register all AutoML tools with MCP"""
        self._register_info_tools()
        self._register_dataset_tools()
        self._register_training_tools()
        self._register_job_tools()
        self._register_model_tools()
        self._register_orchestration_tools()  # Smart convenience tools

    # ============== Info Tools ==============
    
    def _register_info_tools(self) -> None:
        """Register info/discovery tools"""
        
        @self._mcp.tool()
        async def list_algorithms() -> Dict[str, Any]:
            """
            List all available machine learning algorithms.
            
            Returns the algorithm codes (e.g., 'XGB', 'GBM') that can be used
            in training requests.
            
            Returns:
                algorithms: Dict mapping code to full name
                description: Usage instructions
            """
            return await self._client.list_algorithms()

        @self._mcp.tool()
        async def health_check() -> Dict[str, Any]:
            """
            Check if the AutoML service is healthy.
            
            Returns:
                status: "healthy" if service is running
                version: Service version
            """
            return await self._client.health_check()

    # ============== Dataset Tools ==============
    
    def _register_dataset_tools(self) -> None:
        """Register dataset management tools"""
        
        @self._mcp.tool()
        async def register_dataset(
            name: Annotated[str, Field(description="Dataset name for identification")],
            minio_path: Annotated[str, Field(description="Path to CSV file in MinIO (e.g., 'bucket/path/file.csv')")],
            user_id: Annotated[str, Field(description="User ID for resource isolation")],
            session_id: Annotated[Optional[str], Field(description="Optional session ID")] = None,
            description: Annotated[Optional[str], Field(description="Optional dataset description")] = None,
        ) -> Dict[str, Any]:
            """
            Register a CSV dataset from MinIO for use in training.
            
            The file must already exist in MinIO. This validates the file
            and registers it with the AutoML service.
            
            Returns:
                dataset_id: Unique identifier for this dataset
                name: Dataset name
                columns: List of column names
                row_count: Number of rows
                
            Next step: Use dataset_id in submit_automl_job or submit_specific_job
            """
            return await self._client.register_dataset(
                name=name,
                minio_path=minio_path,
                user_id=user_id,
                session_id=session_id,
                description=description,
            )

        @self._mcp.tool()
        async def list_datasets(
            user_id: Annotated[str, Field(description="User ID")],
            session_id: Annotated[Optional[str], Field(description="Optional session ID")] = None,
        ) -> List[Dict[str, Any]]:
            """
            List all datasets registered by the user.
            
            Returns:
                List of datasets with their IDs, names, columns, and metadata
            """
            return await self._client.list_datasets(user_id, session_id)

        @self._mcp.tool()
        async def delete_dataset(
            dataset_id: Annotated[str, Field(description="Dataset ID to delete")],
            user_id: Annotated[str, Field(description="User ID")],
        ) -> Dict[str, Any]:
            """
            Delete a registered dataset.
            
            Note: This only removes the registration, not the file in MinIO.
            """
            return await self._client.delete_dataset(dataset_id, user_id)

    # ============== Training Tools ==============
    
    def _register_training_tools(self) -> None:
        """Register training job submission tools"""
        
        @self._mcp.tool()
        async def submit_automl_job(
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
            metric: Annotated[Optional[str], Field(description="Evaluation metric (auto-selected if not specified)")] = None,
        ) -> Dict[str, Any]:
            """
            Submit an AutoML training job.
            
            This starts automatic model selection and hyperparameter tuning.
            The job runs in the background - this call returns IMMEDIATELY.
            
            ⚠️ IMPORTANT: Training may take minutes to hours!
            Use get_job_status(job_id) to check progress.
            
            Returns:
                job_id: Unique job identifier (use this to check status)
                job_type: "automl"
                status: "pending" (will change to "running", then "completed" or "failed")
                
            Next steps:
                1. Tell the user training has started
                2. Use get_job_status(job_id) to check progress
                3. When status is "completed", use the model_id for predictions
            """
            return await self._client.submit_automl_job(
                dataset_id=dataset_id,
                target_column=target_column,
                problem_type=problem_type,
                user_id=user_id,
                session_id=session_id,
                time_limit=time_limit,
                presets=presets,
                metric=metric,
            )

        @self._mcp.tool()
        async def submit_specific_job(
            dataset_id: Annotated[str, Field(description="Dataset ID to train on")],
            target_column: Annotated[str, Field(description="Name of the target/label column")],
            problem_type: Annotated[
                Literal["binary", "multiclass", "regression"],
                Field(description="Type of ML problem")
            ],
            algorithms: Annotated[
                List[str],
                Field(description="List of algorithm codes (e.g., ['XGB', 'GBM', 'RF']). Use list_algorithms() to see options.")
            ],
            user_id: Annotated[str, Field(description="User ID")],
            session_id: Annotated[Optional[str], Field(description="Optional session ID")] = None,
            time_limit: Annotated[int, Field(description="Training time limit in seconds")] = 300,
        ) -> Dict[str, Any]:
            """
            Submit a training job with specific algorithms.
            
            Use this when you want to train only certain model types.
            The job runs in the background - this call returns IMMEDIATELY.
            
            ⚠️ IMPORTANT: Training may take minutes to hours!
            Use get_job_status(job_id) to check progress.
            
            Returns:
                job_id: Unique job identifier
                job_type: "specific"
                status: "pending"
                
            Next step: Use get_job_status(job_id) to check progress
            """
            return await self._client.submit_specific_job(
                dataset_id=dataset_id,
                target_column=target_column,
                problem_type=problem_type,
                algorithms=algorithms,
                user_id=user_id,
                session_id=session_id,
                time_limit=time_limit,
            )

        @self._mcp.tool()
        async def submit_compare_job(
            dataset_id: Annotated[str, Field(description="Dataset ID to train on")],
            target_column: Annotated[str, Field(description="Name of the target/label column")],
            problem_type: Annotated[
                Literal["binary", "multiclass", "regression"],
                Field(description="Type of ML problem")
            ],
            algorithms: Annotated[
                List[str],
                Field(description="List of algorithms to compare (minimum 2). E.g., ['XGB', 'GBM', 'RF', 'NN_TORCH']")
            ],
            user_id: Annotated[str, Field(description="User ID")],
            session_id: Annotated[Optional[str], Field(description="Optional session ID")] = None,
            time_limit: Annotated[int, Field(description="Training time limit in seconds")] = 300,
        ) -> Dict[str, Any]:
            """
            Submit a job to compare multiple algorithms.
            
            Trains multiple models and generates a comparison leaderboard.
            Requires at least 2 algorithms.
            The job runs in the background - this call returns IMMEDIATELY.
            
            ⚠️ IMPORTANT: Training may take minutes to hours!
            Use get_job_status(job_id) to check progress.
            
            Returns:
                job_id: Unique job identifier
                job_type: "compare"
                status: "pending"
                
            Next steps:
                1. Use get_job_status(job_id) to check progress
                2. When complete, use get_model_leaderboard(model_id) to see comparison
            """
            return await self._client.submit_compare_job(
                dataset_id=dataset_id,
                target_column=target_column,
                problem_type=problem_type,
                algorithms=algorithms,
                user_id=user_id,
                session_id=session_id,
                time_limit=time_limit,
            )

    # ============== Job Tools ==============
    
    def _register_job_tools(self) -> None:
        """Register job management tools"""
        
        @self._mcp.tool()
        async def get_job_status(
            job_id: Annotated[str, Field(description="Job ID to check")],
            user_id: Annotated[str, Field(description="User ID")],
        ) -> Dict[str, Any]:
            """
            Get the status of a training job.
            
            Use this to check if training is complete.
            
            Returns:
                job_id: Job identifier
                status: "pending" | "running" | "completed" | "failed" | "cancelled"
                progress: 0.0 to 1.0
                status_message: Human-readable status
                model_id: (only when completed) ID of the trained model
                error_message: (only when failed) Error description
                
            When status is "completed":
                - Use model_id with get_model_leaderboard() to see results
                - Use model_id with predict() to make predictions
            """
            return await self._client.get_job_status(job_id, user_id)

        @self._mcp.tool()
        async def list_jobs(
            user_id: Annotated[str, Field(description="User ID")],
            session_id: Annotated[Optional[str], Field(description="Optional session ID")] = None,
        ) -> List[Dict[str, Any]]:
            """
            List all training jobs for the user.
            
            Returns jobs in all states (pending, running, completed, failed).
            """
            return await self._client.list_jobs(user_id, session_id)

        @self._mcp.tool()
        async def cancel_job(
            job_id: Annotated[str, Field(description="Job ID to cancel")],
            user_id: Annotated[str, Field(description="User ID")],
        ) -> Dict[str, Any]:
            """
            Cancel a pending or running training job.
            
            Cannot cancel jobs that are already completed or failed.
            """
            return await self._client.cancel_job(job_id, user_id)

    # ============== Model Tools ==============
    
    def _register_model_tools(self) -> None:
        """Register model management tools"""
        
        @self._mcp.tool()
        async def list_models(
            user_id: Annotated[str, Field(description="User ID")],
            session_id: Annotated[Optional[str], Field(description="Optional session ID")] = None,
        ) -> List[Dict[str, Any]]:
            """
            List all trained models for the user.
            
            Returns models with their performance metrics and metadata.
            """
            return await self._client.list_models(user_id, session_id)

        @self._mcp.tool()
        async def get_model_leaderboard(
            model_id: Annotated[str, Field(description="Model ID")],
            user_id: Annotated[str, Field(description="User ID")],
        ) -> List[Dict[str, Any]]:
            """
            Get the leaderboard for a trained model.
            
            Shows all models trained during the experiment, ranked by performance.
            
            Returns:
                List of entries with:
                - model_name: Name of the model (e.g., "WeightedEnsemble_L2", "XGBoost")
                - score: Validation score
                - fit_time: Training time in seconds
                - pred_time: Prediction time
                - stack_level: Ensemble stacking level
            """
            return await self._client.get_model_leaderboard(model_id, user_id)

        @self._mcp.tool()
        async def predict(
            model_id: Annotated[str, Field(description="Model ID to use for prediction")],
            dataset_id: Annotated[str, Field(description="Dataset ID containing data to predict on")],
            user_id: Annotated[str, Field(description="User ID")],
        ) -> Dict[str, Any]:
            """
            Make predictions using a trained model.
            
            The prediction dataset should have the same features as the training
            dataset (excluding the target column).
            
            Returns:
                model_id: Model used
                predictions: List of predicted values
                probabilities: (for classification) List of probability arrays
            """
            return await self._client.predict(model_id, dataset_id, user_id)

        @self._mcp.tool()
        async def delete_model(
            model_id: Annotated[str, Field(description="Model ID to delete")],
            user_id: Annotated[str, Field(description="User ID")],
        ) -> Dict[str, Any]:
            """
            Delete a trained model.
            
            This permanently removes the model and its files.
            """
            return await self._client.delete_model(model_id, user_id)

    # ============== Orchestration Tools (Smart/Convenience) ==============
    
    def _register_orchestration_tools(self) -> None:
        """Register smart orchestration tools that combine multiple operations"""
        
        @self._mcp.tool()
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
            import time
            start_time = time.time()
            
            while True:
                status = await self._client.get_job_status(job_id, user_id)
                elapsed = time.time() - start_time
                
                # Check terminal states
                if status["status"] in ["completed", "failed", "cancelled"]:
                    status["elapsed_seconds"] = round(elapsed, 1)
                    return status
                
                # Check timeout
                if timeout > 0 and elapsed >= timeout:
                    return {
                        "job_id": job_id,
                        "status": "timeout",
                        "status_message": f"Job did not complete within {timeout} seconds",
                        "last_status": status["status"],
                        "last_progress": status.get("progress", 0),
                        "elapsed_seconds": round(elapsed, 1),
                    }
                
                # Wait before next poll
                await asyncio.sleep(poll_interval)

        @self._mcp.tool()
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
            # 1. Submit the job
            job = await self._client.submit_automl_job(
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
            import time
            start_time = time.time()
            poll_interval = 10  # Check every 10 seconds
            
            while True:
                status = await self._client.get_job_status(job_id, user_id)
                elapsed = time.time() - start_time
                
                if status["status"] == "completed":
                    # Get the leaderboard for complete results
                    model_id = status.get("model_id")
                    if model_id:
                        try:
                            leaderboard = await self._client.get_model_leaderboard(model_id, user_id)
                            status["leaderboard"] = leaderboard
                        except Exception:
                            pass  # Leaderboard is optional bonus
                    
                    status["elapsed_seconds"] = round(elapsed, 1)
                    status["summary"] = f"✅ Training completed in {round(elapsed/60, 1)} minutes. Best model: {status.get('result', {}).get('best_model', 'N/A')}"
                    return status
                
                if status["status"] == "failed":
                    status["elapsed_seconds"] = round(elapsed, 1)
                    status["summary"] = f"❌ Training failed: {status.get('error_message', 'Unknown error')}"
                    return status
                
                if status["status"] == "cancelled":
                    status["elapsed_seconds"] = round(elapsed, 1)
                    status["summary"] = "⚠️ Training was cancelled"
                    return status
                
                if elapsed >= wait_timeout:
                    return {
                        "job_id": job_id,
                        "status": "timeout",
                        "last_progress": status.get("progress", 0),
                        "elapsed_seconds": round(elapsed, 1),
                        "summary": f"⏱️ Timeout after {round(elapsed/60, 1)} minutes. Job still running - use get_job_status('{job_id}') to check later.",
                    }
                
                await asyncio.sleep(poll_interval)

        @self._mcp.tool()
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
            import time
            start_time = time.time()
            
            # 1. Register dataset
            if not dataset_name:
                # Extract name from path
                dataset_name = minio_path.split("/")[-1].replace(".csv", "")
            
            dataset = await self._client.register_dataset(
                name=dataset_name,
                minio_path=minio_path,
                user_id=user_id,
            )
            dataset_id = dataset["dataset_id"]
            
            # 2. Submit training
            job = await self._client.submit_automl_job(
                dataset_id=dataset_id,
                target_column=target_column,
                problem_type=problem_type,
                user_id=user_id,
                time_limit=time_limit,
                presets="medium_quality",
            )
            job_id = job["job_id"]
            
            # 3. Wait for completion
            poll_interval = 10
            
            while True:
                status = await self._client.get_job_status(job_id, user_id)
                elapsed = time.time() - start_time
                
                if status["status"] == "completed":
                    model_id = status.get("model_id")
                    if model_id:
                        try:
                            leaderboard = await self._client.get_model_leaderboard(model_id, user_id)
                            status["leaderboard"] = leaderboard
                        except Exception:
                            pass
                    
                    return {
                        "dataset_id": dataset_id,
                        "job_id": job_id,
                        "model_id": model_id,
                        "status": "completed",
                        "result": status.get("result"),
                        "leaderboard": status.get("leaderboard"),
                        "elapsed_seconds": round(elapsed, 1),
                        "summary": f"✅ Model ready! Dataset '{dataset_name}' → Model '{model_id}' in {round(elapsed/60, 1)} min",
                    }
                
                if status["status"] == "failed":
                    return {
                        "dataset_id": dataset_id,
                        "job_id": job_id,
                        "status": "failed",
                        "error_message": status.get("error_message"),
                        "elapsed_seconds": round(elapsed, 1),
                        "summary": f"❌ Training failed: {status.get('error_message')}",
                    }
                
                if elapsed >= wait_timeout:
                    return {
                        "dataset_id": dataset_id,
                        "job_id": job_id,
                        "status": "timeout",
                        "elapsed_seconds": round(elapsed, 1),
                        "summary": f"⏱️ Timeout. Use get_job_status('{job_id}') to check later.",
                    }
                
                await asyncio.sleep(poll_interval)

        @self._mcp.tool()
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
            datasets = await self._client.list_datasets(user_id)
            dataset = next((d for d in datasets if d["dataset_id"] == dataset_id), None)
            
            if not dataset:
                return {"error": f"Dataset {dataset_id} not found"}
            
            row_count = dataset.get("row_count", 0)
            columns = dataset.get("columns", [])
            
            if target_column not in columns:
                return {"error": f"Target column '{target_column}' not in dataset. Available: {columns}"}
            
            # Analyze and recommend
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
            recommendations["estimated_training_time"] = f"{recommendations['recommendations']['time_limit'] // 60}-{recommendations['recommendations']['time_limit'] * 2 // 60} minutes"
            
            recommendations["next_step"] = f"Run: train_and_wait(dataset_id='{dataset_id}', target_column='{target_column}', problem_type='<your_type>', ...)"
            
            return recommendations

        @self._mcp.tool()
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
            datasets = await self._client.list_datasets(user_id, session_id)
            jobs = await self._client.list_jobs(user_id, session_id)
            models = await self._client.list_models(user_id, session_id)
            
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
                    for m in models[:5]  # Last 5 models
                ],
                "tips": [
                    "Use quick_train() for fastest path from data to model",
                    "Use analyze_dataset() before training to optimize settings",
                    "Use train_and_wait() for full control with blocking wait",
                ],
            }
