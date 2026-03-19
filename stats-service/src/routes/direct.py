"""
Stats Service - Direct Analysis Routes (DDD)

Routes for analyzing data directly without storing in MinIO.
Useful for one-time analysis or temporary data.
Refactored to use Domain-Driven Design patterns.
"""

import base64
import io
from typing import List, Optional

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..domain.models import StatsJob, StatsJobId, StatsJobType
from ..domain.services.data_quality import DataQualityAnalyzer, analyze_data_quality
from ..infrastructure.repositories import get_job_queue, get_job_repository

router = APIRouter(prefix="/direct", tags=["Direct Analysis"])


class DirectAnalyzeRequest(BaseModel):
    """Request model for direct analysis (no MinIO storage)"""

    csv_content: str = Field(..., description="CSV content as string (can be base64 encoded for binary safety)")
    is_base64: bool = Field(default=False, description="Whether csv_content is base64 encoded")
    user_id: str = Field(..., description="User ID")
    target_column: Optional[str] = Field(None, description="Target column for association analysis")
    session_id: Optional[str] = Field(None, description="Session ID")


class DirectAnalyzeResponse(BaseModel):
    """Response model for direct analysis"""

    job_id: str
    job_type: str
    status: str
    message: str
    data_preview: dict  # Preview of the data


@router.post("/analyze", response_model=DirectAnalyzeResponse)
async def direct_analyze(request: DirectAnalyzeRequest):
    """
    📊 Analyze CSV data directly without storing in MinIO.

    This is useful for:
    - One-time analysis of temporary data
    - Quick data exploration without permanent storage
    - Testing and development

    The CSV content is passed directly in the request and processed
    without being saved to MinIO. Results are still stored temporarily
    and can be retrieved via the job ID.

    Args:
        csv_content: CSV data as string (or base64 if is_base64=True)
        is_base64: Set to True if csv_content is base64 encoded
        user_id: User ID
        target_column: Optional target for association analysis

    Returns:
        job_id: Job ID for tracking
        data_preview: Preview of the parsed data

    Example:
        ```python
        # Direct string content
        direct_analyze(
            csv_content="col1,col2\\n1,2\\n3,4",
            user_id="user1"
        )

        # Base64 encoded (for binary safety)
        import base64
        encoded = base64.b64encode(csv_bytes).decode()
        direct_analyze(
            csv_content=encoded,
            is_base64=True,
            user_id="user1"
        )
        ```
    """
    try:
        # Decode CSV content
        if request.is_base64:
            csv_bytes = base64.b64decode(request.csv_content)
            csv_str = csv_bytes.decode("utf-8")
        else:
            csv_str = request.csv_content

        # 早期驗證：空內容檢查
        if not csv_str or not csv_str.strip():
            raise HTTPException(status_code=400, detail="CSV content is empty")

        # Parse CSV to validate and get preview
        df = pd.read_csv(io.StringIO(csv_str))

        if df.empty:
            raise HTTPException(status_code=400, detail="CSV content is empty or invalid")

        # Create preview
        preview = {
            "rows": len(df),
            "columns": len(df.columns),
            "column_names": df.columns.tolist(),
            "sample_rows": df.head(3).to_dict(orient="records"),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        }

        # Create job using domain model
        job = StatsJob(
            id=StatsJobId.generate(),
            job_type=StatsJobType.AUTO_ANALYZE_DIRECT,
            user_id=request.user_id,
            session_id=request.session_id,
            params={
                "csv_content": csv_str,  # Store CSV content directly
                "target_column": request.target_column,
                "is_direct": True,  # Flag for worker
            },
        )

        # Save and enqueue
        job_repo = get_job_repository()
        job_queue = get_job_queue()
        await job_repo.save(job)
        await job_queue.enqueue_job(job)

        return DirectAnalyzeResponse(
            job_id=str(job.id),
            job_type=job.job_type.value,
            status=job.status.value,
            message="Direct analysis job submitted. Use /jobs/{job_id} to check status.",
            data_preview=preview,
        )

    except HTTPException:
        # 讓 HTTPException 直接通過，不要被 except Exception 捕獲
        raise
    except pd.errors.ParserError as e:
        raise HTTPException(status_code=400, detail=f"Invalid CSV format: {str(e)}") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process CSV: {str(e)}") from e


class QuickStatsRequest(BaseModel):
    """Request for quick statistics (synchronous, no job queue)"""

    csv_content: str = Field(..., description="CSV content as string")
    is_base64: bool = Field(default=False)
    include_quality_check: bool = Field(default=True, description="Include data quality warnings and recommendations")


