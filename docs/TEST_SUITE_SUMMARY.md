# 測試套件摘要

## 📊 測試統計

| 類別 | 檔案 | 測試數量 | 標記 |
|------|------|----------|------|
| **邊界測試** | `tests/edge_cases/test_data_boundaries.py` | 18 | `@pytest.mark.edge_case` |
| **邊界測試** | `tests/edge_cases/test_input_validation.py` | 20 | `@pytest.mark.edge_case` |
| **E2E 測試** | `tests/e2e/test_complete_workflows.py` | 6 | `@pytest.mark.e2e` |
| **性能測試** | `tests/performance/test_load_stress.py` | 11 | `@pytest.mark.performance` |
| **安全測試** | `tests/security/test_injection_defense.py` | 15 | `@pytest.mark.security` |
| **總計** | 5 個檔案 | **70+** | |

## 🎯 測試覆蓋範圍

### 1. 邊界測試 (Edge Cases) - 38 tests

#### 資料大小邊界 (`test_data_boundaries.py`)
- ✅ 空資料集處理
- ✅ 單筆資料處理
- ✅ 最小統計可行集（2 筆資料）
- ✅ 單一欄位處理
- ✅ 大資料集記憶體效率

#### 資料型態邊界
- ✅ 完全缺失欄位 (all NaN)
- ✅ 常數欄位（零變異）
- ✅ 無限值 (infinity)
- ✅ 極端離群值偵測
- ✅ Unicode 特殊字元

#### 統計邊界
- ✅ 完美正相關 (r=1.0)
- ✅ 完美負相關 (r=-1.0)
- ✅ 零變異群組（t-test 不可行）
- ✅ 極度不平衡群組
- ✅ 群組內所有值相同

#### ML 邊界
- ✅ 特徵數 > 樣本數 (p >> n)
- ✅ 完美可分類資料
- ✅ 極度不平衡類別 (1:1000)

#### 輸入驗證 (`test_input_validation.py`)
- ✅ 空路徑拒絕
- ✅ 不存在檔案處理
- ✅ 路徑遍歷攻擊防禦
- ✅ 超長路徑處理
- ✅ 特殊字元檔名清理
- ✅ 相對 vs 絕對路徑
- ✅ 負數參數拒絕
- ✅ 超大參數限制
- ✅ 無效方法名偵測
- ✅ 空欄位列表處理
- ✅ 重複欄位去重
- ✅ Alpha 值範圍驗證
- ✅ SQL 注入清理
- ✅ 命令注入偵測
- ✅ XSS 轉義
- ✅ 檔案大小限制
- ✅ 速率限制檢查
- ✅ UTF-8/Latin-1 編碼
- ✅ 編碼錯誤處理
- ✅ Unicode 正規化

### 2. E2E 測試 (End-to-End) - 6 tests

#### 完整醫學研究工作流 (`test_complete_workflows.py`)
- ✅ RCT 完整流程
  - 上傳資料 → 品質檢查 → Table One → 統計檢定 → 結果儲存

#### 存活分析工作流
- ✅ Kaplan-Meier → Cox 迴歸完整流程

#### ML 訓練工作流
- ✅ 上傳 → 訓練 → 排行榜 → 預測完整流程

#### 多使用者並行
- ✅ 並行上傳資料
- ✅ 並行執行分析

### 3. 性能測試 (Performance) - 11 tests

#### 負載基準 (`test_load_stress.py`)
- ✅ quick_preview 速度（< 1秒）
- ✅ 統計計算速度（< 3秒）
- ✅ 大資料集效能（< 30秒）

#### 並行請求
- ✅ 10 個並行 preview
- ✅ 100 個連續請求壓力測試

#### 記憶體使用
- ✅ 記憶體洩漏偵測（20 次重複）
- ✅ 大量結果處理

#### 壓力測試
- ✅ 持續負載（5 分鐘）
- ✅ 突發流量（50 個同時請求）

### 4. 安全測試 (Security) - 15 tests

#### 注入攻擊 (`test_injection_defense.py`)
- ✅ 路徑中的 SQL 注入防禦
- ✅ 檔名中的命令注入防禦
- ✅ HTML 報告 XSS 防禦

#### 路徑遍歷
- ✅ 目錄遍歷攻擊拒絕
- ✅ 允許目錄外的絕對路徑拒絕

#### 速率限制
- ✅ 快速連續請求限制

#### 使用者隔離
- ✅ 無法存取其他使用者資料
- ✅ 列表只顯示自己的資料集

#### 輸入清理
- ✅ 超大 payload 拒絕
- ✅ 空字元注入防禦
- ✅ Unicode 正規化處理

