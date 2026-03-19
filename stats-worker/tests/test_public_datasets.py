#!/usr/bin/env python3
"""
Public Dataset Validation Tests

Uses classic public datasets to validate stats-worker functions:
1. Survival Analysis - Rossi recidivism, Lung cancer
2. ROC Analysis - Breast cancer classification
3. TableOne - Titanic passenger demographics
4. Power Analysis - Validate sample size calculations
5. Propensity Score - Treatment effect estimation

Run:
    cd stats-worker
    python3 -m pytest tests/test_public_datasets.py -v
"""

import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


import numpy as np
import pandas as pd
import pytest

# =============================================================================
# Dataset Loaders
# =============================================================================


def load_rossi_recidivism() -> pd.DataFrame:
    """
    Rossi recidivism dataset - classic survival analysis dataset.
    432 convicts released from Maryland prisons.
    """
    try:
        from lifelines.datasets import load_rossi

        return load_rossi()
    except ImportError:
        np.random.seed(42)
        n = 432
        return pd.DataFrame(
            {
                "week": np.random.randint(1, 53, n),
                "arrest": np.random.choice([0, 1], n, p=[0.74, 0.26]),
                "fin": np.random.choice([0, 1], n),
                "age": np.random.randint(18, 50, n),
                "race": np.random.choice([0, 1], n, p=[0.6, 0.4]),
                "wexp": np.random.choice([0, 1], n, p=[0.4, 0.6]),
                "mar": np.random.choice([0, 1], n, p=[0.8, 0.2]),
                "paro": np.random.choice([0, 1], n, p=[0.5, 0.5]),
                "prio": np.random.poisson(3, n),
            }
        )


def load_breast_cancer() -> pd.DataFrame:
    """Wisconsin Breast Cancer dataset. 569 samples, 30 features."""
    from sklearn.datasets import load_breast_cancer as sklearn_bc

    data = sklearn_bc()
    df = pd.DataFrame(data.data, columns=data.feature_names)
    df["target"] = data.target
    return df


def load_iris() -> pd.DataFrame:
    """Iris dataset - 150 samples, 4 features, 3 classes."""
    from sklearn.datasets import load_iris as sklearn_iris

    data = sklearn_iris()
    df = pd.DataFrame(data.data, columns=data.feature_names)
    df["target"] = data.target
    df["species"] = df["target"].map({0: "setosa", 1: "versicolor", 2: "virginica"})
    return df


def load_titanic() -> pd.DataFrame:
    """Titanic dataset - classic survival/classification dataset."""
    try:
        import seaborn as sns

        return sns.load_dataset("titanic")
    except ImportError:
        np.random.seed(42)
        n = 891
        return pd.DataFrame(
            {
                "survived": np.random.choice([0, 1], n, p=[0.62, 0.38]),
                "pclass": np.random.choice([1, 2, 3], n, p=[0.24, 0.21, 0.55]),
                "sex": np.random.choice(["male", "female"], n, p=[0.65, 0.35]),
                "age": np.random.normal(30, 14, n).clip(0.5, 80),
                "sibsp": np.random.poisson(0.5, n),
                "parch": np.random.poisson(0.4, n),
                "fare": np.random.exponential(33, n),
                "embarked": np.random.choice(["S", "C", "Q"], n, p=[0.72, 0.19, 0.09]),
            }
        )


# =============================================================================
# Survival Analysis Tests
# =============================================================================


