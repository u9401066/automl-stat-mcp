# Progress (Updated: 2025-12-09)

## Done

### 2025-12-09 (CSV Path Refactoring)
- ✅ **所有 statistics tools 改用 csv_path（檔案路徑）**
  - 新增 `_read_csv_from_path_or_reject()` helper function
  - 修改 20+ direct tools 從 `csv_content` 改為 `csv_path`
  - 如果 Agent 誤傳資料內容，會返回友善錯誤訊息指導使用正確方式
  - 完全符合 E2E 設計原則：Agent 只傳路徑，MCP 讀取檔案
  - 文檔：`docs/design-issues/002-csv-path-refactoring.md`

- ✅ **E2E 測試框架建立**
  - 建立 `sample_results/` 目錄結構
  - Iris dataset: upload, auto_analyze, tableone, power_analysis, ML training 全部成功
  - Rossi dataset: upload, auto_analyze 成功
  - 修復 upload_tools.py session_id bug
  - 修復 survival_data_summary 參數名不一致 bug

### 2025-12-08 (Phase 6 完成)
- ✅ **Phase 6: MCP 統計工具修復**
  - 修復 23 個損壞的 `stats_worker_tasks` imports
  - Power Analysis Tools (17個) 改用 stats_client API
  - EDA/TableOne Tools (6個) 使用本地 fallback (pandas/scipy)
  - stats-service power.py 端點使用實際 statsmodels 計算
  - 加入 scipy 到 automl-mcp-server/requirements.txt
  - **57 統計工具全部正常運作**

- ✅ MCP 檔案上傳架構重構
  - Volume Mount 方式：`sample_data`, `uploads`, `datasets` 掛載到 `/data/`
  - 雙儲存模式：temporary (Redis) + permanent (MinIO)
  - 新增 upload_tools.py (3 工具)
- ✅ 修復 stats-worker dataset_id 問題
- ✅ 修復 TableOne tuple key 序列化問題
- ✅ E2E 測試全部通過 (5/5)

### 2025-12-07
- 建立 test_public_datasets.py - 16 個測試驗證統計功能
- 測試涵蓋: Survival (KM, Cox, Log-Rank), ROC (curve, comparison, calibration), TableOne, Power Analysis, Propensity Score, Correlation, Distribution, VIF
- 保留所有維護人員文檔的政策已記錄到 Memory Bank

## Doing

- 無進行中任務

## Next

- 完成更多資料集的 E2E 測試（titanic, heart_disease, breast_cancer）
- Git commit 推送所有變更
- 執行完整測試套件確認覆蓋率

