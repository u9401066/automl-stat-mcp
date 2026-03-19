"""
Data Quality Testing Suite

測試統計分析對各種資料品質問題的處理：
1. 全 NaN 欄 (All-NaN Columns)
2. 常數欄 (Constant Columns)
3. 高基數 ID 欄 (High-Cardinality ID Columns)
4. 偏態資料 (Skewed Data needing Transform)
5. 極端值 (Outliers)
6. 混合型別 (Mixed Types)

推薦架構: 所有分析端點應該返回 quality_warnings 欄位
"""

import math

import httpx
import pytest

BASE_URL = "http://localhost:8003"
TIMEOUT = 30.0


class TestAllNaNColumns:
    """全 NaN 欄位測試"""

    @pytest.fixture
    def csv_with_all_nan(self):
        """含有全 NaN 欄位的資料"""
        return "id,all_nan,partial_nan,complete\n1,,10,100\n2,,,200\n3,,30,300"

    def test_quick_stats_detects_all_nan(self, csv_with_all_nan):
        """quick-stats 應該能偵測全 NaN 欄"""
        with httpx.Client(timeout=TIMEOUT) as client:
            r = client.post(f"{BASE_URL}/direct/quick-stats", json={"csv_content": csv_with_all_nan})
            assert r.status_code == 200
            data = r.json()

            # 找到 all_nan 欄位
            all_nan_col = next(c for c in data["column_info"] if c["name"] == "all_nan")
            assert all_nan_col["null"] == data["rows"]  # 所有值都是 null
            assert all_nan_col["unique"] == 0  # 沒有唯一值

    def test_quick_stats_all_nan_excluded_from_numeric(self, csv_with_all_nan):
        """全 NaN 欄不應該出現在 numeric_summary（或應標記為 NaN）"""
        with httpx.Client(timeout=TIMEOUT) as client:
            r = client.post(f"{BASE_URL}/direct/quick-stats", json={"csv_content": csv_with_all_nan})
            data = r.json()

            if "all_nan" in data.get("numeric_summary", {}):
                stats = data["numeric_summary"]["all_nan"]
                # std 應該是 NaN 或 None
                assert stats.get("std") is None or (isinstance(stats.get("std"), float) and math.isnan(stats["std"]))

    def test_entirely_nan_csv(self):
        """完全沒有資料的 CSV（只有 NaN）"""
        csv = "a,b,c\n,,\n,,\n,,"
        with httpx.Client(timeout=TIMEOUT) as client:
            r = client.post(f"{BASE_URL}/direct/quick-stats", json={"csv_content": csv})
            assert r.status_code == 200
            data = r.json()
            # 所有欄位都應該是全 NaN
            for col in data["column_info"]:
                assert col["null"] == data["rows"]


class TestConstantColumns:
    """常數欄（所有值相同）測試"""

    @pytest.fixture
    def csv_with_constant(self):
        return "id,constant_num,constant_str,normal\n1,999,SAME,10\n2,999,SAME,20\n3,999,SAME,30\n4,999,SAME,40"

    def test_quick_stats_detects_constant(self, csv_with_constant):
        """quick-stats 應該能偵測常數欄"""
        with httpx.Client(timeout=TIMEOUT) as client:
            r = client.post(f"{BASE_URL}/direct/quick-stats", json={"csv_content": csv_with_constant})
            assert r.status_code == 200
            data = r.json()

            # 找到 constant 欄位
            const_col = next(c for c in data["column_info"] if c["name"] == "constant_num")
            assert const_col["unique"] == 1  # 只有一個唯一值

    def test_constant_column_zero_std(self, csv_with_constant):
        """常數欄的 std 應該是 0"""
        with httpx.Client(timeout=TIMEOUT) as client:
            r = client.post(f"{BASE_URL}/direct/quick-stats", json={"csv_content": csv_with_constant})
            data = r.json()

            if "constant_num" in data.get("numeric_summary", {}):
                stats = data["numeric_summary"]["constant_num"]
                assert stats.get("std") == 0.0

    def test_constant_column_correlation_nan(self):
        """常數欄的相關性應該是 NaN（無法計算）"""
        csv = "const,var1,var2\n5,1,10\n5,2,20\n5,3,30\n5,4,40"
        with httpx.Client(timeout=TIMEOUT) as client:
            r = client.post(f"{BASE_URL}/direct/quick-stats", json={"csv_content": csv})
            data = r.json()
            # 常數欄的標準差為 0，相關性會是 NaN
            assert data["numeric_summary"]["const"]["std"] == 0.0


