"""
Stats Worker Tasks Bridge

This module provides access to stats-worker analysis functions
for use in the MCP server.
"""
import os
import sys

# Add stats-worker path for imports
stats_worker_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..', 'stats-worker', 'src')
if stats_worker_path not in sys.path:
    sys.path.insert(0, os.path.abspath(stats_worker_path))

try:
    from tasks.advanced_analysis import (
        EnhancedCorrelationResult,
        GroupComparisonResult,
        MissingValueAnalysis,
        MulticollinearityAnalysis,
        analyze_missing_values,
        compare_distributions,
        compute_enhanced_correlation,
        compute_vif,
        run_enhanced_analysis,
    )
    from tasks.auto_analyze_task import run_auto_analyze

    # Phase 6: Power Analysis
    from tasks.power_analysis import (
        # Phase 6.2: ANOVA and Chi-square
        ANOVAPowerAnalysis,
        ANOVAPowerResult,
        ChiSquarePowerAnalysis,
        ChiSquarePowerResult,
        EffectSizeType,
        PowerAnalysisResult,
        ProportionPowerAnalysis,
        # Phase 6.3: Survival Analysis Power
        SurvivalPowerAnalysis,
        SurvivalPowerResult,
        TestType,
        TTestPowerAnalysis,
        calculate_anova_power,
        calculate_anova_sample_size,
        calculate_chisquare_power,
        calculate_chisquare_sample_size,
        calculate_proportion_power,
        calculate_proportion_sample_size,
        calculate_survival_events,
        calculate_survival_from_medians,
        calculate_survival_power,
        calculate_survival_sample_size,
        calculate_ttest_power,
        calculate_ttest_sample_size,
        cohens_d_from_means,
        cohens_f_from_eta_squared,
        cohens_f_from_means,
        cohens_h_from_proportions,
        cramers_v_from_table,
        effect_size_w_from_proportions,
        eta_squared_from_cohens_f,
        hazard_ratio_to_log_hr,
        interpret_effect_size,
    )
    from tasks.propensity_score import (
        BalanceAssessor,
        IPWeighting,
        PropensityScoreEstimator,
        PropensityScoreMatcher,
        assess_balance,
        estimate_propensity_scores,
        estimate_treatment_effect,
        match_propensity_scores,
        propensity_score_analysis,
    )
    from tasks.roc_analysis import (
        AUCComparisonResult,
        CalibrationAnalyzer,
        CalibrationResult,
        DeLongTest,
        NetBenefitAnalyzer,
        PrecisionRecallAnalyzer,
        PrecisionRecallResult,
        ROCAnalyzer,
        ROCCurveResult,
        ROCPoint,
        analyze_calibration,
        # Phase 5A: Enhanced Interactive Functions
        compare_multiple_models,
        compare_roc_curves,
        compute_precision_recall,
        compute_roc_curve,
        find_optimal_threshold,
        full_classifier_evaluation,
        generate_publication_report,
        threshold_analysis,
    )
    from tasks.survival_analysis import (
        CoxPHFitter,
        KaplanMeierEstimator,
        compare_survival_curves,
        cox_regression,
        kaplan_meier_analysis,
        log_rank_test,
        survival_summary,
    )
    from tasks.tableone_generator import (
        TableOneConfig,
        TableOneGenerator,
        TableOneResult,
        generate_tableone,
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
        # ROC/AUC Analysis exports
        "ROCPoint",
        "ROCCurveResult",
        "AUCComparisonResult",
        "CalibrationResult",
        "PrecisionRecallResult",
        "ROCAnalyzer",
        "DeLongTest",
        "CalibrationAnalyzer",
        "PrecisionRecallAnalyzer",
        "NetBenefitAnalyzer",
        "compute_roc_curve",
        "compare_roc_curves",
        "analyze_calibration",
        "compute_precision_recall",
        "find_optimal_threshold",
        "full_classifier_evaluation",
        # Phase 5A: Enhanced Interactive Functions
        "compare_multiple_models",
        "threshold_analysis",
        "generate_publication_report",
        # Phase 6: Power Analysis
        "TTestPowerAnalysis",
        "ProportionPowerAnalysis",
        "PowerAnalysisResult",
        "calculate_ttest_sample_size",
        "calculate_ttest_power",
        "calculate_proportion_sample_size",
        "calculate_proportion_power",
        "cohens_d_from_means",
        "cohens_h_from_proportions",
        "interpret_effect_size",
        "EffectSizeType",
        "TestType",
        # Phase 6.2: ANOVA and Chi-square
        "ANOVAPowerAnalysis",
        "ANOVAPowerResult",
        "ChiSquarePowerAnalysis",
        "ChiSquarePowerResult",
        "calculate_anova_sample_size",
        "calculate_anova_power",
        "calculate_chisquare_sample_size",
        "calculate_chisquare_power",
        "cohens_f_from_means",
        "cohens_f_from_eta_squared",
        "eta_squared_from_cohens_f",
        "effect_size_w_from_proportions",
        "cramers_v_from_table",
        # Phase 6.3: Survival Analysis Power
        "SurvivalPowerAnalysis",
        "SurvivalPowerResult",
        "calculate_survival_events",
        "calculate_survival_sample_size",
        "calculate_survival_power",
        "calculate_survival_from_medians",
        "hazard_ratio_to_log_hr",
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

    # ROC/AUC Analysis stubs
    def compute_roc_curve(*args, **kwargs):
        raise ImportError("stats-worker tasks not available")

    def compare_roc_curves(*args, **kwargs):
        raise ImportError("stats-worker tasks not available")

    def analyze_calibration(*args, **kwargs):
        raise ImportError("stats-worker tasks not available")

    def compute_precision_recall(*args, **kwargs):
        raise ImportError("stats-worker tasks not available")

    def find_optimal_threshold(*args, **kwargs):
        raise ImportError("stats-worker tasks not available")

    def full_classifier_evaluation(*args, **kwargs):
        raise ImportError("stats-worker tasks not available")

    class ROCPoint:
        def __init__(self, *args, **kwargs):
            raise ImportError("stats-worker tasks not available")

    class ROCCurveResult:
        def __init__(self, *args, **kwargs):
            raise ImportError("stats-worker tasks not available")

    class AUCComparisonResult:
        def __init__(self, *args, **kwargs):
            raise ImportError("stats-worker tasks not available")

    class CalibrationResult:
        def __init__(self, *args, **kwargs):
            raise ImportError("stats-worker tasks not available")

    class PrecisionRecallResult:
        def __init__(self, *args, **kwargs):
            raise ImportError("stats-worker tasks not available")

    class ROCAnalyzer:
        def __init__(self, *args, **kwargs):
            raise ImportError("stats-worker tasks not available")

    class DeLongTest:
        def __init__(self, *args, **kwargs):
            raise ImportError("stats-worker tasks not available")

    class CalibrationAnalyzer:
        def __init__(self, *args, **kwargs):
            raise ImportError("stats-worker tasks not available")

    class PrecisionRecallAnalyzer:
        def __init__(self, *args, **kwargs):
            raise ImportError("stats-worker tasks not available")

    class NetBenefitAnalyzer:
        def __init__(self, *args, **kwargs):
            raise ImportError("stats-worker tasks not available")

    # Phase 5A: Enhanced Interactive Functions stubs
    def compare_multiple_models(*args, **kwargs):
        raise ImportError("stats-worker tasks not available")

    def threshold_analysis(*args, **kwargs):
        raise ImportError("stats-worker tasks not available")

    def generate_publication_report(*args, **kwargs):
        raise ImportError("stats-worker tasks not available")

    # Phase 6: Power Analysis stubs
    class TTestPowerAnalysis:
        def __init__(self, *args, **kwargs):
            raise ImportError("stats-worker tasks not available")

    class ProportionPowerAnalysis:
        def __init__(self, *args, **kwargs):
            raise ImportError("stats-worker tasks not available")

    class PowerAnalysisResult:
        def __init__(self, *args, **kwargs):
            raise ImportError("stats-worker tasks not available")

    def calculate_ttest_sample_size(*args, **kwargs):
        raise ImportError("stats-worker tasks not available")

    def calculate_ttest_power(*args, **kwargs):
        raise ImportError("stats-worker tasks not available")

    def calculate_proportion_sample_size(*args, **kwargs):
        raise ImportError("stats-worker tasks not available")

    def calculate_proportion_power(*args, **kwargs):
        raise ImportError("stats-worker tasks not available")

    def cohens_d_from_means(*args, **kwargs):
        raise ImportError("stats-worker tasks not available")

    def cohens_h_from_proportions(*args, **kwargs):
        raise ImportError("stats-worker tasks not available")

    def interpret_effect_size(*args, **kwargs):
        raise ImportError("stats-worker tasks not available")

    class EffectSizeType:
        def __init__(self, *args, **kwargs):
            raise ImportError("stats-worker tasks not available")

    class TestType:
        def __init__(self, *args, **kwargs):
            raise ImportError("stats-worker tasks not available")

    # Phase 6.2: ANOVA and Chi-square stubs
    class ANOVAPowerAnalysis:
        def __init__(self, *args, **kwargs):
            raise ImportError("stats-worker tasks not available")

    class ANOVAPowerResult:
        def __init__(self, *args, **kwargs):
            raise ImportError("stats-worker tasks not available")

    class ChiSquarePowerAnalysis:
        def __init__(self, *args, **kwargs):
            raise ImportError("stats-worker tasks not available")

    class ChiSquarePowerResult:
        def __init__(self, *args, **kwargs):
            raise ImportError("stats-worker tasks not available")

    def calculate_anova_sample_size(*args, **kwargs):
        raise ImportError("stats-worker tasks not available")

    def calculate_anova_power(*args, **kwargs):
        raise ImportError("stats-worker tasks not available")

    def calculate_chisquare_sample_size(*args, **kwargs):
        raise ImportError("stats-worker tasks not available")

    def calculate_chisquare_power(*args, **kwargs):
        raise ImportError("stats-worker tasks not available")

    def cohens_f_from_means(*args, **kwargs):
        raise ImportError("stats-worker tasks not available")

    def cohens_f_from_eta_squared(*args, **kwargs):
        raise ImportError("stats-worker tasks not available")

    def eta_squared_from_cohens_f(*args, **kwargs):
        raise ImportError("stats-worker tasks not available")

    def effect_size_w_from_proportions(*args, **kwargs):
        raise ImportError("stats-worker tasks not available")

    def cramers_v_from_table(*args, **kwargs):
        raise ImportError("stats-worker tasks not available")

    # Phase 6.3: Survival Analysis Power stubs
    class SurvivalPowerAnalysis:
        def __init__(self, *args, **kwargs):
            raise ImportError("stats-worker tasks not available")

    class SurvivalPowerResult:
        def __init__(self, *args, **kwargs):
            raise ImportError("stats-worker tasks not available")

    def calculate_survival_events(*args, **kwargs):
        raise ImportError("stats-worker tasks not available")

    def calculate_survival_sample_size(*args, **kwargs):
        raise ImportError("stats-worker tasks not available")

    def calculate_survival_power(*args, **kwargs):
        raise ImportError("stats-worker tasks not available")

    def calculate_survival_from_medians(*args, **kwargs):
        raise ImportError("stats-worker tasks not available")

    def hazard_ratio_to_log_hr(*args, **kwargs):
        raise ImportError("stats-worker tasks not available")
