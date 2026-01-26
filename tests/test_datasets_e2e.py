#!/usr/bin/env python3
"""
測試 E2E_TEST_PLAN.md 中的 10 個公開資料集

執行方式：
    python tests/test_datasets_e2e.py --dataset iris
    python tests/test_datasets_e2e.py --dataset all
    python tests/test_datasets_e2e.py --suite stats  # 只跑統計分析
    python tests/test_datasets_e2e.py --suite ml     # 只跑 ML 訓練
"""
import argparse
import time
from pathlib import Path
from typing import Dict, List

import requests

# Service URLs
STATS_SERVICE = "http://localhost:8003"
AUTOML_SERVICE = "http://localhost:8001"
MCP_SERVER = "http://localhost:8002"

# 資料集配置
DATASETS = {
    "iris": {
        "file": "iris.csv",
        "type": "multiclass",
        "target": "target",
        "size": "150 rows × 6 columns",
        "stats_tests": ["tableone", "anova", "correlation"],
        "ml_tests": ["multiclass_classification"],
    },
    "breast_cancer": {
        "file": "breast_cancer.csv",
        "type": "binary",
        "target": "diagnosis",
        "size": "569 rows × 31 columns",
        "stats_tests": ["roc", "correlation", "vif"],
        "ml_tests": ["binary_classification"],
    },
    "diabetes": {
        "file": "diabetes.csv",
        "type": "regression",
        "target": "progression",
        "size": "442 rows × 11 columns",
        "stats_tests": ["correlation", "normality"],
        "ml_tests": ["regression"],
    },
    "heart_disease": {
        "file": "heart_disease.csv",
        "type": "binary",
        "target": "target",
        "size": "297 rows × 14 columns",
        "stats_tests": ["tableone", "chi_square"],
        "ml_tests": ["binary_classification"],
    },
    "titanic": {
        "file": "titanic.csv",
        "type": "binary",
        "target": "survived",
        "size": "891 rows × 11 columns",
        "stats_tests": ["tableone", "chi_square", "psm"],
        "ml_tests": ["binary_classification"],
    },
    "california_housing": {
        "file": "california_housing.csv",
        "type": "regression",
        "target": "median_house_value",
        "size": "20640 rows × 9 columns",
        "stats_tests": ["correlation", "distribution"],
        "ml_tests": ["regression"],
    },
    "wine_quality": {
        "file": "wine_quality.csv",
        "type": "multiclass",
        "target": "quality",
        "size": "6497 rows × 12 columns",
        "stats_tests": ["anova", "correlation"],
        "ml_tests": ["multiclass_classification"],
    },
    "adult_income": {
        "file": "adult_income.csv",
        "type": "binary",
        "target": "income",
        "size": "48842 rows × 15 columns",
        "stats_tests": ["tableone", "chi_square"],
        "ml_tests": ["binary_classification"],
    },
    "rossi": {
        "file": "rossi_recidivism.csv",
        "type": "survival",
        "target": "arrest",
        "time_col": "week",
        "size": "432 rows × 10 columns",
        "stats_tests": ["kaplan_meier", "cox", "log_rank"],
        "ml_tests": [],  # Survival analysis 不在 AutoML 範圍
    },
    "stanford_heart": {
        "file": "stanford_heart.csv",
        "type": "survival",
        "target": "status",
        "time_col": "time",
        "size": "103 rows × 6 columns",
        "stats_tests": ["kaplan_meier", "cox"],
        "ml_tests": [],
    },
}


