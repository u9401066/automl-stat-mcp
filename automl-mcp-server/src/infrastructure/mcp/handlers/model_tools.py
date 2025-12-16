"""
Model Management Tools for MCP

Tools for managing trained models (list, leaderboard, predict, delete).
"""
from typing import Annotated, Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from ..client import AutoMLClient


def register_model_tools(mcp: FastMCP, client: AutoMLClient) -> None:
    """Register all model management tools"""

    @mcp.tool()
    async def list_models(
        user_id: Annotated[str, Field(description="User ID")],
        session_id: Annotated[Optional[str], Field(description="Optional session ID")] = None,
    ) -> List[Dict[str, Any]]:
        """
        List all trained models for the user.

        Returns models with their performance metrics and metadata.
        """
        return await client.list_models(user_id, session_id)

    @mcp.tool()
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
        return await client.get_model_leaderboard(model_id, user_id)

    @mcp.tool()
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
        return await client.predict(model_id, dataset_id, user_id)

    @mcp.tool()
    async def delete_model(
        model_id: Annotated[str, Field(description="Model ID to delete")],
        user_id: Annotated[str, Field(description="User ID")],
    ) -> Dict[str, Any]:
        """
        Delete a trained model.

        This permanently removes the model and its files.
        """
        return await client.delete_model(model_id, user_id)
