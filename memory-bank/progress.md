# Progress (Updated: 2025-12-08)

## Done

### 2025-12-08
- ✅ MCP 檔案上傳架構重構
  - Volume Mount 方式：`sample_data`, `uploads`, `datasets` 掛載到 `/data/`
  - 雙儲存模式：temporary (Redis) + permanent (MinIO)
  - 新增 upload_tools.py (3 工具)
- ✅ 修復 stats-worker dataset_id 問題
  - worker 從 job 頂層讀取 `dataset_id` 和 `minio_path`
  - 不再從 `params` 字典讀取
- ✅ 修復 TableOne tuple key 序列化問題
  - MultiIndex tuple keys 轉換為字串以支援 JSON
- ✅ E2E 測試全部通過 (5/5)
  - direct_analyze, quick_stats, tableone, eda, auto_analyze

### 2025-12-07
- 建立 test_public_datasets.py - 16 個測試驗證統計功能
- 測試涵蓋: Survival (KM, Cox, Log-Rank), ROC (curve, comparison, calibration), TableOne, Power Analysis, Propensity Score, Correlation, Distribution, VIF
- 保留所有維護人員文檔的政策已記錄到 Memory Bank

## Doing

- 無進行中任務

## Next

- 完善 upload_tools 實際上傳功能
- 增加 MinIO 上傳端點整合
- 執行完整測試套件確認覆蓋率
- 考慮增加更多邊界案例測試

