# Design Issue #001: Data Cleaning Workflow

**Status**: 🔴 Open  
**Priority**: High  
**Created**: 2025-12-03  
**Category**: UX / Data Quality / MCP Design

---

## 問題描述

當使用者提供的資料有以下問題時，系統該如何處理？

### 資料品質問題類型

| 問題類型 | 範例 | 嚴重程度 |
|---------|------|---------|
| **缺失值 (Missing Values)** | NULL, NaN, 空白欄位 | Medium |
| **隱私資料 (PII)** | 身分證、電話、Email、姓名 | Critical |
| **無效欄位 (Invalid Columns)** | ID欄位、常數欄位、高基數類別 | Low |
| **資料類型錯誤** | 數字存成字串、日期格式錯誤 | Medium |
| **異常值 (Outliers)** | 極端值、不合理數值 | Medium |
| **重複資料** | 完全重複的列 | Low |
| **類別不平衡** | 99% vs 1% 分布 | Medium |

---

## 核心設計問題

### 1. 責任歸屬：誰來處理？

| 選項 | 優點 | 缺點 |
|------|------|------|
| **A. MCP 反覆確認** | 用戶完全控制、透明 | 對話冗長、UX差 |
| **B. Agent 自動處理** | 快速、流暢 | Agent 不一定知道最佳做法、可能錯誤決策 |
| **C. 專用資料清理 MCP** | 清晰職責分離、可重用 | 額外開發成本 |
| **D. 混合模式** | 平衡自動與確認 | 設計複雜度高 |

### 2. 用戶確認頻率

```
Level 1: 全自動 (不問)
├── 優點: 最快
└── 風險: 可能做出用戶不想要的決定

Level 2: 一次確認 (批次處理)
├── 顯示所有問題 → 用戶確認 → 一次處理
└── 優點: 平衡效率與控制

Level 3: 逐項確認 (每個問題都問)
├── 優點: 完全控制
└── 缺點: 對話冗長、體驗差

Level 4: 智慧確認 (按嚴重程度)
├── 嚴重問題必問 (PII)
├── 中等問題建議 (缺失值處理方式)
└── 輕微問題自動 (移除ID欄位)
```

### 3. Agent 知識程度

**問題**: AI Agent 是否有足夠知識做出正確的資料清理決策？

| 決策類型 | Agent 能力 | 建議 |
|---------|-----------|------|
| 移除 ID 欄位 | ✅ 高 | 自動 |
| 缺失值填補方式 | ⚠️ 中 | 提供選項 |
| PII 偵測 | ✅ 高 | 必須確認 |
| 異常值處理 | ⚠️ 中 | 顯示並詢問 |
| 特徵工程 | ❌ 低 | 需領域知識 |

---

## 可用工具/套件

### Python 資料清理套件

| 套件 | 用途 | 成熟度 |
|------|------|--------|
| **pandas** | 基礎清理 | ⭐⭐⭐⭐⭐ |
| **pyjanitor** | 鏈式清理 API | ⭐⭐⭐⭐ |
| **great_expectations** | 資料驗證 | ⭐⭐⭐⭐⭐ |
| **pandas-profiling/ydata** | 品質報告 | ⭐⭐⭐⭐ (已有) |
| **cleanlab** | 標籤錯誤偵測 | ⭐⭐⭐ |
| **feature-engine** | 特徵處理 | ⭐⭐⭐⭐ |
| **presidio** | PII 偵測 (Microsoft) | ⭐⭐⭐⭐ |
| **scrubadub** | PII 清除 | ⭐⭐⭐ |

### 現有 auto_analyze 已偵測的問題

目前 `auto_analyze` 已經可以偵測：
- ✅ 缺失值 (count, percentage)
- ✅ 異常值 (IQR, Z-score)
- ✅ ID 欄位
- ✅ 常數欄位
- ✅ 高相關特徵
- ✅ 資料類型推論
- ❌ PII (尚未實作)
- ❌ 自動修復建議

---

## 提議方案

### 方案 A: 增強現有 Smart Workflow (推薦)

```
1. start_data_analysis(csv)
   ↓
2. 返回 Ticket + 品質報告 + 問題清單
   ↓
3. Agent 根據問題嚴重度決定：
   - Critical (PII): 必須詢問用戶
   - High (>20% missing): 詢問處理方式
   - Medium: 提供建議，用戶可確認或跳過
   - Low: 自動處理，告知用戶
   ↓
4. execute_analysis_ticket(ticket_id, cleaning_options={...})
```

### 方案 B: 專用資料清理 MCP

新增工具組：
- `detect_data_issues(csv)` - 偵測所有問題
- `suggest_cleaning_actions(issues)` - 建議處理方式
- `preview_cleaning_result(csv, actions)` - 預覽清理結果
- `apply_cleaning(csv, actions)` - 執行清理
- `detect_pii(csv)` - 專門偵測 PII

### 方案 C: 互動式清理對話

```python
# MCP Tool: interactive_data_cleaning
async def interactive_data_cleaning(csv_content, user_id):
    """
    啟動互動式資料清理流程。
    
    Returns:
        cleaning_session_id: 清理會話 ID
        issues: 偵測到的問題列表
        suggested_actions: 建議的處理動作
        questions_for_user: 需要用戶回答的問題
    """
```

---

## 待討論問題

1. **PII 處理策略**
   - 偵測到 PII 時：警告並阻止？還是提供遮罩選項？
   - 是否需要合規性日誌？

2. **缺失值處理預設**
   - 數值欄位：均值/中位數/刪除？
   - 類別欄位：眾數/新類別/刪除？
   - 是否需要用戶每次確認？

3. **自動 vs 手動平衡點**
   - 什麼問題應該自動處理？
   - 什麼問題必須用戶確認？

4. **清理結果可逆性**
   - 是否保留原始資料？
   - 是否記錄清理歷史？

---

## 下一步行動

- [ ] 決定採用哪個方案 (A/B/C)
- [ ] 研究 presidio 整合 PII 偵測
- [ ] 設計清理選項的資料結構
- [ ] 原型實作並測試 UX 流程
- [ ] 評估 Agent 在不同場景的決策品質

---

## 相關資源

- [ydata-profiling Expectations](https://docs.profiling.ydata.ai/latest/)
- [Microsoft Presidio](https://microsoft.github.io/presidio/)
- [Great Expectations](https://greatexpectations.io/)
- [Feature Engine](https://feature-engine.trainindata.com/)
