"""
AutoML MCP Tool Handlers

MCP tool handlers for AutoML operations.
Following the pattern from medical-calc-mcp.
"""
from typing import Annotated, Any, Dict, List, Literal, Optional
import asyncio

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .client import get_client


class AutoMLHandler:
    """
    Handler for AutoML MCP tools.
    
    Provides tools for:
    - Dataset management (register, list, delete)
    - Training jobs (submit, status, cancel)
    - Model management (list, leaderboard, predict, delete)
    
    Important: Training jobs are asynchronous!
    - submit_*_job returns immediately with job_id
    - Use get_job_status to check progress
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
