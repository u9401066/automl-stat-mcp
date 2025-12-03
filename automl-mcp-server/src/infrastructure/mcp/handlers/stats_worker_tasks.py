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
    from tasks.survival_analysis import (
        kaplan_meier_analysis,
        cox_regression,
        log_rank_test,
        survival_summary,
        compare_survival_curves,
        KaplanMeierEstimator,
        CoxPHFitter,
    )
    from tasks.propensity_score import (
        estimate_propensity_scores,
        match_propensity_scores,
        estimate_treatment_effect,
        assess_balance,
        propensity_score_analysis,
        PropensityScoreEstimator,
        PropensityScoreMatcher,
        IPWeighting,
        BalanceAssessor,
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
        # Survival Analysis exports
        "kaplan_meier_analysis",
        "cox_regression",
        "log_rank_test",
        "survival_summary",
        "compare_survival_curves",
        "KaplanMeierEstimator",
        "CoxPHFitter",
        # Propensity Score exports
        "estimate_propensity_scores",
        "match_propensity_scores",
        "estimate_treatment_effect",
        "assess_balance",
        "propensity_score_analysis",
        "PropensityScoreEstimator",
        "PropensityScoreMatcher",
        "IPWeighting",
        "BalanceAssessor",
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
    
    # Survival Analysis stubs
    def kaplan_meier_analysis(*args, **kwargs):
        raise ImportError("stats-worker tasks not available")
    
    def cox_regression(*args, **kwargs):
        raise ImportError("stats-worker tasks not available")
    
    def log_rank_test(*args, **kwargs):
        raise ImportError("stats-worker tasks not available")
    
    def survival_summary(*args, **kwargs):
        raise ImportError("stats-worker tasks not available")
    
    def compare_survival_curves(*args, **kwargs):
        raise ImportError("stats-worker tasks not available")
    
    class KaplanMeierEstimator:
        def __init__(self, *args, **kwargs):
            raise ImportError("stats-worker tasks not available")
    
    class CoxPHFitter:
        def __init__(self, *args, **kwargs):
            raise ImportError("stats-worker tasks not available")

    # Propensity Score stubs
    def estimate_propensity_scores(*args, **kwargs):
        raise ImportError("stats-worker tasks not available")
    
    def match_propensity_scores(*args, **kwargs):
        raise ImportError("stats-worker tasks not available")
    
    def estimate_treatment_effect(*args, **kwargs):
        raise ImportError("stats-worker tasks not available")
    
    def assess_balance(*args, **kwargs):
        raise ImportError("stats-worker tasks not available")
    
    def propensity_score_analysis(*args, **kwargs):
        raise ImportError("stats-worker tasks not available")
    
    class PropensityScoreEstimator:
        def __init__(self, *args, **kwargs):
            raise ImportError("stats-worker tasks not available")
    
    class PropensityScoreMatcher:
        def __init__(self, *args, **kwargs):
            raise ImportError("stats-worker tasks not available")
    
    class IPWeighting:
        def __init__(self, *args, **kwargs):
            raise ImportError("stats-worker tasks not available")
    
    class BalanceAssessor:
        def __init__(self, *args, **kwargs):
            raise ImportError("stats-worker tasks not available")
