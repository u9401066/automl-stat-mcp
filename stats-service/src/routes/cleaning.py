"""
Stats Service - Data Cleaning Routes

Routes for data preprocessing and cleaning:
- Convert values to binary (0/1)
- Encode categorical variables
- Handle missing values
- Remove/rename columns
- Auto-clean datasets

Supports two modes:
1. Dataset mode: Provide dataset_id (pre-uploaded to MinIO)
2. Direct mode: Provide csv_path for local file
"""
import io
import os
import uuid
import json
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

import pandas as pd
import numpy as np

router = APIRouter(prefix="/cleaning", tags=["Data Cleaning"])


# =============================================================================
# Request/Response Models
# =============================================================================

class ConvertBinaryRequest(BaseModel):
    """Request for converting a column to binary (0/1)"""
    csv_path: str = Field(..., description="Path to CSV file")
    column: str = Field(..., description="Column name to convert")
    mapping: Dict[str, int] = Field(..., description="Value mapping, e.g. {'200': 0, '400': 1}")
    output_column: Optional[str] = Field(None, description="Output column name (default: {column}_binary)")
    save_path: Optional[str] = Field(None, description="Path to save cleaned CSV (default: auto-generate)")


class EncodeCategoricalRequest(BaseModel):
    """Request for encoding categorical variables"""
    csv_path: str = Field(..., description="Path to CSV file")
    columns: List[str] = Field(..., description="Columns to encode")
    method: str = Field(default="label", description="Encoding method: label, onehot, target")
    target_column: Optional[str] = Field(None, description="Target column for target encoding")
    save_path: Optional[str] = Field(None, description="Path to save cleaned CSV")


class HandleMissingRequest(BaseModel):
    """Request for handling missing values"""
    csv_path: str = Field(..., description="Path to CSV file")
    strategy: str = Field(default="auto", description="Strategy: auto, drop, mean, median, mode, constant")
    columns: Optional[List[str]] = Field(None, description="Specific columns to handle (default: all)")
    fill_value: Optional[Any] = Field(None, description="Value for constant fill strategy")
    threshold: float = Field(default=0.5, description="Drop threshold: columns with > threshold missing will be dropped")
    save_path: Optional[str] = Field(None, description="Path to save cleaned CSV")


class RemoveColumnsRequest(BaseModel):
    """Request for removing columns"""
    csv_path: str = Field(..., description="Path to CSV file")
    columns: List[str] = Field(..., description="Columns to remove")
    save_path: Optional[str] = Field(None, description="Path to save cleaned CSV")


class FilterRowsRequest(BaseModel):
    """Request for filtering rows"""
    csv_path: str = Field(..., description="Path to CSV file")
    column: str = Field(..., description="Column to filter on")
    operator: str = Field(..., description="Operator: eq, ne, gt, lt, ge, le, in, notin, isna, notna")
    value: Optional[Any] = Field(None, description="Value for comparison (not needed for isna/notna)")
    save_path: Optional[str] = Field(None, description="Path to save filtered CSV")


class RenameColumnsRequest(BaseModel):
    """Request for renaming columns"""
    csv_path: str = Field(..., description="Path to CSV file")
    mapping: Dict[str, str] = Field(..., description="Column rename mapping, e.g. {'old_name': 'new_name'}")
    save_path: Optional[str] = Field(None, description="Path to save renamed CSV")


class AutoCleanRequest(BaseModel):
    """Request for automatic data cleaning"""
    csv_path: str = Field(..., description="Path to CSV file")
    target_column: Optional[str] = Field(None, description="Target column to preserve")
    remove_duplicates: bool = Field(default=True, description="Remove duplicate rows")
    handle_missing: bool = Field(default=True, description="Handle missing values")
    remove_constant: bool = Field(default=True, description="Remove constant columns")
    remove_high_cardinality: bool = Field(default=True, description="Remove high cardinality ID-like columns")
    cardinality_threshold: float = Field(default=0.95, description="Cardinality threshold for ID detection")
    missing_threshold: float = Field(default=0.5, description="Missing value threshold for column removal")
    save_path: Optional[str] = Field(None, description="Path to save cleaned CSV")


class ColumnInfoRequest(BaseModel):
    """Request for column information"""
    csv_path: str = Field(..., description="Path to CSV file")


class CleaningResponse(BaseModel):
    """Standard cleaning operation response"""
    success: bool
    message: str
    input_path: str
    output_path: Optional[str] = None
    rows_before: int
    rows_after: int
    columns_before: int
    columns_after: int
    changes: Optional[Dict[str, Any]] = None


