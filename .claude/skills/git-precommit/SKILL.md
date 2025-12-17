---
name: git-precommit
description: Pre-commit orchestration workflow ensuring Memory Bank sync, README/CHANGELOG/ROADMAP updates before git commit. Use when preparing to commit code changes or push to repository. Triggers: GIT, gc, push, commit, 提交, 準備 commit, 要提交了, git commit, pre-commit, 推送, 準備上程式碼.
---

# Git 提交前工作流（編排器）

## 描述
協調多個 Skills 完成 Git 提交前的所有準備工作。

## 觸發條件
- 「準備 commit」「要提交了」「git commit」

## 法規依據
- 憲法：CONSTITUTION.md 第三章
- 子法：.github/bylaws/git-workflow.md

## 執行流程

```
┌─────────────────────────────────────────────────┐
│              Git Pre-Commit Orchestrator        │
├─────────────────────────────────────────────────┤
│  Step 1: memory-sync     [必要] Memory Bank 同步 │
│  Step 2: readme-update   [可選] README 更新      │
│  Step 3: changelog-update[可選] CHANGELOG 更新   │
│  Step 4: roadmap-update  [可選] ROADMAP 更新     │
│  Step 5: arch-check      [條件] 架構文檔檢查     │
│  Step 6: commit-prepare  [最終] 準備提交         │
└─────────────────────────────────────────────────┘
```

---

## 📋 各步驟詳細說明

### Step 1: Memory Bank 同步 [必要]

更新 `memory-bank/` 目錄下的檔案：

| 檔案 | 更新內容 |
|------|----------|
| `activeContext.md` | 當前工作焦點、進行中的變更 |
| `progress.md` | Done/Doing/Next 項目 |
| `decisionLog.md` | 記錄重要決策（如有） |
| `productContext.md` | 專案上下文變更（如有） |

### Step 2: README 更新 [可選]

偵測變更類型並更新對應區塊：

| 變更類型 | 更新區塊 |
|----------|----------|
| 新功能 | 功能列表 |
| 新依賴 | 安裝說明 |
| API 變更 | 使用範例 |
| 結構變更 | 專案結構 |
| 新設定 | 配置說明 |

**不自動修改的區塊：** 授權資訊、貢獻指南、致謝

### Step 3: CHANGELOG 更新 [可選]

遵循 [Keep a Changelog](https://keepachangelog.com/) 格式：

**分類規則：**

| 類型 | 關鍵字偵測 |
|------|------------|
| Added | 新增、add、feat |
| Changed | 變更、修改、update、change |
| Deprecated | 棄用、deprecate |
| Removed | 移除、刪除、remove、delete |
| Fixed | 修復、fix、bug |
| Security | 安全、security、漏洞 |

**版本號決定：**
```
MAJOR.MINOR.PATCH

MAJOR: 重大變更（Breaking Changes）
MINOR: 新功能（向下相容）
PATCH: Bug 修復
```

**輸出範例：**
```
📋 CHANGELOG 更新

偵測到的變更：
  - [Added] 新增用戶認證模組
  - [Fixed] 修復登入問題

建議版本：0.2.0 (MINOR - 新功能)

預覽：
## [0.2.0] - 2025-12-17

### Added
- 新增用戶認證模組

### Fixed  
- 修復登入問題
```

### Step 4: ROADMAP 更新 [可選]

**狀態標記規則：**
```
📋 計劃中 → 🚧 進行中 → ✅ 已完成
```

**自動偵測：** 分析 commit 內容，匹配 ROADMAP 中的項目

**輸出範例：**
```
🗺️ ROADMAP 更新

匹配到的項目：
  ✅ 用戶認證 → 標記為已完成
  🚧 API 文檔 → 保持進行中

建議新增：
  - 新增「密碼重設」到已完成

預覽：
## 已完成 ✅
+ - [x] 用戶認證 (2025-12-17)
```

### Step 5: 架構文檔檢查 [條件]

當有結構性變更時更新：
- 架構圖和說明
- 組件關係
- 技術決策記錄

### Step 6: Commit 準備 [最終]

- 彙整所有變更
- 建議 commit message
- 顯示 staged files

---

## 參數

| 參數 | 說明 | 預設 |
|------|------|------|
| `--skip-readme` | 跳過 README 更新 | false |
| `--skip-changelog` | 跳過 CHANGELOG 更新 | false |
| `--skip-roadmap` | 跳過 ROADMAP 更新 | false |
| `--dry-run` | 只預覽不修改 | false |
| `--quick` | 只執行必要步驟 (memory-sync) | false |

## 使用範例

```
「準備 commit」           # 完整流程
「快速 commit」           # 等同 --quick
「commit --skip-readme」  # 跳過 README
```

## 輸出格式

```
🚀 Git Pre-Commit 工作流

[1/6] Memory Bank 同步 ✅
  └─ progress.md: 更新 2 項
  └─ activeContext.md: 已更新

[2/6] README 更新 ✅
  └─ 新增功能說明

[3/6] CHANGELOG 更新 ✅
  └─ 添加 v0.2.0 條目

[4/6] ROADMAP 更新 ⏭️ (無變更)

[5/6] 架構文檔 ⏭️ (無結構性變更)

[6/6] Commit 準備 ✅
  └─ 建議訊息：feat: 新增用戶認證模組

📋 Staged files:
  - src/auth/...
  - docs/...

準備好了！確認提交？
```
