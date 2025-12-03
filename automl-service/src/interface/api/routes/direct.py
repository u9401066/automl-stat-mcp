"""
FastAPI Router - Direct Analysis endpoints

Routes for analyzing data directly without storing in MinIO.
Useful for pre-training dataset analysis, one-time analysis, or testing.
"""
import base64
import io
from typing import List, Optional, Any, Dict

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field

import pandas as pd
import numpy as np

router = APIRouter(prefix="/direct", tags=["Direct Analysis"])


# ============== Request/Response Models ==============

class DirectAnalyzeRequest(BaseModel):
    """Request model for direct analysis (no MinIO storage)"""
    csv_content: str = Field(
        ..., 
        description="CSV content as string (can be base64 encoded for binary safety)"
    )
    is_base64: bool = Field(
        default=False,
        description="Whether csv_content is base64 encoded"
    )
    target_column: Optional[str] = Field(
        None, 
        description="Target column for ML analysis"
    )


class DirectAnalyzeResponse(BaseModel):
    """Response for direct analysis"""
    rows: int
    columns: int
    column_names: List[str]
    dtypes: Dict[str, str]
    target_analysis: Optional[Dict[str, Any]] = None
    recommendations: Dict[str, Any]
    warnings: List[str]
    data_preview: Dict[str, Any]


class QuickStatsRequest(BaseModel):
    """Request for quick statistics (synchronous)"""
    csv_content: str = Field(..., description="CSV content as string")
    is_base64: bool = Field(default=False)


class QuickStatsResponse(BaseModel):
    """Quick statistics response"""
    rows: int
    columns: int
    column_info: List[Dict[str, Any]]
    missing_summary: Dict[str, Any]
    numeric_summary: Optional[Dict[str, Any]]


class DatasetPreviewRequest(BaseModel):
    """Request for dataset preview"""
    csv_content: str = Field(..., description="CSV content as string")
    is_base64: bool = Field(default=False)
    n_rows: int = Field(default=10, le=100)


class DatasetPreviewResponse(BaseModel):
    """Dataset preview response"""
    rows: int
    columns: int
    column_names: List[str]
    dtypes: Dict[str, str]
    preview: List[Dict[str, Any]]
    missing_values: Dict[str, int]


# ============== Helper Functions ==============

def safe_value(val):
    """Convert value to JSON-safe format"""
    if pd.isna(val):
        return None
    if isinstance(val, (np.integer,)):
        return int(val)
    if isinstance(val, (np.floating,)):
        if np.isnan(val) or np.isinf(val):
            return None
        return float(val)
    if isinstance(val, np.ndarray):
        return val.tolist()
    return val


def decode_csv(csv_content: str, is_base64: bool) -> pd.DataFrame:
    """Decode CSV content and return DataFrame"""
    try:
        if is_base64:
            csv_bytes = base64.b64decode(csv_content)
            csv_str = csv_bytes.decode('utf-8')
        else:
            csv_str = csv_content
        
        df = pd.read_csv(io.StringIO(csv_str))
        
        if df.empty:
            raise ValueError("CSV content is empty or invalid")
        
        return df
    except pd.errors.ParserError as e:
        raise ValueError(f"Invalid CSV format: {str(e)}")
    except Exception as e:
        raise ValueError(f"Failed to parse CSV: {str(e)}")


