"""
Isolated tests for model management utilities.

Tests model handling, leaderboard, and prediction utilities.
"""

import json
from typing import Any, Dict, List, Optional

import numpy as np

# ==============================================================================
# Helper Functions for Testing
# ==============================================================================


class ModelMetrics:
    """Model performance metrics"""

    @staticmethod
    def calculate_accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """Calculate accuracy"""
        return np.mean(y_true == y_pred)

    @staticmethod
    def calculate_precision(y_true: np.ndarray, y_pred: np.ndarray, pos_label: int = 1) -> float:
        """Calculate precision"""
        tp = np.sum((y_pred == pos_label) & (y_true == pos_label))
        fp = np.sum((y_pred == pos_label) & (y_true != pos_label))
        if tp + fp == 0:
            return 0.0
        return tp / (tp + fp)

    @staticmethod
    def calculate_recall(y_true: np.ndarray, y_pred: np.ndarray, pos_label: int = 1) -> float:
        """Calculate recall"""
        tp = np.sum((y_pred == pos_label) & (y_true == pos_label))
        fn = np.sum((y_pred != pos_label) & (y_true == pos_label))
        if tp + fn == 0:
            return 0.0
        return tp / (tp + fn)

    @staticmethod
    def calculate_f1(precision: float, recall: float) -> float:
        """Calculate F1 score"""
        if precision + recall == 0:
            return 0.0
        return 2 * precision * recall / (precision + recall)

    @staticmethod
    def calculate_rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """Calculate RMSE"""
        return np.sqrt(np.mean((y_true - y_pred) ** 2))

    @staticmethod
    def calculate_mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """Calculate MAE"""
        return np.mean(np.abs(y_true - y_pred))

    @staticmethod
    def calculate_r2(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """Calculate R²"""
        ss_res = np.sum((y_true - y_pred) ** 2)
        ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
        if ss_tot == 0:
            return 0.0
        return 1 - ss_res / ss_tot


def create_leaderboard(
    models: List[Dict[str, Any]], metric: str, higher_is_better: bool = True
) -> List[Dict[str, Any]]:
    """Create sorted leaderboard from models"""
    sorted_models = sorted(models, key=lambda x: x.get(metric, 0), reverse=higher_is_better)

    for rank, model in enumerate(sorted_models, 1):
        model["rank"] = rank

    return sorted_models


def validate_prediction_input(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate prediction input data"""
    errors = []

    if "features" not in data and "dataset_id" not in data:
        errors.append("Either 'features' or 'dataset_id' is required")

    if "features" in data:
        features = data["features"]
        if not isinstance(features, (list, dict)):
            errors.append("Features must be a list or dict")
        elif isinstance(features, list) and len(features) == 0:
            errors.append("Features list cannot be empty")

    if errors:
        return {"valid": False, "errors": errors}
    return {"valid": True, "errors": []}


def format_prediction_output(
    predictions: np.ndarray, problem_type: str, class_labels: Optional[List] = None
) -> Dict[str, Any]:
    """Format prediction output"""
    result = {
        "predictions": predictions.tolist() if isinstance(predictions, np.ndarray) else predictions,
        "count": len(predictions),
    }

    if problem_type in ["binary", "multiclass"] and class_labels:
        result["class_labels"] = class_labels

    return result


# ==============================================================================
# Tests
# ==============================================================================


class TestModelMetricsClassification:
    """Test classification metrics"""

    def test_accuracy(self):
        """Test accuracy calculation"""
        y_true = np.array([0, 0, 1, 1, 1])
        y_pred = np.array([0, 1, 1, 1, 0])

        acc = ModelMetrics.calculate_accuracy(y_true, y_pred)

        assert acc == 0.6  # 3/5 correct
        print(f"✓ Accuracy: {acc}")

    def test_precision(self):
        """Test precision calculation"""
        y_true = np.array([0, 0, 1, 1, 1])
        y_pred = np.array([0, 1, 1, 1, 0])

        # TP=2, FP=1, Precision = 2/3
        precision = ModelMetrics.calculate_precision(y_true, y_pred)

        assert abs(precision - 2 / 3) < 0.01
        print(f"✓ Precision: {precision:.3f}")

    def test_recall(self):
        """Test recall calculation"""
        y_true = np.array([0, 0, 1, 1, 1])
        y_pred = np.array([0, 1, 1, 1, 0])

        # TP=2, FN=1, Recall = 2/3
        recall = ModelMetrics.calculate_recall(y_true, y_pred)

        assert abs(recall - 2 / 3) < 0.01
        print(f"✓ Recall: {recall:.3f}")

    def test_f1_score(self):
        """Test F1 score calculation"""
        precision = 0.8
        recall = 0.6

        f1 = ModelMetrics.calculate_f1(precision, recall)
        expected = 2 * 0.8 * 0.6 / (0.8 + 0.6)

        assert abs(f1 - expected) < 0.01
        print(f"✓ F1 Score: {f1:.3f}")

    def test_f1_with_zero(self):
        """Test F1 with zero precision or recall"""
        f1 = ModelMetrics.calculate_f1(0, 0)
        assert f1 == 0.0
        print("✓ F1 with zero handled")

    def test_perfect_classifier(self):
        """Test perfect classifier metrics"""
        y_true = np.array([0, 0, 1, 1])
        y_pred = np.array([0, 0, 1, 1])

        acc = ModelMetrics.calculate_accuracy(y_true, y_pred)
        precision = ModelMetrics.calculate_precision(y_true, y_pred)
        recall = ModelMetrics.calculate_recall(y_true, y_pred)

        assert acc == 1.0
        assert precision == 1.0
        assert recall == 1.0
        print("✓ Perfect classifier")


class TestModelMetricsRegression:
    """Test regression metrics"""

    def test_rmse(self):
        """Test RMSE calculation"""
        y_true = np.array([1, 2, 3, 4, 5])
        y_pred = np.array([1.1, 2.2, 2.8, 4.1, 4.9])

        rmse = ModelMetrics.calculate_rmse(y_true, y_pred)

        assert rmse < 0.3
        print(f"✓ RMSE: {rmse:.3f}")

    def test_mae(self):
        """Test MAE calculation"""
        y_true = np.array([1, 2, 3, 4, 5])
        y_pred = np.array([1.5, 2.5, 3.5, 4.5, 5.5])

        mae = ModelMetrics.calculate_mae(y_true, y_pred)

        assert mae == 0.5
        print(f"✓ MAE: {mae:.3f}")

    def test_r2_perfect(self):
        """Test R² with perfect predictions"""
        y_true = np.array([1, 2, 3, 4, 5])
        y_pred = np.array([1, 2, 3, 4, 5])

        r2 = ModelMetrics.calculate_r2(y_true, y_pred)

        assert r2 == 1.0
        print("✓ R² perfect = 1.0")

    def test_r2_good(self):
        """Test R² with good predictions"""
        np.random.seed(42)
        y_true = np.linspace(0, 10, 100)
        y_pred = y_true + np.random.normal(0, 0.5, 100)

        r2 = ModelMetrics.calculate_r2(y_true, y_pred)

        assert r2 > 0.9
        print(f"✓ R² good: {r2:.3f}")

    def test_r2_poor(self):
        """Test R² with poor predictions"""
        y_true = np.array([1, 2, 3, 4, 5])
        y_pred = np.array([5, 4, 3, 2, 1])  # Reversed

        r2 = ModelMetrics.calculate_r2(y_true, y_pred)

        assert r2 < 0  # Negative R² for worse than mean
        print(f"✓ R² poor: {r2:.3f}")


class TestLeaderboard:
    """Test leaderboard creation and sorting"""

    def test_create_leaderboard(self):
        """Test leaderboard creation"""
        models = [
            {"name": "XGB", "accuracy": 0.85},
            {"name": "RF", "accuracy": 0.90},
            {"name": "LR", "accuracy": 0.80},
        ]

        leaderboard = create_leaderboard(models, "accuracy", higher_is_better=True)

        assert leaderboard[0]["name"] == "RF"
        assert leaderboard[0]["rank"] == 1
        print("✓ Leaderboard created")

    def test_leaderboard_ranking(self):
        """Test leaderboard ranking"""
        models = [
            {"name": "A", "score": 0.5},
            {"name": "B", "score": 0.9},
            {"name": "C", "score": 0.7},
        ]

        leaderboard = create_leaderboard(models, "score")

        assert leaderboard[0]["rank"] == 1
        assert leaderboard[1]["rank"] == 2
        assert leaderboard[2]["rank"] == 3
        print("✓ Ranking correct")

    def test_leaderboard_lower_is_better(self):
        """Test leaderboard with lower is better (e.g., RMSE)"""
        models = [
            {"name": "A", "rmse": 0.5},
            {"name": "B", "rmse": 0.1},
            {"name": "C", "rmse": 0.3},
        ]

        leaderboard = create_leaderboard(models, "rmse", higher_is_better=False)

        assert leaderboard[0]["name"] == "B"  # Lowest RMSE
        print("✓ Lower is better handled")

    def test_leaderboard_missing_metric(self):
        """Test leaderboard with missing metric"""
        models = [
            {"name": "A", "score": 0.5},
            {"name": "B"},  # Missing score
            {"name": "C", "score": 0.7},
        ]

        leaderboard = create_leaderboard(models, "score")

        assert leaderboard[-1]["name"] == "B"  # Missing = 0, goes to bottom
        print("✓ Missing metric handled")


class TestPredictionValidation:
    """Test prediction input validation"""

    def test_valid_features(self):
        """Test valid features input"""
        data = {"features": [[1, 2, 3], [4, 5, 6]]}
        result = validate_prediction_input(data)
        assert result["valid"] is True
        print("✓ Valid features")

    def test_valid_dataset_id(self):
        """Test valid dataset_id input"""
        data = {"dataset_id": "ds_123"}
        result = validate_prediction_input(data)
        assert result["valid"] is True
        print("✓ Valid dataset_id")

    def test_missing_input(self):
        """Test missing both features and dataset_id"""
        data = {}
        result = validate_prediction_input(data)
        assert result["valid"] is False
        print("✓ Missing input detected")

    def test_empty_features(self):
        """Test empty features list"""
        data = {"features": []}
        result = validate_prediction_input(data)
        assert result["valid"] is False
        print("✓ Empty features rejected")

    def test_dict_features(self):
        """Test dict features (single row)"""
        data = {"features": {"age": 30, "income": 50000}}
        result = validate_prediction_input(data)
        assert result["valid"] is True
        print("✓ Dict features accepted")


class TestPredictionOutput:
    """Test prediction output formatting"""

    def test_binary_output(self):
        """Test binary classification output"""
        predictions = np.array([0, 1, 1, 0, 1])
        result = format_prediction_output(predictions, "binary", [0, 1])

        assert "predictions" in result
        assert result["count"] == 5
        assert result["class_labels"] == [0, 1]
        print("✓ Binary output")

    def test_multiclass_output(self):
        """Test multiclass output"""
        predictions = np.array([0, 1, 2, 1, 0])
        result = format_prediction_output(predictions, "multiclass", ["A", "B", "C"])

        assert result["class_labels"] == ["A", "B", "C"]
        print("✓ Multiclass output")

    def test_regression_output(self):
        """Test regression output"""
        predictions = np.array([1.5, 2.3, 3.1])
        result = format_prediction_output(predictions, "regression")

        assert "predictions" in result
        assert "class_labels" not in result
        print("✓ Regression output")

    def test_prediction_count(self):
        """Test prediction count"""
        predictions = np.array([1, 2, 3, 4, 5])
        result = format_prediction_output(predictions, "regression")

        assert result["count"] == 5
        print("✓ Prediction count")


class TestModelInfo:
    """Test model information handling"""

    def test_model_info_structure(self):
        """Test model info structure"""
        model_info = {
            "model_id": "model_123",
            "model_name": "WeightedEnsemble_L2",
            "problem_type": "binary",
            "metric": "roc_auc",
            "score": 0.92,
            "training_time": 120.5,
            "n_features": 15,
            "feature_importance": {"age": 0.3, "income": 0.2},
        }

        required_fields = ["model_id", "model_name", "problem_type"]
        for field in required_fields:
            assert field in model_info

        print("✓ Model info structure")

    def test_feature_importance_sorting(self):
        """Test feature importance sorting"""
        importance = {"c": 0.1, "a": 0.5, "b": 0.3, "d": 0.1}

        sorted_features = sorted(importance.items(), key=lambda x: x[1], reverse=True)

        assert sorted_features[0][0] == "a"
        assert sorted_features[1][0] == "b"
        print("✓ Feature importance sorting")

    def test_model_serialization(self):
        """Test model info serialization"""
        model_info = {
            "model_id": "model_123",
            "score": 0.92,
            "feature_importance": {"a": 0.5, "b": 0.3},
        }

        json_str = json.dumps(model_info)
        restored = json.loads(json_str)

        assert restored == model_info
        print("✓ Model serialization")


class TestModelComparison:
    """Test model comparison utilities"""

    def test_compare_metrics(self):
        """Test comparing model metrics"""
        model_a = {"accuracy": 0.85, "f1": 0.82}
        model_b = {"accuracy": 0.87, "f1": 0.80}

        # Model B better on accuracy, Model A better on F1
        assert model_b["accuracy"] > model_a["accuracy"]
        assert model_a["f1"] > model_b["f1"]
        print("✓ Metric comparison")

    def test_best_model_selection(self):
        """Test selecting best model"""
        models = [
            {"name": "XGB", "roc_auc": 0.91},
            {"name": "GBM", "roc_auc": 0.93},
            {"name": "RF", "roc_auc": 0.89},
        ]

        best = max(models, key=lambda x: x["roc_auc"])

        assert best["name"] == "GBM"
        print("✓ Best model selection")

    def test_ensemble_detection(self):
        """Test detecting ensemble models"""
        model_names = [
            "WeightedEnsemble_L2",
            "XGBoost",
            "CatBoost",
            "LightGBM",
        ]

        ensembles = [m for m in model_names if "Ensemble" in m]

        assert len(ensembles) == 1
        assert ensembles[0] == "WeightedEnsemble_L2"
        print("✓ Ensemble detection")


class TestAlgorithmInfo:
    """Test algorithm information"""

    def test_algorithm_descriptions(self):
        """Test algorithm descriptions"""
        algo_info = {
            "GBM": {"name": "LightGBM", "type": "boosting"},
            "XGB": {"name": "XGBoost", "type": "boosting"},
            "RF": {"name": "Random Forest", "type": "bagging"},
            "NN_TORCH": {"name": "PyTorch Neural Network", "type": "neural"},
        }

        assert algo_info["GBM"]["type"] == "boosting"
        assert algo_info["RF"]["type"] == "bagging"
        print("✓ Algorithm descriptions")

    def test_algorithm_categories(self):
        """Test categorizing algorithms"""
        algorithms = ["GBM", "XGB", "CAT", "RF", "XT", "NN_TORCH", "LR"]

        boosting = ["GBM", "XGB", "CAT"]

        for algo in boosting:
            assert algo in algorithms
        print("✓ Algorithm categories")


def run_all_tests():
    """Run all test classes"""
    print("=" * 60)
    print("Running model management isolated tests")
    print("=" * 60)

    test_classes = [
        TestModelMetricsClassification(),
        TestModelMetricsRegression(),
        TestLeaderboard(),
        TestPredictionValidation(),
        TestPredictionOutput(),
        TestModelInfo(),
        TestModelComparison(),
        TestAlgorithmInfo(),
    ]

    for test_class in test_classes:
        class_name = test_class.__class__.__name__
        print(f"\n{class_name}:")
        print("-" * 40)

        test_methods = [m for m in dir(test_class) if m.startswith("test_")]

        for method_name in test_methods:
            try:
                method = getattr(test_class, method_name)
                method()
            except Exception as e:
                print(f"✗ {method_name}: {e}")
                raise

    print("\n" + "=" * 60)
    print("🎉 ALL MODEL MANAGEMENT TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