class ColumnInfoResponse(BaseModel):
    """Column information response"""
    success: bool
    csv_path: str
    row_count: int
    column_count: int
    columns: List[Dict[str, Any]]


# =============================================================================
# Helper Functions
# =============================================================================

def _load_csv(csv_path: str) -> pd.DataFrame:
    """Load CSV file"""
    if not os.path.exists(csv_path):
        raise HTTPException(status_code=404, detail=f"File not found: {csv_path}")
    
    try:
        return pd.read_csv(csv_path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read CSV: {str(e)}")


def _save_csv(df: pd.DataFrame, save_path: Optional[str], original_path: str) -> str:
    """Save DataFrame to CSV"""
    if not save_path:
        # Generate automatic path
        base, ext = os.path.splitext(original_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = f"{base}_cleaned_{timestamp}{ext}"
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    
    df.to_csv(save_path, index=False)
    return save_path


def _get_column_info(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Get detailed column information"""
    info = []
    for col in df.columns:
        col_info = {
            "name": col,
            "dtype": str(df[col].dtype),
            "non_null_count": int(df[col].notna().sum()),
            "null_count": int(df[col].isna().sum()),
            "null_percentage": round(df[col].isna().mean() * 100, 2),
            "unique_count": int(df[col].nunique()),
            "unique_percentage": round(df[col].nunique() / len(df) * 100, 2) if len(df) > 0 else 0,
        }
        
        # Add type-specific info
        if pd.api.types.is_numeric_dtype(df[col]):
            col_info["type"] = "numeric"
            col_info["min"] = float(df[col].min()) if df[col].notna().any() else None
            col_info["max"] = float(df[col].max()) if df[col].notna().any() else None
            col_info["mean"] = float(df[col].mean()) if df[col].notna().any() else None
            col_info["std"] = float(df[col].std()) if df[col].notna().any() else None
        else:
            col_info["type"] = "categorical"
            value_counts = df[col].value_counts().head(10).to_dict()
            col_info["top_values"] = {str(k): int(v) for k, v in value_counts.items()}
        
        info.append(col_info)
    
    return info


# =============================================================================
# API Endpoints
# =============================================================================

@router.post("/convert-binary", response_model=CleaningResponse)
async def convert_to_binary(request: ConvertBinaryRequest):
    """
    Convert a column to binary (0/1) values.
    
    Useful for:
    - Converting treatment columns (e.g., 200/400 → 0/1)
    - Converting Yes/No to 0/1
    - Creating binary indicators from categorical values
    
    Example:
    ```json
    {
        "csv_path": "/data/sample_data/my_data.csv",
        "column": "Ropica_ML",
        "mapping": {"200": 0, "400": 1}
    }
    ```
    """
    df = _load_csv(request.csv_path)
    rows_before = len(df)
    cols_before = len(df.columns)
    
    if request.column not in df.columns:
        raise HTTPException(status_code=400, detail=f"Column '{request.column}' not found")
    
    # Convert mapping keys to match column dtype
    original_values = df[request.column].unique()
    mapping = {}
    
    for key, value in request.mapping.items():
        # Try to match the key type with column values
        matched = False
        for orig in original_values:
            if str(orig) == str(key) or (pd.notna(orig) and str(int(orig)) == str(key)):
                mapping[orig] = value
                matched = True
                break
        if not matched:
            # Try numeric conversion
            try:
                numeric_key = int(key) if '.' not in key else float(key)
                if numeric_key in original_values:
                    mapping[numeric_key] = value
            except ValueError:
                pass
    
    if not mapping:
        raise HTTPException(
            status_code=400, 
            detail=f"No mapping matches found. Column values: {list(original_values)[:10]}"
        )
    
    # Create new column
    output_col = request.output_column or f"{request.column}_binary"
    df[output_col] = df[request.column].map(mapping)
    
    # Count unmapped values
    unmapped = df[output_col].isna().sum() - df[request.column].isna().sum()
    
    # Save
    output_path = _save_csv(df, request.save_path, request.csv_path)
    
    return CleaningResponse(
        success=True,
        message=f"Converted '{request.column}' to binary column '{output_col}'",
        input_path=request.csv_path,
        output_path=output_path,
        rows_before=rows_before,
        rows_after=len(df),
        columns_before=cols_before,
        columns_after=len(df.columns),
        changes={
            "new_column": output_col,
            "mapping_applied": {str(k): v for k, v in mapping.items()},
            "unmapped_values": int(unmapped),
            "value_counts": df[output_col].value_counts().to_dict()
        }
    )


@router.post("/encode-categorical", response_model=CleaningResponse)
async def encode_categorical(request: EncodeCategoricalRequest):
    """
    Encode categorical variables.
    
    Methods:
    - label: Label encoding (0, 1, 2, ...)
    - onehot: One-hot encoding (creates multiple columns)
    """
    df = _load_csv(request.csv_path)
    rows_before = len(df)
    cols_before = len(df.columns)
    
    missing_cols = [c for c in request.columns if c not in df.columns]
    if missing_cols:
        raise HTTPException(status_code=400, detail=f"Columns not found: {missing_cols}")
    
    changes = {"encoded_columns": {}}
    
    for col in request.columns:
        if request.method == "label":
            # Label encoding
            categories = df[col].unique()
            label_map = {cat: i for i, cat in enumerate(sorted(categories, key=str))}
            df[f"{col}_encoded"] = df[col].map(label_map)
            changes["encoded_columns"][col] = {
                "method": "label",
                "mapping": {str(k): v for k, v in label_map.items()}
            }
        elif request.method == "onehot":
            # One-hot encoding
            dummies = pd.get_dummies(df[col], prefix=col)
            df = pd.concat([df, dummies], axis=1)
            changes["encoded_columns"][col] = {
                "method": "onehot",
                "new_columns": list(dummies.columns)
            }
    
    output_path = _save_csv(df, request.save_path, request.csv_path)
    
    return CleaningResponse(
        success=True,
        message=f"Encoded {len(request.columns)} categorical column(s)",
        input_path=request.csv_path,
        output_path=output_path,
        rows_before=rows_before,
        rows_after=len(df),
        columns_before=cols_before,
        columns_after=len(df.columns),
        changes=changes
    )


@router.post("/handle-missing", response_model=CleaningResponse)
async def handle_missing_values(request: HandleMissingRequest):
    """
    Handle missing values in the dataset.
    
    Strategies:
    - auto: Smart handling based on column type
    - drop: Drop rows with missing values
    - mean: Fill with column mean (numeric only)
    - median: Fill with column median (numeric only)
    - mode: Fill with most frequent value
    - constant: Fill with specified value
    """
    df = _load_csv(request.csv_path)
    rows_before = len(df)
    cols_before = len(df.columns)
    
    columns = request.columns or df.columns.tolist()
    missing_cols = [c for c in columns if c not in df.columns]
    if missing_cols:
        raise HTTPException(status_code=400, detail=f"Columns not found: {missing_cols}")
    
    changes = {"columns_processed": {}, "columns_dropped": [], "rows_dropped": 0}
    
    if request.strategy == "auto":
        # Drop columns with too many missing values
        for col in columns:
            missing_ratio = df[col].isna().mean()
            if missing_ratio > request.threshold:
                df = df.drop(columns=[col])
                changes["columns_dropped"].append(col)
            elif missing_ratio > 0:
                # Fill based on type
                if pd.api.types.is_numeric_dtype(df[col]):
                    fill_value = df[col].median()
                    df[col] = df[col].fillna(fill_value)
                    changes["columns_processed"][col] = {"strategy": "median", "fill_value": float(fill_value)}
                else:
                    fill_value = df[col].mode().iloc[0] if not df[col].mode().empty else "Unknown"
                    df[col] = df[col].fillna(fill_value)
                    changes["columns_processed"][col] = {"strategy": "mode", "fill_value": str(fill_value)}
    
    elif request.strategy == "drop":
        rows_with_na = df[columns].isna().any(axis=1).sum()
        df = df.dropna(subset=columns)
        changes["rows_dropped"] = int(rows_with_na)
    
    elif request.strategy in ["mean", "median", "mode"]:
        for col in columns:
            if df[col].isna().any():
                if request.strategy == "mean":
                    if pd.api.types.is_numeric_dtype(df[col]):
                        fill_value = df[col].mean()
                        df[col] = df[col].fillna(fill_value)
                        changes["columns_processed"][col] = {"strategy": "mean", "fill_value": float(fill_value)}
                elif request.strategy == "median":
                    if pd.api.types.is_numeric_dtype(df[col]):
                        fill_value = df[col].median()
                        df[col] = df[col].fillna(fill_value)
                        changes["columns_processed"][col] = {"strategy": "median", "fill_value": float(fill_value)}
                elif request.strategy == "mode":
                    fill_value = df[col].mode().iloc[0] if not df[col].mode().empty else None
                    if fill_value is not None:
                        df[col] = df[col].fillna(fill_value)
                        changes["columns_processed"][col] = {"strategy": "mode", "fill_value": str(fill_value)}
    
    elif request.strategy == "constant":
        for col in columns:
            if df[col].isna().any():
                df[col] = df[col].fillna(request.fill_value)
                changes["columns_processed"][col] = {"strategy": "constant", "fill_value": request.fill_value}
    
    output_path = _save_csv(df, request.save_path, request.csv_path)
    
    return CleaningResponse(
        success=True,
        message=f"Handled missing values with strategy '{request.strategy}'",
        input_path=request.csv_path,
        output_path=output_path,
        rows_before=rows_before,
        rows_after=len(df),
        columns_before=cols_before,
        columns_after=len(df.columns),
        changes=changes
    )


@router.post("/remove-columns", response_model=CleaningResponse)
async def remove_columns(request: RemoveColumnsRequest):
    """
    Remove specified columns from the dataset.
    """
    df = _load_csv(request.csv_path)
    rows_before = len(df)
    cols_before = len(df.columns)
    
    # Find existing columns
    existing_cols = [c for c in request.columns if c in df.columns]
    missing_cols = [c for c in request.columns if c not in df.columns]
    
    if not existing_cols:
        raise HTTPException(status_code=400, detail=f"No specified columns found. Available: {list(df.columns)[:20]}")
    
    df = df.drop(columns=existing_cols)
    
    output_path = _save_csv(df, request.save_path, request.csv_path)
    
    return CleaningResponse(
        success=True,
        message=f"Removed {len(existing_cols)} column(s)",
        input_path=request.csv_path,
        output_path=output_path,
        rows_before=rows_before,
        rows_after=len(df),
        columns_before=cols_before,
        columns_after=len(df.columns),
        changes={
            "removed_columns": existing_cols,
            "not_found": missing_cols
        }
    )


@router.post("/filter-rows", response_model=CleaningResponse)
async def filter_rows(request: FilterRowsRequest):
    """
    Filter rows based on column values.
    
    Operators:
    - eq: Equal to value
    - ne: Not equal to value
    - gt, lt, ge, le: Greater/less than (or equal)
    - in: Value in list
    - notin: Value not in list
    - isna: Value is null/NaN
    - notna: Value is not null/NaN
    """
    df = _load_csv(request.csv_path)
    rows_before = len(df)
    cols_before = len(df.columns)
    
    if request.column not in df.columns:
        raise HTTPException(status_code=400, detail=f"Column '{request.column}' not found")
    
    col = df[request.column]
    
    if request.operator == "eq":
        mask = col == request.value
    elif request.operator == "ne":
        mask = col != request.value
    elif request.operator == "gt":
        mask = col > request.value
    elif request.operator == "lt":
        mask = col < request.value
    elif request.operator == "ge":
        mask = col >= request.value
    elif request.operator == "le":
        mask = col <= request.value
    elif request.operator == "in":
        mask = col.isin(request.value if isinstance(request.value, list) else [request.value])
    elif request.operator == "notin":
        mask = ~col.isin(request.value if isinstance(request.value, list) else [request.value])
    elif request.operator == "isna":
        mask = col.isna()
    elif request.operator == "notna":
        mask = col.notna()
    else:
        raise HTTPException(status_code=400, detail=f"Unknown operator: {request.operator}")
    
    df = df[mask]
    
    output_path = _save_csv(df, request.save_path, request.csv_path)
    
    return CleaningResponse(
        success=True,
        message=f"Filtered rows where {request.column} {request.operator} {request.value}",
        input_path=request.csv_path,
        output_path=output_path,
        rows_before=rows_before,
        rows_after=len(df),
        columns_before=cols_before,
        columns_after=len(df.columns),
        changes={
            "filter_condition": f"{request.column} {request.operator} {request.value}",
            "rows_kept": len(df),
            "rows_removed": rows_before - len(df)
        }
    )


@router.post("/rename-columns", response_model=CleaningResponse)
async def rename_columns(request: RenameColumnsRequest):
    """
    Rename columns in the dataset.
    """
    df = _load_csv(request.csv_path)
    rows_before = len(df)
    cols_before = len(df.columns)
    
    # Find existing columns
    rename_map = {k: v for k, v in request.mapping.items() if k in df.columns}
    not_found = [k for k in request.mapping.keys() if k not in df.columns]
    
    if not rename_map:
        raise HTTPException(status_code=400, detail=f"No specified columns found. Available: {list(df.columns)[:20]}")
    
    df = df.rename(columns=rename_map)
    
    output_path = _save_csv(df, request.save_path, request.csv_path)
    
    return CleaningResponse(
        success=True,
        message=f"Renamed {len(rename_map)} column(s)",
        input_path=request.csv_path,
        output_path=output_path,
        rows_before=rows_before,
        rows_after=len(df),
        columns_before=cols_before,
        columns_after=len(df.columns),
        changes={
            "renamed": rename_map,
            "not_found": not_found
        }
    )


@router.post("/column-info", response_model=ColumnInfoResponse)
async def get_column_info(request: ColumnInfoRequest):
    """
    Get detailed information about all columns in the dataset.
    
    Returns for each column:
    - Data type
    - Null count and percentage
    - Unique value count
    - For numeric: min, max, mean, std
    - For categorical: top 10 value counts
    """
    df = _load_csv(request.csv_path)
    
    return ColumnInfoResponse(
        success=True,
        csv_path=request.csv_path,
        row_count=len(df),
        column_count=len(df.columns),
        columns=_get_column_info(df)
    )


@router.post("/auto-clean", response_model=CleaningResponse)
async def auto_clean_dataset(request: AutoCleanRequest):
    """
    Automatically clean the dataset.
    
    Operations (configurable):
    1. Remove duplicate rows
    2. Handle missing values (drop columns > threshold, impute others)
    3. Remove constant columns (all same value)
    4. Remove high-cardinality ID-like columns
    
    Always preserves the target column if specified.
    """
    df = _load_csv(request.csv_path)
    rows_before = len(df)
    cols_before = len(df.columns)
    
    changes = {
        "duplicates_removed": 0,
        "columns_dropped_missing": [],
        "columns_dropped_constant": [],
        "columns_dropped_high_cardinality": [],
        "missing_values_imputed": {}
    }
    
    # Columns to protect
    protected = [request.target_column] if request.target_column else []
    
    # 1. Remove duplicates
    if request.remove_duplicates:
        before = len(df)
        df = df.drop_duplicates()
        changes["duplicates_removed"] = before - len(df)
    
    # 2. Handle missing values
    if request.handle_missing:
        for col in df.columns:
            if col in protected:
                continue
            
            missing_ratio = df[col].isna().mean()
            
            if missing_ratio > request.missing_threshold:
                df = df.drop(columns=[col])
                changes["columns_dropped_missing"].append(col)
            elif missing_ratio > 0:
                # Impute
                if pd.api.types.is_numeric_dtype(df[col]):
                    fill_value = df[col].median()
                    df[col] = df[col].fillna(fill_value)
                    changes["missing_values_imputed"][col] = {"strategy": "median", "value": float(fill_value)}
                else:
                    fill_value = df[col].mode().iloc[0] if not df[col].mode().empty else "Unknown"
                    df[col] = df[col].fillna(fill_value)
                    changes["missing_values_imputed"][col] = {"strategy": "mode", "value": str(fill_value)}
    
    # 3. Remove constant columns
    if request.remove_constant:
        for col in df.columns:
            if col in protected:
                continue
            
            if df[col].nunique() <= 1:
                df = df.drop(columns=[col])
                changes["columns_dropped_constant"].append(col)
    
    # 4. Remove high-cardinality ID-like columns
    if request.remove_high_cardinality:
        for col in df.columns:
            if col in protected:
                continue
            
            # Check if likely an ID column
            unique_ratio = df[col].nunique() / len(df)
            if unique_ratio > request.cardinality_threshold:
                # Additional checks: is it string-like or numeric sequential?
                if df[col].dtype == 'object' or (pd.api.types.is_numeric_dtype(df[col]) and 
                    df[col].is_monotonic_increasing):
                    df = df.drop(columns=[col])
                    changes["columns_dropped_high_cardinality"].append(col)
    
    output_path = _save_csv(df, request.save_path, request.csv_path)
    
    return CleaningResponse(
        success=True,
        message="Auto-cleaned dataset",
        input_path=request.csv_path,
        output_path=output_path,
        rows_before=rows_before,
        rows_after=len(df),
        columns_before=cols_before,
        columns_after=len(df.columns),
        changes=changes
    )


# =============================================================================
# Health Check
# =============================================================================

@router.get("/health")
async def cleaning_health():
    """Health check for cleaning routes"""
    return {"status": "healthy", "module": "cleaning"}
