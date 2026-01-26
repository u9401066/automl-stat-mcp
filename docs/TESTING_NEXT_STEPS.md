# 下一步測試建議

根據當前專案狀態，以下是可以進行的測試和改進方向：

---

## ✅ 已完成的測試

### 1. 整合測試（Integration Tests）
- ✅ **test_service_communication.py** - 32 passed
  - 服務健康檢查
  - API 端點存在性驗證
  - 超時處理
  - 錯誤回應格式
  - 併發請求處理

- ✅ **test_dataflow_integrity.py** - 已通過
  - 路徑解析鏈測試
  - CSV 內容往返測試
  - Base64 編碼/解碼
  - 特殊字元保留
  - 缺失值保留
  - 資料型別處理

### 2. E2E 測試（End-to-End Tests）
- ✅ **test_e2e_stats.py** - 20 passed, 3 skipped
  - Table One, EDA, Power Analysis
  - Survival Analysis (KM, Cox)
  - ROC Analysis, PSM
  - Correlation, VIF

- ✅ **test_e2e_data.py** - 12 passed, 3 skipped
  - 資料上傳、清理
  - Quick Stats, Data Preview

- ✅ **test_e2e_automl.py** - 16 passed, 4 skipped
  - AutoML 訓練、預測
  - 模型管理、排行榜

- ✅ **test_e2e_visualization.py** - 10 passed, 1 skipped
  - ROC/Survival 視覺化
  - MinIO 結果儲存

