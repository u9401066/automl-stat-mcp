"""
邊界測試 - 資料大小與型態邊界

測試各種極端情況下的資料處理能力
"""

import os
import tempfile

import numpy as np
import pandas as pd
import pytest


class TestDataSizeBoundaries:
    """測試資料大小邊界情況"""

    def test_empty_dataframe(self):
        """測試空資料集處理"""
        df = pd.DataFrame()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            df.to_csv(f.name, index=False)
            path = f.name

        try:
            # 空 DataFrame 寫出的 CSV 完全為空，pandas 應拋出 EmptyDataError
            with pytest.raises(pd.errors.EmptyDataError):
                pd.read_csv(path)
        finally:
            os.unlink(path)

    def test_single_row_dataframe(self):
        """測試單筆資料"""
        df = pd.DataFrame({"a": [1], "b": [2], "c": [3]})

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            df.to_csv(f.name, index=False)
            path = f.name

        try:
            loaded_df = pd.read_csv(path)
            assert len(loaded_df) == 1

            # 統計分析應警告樣本數不足
            # 單筆資料的樣本標準差應為 NaN
            assert np.isnan(loaded_df["a"].std())
        finally:
            os.unlink(path)

    def test_two_rows_minimum(self):
        """測試最小統計可行集（2筆資料）"""
        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            df.to_csv(f.name, index=False)
            path = f.name

        try:
            loaded_df = pd.read_csv(path)
            assert len(loaded_df) == 2

            # 能計算標準差
            std = loaded_df["a"].std()
            assert std > 0

            # 但某些統計不可行（如 t-test 需要 n>2）
            assert len(loaded_df) < 3  # 警告條件
        finally:
            os.unlink(path)

    def test_single_column_dataframe(self):
        """測試單一欄位"""
        df = pd.DataFrame({"a": [1, 2, 3, 4, 5]})

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            df.to_csv(f.name, index=False)
            path = f.name

        try:
            loaded_df = pd.read_csv(path)
            assert len(loaded_df.columns) == 1

            # 相關性分析應友善處理（無法計算單欄位相關性）
            corr_matrix = loaded_df.corr()
            assert corr_matrix.shape == (1, 1)
            assert corr_matrix.iloc[0, 0] == 1.0  # 自己與自己完美相關
        finally:
            os.unlink(path)

    @pytest.mark.slow
    def test_large_dataset_memory_efficiency(self):
        """測試大資料集記憶體效率（1萬筆）"""
        # 生成較大資料集
        n_rows = 10_000
        df = pd.DataFrame({f"col_{i}": np.random.randn(n_rows) for i in range(10)})

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            df.to_csv(f.name, index=False)
            path = f.name

        try:
            # 使用 chunk 讀取
            chunk_size = 1000
            chunks = []
            for chunk in pd.read_csv(path, chunksize=chunk_size):
                chunks.append(chunk)

            loaded_df = pd.concat(chunks, ignore_index=True)
            assert len(loaded_df) == n_rows
        finally:
            os.unlink(path)


