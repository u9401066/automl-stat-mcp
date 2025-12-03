# Active Context

## Current Goals

- ## 當前任務：實作 auto_analyze 智能統計分析
- ### 設計目標
- 一個工具搞定所有統計分析，AI Agent 不需要知道該用什麼方法。
- ### auto_analyze 功能規劃
- 1. **資料品質檢查**
- - 缺失值分析（比例、模式）
- - 離群值偵測（IQR、Z-score）
- - 重複值檢查
- 2. **變數類型推論**
- - 數值型（連續/離散）
- - 類別型（有序/無序）
- - 日期時間型
- - ID/索引型（排除分析）
- 3. **描述統計（依類型自動選擇）**
- - 數值：mean, sd, median, IQR, skewness, kurtosis
- - 類別：frequency, mode, entropy
- 4. **假設檢定（自動判斷）**
- - 常態性檢定（Shapiro-Wilk）→ 決定用參數/非參數
- - 同質性檢定（Levene）
- 5. **關聯分析（有 target 時）**
- - 數值 vs 數值 → Pearson/Spearman correlation
- - 類別 vs 類別 → Chi-square + Cramér's V
- - 數值 vs 類別 → t-test/ANOVA/Mann-Whitney/Kruskal-Wallis
- 6. **自動產生建議**
- - 資料清理建議
- - 特徵工程建議
- - 適合的 ML 模型建議
- ### 實作計畫
- 1. stats-worker: 新增 auto_analyze_task.py
- 2. stats-service: 新增 /auto-analyze/submit 端點
- 3. MCP: 新增 auto_analyze, run_quick_analysis 工具
- ### 備案
- 如果 auto_analyze 過於複雜，Agent 可以自己決定跑哪些分析（使用現有的獨立工具）

## Current Blockers

- None yet