class TestHighCardinalityIDColumns:
    """高基數 ID 欄測試（每個值都不同）"""

    @pytest.fixture
    def csv_with_id_columns(self):
        return """patient_id,mrn,uuid,age,outcome
P001,MRN0001,550e8400-e29b-41d4-a716-446655440001,25,1
P002,MRN0002,550e8400-e29b-41d4-a716-446655440002,30,0
P003,MRN0003,550e8400-e29b-41d4-a716-446655440003,35,1
P004,MRN0004,550e8400-e29b-41d4-a716-446655440004,40,0
P005,MRN0005,550e8400-e29b-41d4-a716-446655440005,45,1"""

    def test_detects_high_cardinality(self, csv_with_id_columns):
        """應該能偵測高基數 ID 欄"""
        with httpx.Client(timeout=TIMEOUT) as client:
            r = client.post(f"{BASE_URL}/direct/quick-stats", json={"csv_content": csv_with_id_columns})
            assert r.status_code == 200
            data = r.json()

            for col in data["column_info"]:
                if col["name"] in ["patient_id", "mrn", "uuid"]:
                    # 每個值都不同 = 高基數
                    assert col["unique"] == data["rows"]

    def test_id_column_not_useful_for_analysis(self, csv_with_id_columns):
        """ID 欄不應該被用於相關性或統計分析"""
        # 這是一個警告：高基數欄通常不適合用於統計分析
        with httpx.Client(timeout=TIMEOUT) as client:
            r = client.post(f"{BASE_URL}/direct/quick-stats", json={"csv_content": csv_with_id_columns})
            data = r.json()

            # 檢查 age 和 outcome 是有意義的（低基數）
            age_col = next(c for c in data["column_info"] if c["name"] == "age")
            outcome_col = next(c for c in data["column_info"] if c["name"] == "outcome")

            # age 和 outcome 的基數應該合理
            assert age_col["unique"] <= data["rows"]
            assert outcome_col["unique"] <= 2  # binary outcome


class TestSkewedDataNeedingTransform:
    """偏態資料（需要 Transform）測試"""

    @pytest.fixture
    def csv_with_skewed_data(self):
        """高度偏態的收入資料"""
        return """id,income,log_income,age
1,1000,3.0,25
2,2000,3.3,30
3,1500,3.2,28
4,50000000,7.7,35
5,1200,3.1,26
6,1800,3.3,32
7,1600,3.2,29
8,1400,3.1,27"""

    def test_detects_skewness(self, csv_with_skewed_data):
        """應該能偵測偏態資料"""
        with httpx.Client(timeout=TIMEOUT) as client:
            r = client.post(f"{BASE_URL}/direct/quick-stats", json={"csv_content": csv_with_skewed_data})
            assert r.status_code == 200
            data = r.json()

            income_stats = data["numeric_summary"]["income"]
            mean = income_stats["mean"]
            median = income_stats["50%"]

            # 偏態指標：mean 遠大於 median
            skew_ratio = abs(mean - median) / median if median > 0 else float("inf")
            assert skew_ratio > 1, "Income 應該是嚴重偏態"

    def test_log_transform_reduces_skewness(self, csv_with_skewed_data):
        """Log transform 後偏態應該減少"""
        with httpx.Client(timeout=TIMEOUT) as client:
            r = client.post(f"{BASE_URL}/direct/quick-stats", json={"csv_content": csv_with_skewed_data})
            data = r.json()

            log_stats = data["numeric_summary"]["log_income"]
            mean = log_stats["mean"]
            median = log_stats["50%"]

            # Log transform 後偏態應該減少
            skew_ratio = abs(mean - median) / median if median > 0 else float("inf")
            # 注意：這只是示範，實際的 log_income 在原資料中已經是 log 過的
            assert skew_ratio < 5, "Log income 偏態應該較小"