class QuickStatsResponse(BaseModel):
    """Quick statistics response"""

    rows: int
    columns: int
    column_info: List[dict]
    missing_summary: dict
    numeric_summary: Optional[dict]
    # 新增資料品質欄位
    quality_warnings: Optional[List[dict]] = None
    transform_suggestions: Optional[List[dict]] = None
    analysis_readiness: Optional[dict] = None


@router.post("/quick-stats", response_model=QuickStatsResponse)
async def quick_stats(request: QuickStatsRequest):
    """
    ⚡ Get quick statistics synchronously (no job queue).

    This returns immediately with basic statistics.
    For full analysis, use /direct/analyze instead.

    Returns:
        - Row and column counts
        - Column types and info
        - Missing value summary
        - Basic numeric statistics
        - Data quality warnings (if include_quality_check=True)
        - Transform suggestions (if include_quality_check=True)
        - Analysis readiness assessment (if include_quality_check=True)
    """
    try:
        # Decode CSV
        if request.is_base64:
            csv_bytes = base64.b64decode(request.csv_content)
            csv_str = csv_bytes.decode("utf-8")
        else:
            csv_str = request.csv_content

        df = pd.read_csv(io.StringIO(csv_str))

        # Column info
        column_info = []
        for col in df.columns:
            info = {
                "name": col,
                "dtype": str(df[col].dtype),
                "non_null": int(df[col].notna().sum()),
                "null": int(df[col].isna().sum()),
                "unique": int(df[col].nunique()),
            }

            # Add sample values
            non_null = df[col].dropna()
            if len(non_null) > 0:
                info["sample"] = non_null.head(3).tolist()

            column_info.append(info)

        # Missing summary
        missing_summary = {
            "total_missing": int(df.isna().sum().sum()),
            "columns_with_missing": int((df.isna().sum() > 0).sum()),
            "missing_by_column": df.isna().sum().to_dict(),
        }

        # Numeric summary
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        numeric_summary = None
        if numeric_cols:
            desc = df[numeric_cols].describe()
            numeric_summary = desc.to_dict()

        # Data quality check
        quality_warnings = None
        transform_suggestions = None
        analysis_readiness = None

        if request.include_quality_check:
            quality_report = analyze_data_quality(df)
            quality_warnings = quality_report.get("quality_warnings", [])
            transform_suggestions = quality_report.get("transform_suggestions", [])
            analysis_readiness = quality_report.get("analysis_readiness", {})

        return QuickStatsResponse(
            rows=len(df),
            columns=len(df.columns),
            column_info=column_info,
            missing_summary=missing_summary,
            numeric_summary=numeric_summary,
            quality_warnings=quality_warnings,
            transform_suggestions=transform_suggestions,
            analysis_readiness=analysis_readiness,
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {str(e)}") from e


# ============================================================================
# Data Quality Check Endpoint
# ============================================================================


class QualityCheckRequest(BaseModel):
    """Request for data quality check"""

    csv_content: str = Field(..., description="CSV content as string")
    is_base64: bool = Field(default=False)


class QualityCheckResponse(BaseModel):
    """Data quality check response"""

    rows: int
    columns: int
    quality_warnings: List[dict]
    transform_suggestions: List[dict]
    analysis_readiness: dict
    summary: dict


@router.post("/quality-check", response_model=QualityCheckResponse)
async def quality_check(request: QualityCheckRequest):
    """
    🔍 資料品質檢查

    偵測資料品質問題並提供建議：
    - 全 NaN 欄 (ALL_NAN)
    - 常數欄 (CONSTANT)
    - 高基數 ID 欄 (HIGH_CARDINALITY_ID)
    - 高缺失值欄 (HIGH_MISSING)
    - 偏態資料 (SKEWED)
    - 極端值 (OUTLIERS)

    Returns:
        quality_warnings: 品質警告列表
        transform_suggestions: Transform 建議
        analysis_readiness: 分析可行性評估
        summary: 快速摘要
    """
    try:
        # Decode CSV
        if request.is_base64:
            csv_bytes = base64.b64decode(request.csv_content)
            csv_str = csv_bytes.decode("utf-8")
        else:
            csv_str = request.csv_content

        df = pd.read_csv(io.StringIO(csv_str))

        # Run quality analysis
        analyzer = DataQualityAnalyzer()
        report = analyzer.analyze(df)
        quick_summary = analyzer.quick_check(df)

        return QualityCheckResponse(
            rows=len(df),
            columns=len(df.columns),
            quality_warnings=[w.to_dict() for w in report.warnings],
            transform_suggestions=[t.to_dict() for t in report.transform_suggestions],
            analysis_readiness=report.analysis_readiness.to_dict(),
            summary=quick_summary,
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to analyze CSV: {str(e)}") from e
