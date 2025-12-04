"""
Convenience Functions for Advanced Analysis

Run multiple analyses at once.

Contains:
    - run_enhanced_analysis: Run all analyses on a DataFrame
"""
import logging
from typing import Dict, Any, Optional

import pandas as pd
import numpy as np

from .correlation import compute_enhanced_correlation
from .distribution import compare_distributions
from .missing_data import analyze_missing_values
from .multicollinearity import compute_vif

logger = logging.getLogger(__name__)


def run_enhanced_analysis(
    df: pd.DataFrame,
    target_column: Optional[str] = None,
    include_vif: bool = True,
    include_missing_analysis: bool = True,
) -> Dict[str, Any]:
    """
    Run all enhanced analyses on a DataFrame.
    
    Args:
        df: DataFrame to analyze
        target_column: Optional target column for group comparisons
        include_vif: Whether to include VIF analysis
        include_missing_analysis: Whether to include missing value analysis
    
    Returns:
        Dictionary with all analysis results
    """
    results = {}
    
    # Enhanced correlation analysis
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if len(numeric_cols) >= 2:
        corr_result = compute_enhanced_correlation(df, numeric_cols)
        results["correlation_analysis"] = corr_result.to_dict()
    
    # Missing value analysis
    if include_missing_analysis:
        missing_result = analyze_missing_values(df)
        results["missing_analysis"] = missing_result.to_dict()
    
    # VIF analysis
    if include_vif and len(numeric_cols) >= 2:
        vif_result = compute_vif(df, numeric_cols)
        results["multicollinearity"] = vif_result.to_dict()
    
    # Group comparisons (if target specified)
    if target_column and target_column in df.columns:
        if df[target_column].nunique() <= 10:  # Categorical target
            results["group_comparisons"] = {}
            for col in numeric_cols:
                if col != target_column:
                    try:
                        comp_result = compare_distributions(df, col, target_column)
                        results["group_comparisons"][col] = comp_result.to_dict()
                    except Exception as e:
                        logger.warning(f"Group comparison failed for {col}: {e}")
    
    return results
