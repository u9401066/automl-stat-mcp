# Active Context

## Current Status (2025-12-10)

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

- 完成所有 worker tasks 的本地結果整合
- 確保每種分析都有對應的視覺化輸出
- 使用者可完全透過檔案系統存取所有結果

## Current Blockers

- None

## References

- [ROADMAP](../docs/ROADMAP.md) - 完整開發藍圖
- [CHANGELOG](../CHANGELOG.md) - 版本更新記錄
- [Design Issue #001](../docs/design-issues/001-data-cleaning-workflow.md) - 資料清理設計