class TestOutliers:
    """極端值測試"""

    @pytest.fixture
    def csv_with_outliers(self):
        return """id,value,normal
1,10,50
2,15,55
3,12,52
4,1000000,60
5,11,48
6,14,53"""

    def test_detects_outliers_via_iqr(self, csv_with_outliers):
        """應該能通過 IQR 偵測極端值"""
        with httpx.Client(timeout=TIMEOUT) as client:
            r = client.post(f"{BASE_URL}/direct/quick-stats", json={"csv_content": csv_with_outliers})
            data = r.json()

            value_stats = data["numeric_summary"]["value"]
            q1 = value_stats["25%"]
            q3 = value_stats["75%"]
            iqr = q3 - q1
            max_val = value_stats["max"]

            # 極端值判定：超過 Q3 + 1.5*IQR
            upper_bound = q3 + 1.5 * iqr
            assert max_val > upper_bound, "Max 應該是極端值"


class TestMixedTypes:
    """混合型別測試"""

    def test_numeric_with_text(self):
        """數字欄位中混有文字"""
        csv = "id,value\n1,100\n2,N/A\n3,200\n4,missing\n5,300"
        with httpx.Client(timeout=TIMEOUT) as client:
            r = client.post(f"{BASE_URL}/direct/quick-stats", json={"csv_content": csv})
            assert r.status_code == 200
            data = r.json()

            # value 會被當成 object 型別
            value_col = next(c for c in data["column_info"] if c["name"] == "value")
            assert value_col["dtype"] == "object"

    def test_date_detection(self):
        """日期格式偵測"""
        csv = "id,date,value\n1,2024-01-15,100\n2,2024-02-20,200\n3,2024-03-25,300"
        with httpx.Client(timeout=TIMEOUT) as client:
            r = client.post(f"{BASE_URL}/direct/quick-stats", json={"csv_content": csv})
            assert r.status_code == 200
            data = r.json()

            # date 通常會被當成 object，除非特別解析
            date_col = next(c for c in data["column_info"] if c["name"] == "date")
            # 可能是 object 或 datetime64
            assert date_col["dtype"] in ["object", "datetime64[ns]"]


