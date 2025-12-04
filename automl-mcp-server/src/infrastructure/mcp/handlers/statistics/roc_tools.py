"""
ROC/AUC Analysis Tools Module - Classifier Evaluation

This module provides MCP tools for ROC curve analysis,
calibration assessment, and classifier comparison.

Tools:
    - compute_roc_curve: ROC curve with AUC and CI
    - compare_roc_curves: DeLong test for model comparison
    - find_optimal_threshold: Threshold selection methods
    - analyze_calibration: Calibration analysis
    - full_classifier_evaluation: Complete evaluation report
    - compare_multiple_roc_curves: Multi-model comparison
    - interactive_threshold_analysis: Clinical threshold analysis
    - generate_roc_publication_report: Publication-ready report
"""
import base64
import json
from io import StringIO
from typing import List, Optional

import pandas as pd

from .base import logger


def register_roc_tools(mcp, stats_client):
    """Register all ROC/AUC analysis MCP tools."""
    
    @mcp.tool()
    async def compute_roc_curve(
        csv_content: str,
        y_true_col: str,
        y_score_col: str,
        pos_label: int = 1,
        confidence_level: float = 0.95,
        n_bootstrap: int = 1000,
        threshold_method: str = "youden",
        is_base64: bool = False,
    ) -> dict:
        """
        📈 Compute ROC curve with AUC and confidence intervals.
        
        Provides comprehensive ROC analysis including:
        - ROC curve points (FPR, TPR at each threshold)
        - AUC with DeLong or bootstrap confidence intervals
        - Optimal threshold selection
        - Sensitivity, specificity, PPV, NPV at optimal point
        
        Threshold selection methods:
        - youden: Maximizes Youden's J (sensitivity + specificity - 1)
        - cost: Minimizes misclassification cost (specify FP/FN costs)
        - sensitivity: Target minimum sensitivity (e.g., 0.90)
        - specificity: Target minimum specificity
        
        Args:
            csv_content: CSV data as string
            y_true_col: Column with true binary labels (0/1)
            y_score_col: Column with predicted probabilities
            pos_label: Value representing positive class (default 1)
            confidence_level: CI level (default 0.95 for 95% CI)
            n_bootstrap: Bootstrap samples for CI (default 1000)
            threshold_method: How to select optimal threshold
            is_base64: Set True if csv_content is base64 encoded
        
        Returns:
            auc: Area Under the ROC Curve
            auc_ci: Confidence interval {lower, upper}
            auc_se: Standard error of AUC
            optimal_threshold: Best threshold for classification
            optimal_metrics: Sens, spec, PPV, NPV at optimal threshold
            curve: List of ROC points (threshold, fpr, tpr, sens, spec)
            interpretation: Text description of model performance
        """
        try:
            if is_base64:
                csv_content = base64.b64decode(csv_content).decode('utf-8')
            df = pd.read_csv(StringIO(csv_content))
            
            from .stats_worker_tasks import compute_roc_curve as _compute_roc
            
            y_true = df[y_true_col].values
            y_score = df[y_score_col].values
            
            result = _compute_roc(
                y_true=y_true,
                y_score=y_score,
                pos_label=pos_label,
                confidence_level=confidence_level,
                n_bootstrap=n_bootstrap,
                threshold_method=threshold_method,
            )
            
            return result
            
        except ImportError:
            return {"status": "error", "error": "ROC analysis module not available"}
        except Exception as e:
            logger.error(f"compute_roc_curve error: {e}")
            return {"status": "error", "error": str(e)}
    
    @mcp.tool()
    async def compare_roc_curves(
        csv_content: str,
        y_true_col: str,
        model_score_cols: List[str],
        model_names: Optional[List[str]] = None,
        method: str = "delong",
        is_base64: bool = False,
    ) -> dict:
        """
        🔬 Compare ROC curves from multiple models using DeLong test.
        
        Statistical comparison of classifier performance using the
        DeLong et al. (1988) method for comparing correlated AUCs.
        
        This test accounts for the fact that both models are evaluated
        on the same test set, making the comparison valid and powerful.
        
        Use cases:
        - Compare new model vs baseline
        - Compare different algorithms
        - Compare different feature sets
        - Model selection with statistical evidence
        
        Args:
            csv_content: CSV data as string
            y_true_col: Column with true binary labels
            model_score_cols: List of columns with predicted probabilities
            model_names: Optional names for models (for output clarity)
            method: 'delong' (recommended) or 'bootstrap'
            is_base64: Set True if csv_content is base64 encoded
        
        Returns:
            models: Per-model results (AUC, CI, SE)
            pairwise_comparisons: DeLong test for each pair
                - auc_difference: AUC1 - AUC2
                - z_statistic: DeLong Z score
                - p_value: Two-sided p-value
                - significant: Whether difference is significant
                - ci: Confidence interval for difference
            best_model: Model with highest AUC
            recommendation: Statistical interpretation
        """
        try:
            if is_base64:
                csv_content = base64.b64decode(csv_content).decode('utf-8')
            df = pd.read_csv(StringIO(csv_content))
            
            from .stats_worker_tasks import compare_roc_curves as _compare_roc
            
            y_true = df[y_true_col].values
            predictions = {
                name: df[col].values 
                for name, col in zip(
                    model_names or model_score_cols, 
                    model_score_cols
                )
            }
            
            result = _compare_roc(
                y_true=y_true,
                predictions=predictions,
                method=method,
            )
            
            return result
            
        except ImportError:
            return {"status": "error", "error": "ROC analysis module not available"}
        except Exception as e:
            logger.error(f"compare_roc_curves error: {e}")
            return {"status": "error", "error": str(e)}
    
    @mcp.tool()
    async def find_optimal_threshold(
        csv_content: str,
        y_true_col: str,
        y_score_col: str,
        method: str = "youden",
        fp_cost: float = 1.0,
        fn_cost: float = 1.0,
        target_sensitivity: Optional[float] = None,
        target_specificity: Optional[float] = None,
        prevalence: Optional[float] = None,
        is_base64: bool = False,
    ) -> dict:
        """
        🎯 Find optimal classification threshold using various methods.
        
        Different threshold selection strategies for different needs:
        
        **Methods:**
        - youden: Maximizes Youden's J index (balanced accuracy)
        - cost: Minimizes expected cost given FP/FN costs
        - f1: Maximizes F1 score
        - sensitivity: Achieves target sensitivity (minimum)
        - specificity: Achieves target specificity (minimum)
        - prevalence_adjusted: Accounts for class imbalance
        
        **Clinical Examples:**
        - Screening test: High sensitivity, accept lower specificity
        - Confirmatory test: High specificity to minimize false positives
        - Cost-sensitive: Different costs for FP vs FN errors
        
        Args:
            csv_content: CSV data as string
            y_true_col: Column with true binary labels
            y_score_col: Column with predicted probabilities
            method: Threshold selection method
            fp_cost: Cost of false positive (for cost method)
            fn_cost: Cost of false negative (for cost method)
            target_sensitivity: Minimum sensitivity (for sensitivity method)
            target_specificity: Minimum specificity (for specificity method)
            prevalence: Disease prevalence (for prevalence_adjusted method)
            is_base64: Set True if csv_content is base64 encoded
        
        Returns:
            optimal_threshold: Selected threshold value
            method_used: Which method was applied
            metrics_at_threshold: Sens, spec, PPV, NPV, F1, accuracy
            explanation: Why this threshold was selected
            threshold_range: Nearby thresholds and their metrics
        """
        try:
            if is_base64:
                csv_content = base64.b64decode(csv_content).decode('utf-8')
            df = pd.read_csv(StringIO(csv_content))
            
            from .stats_worker_tasks import find_optimal_threshold as _find_threshold
            
            y_true = df[y_true_col].values
            y_score = df[y_score_col].values
            
            result = _find_threshold(
                y_true=y_true,
                y_score=y_score,
                method=method,
                fp_cost=fp_cost,
                fn_cost=fn_cost,
                target_sensitivity=target_sensitivity,
                target_specificity=target_specificity,
                prevalence=prevalence,
            )
            
            return result
            
        except ImportError:
            return {"status": "error", "error": "ROC analysis module not available"}
        except Exception as e:
            logger.error(f"find_optimal_threshold error: {e}")
            return {"status": "error", "error": str(e)}
    
    @mcp.tool()
    async def analyze_calibration(
        csv_content: str,
        y_true_col: str,
        y_score_col: str,
        n_bins: int = 10,
        strategy: str = "uniform",
        is_base64: bool = False,
    ) -> dict:
        """
        📊 Analyze model calibration (predicted vs actual probabilities).
        
        Calibration measures how well predicted probabilities match
        observed frequencies. A well-calibrated model should have
        predicted probability = actual probability.
        
        **Metrics Provided:**
        - Brier Score: Mean squared error of probabilities (lower is better)
        - Hosmer-Lemeshow Test: Chi-square test for calibration
        - Expected Calibration Error (ECE): Average calibration gap
        - Calibration Curve: Observed vs predicted per bin
        
        **Interpretation:**
        - Hosmer-Lemeshow p > 0.05: Good calibration
        - ECE < 0.1: Well calibrated
        - ECE > 0.2: Poor calibration, consider recalibration
        
        **When to Use:**
        - Before using predictions for decision-making
        - When probabilities need to be interpretable
        - For medical risk prediction models
        
        Args:
            csv_content: CSV data as string
            y_true_col: Column with true binary labels
            y_score_col: Column with predicted probabilities
            n_bins: Number of bins for calibration curve
            strategy: 'uniform' (equal width) or 'quantile' (equal count)
            is_base64: Set True if csv_content is base64 encoded
        
        Returns:
            brier_score: Probability accuracy measure
            hosmer_lemeshow: {statistic, p_value, interpretation}
            expected_calibration_error: Average calibration gap
            calibration_curve: Per-bin observed vs predicted
            reliability_diagram_data: Data for plotting
            recommendations: Calibration improvement suggestions
        """
        try:
            if is_base64:
                csv_content = base64.b64decode(csv_content).decode('utf-8')
            df = pd.read_csv(StringIO(csv_content))
            
            from .stats_worker_tasks import analyze_calibration as _analyze_cal
            
            y_true = df[y_true_col].values
            y_score = df[y_score_col].values
            
            result = _analyze_cal(
                y_true=y_true,
                y_score=y_score,
                n_bins=n_bins,
                strategy=strategy,
            )
            
            return result
            
        except ImportError:
            return {"status": "error", "error": "ROC analysis module not available"}
        except Exception as e:
            logger.error(f"analyze_calibration error: {e}")
            return {"status": "error", "error": str(e)}
    
    @mcp.tool()
    async def full_classifier_evaluation(
        csv_content: str,
        y_true_col: str,
        y_score_col: str,
        threshold: Optional[float] = None,
        is_base64: bool = False,
    ) -> dict:
        """
        🏆 Complete classifier evaluation report.
        
        Comprehensive evaluation combining all ROC analysis tools:
        
        1. **Discrimination** (ROC Analysis)
           - ROC curve and AUC with CI
           - Optimal threshold selection
        
        2. **Classification Metrics**
           - Confusion matrix
           - Sensitivity, Specificity
           - PPV, NPV, F1, Accuracy
        
        3. **Calibration**
           - Brier score
           - Hosmer-Lemeshow test
           - Calibration curve
        
        4. **Clinical Utility** (optional)
           - Net benefit analysis
           - Decision curve
        
        Perfect for publication-ready classifier assessment.
        
        Args:
            csv_content: CSV data as string
            y_true_col: Column with true binary labels
            y_score_col: Column with predicted probabilities
            threshold: Classification threshold (default: optimal)
            is_base64: Set True if csv_content is base64 encoded
        
        Returns:
            roc_analysis: Full ROC curve results
            calibration: Calibration analysis
            classification_report: Metrics at threshold
            summary: Executive summary text
            publication_text: Ready-to-use results paragraph
        """
        try:
            if is_base64:
                csv_content = base64.b64decode(csv_content).decode('utf-8')
            df = pd.read_csv(StringIO(csv_content))
            
            from .stats_worker_tasks import full_classifier_evaluation as _full_eval
            
            y_true = df[y_true_col].values
            y_score = df[y_score_col].values
            
            result = _full_eval(
                y_true=y_true,
                y_score=y_score,
                threshold=threshold,
            )
            
            return result
            
        except ImportError:
            return {"status": "error", "error": "ROC analysis module not available"}
        except Exception as e:
            logger.error(f"full_classifier_evaluation error: {e}")
            return {"status": "error", "error": str(e)}
    
    @mcp.tool()
    async def compare_multiple_roc_curves(
        csv_content: str,
        y_true_col: str,
        model_columns: str,  # JSON string: {"Model A": "score_a", "Model B": "score_b", ...}
        correction: str = "bonferroni",
        alpha: float = 0.05,
        is_base64: bool = False,
    ) -> dict:
        """
        📊 Compare 3+ classification models simultaneously.
        
        Performs comprehensive multi-model comparison:
        
        1. **Individual Performance**
           - AUC with 95% CI for each model
           - Ranked by discriminative ability
        
        2. **Pairwise Comparisons**
           - DeLong test between all model pairs
           - Multiple comparison correction
           - Significance matrix
        
        3. **Best Model Selection**
           - Identifies top performer
           - Reports if significantly better
        
        Correction Methods:
        - "bonferroni": Conservative, controls family-wise error
        - "holm": Less conservative step-down procedure
        - "bh": Benjamini-Hochberg FDR control
        - "none": No correction (not recommended)
        
        Args:
            csv_content: CSV data as string
            y_true_col: Column with true binary labels
            model_columns: JSON mapping model names to score columns
                Example: '{"Logistic": "lr_prob", "XGBoost": "xgb_prob", "RF": "rf_prob"}'
            correction: Multiple comparison correction method
            alpha: Significance level (default: 0.05)
            is_base64: Set True if csv_content is base64 encoded
        
        Returns:
            model_rankings: Models ranked by AUC
            pairwise_comparisons: All DeLong test results
            comparison_matrix: P-value matrix
            best_model: Recommended best performer
            interpretation: Human-readable summary
        """
        try:
            if is_base64:
                csv_content = base64.b64decode(csv_content).decode('utf-8')
            df = pd.read_csv(StringIO(csv_content))
            
            # Parse model columns
            model_cols = json.loads(model_columns)
            
            from .stats_worker_tasks import compare_multiple_models as _compare_multi
            
            y_true = df[y_true_col].values
            models = {name: df[col].values for name, col in model_cols.items()}
            
            result = _compare_multi(
                y_true=y_true,
                models=models,
                correction=correction,
                alpha=alpha,
            )
            
            return result
            
        except ImportError:
            return {"status": "error", "error": "ROC analysis module not available"}
        except json.JSONDecodeError as e:
            return {"status": "error", "error": f"Invalid JSON for model_columns: {e}"}
        except Exception as e:
            logger.error(f"compare_multiple_roc_curves error: {e}")
            return {"status": "error", "error": str(e)}
    
    @mcp.tool()
    async def interactive_threshold_analysis(
        csv_content: str,
        y_true_col: str,
        y_score_col: str,
        target_metric: Optional[str] = None,
        target_value: Optional[float] = None,
        n_thresholds: int = 21,
        is_base64: bool = False,
    ) -> dict:
        """
        🎯 Interactive threshold analysis for clinical decision support.
        
        Comprehensive threshold-by-threshold analysis showing:
        
        1. **Complete Metrics Table**
           - Sensitivity, Specificity, PPV, NPV at each threshold
           - F1, Accuracy, Youden's J
           - Likelihood ratios (LR+, LR-)
           - Number needed to screen (NNS)
        
        2. **Target-Based Selection**
           - Find threshold for target sensitivity (screening)
           - Find threshold for target specificity (confirmation)
           - Trade-off analysis
        
        3. **Recommended Thresholds**
           - Youden optimal (balanced)
           - F1 optimal (precision-recall balance)
           - High sensitivity (≥90% for screening)
           - High specificity (≥90% for confirmation)
        
        Args:
            csv_content: CSV data as string
            y_true_col: Column with true binary labels
            y_score_col: Column with predicted probabilities
            target_metric: Metric to optimize ('sensitivity', 'specificity', 'ppv', 'npv', 'f1')
            target_value: Target value (e.g., 0.95 for 95% sensitivity)
            n_thresholds: Number of thresholds to evaluate (default: 21)
            is_base64: Set True if csv_content is base64 encoded
        
        Returns:
            threshold_table: Complete metrics at each threshold
            target_threshold: Threshold achieving target (if specified)
            recommended_thresholds: Best thresholds for common scenarios
            clinical_interpretation: Decision support text
        """
        try:
            if is_base64:
                csv_content = base64.b64decode(csv_content).decode('utf-8')
            df = pd.read_csv(StringIO(csv_content))
            
            from .stats_worker_tasks import threshold_analysis as _threshold_analysis
            
            y_true = df[y_true_col].values
            y_scores = df[y_score_col].values
            
            result = _threshold_analysis(
                y_true=y_true,
                y_scores=y_scores,
                target_metric=target_metric,
                target_value=target_value,
                n_thresholds=n_thresholds,
            )
            
            return result
            
        except ImportError:
            return {"status": "error", "error": "ROC analysis module not available"}
        except Exception as e:
            logger.error(f"interactive_threshold_analysis error: {e}")
            return {"status": "error", "error": str(e)}
    
    @mcp.tool()
    async def generate_roc_publication_report(
        csv_content: str,
        y_true_col: str,
        y_score_col: str,
        model_name: str = "The prediction model",
        outcome_name: str = "the outcome",
        threshold_method: str = "youden",
        decimal_places: int = 2,
        is_base64: bool = False,
    ) -> dict:
        """
        📝 Generate publication-ready ROC analysis report.
        
        Produces formatted text suitable for journal submission:
        
        1. **Results Paragraph** (copy-paste ready)
           - AUC with 95% CI (DeLong method)
           - Optimal threshold and method
           - Sensitivity, Specificity with bootstrap CIs
           - PPV, NPV, Accuracy
           - Calibration assessment
        
        2. **Methods Paragraph**
           - Statistical methods description
           - CI calculation methods
           - Software citations
        
        3. **Table Data**
           - Ready for Table X (Model Performance)
           - All metrics with CIs
        
        4. **Figure Data**
           - ROC curve coordinates
           - AUC annotation
           - Optimal point marker
        
        Args:
            csv_content: CSV data as string
            y_true_col: Column with true binary labels
            y_score_col: Column with predicted probabilities
            model_name: Name for text (e.g., "The XGBoost classifier")
            outcome_name: Outcome for text (e.g., "30-day mortality")
            threshold_method: Method for optimal threshold ('youden', 'f1')
            decimal_places: Decimal places for reporting (default: 2)
            is_base64: Set True if csv_content is base64 encoded
        
        Returns:
            results_text: Main results paragraph
            methods_text: Methods description
            table_data: Data for performance table
            figure_data: Data for ROC curve figure
            all_metrics: Complete metrics dictionary
        """
        try:
            if is_base64:
                csv_content = base64.b64decode(csv_content).decode('utf-8')
            df = pd.read_csv(StringIO(csv_content))
            
            from .stats_worker_tasks import generate_publication_report as _gen_report
            
            y_true = df[y_true_col].values
            y_scores = df[y_score_col].values
            
            result = _gen_report(
                y_true=y_true,
                y_scores=y_scores,
                model_name=model_name,
                outcome_name=outcome_name,
                threshold_method=threshold_method,
                decimal_places=decimal_places,
            )
            
            return result
            
        except ImportError:
            return {"status": "error", "error": "ROC analysis module not available"}
        except Exception as e:
            logger.error(f"generate_roc_publication_report error: {e}")
            return {"status": "error", "error": str(e)}
    
    logger.info("ROC/AUC analysis tools registered: 8 tools")
