"""
Base utilities for advanced analysis.

Contains:
    - safe_round: Safe rounding with None/NaN handling
"""
import math
from typing import Optional


def safe_round(value: Optional[float], decimals: int = 4) -> Optional[float]:
    """
    Round a value safely, returning None for NaN/Inf.
    
    Args:
        value: Value to round
        decimals: Number of decimal places
        
    Returns:
        Rounded value or None
    """
    if value is None:
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    try:
        return round(float(value), decimals)
    except (TypeError, ValueError):
        return None
