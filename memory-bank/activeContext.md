# Active Context

## Current Status (2025-12-16)

### 🎯 剛完成: 整合 template-is-all-you-need 框架

**新增組件:**
- `.claude/skills/` - 12 個 Claude Skills（git-precommit, memory-checkpoint 等）
- `CONSTITUTION.md` - 專案憲法（DDD、Memory Bank、文檔原則）
- `.github/bylaws/` - 4 個子法（ddd-architecture, git-workflow, memory-bank, python-environment）
- `AGENTS.md` - VS Code Copilot Agent 指引
- `.vscode/settings.json` - 啟用 Claude Skills

**可用指令:**
- 「準備 commit」- 執行完整 Git 提交流程
- 「checkpoint」- 保存記憶檢查點
- 「更新 memory」- 同步 Memory Bank
- 「生成測試」- 自動生成測試
- 「review 程式碼」- 程式碼審查

---

## Previous Status (2025-12-10)

### 🎯 平台狀態: v0.5.0 - Visualization + Local Results ✅

**核心設計原則 (重要!):**

> **Agent 只負責四件事：**
> 1. 傳入檔案路徑
> 2. 建立工單（含參數設定）
> 3. 查詢工單狀態
> 4. 取得輸出連結
>
> **所有資料處理、計算、視覺化都是 AutoML 系統內部的事！**

### ✅ 剛完成: Phase 8 Visualization + Local Results

**Phase 8A-8D: Visualization Module**
- `visualization/survival.py` - 生存分析圖（KM 曲線、風險表）
- `visualization/roc.py` - ROC/PR 曲線（信賴區間、校正曲線）
- `visualization/group_comparison.py` - 組間比較（箱形圖、直方圖）
- `visualization/automl.py` - AutoML 結果（特徵重要性、SHAP、學習曲線）

**Phase 8E: Local Results Storage**
- `results/manager.py` - JobResultsManager 本地結果管理
- `results/worker_mixin.py` - Worker 整合 mixin
- 目錄結構：`/results/{user_id}/{job_name}_{timestamp}/`
- 內容：metadata.json, report.json, report.html, figures/, data/

**使用者可直接存取:**
- 瀏覽 `./results/eric/` 看自己的分析結果
- 開啟 HTML 報告檢視視覺化圖表
- 複製 PNG 圖表到簡報

### ✅ 已整合

1. **Worker 整合範例**
   - `process_roc_full_eval_job()` 使用 JobResultsManager
   - 自動儲存圖表到 figures/
   - 生成 HTML 視覺化報告

2. **Docker Volume Mount**
   - `./results:/data/results` 加到 MCP, stats-service, stats-worker

3. **文檔更新**
   - README.md, CHANGELOG.md, ARCHITECTURE_AUDIT.md
   - systemPatterns.md (3 個新 patterns)

### 📋 下一步

1. **整合其餘 worker tasks** - 將 JobResultsManager 應用到所有分析任務
2. **圖表自動化** - 各分析類型自動產生對應圖表
3. **Phase 9: Meta-Analysis** - 固定效應、隨機效應、森林圖

## Current Goals

- ## Current Focus: Result Persistence Feature - COMPLETED
- ### Just Accomplished
- 1. Fixed JSON serialization issue in `result_storage.py`:
- - Added `NumpyJSONEncoder` class to handle numpy types (int64, float64, bool_, ndarray)
- - Added `safe_json_dumps()` helper function
- - Modified `_save_to_redis()` and `_save_to_minio()` to use safe encoder
- 2. Fixed API endpoint routing issue:
- - Changed `_save_to_minio()` to call `stats-service` instead of `automl-service`
- - The `/storage/minio/upload` endpoint exists only in stats-service
- 3. Verified result persistence is working:
- - `compare_groups` results saved to both Redis and MinIO ✓
- - `analyze_correlations` results saved successfully ✓
- - Results accessible via `/storage/minio/download` endpoint ✓
- ### Tools with Result Persistence
- - `analyze_correlations` - saves to Redis + MinIO
- - `compare_groups` - saves to Redis + MinIO
- - `generate_tableone_directly` - saves to Redis + MinIO
- ### Test Results
- ```
- Redis: stats:result:stat_compare_groups_c32b80b7 ✓
- MinIO: automl-results/default/compare_groups/20251212_105836_stat_compare_groups_c32b80b7.json ✓
- MinIO: automl-results/default/correlation/20251212_110048_stat_correlation_e9231bb4.json ✓
- ```
- ### Storage Architecture
- - Redis Key Pattern: `stats:result:{result_id}`
- - MinIO Path Pattern: `{bucket}/{user_id}/{analysis_type}/{timestamp}_{result_id}.json`
- - Default TTL: 7 days for Redis
- ### Next Steps
- 1. Continue painless delivery analysis Phase 5 (multivariate analysis)
- 2. Add result persistence to more tools as needed
- 3. Consider adding `list_saved_results` and `get_saved_result` tools for retrieval

## Current Blockers

- None

## References

- [ROADMAP](../docs/ROADMAP.md) - 完整開發藍圖
- [CHANGELOG](../CHANGELOG.md) - 版本更新記錄
- [Design Issue #001](../docs/design-issues/001-data-cleaning-workflow.md) - 資料清理設計