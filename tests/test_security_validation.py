"""
Security and Input Validation Tests

這些測試專門用於驗證:
1. 路徑遍歷攻擊防護
2. 輸入參數驗證
3. 邊界條件處理

這些測試確保 API 對惡意輸入有正確的防護。
"""
import os

import httpx
import pytest

STATS_API_URL = os.getenv("STATS_API_URL", "http://localhost:8003")


@pytest.fixture
def client():
    """Create httpx client."""
    return httpx.Client(base_url=STATS_API_URL, timeout=30.0)


class TestPathTraversalSecurity:
    """Test protection against path traversal attacks."""

    def test_block_etc_passwd(self, client):
        """直接讀取 /etc/passwd 應該被阻止"""
        response = client.post("/cleaning/column-info", json={
            "csv_path": "/etc/passwd"
        })
        assert response.status_code == 403
        assert "Access denied" in response.text

    def test_block_relative_path_traversal(self, client):
        """相對路徑穿越攻擊應該被阻止"""
        response = client.post("/cleaning/column-info", json={
            "csv_path": "/data/sample_data/../../etc/passwd"
        })
        assert response.status_code == 403
        assert "Access denied" in response.text

    def test_block_double_encoded_traversal(self, client):
        """雙重編碼的路徑穿越攻擊"""
        response = client.post("/cleaning/column-info", json={
            "csv_path": "/data/sample_data/..%2F..%2Fetc/passwd"
        })
        # 應該返回 403 (阻止) 或 404 (找不到)
        assert response.status_code in [403, 404, 400]

    def test_block_root_path(self, client):
        """嘗試讀取根目錄下的檔案"""
        response = client.post("/cleaning/column-info", json={
            "csv_path": "/root/.bashrc"
        })
        assert response.status_code == 403

    def test_block_var_log(self, client):
        """嘗試讀取 log 檔案"""
        response = client.post("/cleaning/column-info", json={
            "csv_path": "/var/log/syslog"
        })
        assert response.status_code in [403, 404]

    def test_allow_valid_sample_data_path(self, client):
        """合法的 sample_data 路徑應該允許"""
        response = client.post("/cleaning/column-info", json={
            "csv_path": "/data/sample_data/iris.csv"
        })
        assert response.status_code == 200

    def test_allow_valid_tmp_path(self, client):
        """/tmp 路徑應該允許 (用於暫存)"""
        # 先檢查 /tmp 是否有效 (即使檔案不存在也返回 404 而不是 403)
        response = client.post("/cleaning/column-info", json={
            "csv_path": "/tmp/nonexistent.csv"
        })
        assert response.status_code in [404, 400]  # 找不到檔案，但不是 403
        assert response.status_code != 403  # 確認不是權限拒絕