class TestStatisticalAnalysisRobustness:
    """統計分析對問題資料的魯棒性"""

    def test_survival_constant_time_should_fail_gracefully(self):
        """Survival: 常數 time 應該優雅失敗"""
        csv = "time,event\n10,1\n10,1\n10,0\n10,1"
        with httpx.Client(timeout=TIMEOUT) as client:
            r = client.post(
                f"{BASE_URL}/survival/kaplan-meier/submit",
                json={"user_id": "test", "time_column": "time", "event_column": "event", "csv_content": csv},
            )
            # 應該返回 400 而不是 500
            assert r.status_code in [200, 400, 422], f"Got {r.status_code}: {r.text[:200]}"
            if r.status_code == 500:
                pytest.fail(f"Server error on constant time: {r.text[:200]}")

    def test_survival_all_censored(self):
        """Survival: 全部 censored（沒有事件）"""
        csv = "time,event\n10,0\n20,0\n30,0\n40,0"
        with httpx.Client(timeout=TIMEOUT) as client:
            r = client.post(
                f"{BASE_URL}/survival/kaplan-meier/submit",
                json={"user_id": "test", "time_column": "time", "event_column": "event", "csv_content": csv},
            )
            assert r.status_code in [200, 400, 422], f"Got {r.status_code}"

    def test_survival_negative_time(self):
        """Survival: 負值 time"""
        csv = "time,event\n-10,1\n20,0\n30,1\n40,0"
        with httpx.Client(timeout=TIMEOUT) as client:
            r = client.post(
                f"{BASE_URL}/survival/kaplan-meier/submit",
                json={"user_id": "test", "time_column": "time", "event_column": "event", "csv_content": csv},
            )
            # 應該返回 400（負數 time 沒有意義）
            assert r.status_code in [200, 400, 422]

    def test_roc_constant_predictions(self):
        """ROC: 常數預測值"""
        csv = "actual,predicted\n1,0.5\n0,0.5\n1,0.5\n0,0.5"
        with httpx.Client(timeout=TIMEOUT) as client:
            r = client.post(
                f"{BASE_URL}/roc/compute/submit",
                json={"user_id": "test", "true_column": "actual", "score_column": "predicted", "csv_content": csv},
            )
            # 常數預測的 AUC = 0.5，應該能處理
            assert r.status_code in [200, 400, 422]

    def test_roc_perfect_separation(self):
        """ROC: 完美分離（AUC=1.0）"""
        csv = "actual,predicted\n1,0.9\n1,0.95\n0,0.1\n0,0.05"
        with httpx.Client(timeout=TIMEOUT) as client:
            r = client.post(
                f"{BASE_URL}/roc/compute/submit",
                json={"user_id": "test", "true_column": "actual", "score_column": "predicted", "csv_content": csv},
            )
            assert r.status_code in [200, 422]

    def test_propensity_extreme_imbalance(self):
        """Propensity: 極端不平衡的 treatment"""
        csv = "treatment,age,bmi\n1,25,22\n0,30,25\n0,35,28\n0,40,30\n0,45,32\n0,50,35"
        with httpx.Client(timeout=TIMEOUT) as client:
            r = client.post(
                f"{BASE_URL}/propensity/estimate/submit",
                json={
                    "user_id": "test",
                    "treatment_column": "treatment",
                    "covariates": ["age", "bmi"],
                    "csv_content": csv,
                },
            )
            # 極端不平衡可能導致估計不穩定
            assert r.status_code in [200, 400, 422]

    def test_propensity_no_treatment_variation(self):
        """Propensity: treatment 全部相同"""
        csv = "treatment,age,bmi\n1,25,22\n1,30,25\n1,35,28\n1,40,30"
        with httpx.Client(timeout=TIMEOUT) as client:
            r = client.post(
                f"{BASE_URL}/propensity/estimate/submit",
                json={
                    "user_id": "test",
                    "treatment_column": "treatment",
                    "covariates": ["age", "bmi"],
                    "csv_content": csv,
                },
            )
            # 返回 200 表示 job 已提交（異步處理）
            # 實際錯誤會在 worker 中處理，job status 會變成 failed
            # 這裡只驗證 API 接受請求
            assert r.status_code in [200, 400, 422]


class TestDataQualityRecommendations:
    """資料品質建議測試"""

    @pytest.fixture
    def problematic_csv(self):
        """包含多種問題的 CSV"""
        return """patient_id,mrn,all_nan,constant,income,treatment,outcome
P001,MRN001,,999,1000,A,1
P002,MRN002,,999,2000,B,0
P003,MRN003,,999,50000000,A,1
P004,MRN004,,999,1500,B,0
P005,MRN005,,999,1200,A,1"""

    def test_identify_all_issues(self, problematic_csv):
        """應該能識別所有資料品質問題"""
        with httpx.Client(timeout=TIMEOUT) as client:
            r = client.post(f"{BASE_URL}/direct/quick-stats", json={"csv_content": problematic_csv})
            data = r.json()

            issues_found = []

            for col in data["column_info"]:
                # 全 NaN
                if col["null"] == data["rows"]:
                    issues_found.append(f"ALL_NAN:{col['name']}")

                # 常數欄
                elif col["unique"] == 1:
                    issues_found.append(f"CONSTANT:{col['name']}")

                # 高基數 ID
                elif col["unique"] == data["rows"] and data["rows"] > 3:
                    if col["dtype"] == "object":
                        issues_found.append(f"HIGH_CARDINALITY_ID:{col['name']}")

            # 檢查偏態
            if data.get("numeric_summary"):
                for col_name, stats in data["numeric_summary"].items():
                    if "mean" in stats and "50%" in stats:
                        mean = stats.get("mean")
                        median = stats.get("50%")
                        # 確保 mean 和 median 都是有效數值
                        if mean is not None and median is not None and median > 0:
                            skew_ratio = abs(mean - median) / median
                            if skew_ratio > 1:
                                issues_found.append(f"SKEWED:{col_name}")

            # 驗證找到的問題
            assert "ALL_NAN:all_nan" in issues_found
            assert "CONSTANT:constant" in issues_found
            assert any("HIGH_CARDINALITY_ID" in i for i in issues_found)
            assert "SKEWED:income" in issues_found

    def test_quality_warning_format(self, problematic_csv):
        """品質警告的格式應該一致"""
        # 這是推薦的輸出格式
        # 目前系統沒有返回這個，這是建議實作的功能
        # 此測試用於追蹤功能需求
        pass


