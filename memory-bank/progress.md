# Progress (Updated: 2025-12-08)

## Done

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

- 執行完整測試套件確認覆蓋率
- 完善 upload_tools 實際上傳功能
- 考慮增加更多邊界案例測試