class TestSurvivalAnalysisPublicData:
    """Test survival analysis with public datasets."""

    def test_kaplan_meier_rossi(self):
        """Test Kaplan-Meier on Rossi recidivism data."""
        from tasks.survival_analysis import kaplan_meier_analysis

        df = load_rossi_recidivism()

        # kaplan_meier_analysis(df, time_col, event_col, group_col)
        result = kaplan_meier_analysis(df=df, time_col="week", event_col="arrest")

        # Validate structure
        assert result is not None

        # Known: ~26% were arrested (104 out of 432)
        # API returns 'overall' dict with survival data when no group
        assert "overall" in result or "analysis_type" in result
        print("✅ Kaplan-Meier Rossi: Analysis completed")

    def test_log_rank_rossi(self):
        """Test log-rank test comparing survival curves by financial aid."""
        from tasks.survival_analysis import log_rank_test

        df = load_rossi_recidivism()

        # log_rank_test(times, events, groups) - positional args as numpy arrays
        result = log_rank_test(times=df["week"].values, events=df["arrest"].values, groups=df["fin"].values)

        result_dict = result.to_dict() if hasattr(result, "to_dict") else result

        # Should have log-rank test result with p_value
        assert "p_value" in result_dict
        print(f"✅ Log-Rank Rossi: fin=0 vs fin=1, p={result_dict.get('p_value', 'N/A'):.4f}")

    def test_cox_regression_rossi(self):
        """Test Cox regression on Rossi data."""
        from tasks.survival_analysis import cox_regression

        df = load_rossi_recidivism()

        # cox_regression(df, time_col, event_col, covariates)
        result = cox_regression(df=df, time_col="week", event_col="arrest", covariates=["fin", "age", "prio", "mar"])

        # Should have coefficients
        assert "coefficients" in result or "summary" in result
        print("✅ Cox Regression Rossi: Completed")


# =============================================================================
# ROC Analysis Tests
# =============================================================================


class TestROCAnalysisPublicData:
    """Test ROC analysis with public datasets."""

    def test_roc_breast_cancer(self):
        """Test ROC curve on breast cancer data."""
        from sklearn.linear_model import LogisticRegression
        from sklearn.model_selection import train_test_split
        from tasks.roc_analysis import compute_roc_curve

        df = load_breast_cancer()
        X = df.drop(["target"], axis=1)
        y = df["target"]

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)
        model = LogisticRegression(max_iter=1000, random_state=42)
        model.fit(X_train, y_train)
        y_prob = model.predict_proba(X_test)[:, 1]

        # compute_roc_curve(y_true, y_scores) - note: y_scores not y_score
        result = compute_roc_curve(y_true=y_test.tolist(), y_scores=y_prob.tolist())

        # Breast cancer with LR should have AUC > 0.95
        assert result["auc"] > 0.90, f"Expected AUC > 0.90, got {result['auc']}"
        print(f"✅ ROC Breast Cancer: AUC = {result['auc']:.4f}")

    def test_roc_comparison_breast_cancer(self):
        """Test ROC curve comparison with multiple models."""
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.linear_model import LogisticRegression
        from sklearn.model_selection import train_test_split
        from tasks.roc_analysis import compare_roc_curves

        df = load_breast_cancer()
        X = df.drop(["target"], axis=1)
        y = df["target"]

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)

        lr = LogisticRegression(max_iter=1000, random_state=42)
        rf = RandomForestClassifier(n_estimators=50, random_state=42)

        lr.fit(X_train, y_train)
        rf.fit(X_train, y_train)

        y_prob_lr = lr.predict_proba(X_test)[:, 1]
        y_prob_rf = rf.predict_proba(X_test)[:, 1]

        # compare_roc_curves(y_true, scores1, scores2, model1_name, model2_name)
        result = compare_roc_curves(
            y_true=y_test.tolist(),
            scores1=y_prob_lr.tolist(),
            scores2=y_prob_rf.tolist(),
            model1_name="Logistic Regression",
            model2_name="Random Forest",
        )

        # API returns 'comparison' with 'p_value' inside, and 'model1', 'model2' for AUCs
        assert "comparison" in result or "model1" in result
        p_value = result.get("comparison", {}).get("p_value", "N/A")
        print(f"✅ ROC Comparison: LR vs RF, DeLong p={p_value}")

    def test_calibration_breast_cancer(self):
        """Test calibration analysis."""
        from sklearn.linear_model import LogisticRegression
        from sklearn.model_selection import train_test_split
        from tasks.roc_analysis import analyze_calibration

        df = load_breast_cancer()
        X = df.drop(["target"], axis=1)
        y = df["target"]

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)

        model = LogisticRegression(max_iter=1000, random_state=42)
        model.fit(X_train, y_train)
        y_prob = model.predict_proba(X_test)[:, 1]

        result = analyze_calibration(y_true=y_test.tolist(), y_prob=y_prob.tolist())

        assert result["brier_score"] < 0.15, f"Brier score too high: {result['brier_score']}"
        print(f"✅ Calibration: Brier Score = {result['brier_score']:.4f}")