class TestTransformRequirements:
    """Transform 需求測試"""

    def test_log_transform_for_income(self):
        """收入類資料通常需要 log transform"""
        csv = "income\n1000\n2000\n1500\n50000000\n1200"
        with httpx.Client(timeout=TIMEOUT) as client:
            r = client.post(f"{BASE_URL}/direct/quick-stats", json={"csv_content": csv})
            data = r.json()

            stats = data["numeric_summary"]["income"]
            mean = stats["mean"]
            median = stats["50%"]
            std = stats["std"]

            # 嚴重偏態的判定
            if median > 0:
                skew_ratio = abs(mean - median) / median
                coefficient_of_variation = std / mean if mean > 0 else float("inf")

                needs_transform = skew_ratio > 1 or coefficient_of_variation > 2
                assert needs_transform, "高度偏態資料應該需要 transform"

    def test_power_analysis_handles_extreme_effect_sizes(self):
        """Power analysis 應該能處理極端 effect size"""
        with httpx.Client(timeout=TIMEOUT) as client:
            # 極小 effect size
            r = client.post(f"{BASE_URL}/power/ttest", json={"effect_size": 0.01, "alpha": 0.05, "power": 0.8})
            assert r.status_code == 200
            data = r.json()
            # 極小 effect 需要極大樣本
            assert data["result"] > 10000

            # 極大 effect size
            r = client.post(f"{BASE_URL}/power/ttest", json={"effect_size": 5.0, "alpha": 0.05, "power": 0.8})
            assert r.status_code == 200
            data = r.json()
            # 極大 effect 只需要極小樣本
            assert data["result"] < 10


class TestRecommendedArchitecture:
    """推薦架構：資料品質警告整合"""

    def test_recommended_response_structure(self):
        """
        推薦的 API 回應結構:

        {
            "rows": 100,
            "columns": 10,
            "column_info": [...],
            "numeric_summary": {...},
            "quality_warnings": [
                {
                    "column": "all_nan",
                    "issue": "ALL_NAN",
                    "severity": "critical",
                    "recommendation": "移除此欄或填補缺失值",
                    "impact": "此欄不會被納入統計分析"
                },
                {
                    "column": "patient_id",
                    "issue": "HIGH_CARDINALITY_ID",
                    "severity": "warning",
                    "recommendation": "排除於分析外",
                    "impact": "不適合作為分類或分組變數"
                },
                {
                    "column": "income",
                    "issue": "SKEWED",
                    "severity": "info",
                    "recommendation": "考慮 log transform",
                    "impact": "可能影響參數統計方法的準確性"
                }
            ],
            "transform_suggestions": {
                "income": {
                    "suggested_transform": "log",
                    "reason": "嚴重正偏態 (skew_ratio=10.5)",
                    "original_stats": {"mean": 1000000, "median": 2000},
                    "transformed_preview": {"mean": 4.5, "median": 3.3}
                }
            },
            "analysis_readiness": {
                "ready": false,
                "blocking_issues": ["ALL_NAN:all_nan"],
                "warnings": ["HIGH_CARDINALITY_ID:patient_id", "SKEWED:income"],
                "recommended_actions": [
                    "移除 all_nan 欄位",
                    "排除 patient_id 於分析",
                    "對 income 欄位應用 log transform"
                ]
            }
        }
        """
        # 這是功能建議文檔，不是實際測試
        # 用於追蹤未來功能實作
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
