---
name: master-workflow
description: Master navigation hub showing all available workflows and when to use each skill. Use when unsure which workflow to follow, need guidance on available skills, or want to see all options. Triggers: help, 幫助, 該用什麼, which skill, workflow, 流程, 導覽, navigation, skills list, 有哪些技能.
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
| **readme-updater** | 更新 readme | README 更新 |

### 程式碼品質

| Skill | 觸發詞 | 用途 |
|-------|--------|------|
| **test-generator** | 產生測試 | 自動生成測試 |
| **code-reviewer** | review | 程式碼審查 |
| **code-refactor** | 重構 | 程式碼重構 |
| **ddd-architect** | 架構 | DDD 架構檢查 |

### MCP 資料分析（本專案核心）

| Skill | 觸發詞 | 用途 |
|-------|--------|------|
| **mcp-project-workflow** | 新專案, 完整流程, SOP | ⭐ 專案完整操作流程 |
| **mcp-data-analysis** | 分析資料, EDA, 快速分析 | 資料探索分析 |
| **mcp-ml-training** | 訓練模型, AutoML, train | ML 模型訓練 |
| **mcp-statistical-analysis** | 統計分析, 存活分析, PSM | 進階統計分析 |
| **mcp-data-cleaning** | 資料清理, preprocess | 資料前處理 |
| **mcp-result-delivery** | 下載結果, 取得報告, 傳檔案 | 結果交付與專案管理 |
| **mcp-tools-reference** | 工具清單, MCP 工具 | 工具速查參考 |

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

## 📊 MCP 資料分析流程

```
┌─────────────────────────────────────────────────────────────────────┐
│                     MCP 資料分析流程                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  「新專案」「完整流程」「正式研究」                                   │
│         ↓                                                           │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  ⭐ mcp-project-workflow (最完整！)                          │    │
│  │  Step 0: 檢視可用資料 (list_available_files, quick_preview) │    │
│  │  Step 1: 建立專案目錄 (create_project_workspace)            │    │
│  │  Step 2: 上傳資料 (upload_dataset)                          │    │
│  │  Step 3: 品質檢查 (quality_check)                           │    │
│  │  Step 4: 執行分析 (smart_analyze / automl / survival)       │    │
│  │  Step 5: 取得結果 (get_analysis_result)                     │    │
│  │  Step 6: 產生報告 (generate_analysis_report)                │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  「快速分析」「分析一下」（不需建專案）                               │
│         ↓                                                           │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  🚀 mcp-data-analysis (含快速分析功能)                       │    │
│  │  quick_preview → smart_analyze → 結果彙整                    │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  「分析這個資料」「EDA」                                              │
│         ↓                                                           │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  📊 mcp-data-analysis                                        │    │
│  │  list_available_files → direct_preview_data → auto_analyze  │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  「我要訓練模型」                                                     │
│         ↓                                                           │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  🤖 mcp-ml-training                                         │    │
│  │  upload_dataset → submit_automl_job → get_job_status →      │    │
│  │  get_model_leaderboard → predict                            │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  「做存活分析/傾向分數/ROC」                                          │
│         ↓                                                           │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  🔬 mcp-statistical-analysis                                │    │
│  │  Survival / PSM / ROC / Power Analysis                      │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  「清理資料」                                                        │
│         ↓                                                           │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  🧹 mcp-data-cleaning                                       │    │
│  │  handle_missing_values → encode_categorical → filter_rows   │    │
│  └─────────────────────────────────────────────────────────────┘    │
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
| 產生測試 | generate test | test-generator |
| 重構 | refactor | code-refactor |
| review | review | code-reviewer |
| **新專案, 完整流程, SOP** | **full workflow, project setup** | **mcp-project-workflow** |
| **分析資料, 快速分析, 探索** | **EDA, explore, quick analysis** | **mcp-data-analysis** |
| **訓練模型** | **train, AutoML, ML** | **mcp-ml-training** |
| **存活分析, PSM, ROC** | **survival, propensity** | **mcp-statistical-analysis** |
| **資料清理, 缺失值** | **clean, preprocess** | **mcp-data-cleaning** |
| **下載結果, 傳檔案** | **download, report, share** | **mcp-result-delivery** |
| **MCP 工具, 工具清單** | **tools, reference** | **mcp-tools-reference** |