def analyze_target(df: pd.DataFrame, target_column: str) -> Dict[str, Any]:
    """Analyze target column for ML recommendations"""
    if target_column not in df.columns:
        return {"error": f"Target column '{target_column}' not found"}
    
    target = df[target_column]
    analysis = {
        "column": target_column,
        "dtype": str(target.dtype),
        "missing": int(target.isna().sum()),
        "unique_values": int(target.nunique()),
    }
    
    # Determine problem type
    if target.dtype in ['object', 'bool', 'category']:
        # Classification
        unique = target.nunique()
        if unique == 2:
            analysis["recommended_problem_type"] = "binary"
        else:
            analysis["recommended_problem_type"] = "multiclass"
        
        # Class distribution
        value_counts = target.value_counts()
        analysis["class_distribution"] = {
            str(k): int(v) for k, v in value_counts.items()
        }
        
        # Check for imbalance
        if len(value_counts) >= 2:
            ratio = value_counts.max() / value_counts.min()
            if ratio > 10:
                analysis["imbalance_warning"] = f"High class imbalance detected (ratio: {ratio:.1f}:1)"
    else:
        # Regression
        analysis["recommended_problem_type"] = "regression"
        analysis["statistics"] = {
            "mean": safe_value(target.mean()),
            "std": safe_value(target.std()),
            "min": safe_value(target.min()),
            "max": safe_value(target.max()),
            "median": safe_value(target.median()),
        }
    
    return analysis


def get_ml_recommendations(df: pd.DataFrame, target_column: Optional[str]) -> Dict[str, Any]:
    """Generate ML training recommendations"""
    n_rows = len(df)
    n_cols = len(df.columns)
    
    recommendations = {
        "dataset_size": "small" if n_rows < 1000 else "medium" if n_rows < 100000 else "large",
    }
    
    # Preset recommendation based on size
    if n_rows < 1000:
        recommendations["recommended_presets"] = ["medium_quality", "good_quality"]
        recommendations["recommended_time_limit"] = 120  # 2 min for small
    elif n_rows < 10000:
        recommendations["recommended_presets"] = ["medium_quality", "good_quality"]
        recommendations["recommended_time_limit"] = 300  # 5 min
    elif n_rows < 100000:
        recommendations["recommended_presets"] = ["medium_quality"]
        recommendations["recommended_time_limit"] = 600  # 10 min
    else:
        recommendations["recommended_presets"] = ["optimize_for_deployment", "medium_quality"]
        recommendations["recommended_time_limit"] = 1200  # 20 min
    
    # Feature analysis
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
    
    if target_column:
        if target_column in numeric_cols:
            numeric_cols.remove(target_column)
        if target_column in categorical_cols:
            categorical_cols.remove(target_column)
    
    recommendations["feature_summary"] = {
        "numeric_features": len(numeric_cols),
        "categorical_features": len(categorical_cols),
        "total_features": len(numeric_cols) + len(categorical_cols),
    }
    
    # High cardinality warning
    high_cardinality = []
    for col in categorical_cols:
        if df[col].nunique() > 100:
            high_cardinality.append(col)
    
    if high_cardinality:
        recommendations["high_cardinality_columns"] = high_cardinality
    
    return recommendations


def get_data_warnings(df: pd.DataFrame) -> List[str]:
    """Generate data quality warnings"""
    warnings = []
    
    # Missing values
    missing_pct = df.isna().sum() / len(df) * 100
    high_missing = missing_pct[missing_pct > 30].index.tolist()
    if high_missing:
        warnings.append(f"High missing values (>30%): {high_missing}")
    
    # Constant columns
    constant_cols = [col for col in df.columns if df[col].nunique() <= 1]
    if constant_cols:
        warnings.append(f"Constant columns (no variance): {constant_cols}")
    
    # Duplicate rows
    dup_count = df.duplicated().sum()
    if dup_count > 0:
        dup_pct = dup_count / len(df) * 100
        if dup_pct > 5:
            warnings.append(f"Duplicate rows: {dup_count} ({dup_pct:.1f}%)")
    
    # ID-like columns
    for col in df.columns:
        if df[col].nunique() == len(df):
            if df[col].dtype == 'object' or 'id' in col.lower():
                warnings.append(f"Possible ID column (all unique): {col}")
    
    return warnings


# ============== Endpoints ==============

