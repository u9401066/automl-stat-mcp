# Progress (Updated: 2025-12-10)

## Done

### 2025-12-10 (Phase 8: Visualization + Local Results)
- ✅ **Phase 8A-8D: Visualization Module 完成**
  - `visualization/survival.py` - 生存分析圖表（KM 曲線、風險表、累積風險）
  - `visualization/roc.py` - ROC/PR 曲線（含信賴區間、比較、校正曲線）
  - `visualization/group_comparison.py` - 組間比較（箱形圖、直方圖、散佈圖）
  - `visualization/automl.py` - AutoML 結果（特徵重要性、SHAP、學習曲線）
  - 39 個測試案例全部通過

- ✅ **Phase 8E: Local Results Storage 完成**
  - `results/manager.py` - JobResultsManager 本地結果管理
  - `results/worker_mixin.py` - Worker 整合 mixin
  - 目錄結構：`/results/{user_id}/{job_name}_{timestamp}/`
  - 自動生成：metadata.json, report.json, report.html, figures/, data/
  - docker-compose.yml 新增 `./results:/data/results` volume

- ✅ **Worker 整合範例**
  - `process_roc_full_eval_job()` 已整合 JobResultsManager
  - 自動儲存 ROC 曲線圖到 figures/
  - 生成 HTML 視覺化報告

- ✅ **文檔更新**
  - README.md 新增 Local Results Storage 章節
  - CHANGELOG.md v0.5.0 版本記錄
  - ARCHITECTURE_AUDIT.md Phase 5 更新
  - systemPatterns.md 新增 3 個 patterns

### 2025-12-09 (Phase 7 Data Cleaning + Worker Optimization)
- ✅ **Phase 7 Data Cleaning Service 完成**
  - Stats Service 新增 9 個 cleaning API endpoints
  - MCP cleaning tools 全部可用（9 個工具）
  - convert-binary: 轉換欄位為 0/1（傾向分數分析必需）
  - encode-categorical: Label/OneHot 編碼
  - handle-missing: 缺失值處理
  - remove-columns/filter-rows/rename-columns: 資料操作
  - column-info: 欄位資訊查詢
  - auto-clean: 一鍵自動清理

- ✅ **Worker 結果存儲優化**
  - `estimate_propensity_scores()` 改為只存統計摘要（不存完整分數陣列）
  - `match_propensity_scores()` 改為只存配對摘要（不存索引陣列）
  - 新增 `sanitize_for_json()` 處理 NaN/Infinity JSON 序列化
  - 大幅減少 MinIO 存儲空間使用

- ✅ **Stats Service Bug Fixes**
  - StatsJobType enum 補齊 propensity/survival/ROC/power 工作類型
  - StatsJobId 改為 string 支援 "propensity-xxx" 格式
  - Redis async client 正確初始化 (from_url)

### 2025-12-09 (Data Cleaning + Upload Enhancement - Earlier)
- ✅ **Upload Tools 增強**
  - 欄位名稱自動清理（Excel 特殊符號 → 底線）
  - 保留中文字元，移除 `Unnamed:` Excel 殘留
  - Metadata JSON 生成（原始↔清理後欄位對照）
  - 預覽截斷（2 rows, 10 columns）避免 response 過大
  - Volume mount `/data/processed` 存放處理後檔案

- ✅ **統計功能測試**
  - 樣本數計算：t-test, proportion, effect_size, sensitivity 全部正常
  - TableOne 生成：painless 資料集 Ropica 200 vs 400 比較成功
  - 傾向分數分析：偵測到問題（treatment 需為 binary 0/1）

- 🔄 **Data Cleaning Tools 架構規劃**
  - 設計決策：整合到 Stats Service（而非獨立服務）
  - 新增設計文件：`docs/design-issues/002-data-cleaning-service.md`
  - 新增工具模組：`cleaning_tools.py`（MCP 端，待完成 Stats Service API）

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

- 🔄 **Worker 整合擴展**
  - [ ] 其他 job types 整合 JobResultsManager
  - [ ] 各種分析自動生成對應圖表

## Next

- Phase 9: Meta-Analysis (固定效應、隨機效應、森林圖)
- 完善其餘 worker tasks 的本地結果整合
- 監控儀表板 (Grafana)
- 日誌集中化

