"""
Stats Service - Auto Analyze Routes

Routes for intelligent automatic statistical analysis.
Refactored to use DDD Use Cases.
"""
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..application.dto import SubmitAutoAnalyzeRequest as SubmitAutoAnalyzeDTO
from ..application.use_cases import (
    DatasetNotFoundError,
    SubmitAutoAnalyzeUseCase,
)
from ..infrastructure.redis_dataset_store import redis_dataset_store
from ..infrastructure.repositories import get_job_queue, get_job_repository

router = APIRouter(prefix="/auto-analyze", tags=["Auto Analyze"])


class AutoAnalyzeRequest(BaseModel):
    """Request model for auto-analyze job submission"""
    dataset_id: str = Field(..., description="Dataset ID in MinIO")
    user_id: str = Field(..., description="User ID for isolation")
    session_id: Optional[str] = Field(None, description="Optional session ID")
    target_column: Optional[str] = Field(
        None,
        description="Target column for association analysis (optional). If provided, will analyze relationships between features and target."
    )


class AutoAnalyzeResponse(BaseModel):
    """Response model for auto-analyze job submission"""
    job_id: str
    job_type: str
    status: str
    message: str


def _get_submit_use_case() -> SubmitAutoAnalyzeUseCase:
    """Dependency injection for submit use case"""
    return SubmitAutoAnalyzeUseCase(
        job_repo=get_job_repository(),
        dataset_store=redis_dataset_store,
        job_queue=get_job_queue(),
    )


@router.post("/submit", response_model=AutoAnalyzeResponse)
async def submit_auto_analyze_job(request: AutoAnalyzeRequest):
    """
    🧠 Submit an intelligent auto-analysis job.

    This automatically performs comprehensive statistical analysis:

    1. **Data Quality Check**
       - Missing values analysis (count, pattern)
       - Outlier detection (IQR, Z-score)
       - Duplicate row detection

    2. **Variable Type Inference**
       - Numeric (continuous/discrete)
       - Categorical (nominal/ordinal)
       - Datetime, ID columns (auto-excluded)

    3. **Descriptive Statistics**
       - Numeric: mean, std, median, IQR, skewness, kurtosis
       - Categorical: frequency, mode, top values

    4. **Hypothesis Testing**
       - Normality test (Shapiro-Wilk/D'Agostino)
       - Auto-selects parametric vs non-parametric tests

    5. **Association Analysis** (if target_column provided)
       - Numeric vs Numeric: Pearson/Spearman correlation
       - Categorical vs Categorical: Chi-square + Cramér's V
       - Numeric vs Categorical: t-test/ANOVA/Mann-Whitney/Kruskal-Wallis

    6. **Recommendations**
       - Data cleaning suggestions
       - Feature engineering ideas
       - Suitable ML model recommendations

    Args:
        dataset_id: ID of dataset to analyze
        user_id: User ID
        target_column: Optional target for association analysis

    Returns:
        job_id for tracking progress

    Example:
        ```
        # Basic analysis
        submit_auto_analyze(dataset_id="abc123", user_id="user1")

        # With target column for ML prep
        submit_auto_analyze(
            dataset_id="abc123",
            user_id="user1",
            target_column="price"  # Will analyze what features predict price
        )
        ```
    """
    use_case = _get_submit_use_case()

    try:
        result = await use_case.execute(
            SubmitAutoAnalyzeDTO(
                dataset_id=request.dataset_id,
                user_id=request.user_id,
                session_id=request.session_id,
                target_column=request.target_column,
            )
        )

        return AutoAnalyzeResponse(
            job_id=result.job_id,
            job_type=result.job_type,
            status=result.status,
            message=result.message,
        )

    except DatasetNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/capabilities")
async def get_capabilities():
    """
    Get the capabilities of the auto-analyze engine.

    Returns a description of all automatic analyses performed.
    """
    return {
        "name": "Intelligent Auto-Analyze Engine",
        "version": "1.0.0",
        "capabilities": {
            "data_quality": [
                "Missing value analysis (count, percentage, pattern)",
                "Outlier detection (IQR method, Z-score method)",
                "Duplicate row detection",
                "Constant column detection",
                "ID column detection",
            ],
            "descriptive_statistics": {
                "numeric": [
                    "Mean, Standard Deviation",
                    "Median, IQR (Q25, Q75)",
                    "Min, Max, Range",
                    "Skewness, Kurtosis",
                ],
                "categorical": [
                    "Mode and frequency",
                    "Top N value distribution",
                    "Unique value count",
                ],
            },
            "hypothesis_testing": [
                "Normality test (Shapiro-Wilk for n<5000, D'Agostino otherwise)",
                "Auto-selection of parametric vs non-parametric tests",
            ],
            "association_analysis": {
                "numeric_vs_numeric": "Pearson or Spearman correlation (based on normality)",
                "categorical_vs_categorical": "Chi-square test + Cramér's V",
                "numeric_vs_categorical_2groups": "Independent t-test or Mann-Whitney U",
                "numeric_vs_categorical_multigroup": "One-way ANOVA or Kruskal-Wallis H",
            },
            "recommendations": [
                "Data cleaning suggestions",
                "Feature engineering recommendations",
                "Multicollinearity warnings",
                "ML model type suggestions",
            ],
        },
        "output_format": {
            "metadata": "Basic dataset info (rows, cols, memory)",
            "column_summary": "Lists of columns by type",
            "columns": "Detailed profile for each column",
            "data_quality": "Quality score and issues",
            "correlation_matrix": "For numeric columns",
            "target_analysis": "Association tests with target (if provided)",
            "recommendations": "Actionable suggestions",
            "summary": "Human-readable overview",
        },
    }
