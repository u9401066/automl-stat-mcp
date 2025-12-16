---
name: master-workflow
description: Master reference for all workflows and when to use which skill. This is the navigation hub for all project activities.
---

# Master Workflow 技能 (工作流總覽)

## 描述
所有工作流的導航中心，幫助決定何時使用哪個 Skill。

---

## 🗺️ 工作流導航圖

```
                         ┌─────────────────────────────────────┐
                         │        🌅 Session Start             │
                         │   「開始」「繼續」「我回來了」        │
                         └─────────────────┬───────────────────┘
                                           │
                    ┌──────────────────────┼──────────────────────┐
                    │                      │                      │
                    ▼                      ▼                      ▼
         ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
         │  📋 Task        │    │  🔧 Debug       │    │  📊 Audit       │
         │  Workflow       │    │  Workflow       │    │  Project        │
         │ 「開始做{X}」    │    │ 「除錯」「bug」 │    │ 「審計」「檢查」 │
         └────────┬────────┘    └────────┬────────┘    └─────────────────┘
                  │                      │
                  │              ┌───────┴───────┐
                  │              │ 修復完成      │
                  │              └───────┬───────┘
                  │                      │
                  ▼                      ▼
         ┌─────────────────────────────────────────┐
         │           📦 Feature Delivery           │
         │    「交付」「完成功能」「ship it」        │
         └─────────────────┬───────────────────────┘
                           │
                           ▼
         ┌─────────────────────────────────────────┐
         │          🔄 Git Pre-commit              │
         │    「準備 commit」「要提交了」           │
         └─────────────────┬───────────────────────┘
                           │
           ┌───────────────┴───────────────┐
           │                               │
           ▼                               ▼
┌─────────────────┐              ┌─────────────────┐
│ 💾 Memory       │              │ 🌙 Session      │
│ Checkpoint      │              │ End             │
│「checkpoint」   │              │「收工」「下班」 │
└─────────────────┘              └─────────────────┘
```

---

## 📋 Skill 快速參照表

### 工作階段管理

| Skill | 觸發詞 | 用途 |
|-------|--------|------|
| **session-start** | 開始, 繼續, resume | 開始工作，恢復上下文 |
| **session-end** | 收工, 下班, wrap up | 結束工作，保存狀態 |
| **memory-checkpoint** | checkpoint, 存檔 | 中途保存記憶 |

### 任務執行

| Skill | 觸發詞 | 用途 |
|-------|--------|------|
| **task-workflow** | 做任務, implement | 執行單一任務 |
| **debug-workflow** | 除錯, bug, error | 系統化除錯 |
| **feature-delivery** | 交付, ship it | 完整功能交付 |

### 專案管理

| Skill | 觸發詞 | 用途 |
|-------|--------|------|
| **project-audit** | 審計, 檢查專案 | 全面專案審計 |
| **git-precommit** | 準備 commit | 提交前準備 |

### 文檔維護

| Skill | 觸發詞 | 用途 |
|-------|--------|------|
| **memory-updater** | 更新 memory | Memory Bank 同步 |
| **readme-updater** | 更新 readme | README 更新 |
| **changelog-updater** | 更新 changelog | CHANGELOG 更新 |
| **roadmap-updater** | 更新 roadmap | ROADMAP 更新 |

### 程式碼品質

| Skill | 觸發詞 | 用途 |
|-------|--------|------|
| **test-generator** | 產生測試 | 自動生成測試 |
| **code-reviewer** | review | 程式碼審查 |
| **code-refactor** | 重構 | 程式碼重構 |
| **ddd-architect** | 架構 | DDD 架構檢查 |

---

## 🔄 典型工作日流程

```
┌─────────────────────────────────────────────────────────────────────┐
│                        典型工作日流程                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  09:00  🌅 「開始工作」                                              │
│         ↓                                                           │
│         session-start → 恢復上下文 → 確認今日目標                    │
│                                                                      │
│  09:15  📋 「開始做 {任務 1}」                                        │
│         ↓                                                           │
│         task-workflow → Plan → Execute → Verify → Complete          │
│                                                                      │
│  11:00  📋 「開始做 {任務 2}」                                        │
│         ↓                                                           │
│         task-workflow → ...                                         │
│                                                                      │
│  12:00  💾 「checkpoint」(午餐前)                                     │
│         ↓                                                           │
│         memory-checkpoint → 保存當前狀態                             │
│                                                                      │
│  14:00  🔧 「有個 bug...」                                           │
│         ↓                                                           │
│         debug-workflow → Reproduce → Locate → Fix → Verify          │
│                                                                      │
│  16:00  📦 「功能完成，準備交付」                                     │
│         ↓                                                           │
│         feature-delivery → 完整交付檢查                              │
│                                                                      │
│  17:00  🔄 「準備 commit」                                           │
│         ↓                                                           │
│         git-precommit → Memory sync → Docs update → Commit          │
│                                                                      │
│  17:30  🌙 「收工」                                                  │
│         ↓                                                           │
│         session-end → 保存狀態 → 交接報告                            │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## ⚠️ 常見問題：何時該用哪個 Skill？

### Q: 我要開始寫程式碼了
**A:** 先確認有沒有執行 `session-start`，然後用 `task-workflow`

### Q: 程式碼出錯了
**A:** 用 `debug-workflow`，不要亂改

### Q: 功能寫完了
**A:** 用 `feature-delivery` 確保交付完整

### Q: 要提交了
**A:** 用 `git-precommit`，會自動處理 Memory Bank 和文檔

### Q: 要離開了
**A:** 用 `session-end`，確保下次能接續

### Q: 對話太長了
**A:** 用 `memory-checkpoint` 保存重要記憶

### Q: 專案亂了
**A:** 用 `project-audit` 全面檢查

---

## 📌 重要原則

### 1. 永遠從 session-start 開始
- 恢復上下文
- 確認狀態
- 設定目標

### 2. 一次只做一件事
- 用 task-workflow 追蹤
- 完成一個再開始下一個

### 3. 頻繁保存
- 重要進展後 checkpoint
- 提交前 git-precommit
- 離開前 session-end

### 4. 交付要完整
- 用 feature-delivery 檢查
- 包含測試、文檔、範例

### 5. 定期審計
- 用 project-audit 檢查
- 維持專案健康

---

## 🏷️ 所有觸發詞總表

| 中文 | 英文 | Skill |
|------|------|-------|
| 開始, 繼續, 我回來了 | start, resume, continue | session-start |
| 收工, 下班, 今天到這 | end, bye, wrap up | session-end |
| 存檔, 記憶檢查點 | checkpoint, save | memory-checkpoint |
| 做任務, 執行 | task, do, implement | task-workflow |
| 除錯, bug | debug, error, fix | debug-workflow |
| 交付, 完成功能 | deliver, ship | feature-delivery |
| 審計, 檢查專案 | audit, review | project-audit |
| 準備 commit, 要提交 | commit, push | git-precommit |
| 更新 memory | update memory | memory-updater |
| 產生測試 | generate test | test-generator |
| 重構 | refactor | code-refactor |
| review | review | code-reviewer |