# =============================================================================
# TableOne Tests
# =============================================================================


class TestTableOnePublicData:
    """Test TableOne generation with public datasets."""

    def test_tableone_titanic(self):
        """Test TableOne on Titanic data."""
        from tasks.tableone_generator import TableOneGenerator

        df = load_titanic()
        df_clean = df[["survived", "pclass", "sex", "age", "fare"]].dropna()

        # TableOneGenerator() then generate(df, ...) - not __init__(data=...)
        generator = TableOneGenerator()
        result = generator.generate(
            df=df_clean, categorical=["pclass", "sex"], continuous=["age", "fare"], groupby="survived"
        )

        result_dict = result.to_dict() if hasattr(result, "to_dict") else result
        assert result_dict is not None
        print(f"✅ TableOne Titanic: Generated for {len(df_clean)} passengers")

    def test_tableone_iris(self):
        """Test TableOne on Iris data."""
        from tasks.tableone_generator import TableOneGenerator

        df = load_iris()

        # TableOneGenerator() then generate(df, ...)
        generator = TableOneGenerator()
        result = generator.generate(
            df=df,
            categorical=[],
            continuous=["sepal length (cm)", "sepal width (cm)", "petal length (cm)", "petal width (cm)"],
            groupby="species",
        )

        result_dict = result.to_dict() if hasattr(result, "to_dict") else result
        assert result_dict is not None
        print("✅ TableOne Iris: 3 species compared")


# =============================================================================
# Power Analysis Tests
# =============================================================================


class TestPowerAnalysisValidation:
    """Validate power analysis with known results."""

    def test_ttest_sample_size_known_values(self):
        """Test t-test sample size against known values."""
        from tasks.power_analysis import calculate_ttest_sample_size

        # Cohen's d=0.5, power=0.80, alpha=0.05 → ~64 per group
        result = calculate_ttest_sample_size(effect_size=0.5, power=0.80, alpha=0.05)

        # API returns {'results': {'sample_size_per_group': N, ...}, ...}
        n_per_group = result["results"]["sample_size_per_group"]

        assert 60 <= n_per_group <= 70, f"Expected ~64, got {n_per_group}"
        print(f"✅ T-test Sample Size: d=0.5 → n={n_per_group} per group")

    def test_proportion_sample_size_known_values(self):
        """Test proportion sample size against known values."""
        from tasks.power_analysis import calculate_proportion_sample_size

        # p1=0.5, p2=0.65, power=0.80, alpha=0.05 → ~175 per group
        result = calculate_proportion_sample_size(p1=0.50, p2=0.65, power=0.80, alpha=0.05)

        # API returns {'results': {'sample_size_per_group': N, ...}, ...}
        n_per_group = result["results"]["sample_size_per_group"]

        assert 160 <= n_per_group <= 190, f"Expected ~175, got {n_per_group}"
        print(f"✅ Proportion Sample Size: 0.50→0.65 → n={n_per_group} per group")

    def test_survival_sample_size_known_values(self):
        """Test survival sample size (Schoenfeld formula)."""
        from tasks.power_analysis import calculate_survival_sample_size

        # HR=0.7, power=0.80, alpha=0.05 → ~248 events
        result = calculate_survival_sample_size(hazard_ratio=0.7, power=0.80, alpha=0.05)

        # API returns {'results': {'n_events': N, 'total_n': M, ...}, ...}
        events = result["results"]["n_events"]

        assert 230 <= events <= 270, f"Expected ~248 events, got {events}"
        print(f"✅ Survival Sample Size: HR=0.7 → {events} events needed")