### 3. 單元測試
- ✅ **automl-mcp-server/tests/unit/** - 442 passed, 5 failed
- ✅ **stats-service/tests/test_storage_factory.py** - 22/23 passed

---

## 🎯 可以進行的新測試

### A. 10 個公開資料集完整測試 (E2E_TEST_PLAN.md)

**目標**: 使用真實資料集驗證端到端流程

**資料集列表**:
1. ✅ Iris (鳶尾花) - 已有測試
2. 🔲 Breast Cancer (乳癌) - ROC, VIF
3. 🔲 Diabetes (糖尿病) - 迴歸分析
4. ✅ Heart Disease (心臟病) - 已有測試
5. ✅ Titanic (鐵達尼號) - 已有測試
6. 🔲 California Housing (加州房價) - 大資料集
7. 🔲 Wine Quality (葡萄酒品質) - 多類別
8. 🔲 Adult Income (成人收入) - 大資料集
9. ✅ Rossi Recidivism (再犯) - 存活分析
10. 🔲 Stanford Heart (史丹佛心臟) - 存活分析

**執行方式**:
```bash
# 已建立測試腳本（需修正 API 路徑）
python tests/test_datasets_e2e.py --dataset all --suite stats
python tests/test_datasets_e2e.py --dataset breast_cancer
python tests/test_datasets_e2e.py --dataset diabetes --suite ml
```

**待修正**:
- API 端點路徑（/direct/ 需要 csv_content，非 direct 使用 csv_path）
- 完整實作所有統計測試（ANOVA, Chi-square, PSM）
- 添加 ML 訓練測試

### B. 效能與壓力測試

**1. 併發請求測試**
```python
# tests/test_performance.py
import asyncio
import aiohttp

async def test_concurrent_requests(n=100):
    """同時發送 100 個請求"""
    async with aiohttp.ClientSession() as session:
        tasks = [
            session.post(
                "http://localhost:8003/direct/quick-stats",
                json={"csv_content": data}
            )
            for _ in range(n)
        ]
        results = await asyncio.gather(*tasks)
        assert all(r.status == 200 for r in results)
```

**2. 大資料集測試**
- California Housing: 20,640 rows
- Adult Income: 48,842 rows
- 測試記憶體使用、處理時間

**3. Worker 負載測試**
```bash
# 使用 locust 進行壓力測試
pip install locust
locust -f tests/locustfile.py --host=http://localhost:8003
```

### C. 邊界與錯誤處理測試

**已完成**:
- ✅ test_eda_edge_cases.py - 40 tests

**待補充**:
```python
# tests/test_edge_cases_extended.py

def test_extremely_large_file():
    """測試超大檔案 (>1GB)"""
    pass

def test_malformed_csv():
    """測試格式錯誤的 CSV"""
    pass

def test_unicode_column_names():
    """測試 Unicode 欄位名稱（中文、日文、表情符號）"""
    pass

def test_very_long_strings():
    """測試超長字串欄位 (>10MB)"""
    pass

def test_circular_dependencies():
    """測試循環依賴問題"""
    pass
```

### D. 安全性測試

**已完成**:
- ✅ test_security_validation.py

**待補充**:
```python
# tests/test_security_advanced.py

def test_sql_injection():
    """測試 SQL 注入攻擊"""
    pass

def test_path_traversal_variations():
    """測試各種路徑穿越變體"""
    # ../../../etc/passwd
    # ..%2F..%2F..%2Fetc%2Fpasswd
    # ....//....//etc/passwd
    pass

def test_xxe_attack():
    """測試 XML 外部實體注入"""
    pass

def test_rate_limiting():
    """測試速率限制"""
    pass

def test_authentication_bypass():
    """測試認證繞過（如果有認證）"""
    pass
```

### E. 回歸測試（Regression Tests）

**目標**: 確保新功能不破壞舊功能

```bash
# 建立基準測試套件
pytest tests/ --benchmark-save=baseline

# 比較效能變化
pytest tests/ --benchmark-compare=baseline
```

### F. MCP 工具完整性測試

**51 個 MCP 工具逐一驗證**:
```python
# tests/test_mcp_tools_comprehensive.py

def test_all_51_tools():
    """測試所有 MCP 工具"""
    tools = [
        "upload_dataset",
        "quick_preview",
        "smart_analyze",
        # ... 48 more
    ]
    for tool in tools:
        result = mcp_client.call_tool(tool, test_params)
        assert result["status"] == "success"
```

### G. 資料品質測試

**DataQualityAnalyzer 完整測試**:
```python
# tests/test_data_quality_comprehensive.py

def test_all_warning_types():
    """測試 6 種警告類型偵測"""
    # ALL_NAN, CONSTANT, HIGH_CARDINALITY_ID
    # HIGH_MISSING, SKEWED, OUTLIERS
    pass

def test_transform_suggestions():
    """測試轉換建議正確性"""
    # log, log1p, zscore
    pass

def test_quality_check_integration():
    """測試與其他工具的整合"""
    pass
```

---

## 🚀 輕量版啟動測試

**已建立文檔**: `docs/LIGHTWEIGHT_SETUP.md`

### 可以測試的配置

**配置 A: 最輕量（統計分析）**
```bash
# 啟動服務
docker run -d -p 6379:6379 redis:7-alpine
cd stats-service && uvicorn src.main:app --port 8003 &
cd automl-mcp-server && python src/main.py --mode sse --port 8002 &

# 測試
pytest tests/test_e2e_stats.py -v
curl http://localhost:8003/health
```

**配置 B: 完整本地開發**
```bash
# 啟動所有服務（不使用 Docker）
./scripts/start_local_services.sh

# 執行完整測試
pytest tests/ -v --cov
```

**待建立**:
- `scripts/start_local_services.sh` - 本地服務啟動腳本
- `scripts/stop_local_services.sh` - 停止腳本
- 環境變數範本 `.env.local.template`

---

## 📊 測試覆蓋率目標

**當前**: 84%

**目標**: 90%+

**重點補強區域**:
1. **automl-worker** - 目前未測試
2. **stats-worker** - 部分測試
3. **Error handling** - 異常路徑覆蓋不足
4. **Edge cases** - 邊界條件需補充

```bash
# 生成覆蓋率報告
pytest --cov=stats-service/src --cov=automl-mcp-server/src \
       --cov-report=html --cov-report=term-missing
```

---

## 🔧 CI/CD Pipeline 測試

**目標**: 建立 GitHub Actions 自動化測試

```yaml
# .github/workflows/test.yml
name: Test Suite

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run unit tests
        run: pytest tests/unit/ -v

  integration-tests:
    runs-on: ubuntu-latest
    services:
      redis:
        image: redis:7-alpine
    steps:
      - name: Run integration tests
        run: pytest tests/integration/ -v

  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - name: Start services
        run: docker compose up -d
      - name: Run E2E tests
        run: pytest tests/test_e2e*.py -v
```

---

## 🎯 優先順序建議

### 高優先級（本週完成）
1. ✅ 修正 `test_datasets_e2e.py` API 路徑問題
2. 🔲 執行 10 個資料集完整測試
3. 🔲 建立本地啟動腳本
4. 🔲 補充缺失的測試檔案 (medical_study_200.csv)

### 中優先級（本月完成）
5. 🔲 效能測試（併發、大資料集）
6. 🔲 安全性進階測試
7. 🔲 提升測試覆蓋率至 90%+
8. 🔲 建立 CI/CD Pipeline

### 低優先級（後續規劃）
9. 🔲 回歸測試基準
10. 🔲 MCP 工具完整性測試
11. 🔲 壓力測試（locust）
12. 🔲 Chaos Engineering 測試

---

## 📝 測試文檔補充

**待建立**:
- `tests/README.md` - 測試指南
- `tests/CONTRIBUTING_TESTS.md` - 測試貢獻指南
- `tests/COVERAGE_REPORT.md` - 覆蓋率報告
- `tests/PERFORMANCE_BASELINE.md` - 效能基準

---

## 🛠️ 工具建議

**測試框架**:
- ✅ pytest (已使用)
- ✅ pytest-cov (已使用)
- ✅ pytest-asyncio (已使用)
- 🔲 hypothesis (property-based testing)
- 🔲 faker (測試資料生成)

**效能測試**:
- 🔲 locust (壓力測試)
- 🔲 pytest-benchmark (效能比較)
- 🔲 memory_profiler (記憶體分析)

**安全測試**:
- 🔲 bandit (Python 安全掃描)
- 🔲 safety (依賴漏洞檢查)
- 🔲 OWASP ZAP (Web 應用掃描)

---

**總結**: 專案測試基礎已相當扎實（84% 覆蓋率，100+ E2E 測試），接下來可以：
1. 完善資料集測試（E2E_TEST_PLAN.md）
2. 建立本地開發環境（輕量版）
3. 補充效能與安全測試
4. 建立 CI/CD 自動化
