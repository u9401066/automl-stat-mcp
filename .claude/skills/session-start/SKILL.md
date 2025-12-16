---
name: session-start
description: Initialize work session with context recovery and task planning. Triggers: START, 開始, 開工, 繼續, 接續上次, 我回來了, resume, continue, 今天做什麼.
---

# Session Start 技能 (工作階段開始)

## 描述
每次開始工作時的標準流程，從 Memory Bank 恢復上下文並規劃任務。

## 觸發條件
- 「開始工作」「開工」「繼續」
- 「接續上次」「我回來了」
- 「resume」「continue」
- 每天第一次對話

---

## 🎯 執行流程

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Session Start Workflow                            │
├─────────────────────────────────────────────────────────────────────┤
│  Step 1: 讀取 Memory Bank 恢復上下文                                  │
│  Step 2: 檢查上次未完成的工作                                         │
│  Step 3: 確認今日目標                                                │
│  Step 4: 建立 Todo List                                             │
│  Step 5: 更新 activeContext.md                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📋 Step 1: 讀取 Memory Bank

**必讀文件（依序）：**

```bash
# 1. 當前狀態
read_file memory-bank/activeContext.md

# 2. 進度追蹤
read_file memory-bank/progress.md

# 3. 決策記錄（如有需要）
read_file memory-bank/decisionLog.md
```

**關鍵資訊提取：**
- 上次工作焦點是什麼？
- 哪些任務「進行中」(Doing)？
- 有哪些待處理事項？
- 最近做了什麼決策？

---

## 📋 Step 2: 檢查未完成工作

**檢查清單：**

| 項目 | 檢查方式 |
|------|----------|
| 未提交變更 | `git status` |
| 進行中任務 | progress.md 的 Doing 區塊 |
| 待處理事項 | activeContext.md 的待辦事項 |
| 測試狀態 | 上次測試是否通過？ |

---

## 📋 Step 3: 確認今日目標

**詢問使用者（如未明確）：**

```
📋 根據 Memory Bank，上次的工作狀態：

**進行中：**
- [ ] {從 progress.md 提取}

**待處理：**
- [ ] {從 activeContext.md 提取}

**未提交變更：**
- {從 git status 提取}

---

今天想要：
1. 繼續上次的工作？
2. 開始新任務？
3. 先處理未提交的變更？
```

---

## 📋 Step 4: 建立 Todo List

**使用 manage_todo_list 工具：**

```python
manage_todo_list(
    operation="write",
    todoList=[
        {
            "id": 1,
            "title": "恢復上下文",
            "description": "從 Memory Bank 讀取並確認狀態",
            "status": "completed"
        },
        {
            "id": 2,
            "title": "{今日第一個任務}",
            "description": "{具體描述}",
            "status": "in-progress"
        },
        # ... 更多任務
    ]
)
```

---

## 📋 Step 5: 更新 activeContext.md

```markdown
# Active Context (Updated: YYYY-MM-DD HH:MM)

## 當前工作階段
- 開始時間：{timestamp}
- 目標：{今日目標}

## 今日計畫
1. {任務 1}
2. {任務 2}
3. ...

## 上次未完成
- {從上次繼承的待辦}
```

---

## 💡 最佳實踐

### 每次開始工作時
1. **先讀取**，不要直接開始寫程式碼
2. **確認狀態**，知道專案目前在哪裡
3. **明確目標**，今天要完成什麼
4. **建立追蹤**，用 Todo List 追蹤進度

### 如果記憶被壓縮
如果發現對話開始時沒有完整上下文：
1. 執行 `session-start` 重新載入
2. 明確告訴 AI「請從 Memory Bank 恢復上下文」
3. 重要細節已經保存在 Memory Bank，不會遺失

---

## 📌 輸出範例

```
🌅 工作階段開始

📖 從 Memory Bank 恢復上下文...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 專案狀態
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**上次工作：** 2025-12-16 - 測試框架建立
**進度：** 421 單元測試 ✅, E2E 12/13 ✅

**進行中任務：**
- [ ] 法規更新 - 新增 file-paths.md, docker-operations.md

**未提交變更：**
- (clean)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 今日規劃
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

請問今天要：
1. 繼續完善法規文件？
2. 開始新功能開發？
3. 其他任務？
```
