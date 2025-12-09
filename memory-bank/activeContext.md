# Active Context

## Current Status (2025-12-08)

### 🎯 平台狀態: v1.1 穩定運行 ✅

**核心設計原則 (重要!):**

> **Agent 只負責四件事：**
> 1. 傳入檔案路徑
> 2. 建立工單（含參數設定）
> 3. 查詢工單狀態
> 4. 取得輸出連結
>
> **所有資料處理、計算、轉換都是 AutoML 系統內部的事！**

### ✅ 已完成

1. **Phase 6: MCP 統計工具修復** (2025-12-08)
   - 修復 23 個損壞的 `stats_worker_tasks` imports
   - Power Analysis Tools (17個) 改用 stats_client API
   - EDA/TableOne Tools (6個) 使用本地 fallback
   - **57 統計工具全部正常運作**

2. **核心功能**
   - AutoML 訓練（提交 → 等待 → 取結果）
   - 統計分析（TableOne, EDA, Auto-Analyze）
   - Power Analysis (T-test, Proportion, ANOVA, Chi-square, Survival)
   - E2E 測試全部通過 (5/5)

### ✅ 已解決問題

**MCP 工具架構問題 (已修復):**
- ~~30 個工具返回 "Module not available"~~ → 全部修復
- Power Analysis: 改用 stats_client → stats-service API
- EDA Tools: 使用本地 pandas/scipy fallback
- stats-service power.py: 使用 statsmodels 計算

### 📋 下一步

1. **執行完整測試套件** 確認所有功能正常
2. **完善文檔** 更新 MCP 工具清單
3. **考慮 Phase 7** Meta-Analysis 功能

## Current Goals

- ## Current Focus (2025-12-09)
- ### ✅ Just Completed: Phase 7 Data Cleaning + Worker Optimization
- **Stats Service Cleaning API (9 endpoints):**
- - `/cleaning/convert-binary` - 轉換欄位為 0/1
- - `/cleaning/encode-categorical` - 類別編碼 (Label/OneHot)
- - `/cleaning/handle-missing` - 缺失值處理
- - `/cleaning/remove-columns` - 移除欄位
- - `/cleaning/filter-rows` - 篩選資料列
- - `/cleaning/rename-columns` - 重新命名欄位
- - `/cleaning/column-info` - 取得欄位資訊
- - `/cleaning/auto-clean` - 自動清理
- - `/cleaning/health` - 健康檢查
- **Worker Result Optimization:**
- - 修改 `estimate_propensity_scores()` 不再回傳完整分數陣列，改為統計摘要
- - 修改 `match_propensity_scores()` 不再回傳完整索引陣列，改為配對摘要
- - 新增 `sanitize_for_json()` 處理 NaN/Infinity JSON 序列化問題
- - 大幅減少 MinIO 存儲空間使用
- **Key Bug Fixes:**
- - StatsJobType enum 補齊所有工作類型
- - StatsJobId 改為 string 支援 "propensity-xxx" 格式
- - Redis async client 正確初始化
- ### Next Actions
- - 完整 E2E 測試（傾向分數分析工作流）
- - 更多資料集測試
- - 考慮 Meta-Analysis (Phase 8) 或其他進階功能

## Current Blockers

- stats-service 缺少部分 API endpoints

## References

- [ROADMAP](../docs/ROADMAP.md) - 完整開發藍圖
- [ROC Features Plan](../docs/ROC_AUC_Interactive_Features_Plan.md) - Phase 5+ 詳細規劃
- [Design Issue #001](../docs/design-issues/001-data-cleaning-workflow.md) - 資料清理設計