class TestPowerAnalysisValidation:
    """Test input validation for power analysis endpoints."""

    def test_effect_size_zero_rejected(self, client):
        """effect_size=0 應該返回驗證錯誤"""
        response = client.post("/power/ttest", json={
            "effect_size": 0,
            "alpha": 0.05,
            "power": 0.8
        })
        assert response.status_code == 422
        assert "effect_size" in response.text
        assert "zero" in response.text.lower()

    def test_negative_effect_size_handling(self, client):
        """負的 effect_size 應該被處理 (絕對值或錯誤)"""
        response = client.post("/power/ttest", json={
            "effect_size": -0.5,
            "alpha": 0.05,
            "power": 0.8
        })
        # 允許 200 (取絕對值) 或 422 (驗證錯誤)
        assert response.status_code in [200, 422]

    def test_alpha_greater_than_one_rejected(self, client):
        """alpha > 1 應該返回驗證錯誤"""
        response = client.post("/power/ttest", json={
            "effect_size": 0.5,
            "alpha": 1.5,
            "power": 0.8
        })
        assert response.status_code == 422
        assert "alpha" in response.text

    def test_alpha_zero_rejected(self, client):
        """alpha = 0 應該返回驗證錯誤"""
        response = client.post("/power/ttest", json={
            "effect_size": 0.5,
            "alpha": 0,
            "power": 0.8
        })
        assert response.status_code == 422

    def test_alpha_one_rejected(self, client):
        """alpha = 1 應該返回驗證錯誤"""
        response = client.post("/power/ttest", json={
            "effect_size": 0.5,
            "alpha": 1.0,
            "power": 0.8
        })
        assert response.status_code == 422

    def test_negative_n_rejected(self, client):
        """n < 0 應該返回驗證錯誤"""
        response = client.post("/power/ttest", json={
            "effect_size": 0.5,
            "n": -10,
            "alpha": 0.05
        })
        assert response.status_code == 422
        assert "n" in response.text

    def test_zero_n_rejected(self, client):
        """n = 0 應該返回驗證錯誤"""
        response = client.post("/power/ttest", json={
            "effect_size": 0.5,
            "n": 0,
            "alpha": 0.05
        })
        assert response.status_code == 422

    def test_power_greater_than_one_rejected(self, client):
        """power > 1 應該返回驗證錯誤"""
        response = client.post("/power/ttest", json={
            "effect_size": 0.5,
            "alpha": 0.05,
            "power": 1.5
        })
        assert response.status_code == 422

    def test_valid_ttest_request_accepted(self, client):
        """合法的請求應該成功"""
        response = client.post("/power/ttest", json={
            "effect_size": 0.5,
            "alpha": 0.05,
            "power": 0.8
        })
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        assert data["result"] > 0


class TestProportionPowerValidation:
    """Test validation for proportion power analysis."""

    def test_proportion_greater_than_one_rejected(self, client):
        """比例 > 1 應該返回驗證錯誤"""
        response = client.post("/power/proportion", json={
            "p1": 2.0,
            "p2": 0.3,
            "alpha": 0.05
        })
        assert response.status_code == 422
        assert "p1" in response.text or "proportion" in response.text.lower()

    def test_negative_proportion_rejected(self, client):
        """負比例應該返回驗證錯誤"""
        response = client.post("/power/proportion", json={
            "p1": -0.5,
            "p2": 0.3,
            "alpha": 0.05
        })
        assert response.status_code == 422


class TestSurvivalPowerValidation:
    """Test validation for survival power analysis."""

    def test_hazard_ratio_one_rejected(self, client):
        """hazard_ratio = 1 (無效果) 應該返回驗證錯誤"""
        response = client.post("/power/survival", json={
            "hazard_ratio": 1.0,
            "p1": 0.3,
            "alpha": 0.05
        })
        assert response.status_code == 422
        assert "hazard_ratio" in response.text

    def test_zero_hazard_ratio_rejected(self, client):
        """hazard_ratio = 0 應該返回驗證錯誤"""
        response = client.post("/power/survival", json={
            "hazard_ratio": 0,
            "p1": 0.3,
            "alpha": 0.05
        })
        assert response.status_code == 422

    def test_negative_hazard_ratio_rejected(self, client):
        """負 hazard_ratio 應該返回驗證錯誤"""
        response = client.post("/power/survival", json={
            "hazard_ratio": -0.5,
            "p1": 0.3,
            "alpha": 0.05
        })
        assert response.status_code == 422


class TestANOVAPowerValidation:
    """Test validation for ANOVA power analysis."""

    def test_k_less_than_two_rejected(self, client):
        """k < 2 (組數不足) 應該返回驗證錯誤"""
        response = client.post("/power/anova", json={
            "effect_size": 0.25,
            "k": 1,
            "alpha": 0.05
        })
        assert response.status_code == 422
        assert "k" in response.text


class TestTypeCoercion:
    """Test type handling and coercion."""

    def test_string_as_number_rejected(self, client):
        """字串數字應該被 FastAPI 驗證拒絕"""
        response = client.post("/power/ttest", json={
            "effect_size": "not_a_number",
            "alpha": 0.05,
            "power": 0.8
        })
        assert response.status_code == 422

    def test_null_required_field_rejected(self, client):
        """必填欄位為 null 應該被拒絕"""
        response = client.post("/power/proportion", json={
            "p1": None,
            "p2": 0.3,
            "alpha": 0.05
        })
        assert response.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
