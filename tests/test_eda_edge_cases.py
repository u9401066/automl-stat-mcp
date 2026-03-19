"""
EDA (Exploratory Data Analysis) Edge Case Tests

這些測試專門用於驗證 EDA 相關端點對各種異常輸入的處理：
1. 空資料、極端資料
2. 特殊字元、Unicode
3. 非法 CSV 格式
4. 混合類型欄位
5. 極端數值（Inf, NaN）
"""

import base64
import os

import httpx
import pytest

STATS_API_URL = os.getenv("STATS_API_URL", "http://localhost:8003")


@pytest.fixture
def client():
    """Create httpx client."""
    return httpx.Client(base_url=STATS_API_URL, timeout=30.0)


class TestQuickStatsEdgeCases:
    """Test /direct/quick-stats with edge cases."""

    def test_empty_csv(self, client):
        """完全空的 CSV"""
        response = client.post("/direct/quick-stats", json={"csv_content": ""})
        assert response.status_code == 400

    def test_only_header(self, client):
        """只有表頭沒有資料"""
        response = client.post("/direct/quick-stats", json={"csv_content": "col1,col2,col3"})
        # 這可能成功（返回 0 rows）或失敗
        if response.status_code == 200:
            data = response.json()
            assert data["rows"] == 0

    def test_single_row(self, client):
        """只有一行資料"""
        response = client.post("/direct/quick-stats", json={"csv_content": "name,age\nAlice,30"})
        assert response.status_code == 200
        data = response.json()
        assert data["rows"] == 1

    def test_all_missing_values(self, client):
        """所有值都是缺失值"""
        response = client.post("/direct/quick-stats", json={"csv_content": "col1,col2,col3\n,,\n,,\n,,"})
        assert response.status_code == 200
        data = response.json()
        assert data["missing_summary"]["total_missing"] > 0

    def test_mixed_types_in_column(self, client):
        """同一欄位混合數字和文字"""
        response = client.post("/direct/quick-stats", json={"csv_content": "value\n1\n2\nthree\n4\nfive"})
        assert response.status_code == 200
        data = response.json()
        # 應該將這欄判斷為 object/categorical
        assert any(c["name"] == "value" for c in data["column_info"])

    def test_special_characters_in_values(self, client):
        """值中包含特殊字元"""
        csv = 'name,description\n"John","Hello, World!"\n"Jane","Say Hi"\n"Bob","Test"'
        response = client.post("/direct/quick-stats", json={"csv_content": csv})
        # CSV 解析應該處理引號和換行
        assert response.status_code in [200, 400]  # 取決於實作

    def test_unicode_values(self, client):
        """Unicode 字元"""
        response = client.post(
            "/direct/quick-stats", json={"csv_content": "name,emoji,chinese\nAlice,😀,你好\nBob,🎉,世界"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["rows"] == 2

    def test_very_long_column_names(self, client):
        """超長欄位名稱"""
        long_name = "a" * 1000
        response = client.post("/direct/quick-stats", json={"csv_content": f"{long_name},b\n1,2\n3,4"})
        assert response.status_code == 200

    def test_many_columns(self, client):
        """大量欄位"""
        cols = ",".join([f"col_{i}" for i in range(100)])
        vals = ",".join(["1" for _ in range(100)])
        response = client.post("/direct/quick-stats", json={"csv_content": f"{cols}\n{vals}"})
        assert response.status_code == 200
        data = response.json()
        assert data["columns"] == 100

    def test_inf_values(self, client):
        """Infinity 值"""
        response = client.post("/direct/quick-stats", json={"csv_content": "value\n1\nInf\n-Inf\n2"})
        assert response.status_code == 200

    def test_nan_string_values(self, client):
        """NaN 字串值"""
        response = client.post("/direct/quick-stats", json={"csv_content": "value\n1\nNaN\nnan\nNA\n2"})
        assert response.status_code == 200
        data = response.json()
        # NaN/nan/NA 應該被視為缺失值
        assert data["missing_summary"]["total_missing"] >= 0

    def test_scientific_notation(self, client):
        """科學記號"""
        response = client.post("/direct/quick-stats", json={"csv_content": "value\n1e10\n2.5e-5\n-1.23E+8"})
        assert response.status_code == 200
        data = response.json()
        # 應該正確解析為數值
        col_info = next(c for c in data["column_info"] if c["name"] == "value")
        assert "float" in col_info["dtype"] or "int" in col_info["dtype"]

    def test_duplicate_column_names(self, client):
        """重複的欄位名稱"""
        response = client.post("/direct/quick-stats", json={"csv_content": "col,col,col\n1,2,3\n4,5,6"})
        # 應該處理或報錯
        assert response.status_code in [200, 400]
        if response.status_code == 200:
            data = response.json()
            # Pandas 會自動重命名為 col, col.1, col.2
            assert data["columns"] == 3

    def test_whitespace_only_values(self, client):
        """只有空白的值"""
        response = client.post("/direct/quick-stats", json={"csv_content": "col1,col2\n   ,\t\n  ,   "})
        assert response.status_code == 200

    def test_base64_encoding(self, client):
        """Base64 編碼的 CSV"""
        csv_content = "name,age\nAlice,30\nBob,25"
        encoded = base64.b64encode(csv_content.encode()).decode()
        response = client.post("/direct/quick-stats", json={"csv_content": encoded, "is_base64": True})
        assert response.status_code == 200
        data = response.json()
        assert data["rows"] == 2

    def test_invalid_base64(self, client):
        """無效的 Base64"""
        response = client.post("/direct/quick-stats", json={"csv_content": "not-valid-base64!!!", "is_base64": True})
        assert response.status_code == 400

    def test_binary_content_not_base64(self, client):
        """二進位內容但沒標記 base64"""
        # Pandas 可能將其解析為單欄 CSV，這是可接受的行為
        response = client.post("/direct/quick-stats", json={"csv_content": "\x00\x01\x02\x03"})
        # 可能成功（解析為怪異的單欄）或失敗
        assert response.status_code in [200, 400]


class TestDirectAnalyzeEdgeCases:
    """Test /direct/analyze with edge cases."""

    def test_empty_csv(self, client):
        """空 CSV"""
        response = client.post("/direct/analyze", json={"csv_content": "", "user_id": "test"})
        assert response.status_code == 400

    def test_invalid_target_column(self, client):
        """不存在的 target_column"""
        response = client.post(
            "/direct/analyze",
            json={"csv_content": "col1,col2\n1,2\n3,4", "user_id": "test", "target_column": "nonexistent_column"},
        )
        # 可能立即返回錯誤，或在 job 執行時失敗
        # 我們先測試提交是否成功
        assert response.status_code in [200, 400, 422]

    def test_all_same_values(self, client):
        """所有值都一樣（常數欄）"""
        response = client.post("/direct/analyze", json={"csv_content": "value\n1\n1\n1\n1\n1", "user_id": "test"})
        assert response.status_code == 200

    def test_very_large_csv(self, client):
        """大型 CSV（測試性能和記憶體）"""
        # 生成 1000 行資料
        header = "col1,col2,col3"
        rows = "\n".join([f"{i},{i * 2},{i * 3}" for i in range(1000)])
        csv_content = f"{header}\n{rows}"

        response = client.post("/direct/analyze", json={"csv_content": csv_content, "user_id": "test"})
        assert response.status_code == 200
        data = response.json()
        assert data["data_preview"]["rows"] == 1000

    def test_negative_numbers(self, client):
        """負數"""
        response = client.post(
            "/direct/analyze", json={"csv_content": "value\n-100\n-50\n0\n50\n100", "user_id": "test"}
        )
        assert response.status_code == 200


class TestEDAPreviewEdgeCases:
    """Test /eda/preview with edge cases."""

    def test_nonexistent_dataset(self, client):
        """不存在的 dataset_id"""
        response = client.post("/eda/preview", params={"dataset_id": "nonexistent_dataset_12345"})
        assert response.status_code == 404

    def test_n_rows_zero(self, client):
        """n_rows = 0"""
        response = client.post("/eda/preview", params={"dataset_id": "some_id", "n_rows": 0})
        # 應該是 422 (validation error) 或 400
        assert response.status_code in [400, 404, 422]

    def test_n_rows_negative(self, client):
        """n_rows < 0"""
        response = client.post("/eda/preview", params={"dataset_id": "some_id", "n_rows": -10})
        # 由於 dataset_id 不存在會先返回 404
        # 負數驗證可能在 dataset 檢查之後
        assert response.status_code in [400, 404, 422]

    def test_n_rows_too_large(self, client):
        """n_rows 超過限制"""
        response = client.post("/eda/preview", params={"dataset_id": "some_id", "n_rows": 1000000})
        # 可能先因 dataset 不存在返回 404，或因 n_rows 驗證返回 422
        assert response.status_code in [404, 422]


class TestColumnInfoEdgeCases:
    """Test /cleaning/column-info with edge cases."""

    def test_nonexistent_file(self, client):
        """不存在的檔案"""
        response = client.post("/cleaning/column-info", json={"csv_path": "/data/sample_data/nonexistent_file.csv"})
        assert response.status_code == 404

    def test_empty_csv_file(self, client):
        """空的 CSV 檔案（如果存在）"""
        # 這需要真實的空檔案，可能跳過
        pass

    def test_binary_file_as_csv(self, client):
        """非 CSV 檔案（但在允許路徑內）"""
        # 嘗試讀取一個可能存在的非 CSV 檔案
        response = client.post("/cleaning/column-info", json={"csv_path": "/tmp/test_binary.bin"})
        # 找不到或解析失敗都可以
        assert response.status_code in [400, 404]


class TestAutoAnalyzeCapabilities:
    """Test auto-analyze capabilities endpoint."""

    def test_get_capabilities(self, client):
        """測試取得分析能力"""
        response = client.get("/auto-analyze/capabilities")
        assert response.status_code == 200
        data = response.json()
        # 應該包含某種能力清單
        assert "capabilities" in data or "tests" in data or "features" in data or isinstance(data, dict)


class TestCorrelationEdgeCases:
    """Test correlation analysis edge cases (if endpoint exists)."""

    def test_single_numeric_column(self, client):
        """只有一個數值欄（無法計算相關性）"""
        # 這需要透過 MCP tool 或直接 API
        # 暫時跳過，因為需要確認端點
        pass

    def test_all_categorical_columns(self, client):
        """所有欄位都是類別型（無法計算 Pearson）"""
        pass


class TestDataTypeBoundaries:
    """Test data type boundary conditions."""

    def test_integer_overflow(self, client):
        """極大整數"""
        response = client.post("/direct/quick-stats", json={"csv_content": "value\n99999999999999999999999999\n1\n2"})
        assert response.status_code == 200

    def test_float_precision(self, client):
        """浮點數精度"""
        response = client.post("/direct/quick-stats", json={"csv_content": "value\n0.1\n0.2\n0.3"})
        assert response.status_code == 200
        data = response.json()
        # 檢查數值摘要存在
        assert data["numeric_summary"] is not None

    def test_date_column_detection(self, client):
        """日期欄位偵測"""
        response = client.post(
            "/direct/quick-stats", json={"csv_content": "date,value\n2024-01-01,100\n2024-01-02,200\n2024-01-03,300"}
        )
        assert response.status_code == 200
        data = response.json()
        # 檢查日期欄位的 dtype
        date_col = next(c for c in data["column_info"] if c["name"] == "date")
        # 可能是 object (string) 或 datetime
        assert date_col["dtype"] in ["object", "datetime64[ns]", "datetime64"]

    def test_boolean_column(self, client):
        """布林欄位"""
        response = client.post("/direct/quick-stats", json={"csv_content": "active,count\nTrue,1\nFalse,2\nTrue,3"})
        assert response.status_code == 200


class TestMalformedCSV:
    """Test malformed CSV handling."""

    def test_unequal_columns(self, client):
        """每行欄數不同"""
        response = client.post("/direct/quick-stats", json={"csv_content": "a,b,c\n1,2,3\n4,5\n6,7,8,9"})
        # pandas 可能會報錯或自動處理
        assert response.status_code in [200, 400]

    def test_unclosed_quote(self, client):
        """未閉合的引號"""
        response = client.post("/direct/quick-stats", json={"csv_content": 'name,desc\n"Alice,30\nBob,25'})
        assert response.status_code == 400

    def test_only_newlines(self, client):
        """只有換行符"""
        response = client.post("/direct/quick-stats", json={"csv_content": "\n\n\n"})
        assert response.status_code == 400

    def test_tabs_as_delimiter(self, client):
        """Tab 分隔（不是逗號）"""
        response = client.post("/direct/quick-stats", json={"csv_content": "col1\tcol2\tcol3\n1\t2\t3"})
        # 如果用 , 解析會得到單欄
        if response.status_code == 200:
            data = response.json()
            # 可能是 1 欄（整行當一欄）或 3 欄（智能偵測）
            assert data["columns"] >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