## 🚀 快速執行

### 互動模式
```bash
./run_tests.sh
```

### 直接執行特定測試
```bash
./run_tests.sh edge        # 邊界測試
./run_tests.sh e2e         # E2E 測試
./run_tests.sh performance # 性能測試
./run_tests.sh security    # 安全測試
./run_tests.sh all         # 全部測試
./run_tests.sh coverage    # 覆蓋率報告
```

### 使用 pytest 直接執行
```bash
# 執行特定標記
pytest -m edge_case tests/
pytest -m e2e tests/
pytest -m performance tests/
pytest -m security tests/

# 執行特定檔案
pytest tests/edge_cases/test_data_boundaries.py -v
pytest tests/e2e/test_complete_workflows.py -v

# 執行特定測試
pytest tests/edge_cases/test_data_boundaries.py::TestDataSizeBoundaries::test_empty_dataframe -v

# 產生覆蓋率報告
pytest --cov=. --cov-report=html --cov-report=term tests/
```

## 📝 測試標記 (Markers)

專案中已定義的 pytest markers (在 `pytest.ini`):

### 測試類型
- `@pytest.mark.unit` - 單元測試
- `@pytest.mark.integration` - 整合測試
- `@pytest.mark.e2e` - E2E 測試

### 優先級
- `@pytest.mark.fast` - 快速測試 (< 1s)
- `@pytest.mark.slow` - 慢速測試 (> 10s)

### 功能領域
- `@pytest.mark.data_analysis` - 資料分析測試
- `@pytest.mark.ml` - 機器學習測試
- `@pytest.mark.survival` - 存活分析測試

### 測試類別
- `@pytest.mark.edge_case` - 邊界測試 ⭐
- `@pytest.mark.performance` - 性能測試 ⭐
- `@pytest.mark.security` - 安全測試 ⭐
- `@pytest.mark.benchmark` - 基準測試

### 基礎設施
- `@pytest.mark.redis` - 需要 Redis
- `@pytest.mark.minio` - 需要 MinIO
- `@pytest.mark.docker` - 需要 Docker 服務

## 🎯 下一步計畫

根據 [TESTING_ENHANCEMENT_PLAN.md](TESTING_ENHANCEMENT_PLAN.md)，仍需補充：

### Phase 5: Chaos Testing (10+ tests)
- ⏳ 隨機服務故障
- ⏳ 網路分區模擬
- ⏳ 磁碟空間耗盡
- ⏳ Redis 連線中斷恢復
- ⏳ Worker 崩潰恢復

### Phase 6: Regression Testing (30+ tests)
- ⏳ 模型準確度基準
- ⏳ 輸出格式一致性
- ⏳ API 回應格式穩定性
- ⏳ 向後相容性測試

## 📊 測試執行範例

### 成功輸出範例
```
$ ./run_tests.sh edge

╔════════════════════════════════════════════════════════════════╗
║          AutoML Stat MCP - 測試執行腳本                        ║
╚════════════════════════════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
執行: 邊界測試
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

collected 38 items

tests/edge_cases/test_data_boundaries.py::TestDataSizeBoundaries::test_empty_dataframe PASSED [2%]
tests/edge_cases/test_data_boundaries.py::TestDataSizeBoundaries::test_single_row_dataframe PASSED [5%]
...
tests/edge_cases/test_input_validation.py::TestEncodingBoundaries::test_unicode_normalization PASSED [100%]

================================ 38 passed in 12.45s =================================

✅ 測試通過: 邊界測試

╔════════════════════════════════════════════════════════════════╗
║                    測試執行完成                                 ║
╚════════════════════════════════════════════════════════════════╝
```

## 🔍 覆蓋率目標

- **現況**: ~30% (基礎測試)
- **短期目標** (v0.2.0): 50%+ (加入 edge cases + e2e)
- **中期目標** (v0.3.0): 65%+ (加入 performance + security)
- **長期目標** (v1.0.0): 75%+ (加入 chaos + regression)

## 📚 相關文檔

- [TESTING_STRATEGY.md](TESTING_STRATEGY.md) - 測試策略總覽
- [TESTING_ENHANCEMENT_PLAN.md](TESTING_ENHANCEMENT_PLAN.md) - 測試增強計畫（145+ tests）
- [E2E_TEST_PLAN.md](../tests/E2E_TEST_PLAN.md) - E2E 測試詳細計畫
- [TEST_COVERAGE_PLAN.md](../tests/TEST_COVERAGE_PLAN.md) - 測試覆蓋率計畫
