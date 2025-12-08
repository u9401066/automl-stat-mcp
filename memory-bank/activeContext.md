# Active Context

## Current Status (2025-01-13)

### 🎯 平台狀態: v2.0 架構重構中

**核心設計原則 (重要!):**

> **Agent 只負責四件事：**
> 1. 傳入檔案路徑
> 2. 建立工單（含參數設定）
> 3. 查詢工單狀態
> 4. 取得輸出連結
>
> **所有資料處理、計算、轉換都是 AutoML 系統內部的事！**

### ✅ 已完成

1. **架構文件重構** (2025-01-13)
   - `docs/AGENT_WORKFLOW.md` - Agent 工作流設計
   - `docs/MCP_TOOLS_INVENTORY.md` - 工具盤點
   - `README.md` - 簡化為 18 核心工具
   - `memory-bank/productContext.md` - 架構原則

2. **核心功能**
   - AutoML 訓練（提交 → 等待 → 取結果）
   - 統計分析（TableOne, EDA, Auto-Analyze）
   - E2E 測試全部通過 (5/5)

### ⚠️ 已知問題

**MCP 工具架構問題：**
- ~30 個工具返回 "Module not available"
- 原因：MCP 容器無法 import stats-worker 的模組
- 影響：Propensity、Survival、ROC、Power Analysis
- 解決方案：新增 stats-service API endpoints

### 📋 下一步

1. **修復 stats-service API**
   - 新增 `/propensity/*` endpoints
   - 新增 `/survival/*` endpoints
   - 新增 `/roc/*` endpoints
   - 新增 `/power/*` endpoints

2. **簡化 MCP 工具註冊**
   - 移除無法運作的工具
   - 只保留 18 核心工具

## Current Goals

精簡 Agent 職責，確保 Agent 只做：
1. 傳檔案路徑
2. 建工單
3. 查狀態
4. 拿結果

## Current Blockers

- stats-service 缺少部分 API endpoints

## References

- [ROADMAP](../docs/ROADMAP.md) - 完整開發藍圖
- [ROC Features Plan](../docs/ROC_AUC_Interactive_Features_Plan.md) - Phase 5+ 詳細規劃
- [Design Issue #001](../docs/design-issues/001-data-cleaning-workflow.md) - 資料清理設計