class DatasetTester:
    def __init__(self, data_root: str = "/home/eric/workspace251204", verbose: bool = False):
        self.data_root = Path(data_root)
        self.sample_data = self.data_root / "sample_data"
        self.results = {}
        self.verbose = verbose

    def get_csv_path(self, filename: str) -> str:
        """取得 CSV 檔案路徑（根據是否使用 Docker）"""
        # 優先使用 Docker 路徑（服務在容器內）
        return f"/data/sample_data/{filename}"

    def test_service_health(self) -> bool:
        """檢查服務健康狀態"""
        try:
            resp = requests.get(f"{STATS_SERVICE}/health", timeout=5)
            return resp.status_code == 200
        except Exception as e:
            print(f"❌ Stats Service 未啟動: {e}")
            return False

    def test_quick_stats(self, dataset_name: str, config: Dict) -> Dict:
        """測試 Quick Stats"""
        csv_path = self.get_csv_path(config["file"])

        try:
            resp = requests.post(
                f"{STATS_SERVICE}/direct/quick-stats",
                json={"csv_path": csv_path},
                timeout=30
            )

            if resp.status_code == 200:
                data = resp.json()
                return {
                    "status": "✅ PASS",
                    "rows": data.get("shape", {}).get("rows"),
                    "columns": data.get("shape", {}).get("columns"),
                }
            else:
                error_msg = resp.text[:200] if len(resp.text) > 200 else resp.text
                if self.verbose:
                    print(f"\n      Error: {error_msg}")
                return {"status": f"❌ FAIL ({resp.status_code})", "error": error_msg}

        except Exception as e:
            if self.verbose:
                print(f"\n      Exception: {str(e)}")
            return {"status": "❌ ERROR", "error": str(e)}

    def test_tableone(self, dataset_name: str, config: Dict) -> Dict:
        """測試 Table One 生成"""
        csv_path = self.get_csv_path(config["file"])

        try:
            resp = requests.post(
                f"{STATS_SERVICE}/tableone/generate-direct",
                json={
                    "csv_path": csv_path,
                    "group_column": config.get("target"),
                },
                timeout=60
            )

            if resp.status_code == 200:
                data = resp.json()
                return {
                    "status": "✅ PASS",
                    "groups": len(data.get("table", {}).get("groups", [])),
                }
            else:
                return {"status": "❌ FAIL", "error": resp.text}

        except Exception as e:
            return {"status": "❌ ERROR", "error": str(e)}

    def test_correlation(self, dataset_name: str, config: Dict) -> Dict:
        """測試相關性分析"""
        csv_path = self.get_csv_path(config["file"])

        try:
            resp = requests.post(
                f"{STATS_SERVICE}/eda/correlation",
                json={
                    "csv_path": csv_path,
                    "method": "pearson",
                },
                timeout=60
            )

            if resp.status_code == 200:
                data = resp.json()
                return {
                    "status": "✅ PASS",
                    "matrix_size": len(data.get("correlation_matrix", [])),
                }
            else:
                return {"status": "❌ FAIL", "error": resp.text}

        except Exception as e:
            return {"status": "❌ ERROR", "error": str(e)}

    def test_kaplan_meier(self, dataset_name: str, config: Dict) -> Dict:
        """測試 Kaplan-Meier 存活分析"""
        csv_path = self.get_csv_path(config["file"])

        try:
            resp = requests.post(
                f"{STATS_SERVICE}/survival/kaplan-meier",
                json={
                    "csv_path": csv_path,
                    "time_col": config.get("time_col"),
                    "event_col": config.get("target"),
                },
                timeout=60
            )

            if resp.status_code == 200:
                data = resp.json()
                return {
                    "status": "✅ PASS",
                    "median_survival": data.get("median_survival_time"),
                }
            else:
                return {"status": "❌ FAIL", "error": resp.text}

        except Exception as e:
            return {"status": "❌ ERROR", "error": str(e)}

    def run_stats_tests(self, dataset_name: str) -> Dict:
        """執行統計分析測試"""
        config = DATASETS[dataset_name]
        results = {}

        print(f"\n📊 Testing {dataset_name} - Statistics")
        print(f"   File: {config['file']}")
        print(f"   Size: {config['size']}")

        # Quick Stats (所有資料集)
        print("   ├─ Quick Stats...", end=" ")
        results["quick_stats"] = self.test_quick_stats(dataset_name, config)
        print(results["quick_stats"]["status"])

        # Table One (非存活分析)
        if "tableone" in config["stats_tests"]:
            print("   ├─ Table One...", end=" ")
            results["tableone"] = self.test_tableone(dataset_name, config)
            print(results["tableone"]["status"])

        # Correlation (大部分資料集)
        if "correlation" in config["stats_tests"]:
            print("   ├─ Correlation...", end=" ")
            results["correlation"] = self.test_correlation(dataset_name, config)
            print(results["correlation"]["status"])

        # Kaplan-Meier (存活分析)
        if "kaplan_meier" in config["stats_tests"]:
            print("   ├─ Kaplan-Meier...", end=" ")
            results["kaplan_meier"] = self.test_kaplan_meier(dataset_name, config)
            print(results["kaplan_meier"]["status"])

        return results

    def run_ml_tests(self, dataset_name: str) -> Dict:
        """執行 ML 訓練測試（需要 AutoML Service）"""
        config = DATASETS[dataset_name]

        if not config["ml_tests"]:
            print(f"\n🤖 Skipping {dataset_name} - No ML tests defined")
            return {}

        print(f"\n🤖 Testing {dataset_name} - Machine Learning")
        print("   ⚠️  ML tests require AutoML Service (not implemented yet)")
        return {}

    def run_dataset(self, dataset_name: str, suite: str = "all") -> Dict:
        """執行單一資料集的完整測試"""
        if dataset_name not in DATASETS:
            print(f"❌ Unknown dataset: {dataset_name}")
            return {}

        results = {"dataset": dataset_name, "timestamp": time.time()}

        if suite in ["all", "stats"]:
            results["stats"] = self.run_stats_tests(dataset_name)

        if suite in ["all", "ml"]:
            results["ml"] = self.run_ml_tests(dataset_name)

        return results

    def run_all(self, suite: str = "all"):
        """執行所有資料集測試"""
        print("=" * 70)
        print("📋 E2E Dataset Testing Suite")
        print("=" * 70)

        # 檢查服務
        if not self.test_service_health():
            print("\n⚠️  請先啟動 Stats Service")
            print("   Docker: docker compose up -d")
            print("   Local:  python stats-service/src/main.py")
            return

        all_results = []

        for dataset_name in DATASETS.keys():
            result = self.run_dataset(dataset_name, suite)
            all_results.append(result)

        # 摘要報告
        self.print_summary(all_results)

        return all_results

    def print_summary(self, results: List[Dict]):
        """列印摘要報告"""
        print("\n" + "=" * 70)
        print("📈 Test Summary")
        print("=" * 70)

        total = len(results)
        stats_pass = 0
        stats_fail = 0

        for result in results:
            if "stats" in result:
                for _test_name, test_result in result["stats"].items():
                    if test_result.get("status", "").startswith("✅"):
                        stats_pass += 1
                    else:
                        stats_fail += 1

        print(f"Datasets Tested: {total}")
        print(f"Stats Tests: {stats_pass} passed, {stats_fail} failed")
        print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="E2E Dataset Testing")
    parser.add_argument(
        "--dataset",
        choices=list(DATASETS.keys()) + ["all"],
        default="all",
        help="選擇要測試的資料集"
    )
    parser.add_argument(
        "--suite",
        choices=["all", "stats", "ml"],
        default="all",
        help="選擇測試套件"
    )
    parser.add_argument(
        "--data-root",
        default="/home/eric/workspace251204",
        help="資料根目錄"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="顯示詳細錯誤訊息"
    )

    args = parser.parse_args()

    tester = DatasetTester(data_root=args.data_root, verbose=args.verbose)

    if args.dataset == "all":
        tester.run_all(suite=args.suite)
    else:
        tester.run_dataset(args.dataset, suite=args.suite)


if __name__ == "__main__":
    main()