# =============================================================================
# Propensity Score Tests
# =============================================================================


class TestPropensityScorePublicData:
    """Test propensity score analysis with Rossi data."""

    def test_propensity_score_rossi(self):
        """Test propensity score estimation on Rossi data."""
        from tasks.propensity_score import PropensityScoreEstimator

        df = load_rossi_recidivism()

        # PropensityScoreEstimator().fit(X, treatment) - separate covariate matrix and treatment
        covariate_cols = ["age", "race", "wexp", "mar", "prio"]
        X = df[covariate_cols]
        treatment = df["fin"]

        estimator = PropensityScoreEstimator()
        result = estimator.fit(X, treatment)

        # Result has 'scores' attribute (ndarray) and to_dict() for dict output
        assert result.scores is not None
        assert len(result.scores) == len(df)
        print(f"✅ Propensity Score Rossi: Estimated for {len(df)} subjects")

    def test_propensity_matching_rossi(self):
        """Test propensity score matching on Rossi data."""
        from tasks.propensity_score import PropensityScoreEstimator, PropensityScoreMatcher

        df = load_rossi_recidivism()

        # First estimate propensity scores
        covariate_cols = ["age", "race", "wexp", "mar", "prio"]
        X = df[covariate_cols]
        treatment = df["fin"].values

        estimator = PropensityScoreEstimator()
        ps_result = estimator.fit(X, treatment)
        scores = ps_result.scores  # attribute is 'scores' not 'propensity_scores'

        # Then match using PropensityScoreMatcher.match(scores, treatment)
        matcher = PropensityScoreMatcher()
        result = matcher.match(scores, treatment)

        # Result has n_matched attribute
        assert result.n_matched > 0
        print(f"✅ Propensity Matching Rossi: {result.n_matched} matched pairs created")


# =============================================================================
# Enhanced Statistics Tests
# =============================================================================


class TestEnhancedStatisticsPublicData:
    """Test enhanced statistics with public datasets."""

    def test_correlation_iris(self):
        """Test correlation analysis on Iris data."""
        from tasks.analysis.correlation import compute_enhanced_correlation

        df = load_iris()
        numeric_cols = ["sepal length (cm)", "sepal width (cm)", "petal length (cm)", "petal width (cm)"]

        # compute_enhanced_correlation(df, columns, method, alpha, min_correlation)
        result = compute_enhanced_correlation(df, columns=numeric_cols)

        result_dict = result.to_dict() if hasattr(result, "to_dict") else result

        # API returns 'matrices' with 'pearson' inside
        assert "matrices" in result_dict or "pearson_matrix" in result_dict
        print("✅ Correlation Iris: Matrix computed")

    def test_distribution_comparison_iris(self):
        """Test distribution comparison across Iris species."""
        from tasks.analysis.distribution import compare_distributions

        df = load_iris()

        # compare_distributions(df, numeric_col, group_col)
        result = compare_distributions(df=df, numeric_col="petal length (cm)", group_col="species")

        result_dict = result.to_dict() if hasattr(result, "to_dict") else result

        # Petal length differs significantly across species
        # API returns 'main_test' with 'p_value'
        p_value = result_dict.get("main_test", {}).get("p_value", 1)
        assert p_value < 0.001, f"Expected significant p-value, got {p_value}"
        print(f"✅ Distribution Comparison: p={p_value:.2e}")

    def test_multicollinearity_breast_cancer(self):
        """Test VIF analysis on breast cancer data."""
        from tasks.analysis.multicollinearity import compute_vif

        df = load_breast_cancer()
        feature_cols = list(df.columns[:10])  # First 10 features

        # compute_vif(df, columns, vif_threshold)
        result = compute_vif(df, columns=feature_cols)

        result_dict = result.to_dict() if hasattr(result, "to_dict") else result

        # API returns 'vif_results' list
        assert "vif_results" in result_dict
        print(f"✅ VIF Breast Cancer: Checked {len(feature_cols)} features")


# =============================================================================
# Run All Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
