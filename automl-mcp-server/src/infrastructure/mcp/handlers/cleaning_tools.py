"""
Data Cleaning Tools Module

MCP tools for data preprocessing and cleaning operations.
Enables AI agents to transform and prepare data for analysis.
"""
import base64
import io
import json
import logging
import os
from datetime import datetime
from typing import Optional, List, Dict, Any

import pandas as pd
import numpy as np
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)


def register_cleaning_tools(mcp: FastMCP, automl_client) -> None:
    """Register data cleaning tools with MCP server"""
    
    from .stats_client import StatsClient
    stats_client = StatsClient()
    
    # ==================== HELPER FUNCTIONS ====================
    
    def _parse_csv(csv_path: str) -> pd.DataFrame:
        """Load CSV from path"""
        return pd.read_csv(csv_path)
    
    def _get_csv_content(df: pd.DataFrame) -> str:
        """Convert DataFrame to CSV string (in-memory, no file write).
        
        All cleaned data is returned as CSV content for:
        - Direct use by Agent/user
        - Upload to MinIO if permanent storage needed
        - Store in Redis if temporary storage needed
        """
        return df.to_csv(index=False)
    
    # ==================== COLUMN TRANSFORMATION TOOLS ====================
    
    @mcp.tool()
    async def convert_to_binary(
        csv_path: str,
        column: str,
        mapping: Dict[str, int],
        user_id: str = "default",
        save_result: bool = True,
    ) -> dict:
        """
        🔄 Convert a column to binary (0/1) format.
        
        Essential for propensity score analysis and many ML algorithms
        that require binary treatment indicators.
        
        Args:
            csv_path: Path to CSV file (e.g., /data/sample_data/file.csv or /data/projects/my_project/data/file.csv)
            column: Column name to convert
            mapping: Dict mapping original values to 0 or 1
                    e.g., {"200": 0, "400": 1} or {"control": 0, "treatment": 1}
            user_id: User ID for tracking
            save_result: Whether to return csv_content for upload
        
        Returns:
            status: "success" or "error"
            original_values: Unique values before conversion
            new_values: Values after conversion (should be 0 and 1)
            csv_content: Processed CSV (if save_result=True) - upload to MinIO or use directly
            preview: Sample of converted data
        
        Example:
            # Convert Ropica dosage to binary treatment indicator
            convert_to_binary(
                csv_path="/data/sample_data/painless.csv",
                column="Ropica_ML",
                mapping={"200": 0, "400": 1},
                user_id="eric"
            )
        """
        try:
            df = _parse_csv(csv_path)
            
            if column not in df.columns:
                return {
                    "status": "error",
                    "error": f"Column '{column}' not found",
                    "available_columns": list(df.columns)[:20],
                }
            
            # Get original values
            original_values = df[column].dropna().unique().tolist()
            
            # Convert mapping keys to match column dtype
            col_dtype = df[column].dtype
            converted_mapping = {}
            for k, v in mapping.items():
                if pd.api.types.is_numeric_dtype(col_dtype):
                    try:
                        converted_mapping[float(k)] = v
                        converted_mapping[int(float(k))] = v
                    except:
                        converted_mapping[k] = v
                else:
                    converted_mapping[str(k)] = v
            
            # Apply mapping
            new_column_name = f"{column}_binary"
            df[new_column_name] = df[column].map(converted_mapping)
            
            # Check for unmapped values
            unmapped = df[df[new_column_name].isna() & df[column].notna()][column].unique()
            
            result = {
                "status": "success",
                "column": column,
                "new_column": new_column_name,
                "original_values": [str(v) for v in original_values],
                "mapping_applied": {str(k): v for k, v in mapping.items()},
                "new_values": df[new_column_name].dropna().unique().tolist(),
                "rows_converted": int(df[new_column_name].notna().sum()),
                "rows_unmapped": int(len(unmapped)),
            }
            
            if len(unmapped) > 0:
                result["unmapped_values"] = [str(v) for v in unmapped[:10]]
                result["warning"] = f"Some values were not mapped: {unmapped[:5]}"
            
            # Return CSV content in memory (no local file storage)
            if save_result:
                result["csv_content"] = _get_csv_content(df)
                result["message"] = f"Binary column '{new_column_name}' created. Use csv_content for further analysis or upload to MinIO."
            else:
                result["message"] = f"Binary column '{new_column_name}' created (preview only)"
            
            # Preview
            result["preview"] = df[[column, new_column_name]].head(5).to_dict('records')
            
            return result
            
        except Exception as e:
            logger.exception(f"Error in convert_to_binary: {e}")
            return {"status": "error", "error": str(e)}
    
    @mcp.tool()
    async def encode_categorical(
        csv_path: str,
        column: str,
        method: str = "label",
        user_id: str = "default",
        save_result: bool = True,
    ) -> dict:
        """
        🏷️ Encode categorical column to numeric.
        
        Methods:
        - label: Assign integers 0, 1, 2, ... to each category
        - onehot: Create binary columns for each category
        - ordinal: Like label but preserves order (if provided)
        
        Args:
            csv_path: Path to CSV file
            column: Column name to encode
            method: "label", "onehot", or "ordinal"
            user_id: User ID
            save_result: Whether to return csv_content
        
        Returns:
            status: "success" or "error"
            encoding_map: Mapping of original values to encoded values
            new_columns: List of new column names created
            csv_content: Processed CSV (if save_result=True)
        
        Example:
            encode_categorical(
                csv_path="/data/sample_data/data.csv",
                column="gender",
                method="label"
            )
            # Result: gender -> gender_encoded (0=Female, 1=Male)
        """
        try:
            df = _parse_csv(csv_path)
            
            if column not in df.columns:
                return {
                    "status": "error",
                    "error": f"Column '{column}' not found",
                }
            
            unique_values = df[column].dropna().unique().tolist()
            
            if method == "label":
                # Label encoding
                encoding_map = {v: i for i, v in enumerate(sorted(str(v) for v in unique_values))}
                new_col = f"{column}_encoded"
                df[new_col] = df[column].astype(str).map(encoding_map)
                new_columns = [new_col]
                
            elif method == "onehot":
                # One-hot encoding
                dummies = pd.get_dummies(df[column], prefix=column, dummy_na=False)
                df = pd.concat([df, dummies], axis=1)
                new_columns = list(dummies.columns)
                encoding_map = {col: f"{column}_{col}" for col in unique_values}
                
            else:
                return {"status": "error", "error": f"Unknown method: {method}"}
            
            result = {
                "status": "success",
                "column": column,
                "method": method,
                "encoding_map": {str(k): v for k, v in encoding_map.items()},
                "new_columns": new_columns,
                "unique_values_count": len(unique_values),
            }
            
            if save_result:
                result["csv_content"] = _get_csv_content(df)
                result["message"] = "Encoding complete. Use csv_content for further analysis or upload to MinIO."
            
            return result
            
        except Exception as e:
            logger.exception(f"Error in encode_categorical: {e}")
            return {"status": "error", "error": str(e)}
    
    @mcp.tool()
    async def handle_missing_values(
        csv_path: str,
        strategy: str = "auto",
        columns: Optional[List[str]] = None,
        fill_value: Optional[Any] = None,
        user_id: str = "default",
        save_result: bool = True,
    ) -> dict:
        """
        🔧 Handle missing values in dataset.
        
        Strategies:
        - auto: Numeric → median, Categorical → mode
        - mean: Fill with column mean (numeric only)
        - median: Fill with column median (numeric only)
        - mode: Fill with most frequent value
        - constant: Fill with specified value
        - drop_rows: Remove rows with missing values
        - drop_columns: Remove columns with any missing values
        
        Args:
            csv_path: Path to CSV file
            strategy: How to handle missing values
            columns: Specific columns to process (None = all)
            fill_value: Value to use for "constant" strategy
            user_id: User ID
            save_result: Whether to return csv_content
        
        Returns:
            status: "success" or "error"
            columns_processed: List of processed columns
            missing_before: Missing count before
            missing_after: Missing count after
            csv_content: Processed CSV (if save_result=True)
        
        Example:
            handle_missing_values(
                csv_path="/data/sample_data/data.csv",
                strategy="auto"
            )
        """
        try:
            df = _parse_csv(csv_path)
            
            missing_before = df.isnull().sum().sum()
            
            if columns:
                target_cols = [c for c in columns if c in df.columns]
            else:
                target_cols = df.columns.tolist()
            
            processed = []
            
            for col in target_cols:
                if df[col].isnull().sum() == 0:
                    continue
                
                if strategy == "auto":
                    if pd.api.types.is_numeric_dtype(df[col]):
                        df[col] = df[col].fillna(df[col].median())
                    else:
                        mode_val = df[col].mode()
                        if len(mode_val) > 0:
                            df[col] = df[col].fillna(mode_val[0])
                            
                elif strategy == "mean":
                    if pd.api.types.is_numeric_dtype(df[col]):
                        df[col] = df[col].fillna(df[col].mean())
                        
                elif strategy == "median":
                    if pd.api.types.is_numeric_dtype(df[col]):
                        df[col] = df[col].fillna(df[col].median())
                        
                elif strategy == "mode":
                    mode_val = df[col].mode()
                    if len(mode_val) > 0:
                        df[col] = df[col].fillna(mode_val[0])
                        
                elif strategy == "constant":
                    df[col] = df[col].fillna(fill_value)
                    
                elif strategy == "drop_rows":
                    df = df.dropna(subset=[col])
                    
                elif strategy == "drop_columns":
                    if df[col].isnull().any():
                        df = df.drop(columns=[col])
                        
                processed.append(col)
            
            missing_after = df.isnull().sum().sum()
            
            result = {
                "status": "success",
                "strategy": strategy,
                "columns_processed": processed,
                "missing_before": int(missing_before),
                "missing_after": int(missing_after),
                "missing_removed": int(missing_before - missing_after),
                "rows_after": len(df),
                "columns_after": len(df.columns),
            }
            
            if save_result:
                result["csv_content"] = _get_csv_content(df)
                result["message"] = "Missing values handled. Use csv_content for further analysis or upload to MinIO."
            
            return result
            
        except Exception as e:
            logger.exception(f"Error in handle_missing_values: {e}")
            return {"status": "error", "error": str(e)}
    
    @mcp.tool()
    async def remove_columns(
        csv_path: str,
        columns: List[str],
        user_id: str = "default",
        save_result: bool = True,
    ) -> dict:
        """
        🗑️ Remove specified columns from dataset.
        
        Use this to:
        - Remove ID columns before analysis
        - Drop constant columns
        - Exclude irrelevant features
        - Remove PII columns
        
        Args:
            csv_path: Path to CSV file
            columns: List of column names to remove
            user_id: User ID
            save_result: Whether to save result
        
        Returns:
            status: "success" or "error"
            columns_removed: Successfully removed columns
            columns_not_found: Columns that didn't exist
            columns_remaining: Number of columns after removal
            output_path: Path to saved file
        """
        try:
            df = _parse_csv(csv_path)
            
            existing = [c for c in columns if c in df.columns]
            not_found = [c for c in columns if c not in df.columns]
            
            df = df.drop(columns=existing, errors='ignore')
            
            result = {
                "status": "success",
                "columns_removed": existing,
                "columns_not_found": not_found,
                "columns_remaining": len(df.columns),
                "remaining_columns": list(df.columns)[:20],
            }
            
            if save_result:
                result["csv_content"] = _get_csv_content(df)
                result["message"] = "Columns removed. Use csv_content for further analysis or upload to MinIO."
            
            return result
            
        except Exception as e:
            logger.exception(f"Error in remove_columns: {e}")
            return {"status": "error", "error": str(e)}
    
    @mcp.tool()
    async def rename_columns(
        csv_path: str,
        mapping: Dict[str, str],
        user_id: str = "default",
        save_result: bool = True,
    ) -> dict:
        """
        ✏️ Rename columns in dataset.
        
        Args:
            csv_path: Path to CSV file
            mapping: Dict of old_name -> new_name
            user_id: User ID
            save_result: Whether to save result
        
        Returns:
            status: "success" or "error"
            columns_renamed: Successfully renamed columns
            output_path: Path to saved file
        
        Example:
            rename_columns(
                csv_path="/data/file.csv",
                mapping={"old_name": "new_name", "年齡": "age"}
            )
        """
        try:
            df = _parse_csv(csv_path)
            
            existing_mapping = {k: v for k, v in mapping.items() if k in df.columns}
            not_found = [k for k in mapping.keys() if k not in df.columns]
            
            df = df.rename(columns=existing_mapping)
            
            result = {
                "status": "success",
                "columns_renamed": existing_mapping,
                "columns_not_found": not_found,
                "new_columns": list(df.columns)[:20],
            }
            
            if save_result:
                result["csv_content"] = _get_csv_content(df)
                result["message"] = "Columns renamed. Use csv_content for further analysis or upload to MinIO."
            
            return result
            
        except Exception as e:
            logger.exception(f"Error in rename_columns: {e}")
            return {"status": "error", "error": str(e)}
    
    @mcp.tool()
    async def filter_rows(
        csv_path: str,
        column: str,
        condition: str,
        value: Any,
        user_id: str = "default",
        save_result: bool = True,
    ) -> dict:
        """
        🔍 Filter rows based on condition.
        
        Conditions:
        - eq: Equal to value
        - ne: Not equal to value
        - gt: Greater than value
        - lt: Less than value
        - gte: Greater than or equal
        - lte: Less than or equal
        - in: Value is in list
        - notin: Value is not in list
        - notna: Value is not missing
        - isna: Value is missing
        
        Args:
            csv_path: Path to CSV file
            column: Column to filter on
            condition: Filter condition (eq, ne, gt, lt, gte, lte, in, notin, notna, isna)
            value: Value to compare against (use list for in/notin)
            user_id: User ID
            save_result: Whether to save result
        
        Returns:
            status: "success" or "error"
            rows_before: Row count before filter
            rows_after: Row count after filter
            rows_removed: Number of rows filtered out
            output_path: Path to saved file
        
        Example:
            # Keep only rows where age > 18
            filter_rows(csv_path="...", column="age", condition="gt", value=18)
            
            # Keep rows where category is in ['A', 'B']
            filter_rows(csv_path="...", column="category", condition="in", value=["A", "B"])
        """
        try:
            df = _parse_csv(csv_path)
            rows_before = len(df)
            
            if column not in df.columns:
                return {"status": "error", "error": f"Column '{column}' not found"}
            
            if condition == "eq":
                df = df[df[column] == value]
            elif condition == "ne":
                df = df[df[column] != value]
            elif condition == "gt":
                df = df[df[column] > value]
            elif condition == "lt":
                df = df[df[column] < value]
            elif condition == "gte":
                df = df[df[column] >= value]
            elif condition == "lte":
                df = df[df[column] <= value]
            elif condition == "in":
                df = df[df[column].isin(value)]
            elif condition == "notin":
                df = df[~df[column].isin(value)]
            elif condition == "notna":
                df = df[df[column].notna()]
            elif condition == "isna":
                df = df[df[column].isna()]
            else:
                return {"status": "error", "error": f"Unknown condition: {condition}"}
            
            rows_after = len(df)
            
            result = {
                "status": "success",
                "column": column,
                "condition": condition,
                "value": str(value),
                "rows_before": rows_before,
                "rows_after": rows_after,
                "rows_removed": rows_before - rows_after,
            }
            
            if save_result:
                result["csv_content"] = _get_csv_content(df)
                result["message"] = "Rows filtered. Use csv_content for further analysis or upload to MinIO."
            
            return result
            
        except Exception as e:
            logger.exception(f"Error in filter_rows: {e}")
            return {"status": "error", "error": str(e)}
    
    @mcp.tool()
    async def get_column_info(
        csv_path: str,
        columns: Optional[List[str]] = None,
    ) -> dict:
        """
        📋 Get detailed information about columns.
        
        Useful for understanding data before cleaning.
        
        Args:
            csv_path: Path to CSV file
            columns: Specific columns to analyze (None = all)
        
        Returns:
            columns: Dict with info for each column including:
                - dtype: Data type
                - unique_count: Number of unique values
                - missing_count: Number of missing values
                - missing_pct: Percentage missing
                - sample_values: Sample of values
                - is_numeric: Whether column is numeric
                - is_binary: Whether column has only 2 unique values
        """
        try:
            df = _parse_csv(csv_path)
            
            if columns:
                target_cols = [c for c in columns if c in df.columns]
            else:
                target_cols = df.columns.tolist()
            
            column_info = {}
            
            for col in target_cols:
                unique_vals = df[col].dropna().unique()
                missing = df[col].isnull().sum()
                
                info = {
                    "dtype": str(df[col].dtype),
                    "unique_count": len(unique_vals),
                    "missing_count": int(missing),
                    "missing_pct": round(missing / len(df) * 100, 2),
                    "is_numeric": bool(pd.api.types.is_numeric_dtype(df[col])),
                    "is_binary": len(unique_vals) == 2,
                    "sample_values": [str(v) for v in unique_vals[:5]],
                }
                
                if pd.api.types.is_numeric_dtype(df[col]):
                    info["min"] = float(df[col].min()) if not df[col].isnull().all() else None
                    info["max"] = float(df[col].max()) if not df[col].isnull().all() else None
                    info["mean"] = float(df[col].mean()) if not df[col].isnull().all() else None
                
                column_info[col] = info
            
            # Identify potential issues
            binary_columns = [c for c, i in column_info.items() if i["is_binary"]]
            high_missing = [c for c, i in column_info.items() if i["missing_pct"] > 20]
            constant_columns = [c for c, i in column_info.items() if i["unique_count"] <= 1]
            
            return {
                "status": "success",
                "total_rows": len(df),
                "total_columns": len(df.columns),
                "columns": column_info,
                "summary": {
                    "binary_columns": binary_columns,
                    "high_missing_columns": high_missing,
                    "constant_columns": constant_columns,
                },
                "recommendations": _generate_recommendations(column_info),
            }
            
        except Exception as e:
            logger.exception(f"Error in get_column_info: {e}")
            return {"status": "error", "error": str(e)}
    
    def _generate_recommendations(column_info: dict) -> List[str]:
        """Generate cleaning recommendations based on column info"""
        recs = []
        
        for col, info in column_info.items():
            if info["is_binary"] and info["is_numeric"]:
                vals = info["sample_values"]
                if "0" not in vals or "1" not in vals:
                    recs.append(
                        f"Column '{col}' is binary but not 0/1. "
                        f"Consider using convert_to_binary() for propensity analysis."
                    )
            
            if info["missing_pct"] > 50:
                recs.append(
                    f"Column '{col}' has {info['missing_pct']}% missing. "
                    "Consider dropping this column."
                )
            elif info["missing_pct"] > 20:
                recs.append(
                    f"Column '{col}' has {info['missing_pct']}% missing. "
                    "Consider imputation with handle_missing_values()."
                )
            
            if info["unique_count"] <= 1:
                recs.append(
                    f"Column '{col}' is constant. Consider removing with remove_columns()."
                )
        
        return recs[:10]  # Limit recommendations
    
    logger.info("Registered data cleaning tools: convert_to_binary, encode_categorical, "
                "handle_missing_values, remove_columns, rename_columns, filter_rows, get_column_info")
