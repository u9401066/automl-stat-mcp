"""
Stats Worker Tasks Bridge

This module provides access to stats-worker analysis functions
for use in the MCP server.
"""
import sys
import os

# Add stats-worker path for imports
stats_worker_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..', 'stats-worker', 'src')
if stats_worker_path not in sys.path:
    sys.path.insert(0, os.path.abspath(stats_worker_path))

try:
    from tasks.advanced_analysis import (
        compute_enhanced_correlation,
        compare_distributions,
        analyze_missing_values,
        compute_vif,
        run_enhanced_analysis,
        EnhancedCorrelationResult,
        GroupComparisonResult,
        MissingValueAnalysis,
        MulticollinearityAnalysis,
    )
    from tasks.auto_analyze_task import run_auto_analyze
    from tasks.tableone_generator import (
        generate_tableone,
        TableOneGenerator,
        TableOneConfig,
        TableOneResult,
    )
    
    __all__ = [
        "compute_enhanced_correlation",
        "compare_distributions", 
        "analyze_missing_values",
        "compute_vif",
        "run_enhanced_analysis",
        "run_auto_analyze",
        "EnhancedCorrelationResult",
        "GroupComparisonResult",
        "MissingValueAnalysis",
        "MulticollinearityAnalysis",
        # TableOne exports
        "generate_tableone",
        "TableOneGenerator",
        "TableOneConfig",
        "TableOneResult",
    ]
    
except ImportError as e:
    import logging
    logging.warning(f"Could not import stats-worker tasks: {e}")
    
    # Provide stub functions that raise helpful errors
    def compute_enhanced_correlation(*args, **kwargs):
        raise ImportError("stats-worker tasks not available")
    
    def compare_distributions(*args, **kwargs):
        raise ImportError("stats-worker tasks not available")
    
    def analyze_missing_values(*args, **kwargs):
        raise ImportError("stats-worker tasks not available")
    
    def compute_vif(*args, **kwargs):
        raise ImportError("stats-worker tasks not available")
    
    def run_enhanced_analysis(*args, **kwargs):
        raise ImportError("stats-worker tasks not available")
    
    def run_auto_analyze(*args, **kwargs):
        raise ImportError("stats-worker tasks not available")
    
    def generate_tableone(*args, **kwargs):
        raise ImportError("stats-worker tasks not available")
    
    class TableOneGenerator:
        def __init__(self, *args, **kwargs):
            raise ImportError("stats-worker tasks not available")
    
    class TableOneConfig:
        def __init__(self, *args, **kwargs):
            raise ImportError("stats-worker tasks not available")
    
    class TableOneResult:
        def __init__(self, *args, **kwargs):
            raise ImportError("stats-worker tasks not available")