@router.post("/analyze", response_model=DirectAnalyzeResponse)
async def direct_analyze(
    request: DirectAnalyzeRequest,
    x_user_id: str = Header(..., description="User ID"),
):
    """
    📊 Analyze CSV data directly for ML training preparation.
    
    This is useful for:
    - Pre-training dataset analysis
    - Quick data exploration without MinIO upload
    - Testing and development
    
    Returns:
        - Dataset shape and structure
        - Target column analysis (if provided)
        - ML training recommendations
        - Data quality warnings
        
    Example:
        ```python
        direct_analyze(
            csv_content="col1,col2,target\\n1,2,0\\n3,4,1",
            target_column="target"
        )
        ```
    """
    try:
        df = decode_csv(request.csv_content, request.is_base64)
        
        # Target analysis
        target_analysis = None
        if request.target_column:
            target_analysis = analyze_target(df, request.target_column)
        
        # Recommendations
        recommendations = get_ml_recommendations(df, request.target_column)
        
        # Warnings
        warnings = get_data_warnings(df)
        
        # Preview
        preview_rows = df.head(5).to_dict(orient="records")
        # Convert numpy types
        for row in preview_rows:
            for k, v in row.items():
                row[k] = safe_value(v)
        
        return DirectAnalyzeResponse(
            rows=len(df),
            columns=len(df.columns),
            column_names=df.columns.tolist(),
            dtypes={col: str(dtype) for col, dtype in df.dtypes.items()},
            target_analysis=target_analysis,
            recommendations=recommendations,
            warnings=warnings,
            data_preview={
                "sample_rows": preview_rows,
                "sample_count": min(5, len(df)),
            },
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/quick-stats", response_model=QuickStatsResponse)
async def quick_stats(
    request: QuickStatsRequest,
    x_user_id: str = Header(..., description="User ID"),
):
    """
    ⚡ Get quick statistics synchronously.
    
    Returns immediately with basic statistics for the CSV data.
    For full ML analysis, use /direct/analyze instead.
    
    Returns:
        - Row and column counts
        - Column types and info
        - Missing value summary
        - Basic numeric statistics
    """
    try:
        df = decode_csv(request.csv_content, request.is_base64)
        
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
            
            # Sample values
            non_null = df[col].dropna()
            if len(non_null) > 0:
                samples = non_null.head(3).tolist()
                info["sample"] = [safe_value(s) for s in samples]
            
            column_info.append(info)
        
        # Missing summary
        missing_summary = {
            "total_missing": int(df.isna().sum().sum()),
            "columns_with_missing": int((df.isna().sum() > 0).sum()),
            "missing_by_column": {k: int(v) for k, v in df.isna().sum().to_dict().items()},
        }
        
        # Numeric summary
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        numeric_summary = None
        if numeric_cols:
            desc = df[numeric_cols].describe()
            # Convert to safe values
            numeric_summary = {}
            for col in desc.columns:
                numeric_summary[col] = {
                    stat: safe_value(val) for stat, val in desc[col].items()
                }
        
        return QuickStatsResponse(
            rows=len(df),
            columns=len(df.columns),
            column_info=column_info,
            missing_summary=missing_summary,
            numeric_summary=numeric_summary,
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Statistics failed: {str(e)}")


@router.post("/preview", response_model=DatasetPreviewResponse)
async def preview_dataset(
    request: DatasetPreviewRequest,
    x_user_id: str = Header(..., description="User ID"),
):
    """
    👀 Preview dataset before registration.
    
    Returns the first N rows and basic metadata.
    Useful for verifying data before MinIO upload.
    """
    try:
        df = decode_csv(request.csv_content, request.is_base64)
        
        # Get preview rows
        preview_df = df.head(request.n_rows)
        preview_records = preview_df.to_dict(orient="records")
        
        # Convert numpy types
        for row in preview_records:
            for k, v in row.items():
                row[k] = safe_value(v)
        
        return DatasetPreviewResponse(
            rows=len(df),
            columns=len(df.columns),
            column_names=df.columns.tolist(),
            dtypes={col: str(dtype) for col, dtype in df.dtypes.items()},
            preview=preview_records,
            missing_values={k: int(v) for k, v in df.isna().sum().to_dict().items()},
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preview failed: {str(e)}")
