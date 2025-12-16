"""
Training Tools for MCP

Tools for submitting training jobs.
"""
from typing import Annotated, Any, Dict, List, Literal, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from ..client import AutoMLClient


def register_training_tools(mcp: FastMCP, client: AutoMLClient) -> None:
    """Register all training submission tools"""

    @mcp.tool()
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
        return await client.submit_automl_job(
            dataset_id=dataset_id,
            target_column=target_column,
            problem_type=problem_type,
            user_id=user_id,
            session_id=session_id,
            time_limit=time_limit,
            presets=presets,
            metric=metric,
        )

    @mcp.tool()
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
        return await client.submit_specific_job(
            dataset_id=dataset_id,
            target_column=target_column,
            problem_type=problem_type,
            algorithms=algorithms,
            user_id=user_id,
            session_id=session_id,
            time_limit=time_limit,
        )

    @mcp.tool()
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
        return await client.submit_compare_job(
            dataset_id=dataset_id,
            target_column=target_column,
            problem_type=problem_type,
            algorithms=algorithms,
            user_id=user_id,
            session_id=session_id,
            time_limit=time_limit,
        )