class TestDataTypeBoundaries:
    """測試資料型態邊界情況"""

    def test_all_nan_column(self):
        """測試完全缺失的欄位"""
        df = pd.DataFrame({"a": [1, 2, 3], "b": [np.nan, np.nan, np.nan]})

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            df.to_csv(f.name, index=False)
            path = f.name

        try:
            loaded_df = pd.read_csv(path)

            # 檢查 all NaN
            assert loaded_df["b"].isna().all()

            # 應該警告該欄位無用
            missing_pct = loaded_df["b"].isna().sum() / len(loaded_df)
            assert missing_pct == 1.0
        finally:
            os.unlink(path)

    def test_constant_column(self):
        """測試所有值相同的欄位（零變異）"""
        df = pd.DataFrame({"a": [1, 2, 3, 4, 5], "constant": [1, 1, 1, 1, 1]})

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            df.to_csv(f.name, index=False)
            path = f.name

        try:
            loaded_df = pd.read_csv(path)

            # 檢查零變異
            assert loaded_df["constant"].std() == 0
            assert loaded_df["constant"].nunique() == 1

            # 應該警告該欄位對分析無貢獻
        finally:
            os.unlink(path)

    def test_infinity_values(self):
        """測試無限值處理"""
        df = pd.DataFrame({"a": [1, 2, np.inf, 4, -np.inf]})

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            df.to_csv(f.name, index=False)
            path = f.name

        try:
            loaded_df = pd.read_csv(path)

            # 檢查無限值
            assert np.isinf(loaded_df["a"]).sum() == 2

            # 替換無限值為 NaN
            cleaned_df = loaded_df.replace([np.inf, -np.inf], np.nan)
            assert cleaned_df["a"].isna().sum() == 2
        finally:
            os.unlink(path)

    def test_extreme_outliers(self):
        """測試極端離群值偵測"""
        df = pd.DataFrame(
            {
                "a": [1, 2, 3, 4, 1e10]  # 最後一個是極端離群值
            }
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            df.to_csv(f.name, index=False)
            path = f.name

        try:
            loaded_df = pd.read_csv(path)

            # 使用 IQR 偵測離群值
            Q1 = loaded_df["a"].quantile(0.25)
            Q3 = loaded_df["a"].quantile(0.75)
            IQR = Q3 - Q1

            lower_bound = Q1 - 3 * IQR
            upper_bound = Q3 + 3 * IQR

            outliers = loaded_df[(loaded_df["a"] < lower_bound) | (loaded_df["a"] > upper_bound)]
            assert len(outliers) == 1
            assert outliers.iloc[0]["a"] == 1e10
        finally:
            os.unlink(path)

    def test_unicode_special_chars(self):
        """測試特殊 Unicode 字元處理"""
        df = pd.DataFrame(
            {
                "名字": ["測試", "🎉", "中文"],
                "emoji": ["😀", "🚀", "🎯"],
                "mixed": ["Hello世界", "Test測試", "Data資料"],
            }
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
            df.to_csv(f.name, index=False)
            path = f.name

        try:
            # 使用 UTF-8 讀取
            loaded_df = pd.read_csv(path, encoding="utf-8")

            assert len(loaded_df) == 3
            assert "名字" in loaded_df.columns
            assert loaded_df["emoji"].iloc[0] == "😀"
            assert loaded_df["mixed"].iloc[0] == "Hello世界"
        finally:
            os.unlink(path)


class TestStatisticalBoundaries:
    """測試統計分析邊界情況"""

    def test_perfect_correlation(self):
        """測試完美正相關 (r=1.0)"""
        df = pd.DataFrame(
            {
                "a": [1, 2, 3, 4, 5],
                "b": [2, 4, 6, 8, 10],  # b = 2*a
            }
        )

        corr = df["a"].corr(df["b"])
        assert abs(corr - 1.0) < 1e-10

    def test_perfect_negative_correlation(self):
        """測試完美負相關 (r=-1.0)"""
        df = pd.DataFrame(
            {
                "a": [1, 2, 3, 4, 5],
                "b": [5, 4, 3, 2, 1],  # b = 6-a
            }
        )

        corr = df["a"].corr(df["b"])
        assert abs(corr - (-1.0)) < 1e-10

    def test_zero_variance_group(self):
        """測試零變異群組（無法計算 t-test）"""
        df = pd.DataFrame(
            {
                "group": [0, 0, 0, 1, 1, 1],
                "value": [1, 1, 1, 2, 3, 4],  # Group 0 零變異
            }
        )

        group0 = df[df["group"] == 0]["value"]
        group1 = df[df["group"] == 1]["value"]

        assert group0.std() == 0
        assert group1.std() > 0

        # t-test 目前會返回有限結果，但需提醒其可靠性受限
        from scipy import stats

        test_result = stats.ttest_ind(group0, group1)
        assert test_result is not None

    def test_extremely_unbalanced_groups(self):
        """測試極度不平衡群組"""
        df = pd.DataFrame({"group": [0] + [1] * 100, "value": np.random.randn(101)})

        # 檢查不平衡比例
        group_counts = df["group"].value_counts()
        ratio = group_counts.max() / group_counts.min()

        assert ratio == 100  # 1:100 不平衡

        # 應該警告樣本不平衡

    def test_all_same_values_in_group(self):
        """測試群組內所有值相同"""
        df = pd.DataFrame({"group": [0, 0, 0, 1, 1, 1], "value": [1, 1, 1, 2, 2, 2]})

        # 兩個群組都是常數
        for group_id in [0, 1]:
            group_data = df[df["group"] == group_id]["value"]
            assert group_data.nunique() == 1


class TestMLBoundaries:
    """測試 ML 訓練邊界情況"""

    def test_more_features_than_samples(self):
        """測試特徵數 > 樣本數 (p >> n)"""
        n_samples = 10
        n_features = 100

        df = pd.DataFrame(np.random.randn(n_samples, n_features), columns=[f"feature_{i}" for i in range(n_features)])
        df["target"] = np.random.randint(0, 2, n_samples)

        # 應該警告或自動特徵選擇
        assert n_features > n_samples

    def test_perfectly_separable_data(self):
        """測試完美可分類資料（過擬合風險）"""
        df = pd.DataFrame({"x": [1, 2, 3, 4, 5, 6], "y": [0, 0, 0, 1, 1, 1]})

        # 檢查完美可分性
        group0 = df[df["y"] == 0]["x"]
        group1 = df[df["y"] == 1]["x"]

        assert group0.max() < group1.min()  # 完全可分

        # 訓練應該達到 100% 準確度，但應警告過擬合

    def test_extreme_class_imbalance(self):
        """測試極度不平衡類別 (1:1000)"""
        n_minority = 1
        n_majority = 1000

        df = pd.DataFrame(
            {"feature": np.random.randn(n_minority + n_majority), "target": [0] * n_minority + [1] * n_majority}
        )

        # 檢查不平衡
        class_counts = df["target"].value_counts()
        ratio = class_counts.max() / class_counts.min()

        assert ratio == 1000

        # 應該自動使用 class_weight 或 SMOTE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
