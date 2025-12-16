# AGENTS.md - VS Code Copilot Agent 指引

此文件為 VS Code GitHub Copilot 的 Agent Mode 提供專案上下文。

---

## 專案規則

### 法規遵循
你必須遵守以下法規層級：

1. **憲法**：`CONSTITUTION.md` - 最高原則，不可違反
2. **子法**：`.github/bylaws/*.md` - 細則規範
3. **技能**：`.claude/skills/*/SKILL.md` - 操作程序

### 架構原則

- 採用 **DDD (Domain-Driven Design)**
- **DAL (Data Access Layer) 必須獨立**
- 依賴方向：`Presentation → Application → Domain ← Infrastructure`

詳見：`.github/bylaws/ddd-architecture.md`

### Python 環境規則

- **優先使用 uv** 管理套件和虛擬環境
- 新專案必須建立 `pyproject.toml` + `uv.lock`
- 禁止全域安裝套件

```bash
# 初始化環境
uv venv
uv sync --all-extras

# 安裝依賴
uv add package-name
uv add --dev pytest ruff
```

詳見：`.github/bylaws/python-environment.md`

### Memory Bank 同步

每次重要操作必須更新 Memory Bank：

| 操作 | 更新文件 |
|------|----------|
| 完成任務 | `progress.md` (Done) |
| 開始任務 | `progress.md` (Doing), `activeContext.md` |
| 重大決策 | `decisionLog.md` |
| 架構變更 | `architect.md` |

詳見：`.github/bylaws/memory-bank.md`

### Git 工作流

提交前必須執行檢查清單：
1. ✅ Memory Bank 同步（必要）
2. 📖 README 更新（如需要）
3. 📋 CHANGELOG 更新（如需要）
4. 🗺️ ROADMAP 標記（如需要）

詳見：`.github/bylaws/git-workflow.md`

### 檔案路徑規則

⚠️ **這是最常犯的錯誤！**

| 環境 | 路徑前綴 | 使用時機 |
|------|----------|----------|
| Container | `/data/sample_data/` | MCP 工具參數、API 請求 |
| Container | `/data/projects/` | 使用者專案資料 |
| Host | `/home/eric/...` | 本機測試、IDE 開發 |

```python
# ❌ 錯誤：MCP 工具中使用 Host 路徑
csv_path="/home/eric/workspace251204/sample_data/iris.csv"

# ✅ 正確：使用 Container 路徑
csv_path="/data/sample_data/iris.csv"
```

**測試檔案位置：**
- ✅ `tests/` - 整合/E2E 測試
- ✅ `{service}/tests/` - 服務單元測試
- ❌ 根目錄禁止放任何測試

詳見：`.github/bylaws/file-paths.md`

### Docker 服務操作

```bash
# 啟動所有服務
docker compose up -d

# 重建單一服務
docker compose up -d --build automl-mcp

# 擴展 Worker
docker compose up -d --scale automl-worker=8

# 查看日誌
docker compose logs -f automl-mcp

# 進入容器除錯
docker compose exec automl-mcp ls /data/sample_data/
```

**MinIO/Redis 配置：** 使用 `.env` 檔案

詳見：`.github/bylaws/docker-operations.md`

---

## 🔄 工作流 Skills（最重要！）

**每次工作必用的 Skills：**

| 時機 | Skill | 觸發詞 |
|------|-------|--------|
| 開始工作 | `session-start` | 開始, 繼續, resume |
| 執行任務 | `task-workflow` | 做任務, implement |
| 遇到 bug | `debug-workflow` | 除錯, bug, error |
| 功能完成 | `feature-delivery` | 交付, ship it |
| 準備提交 | `git-precommit` | 準備 commit |
| 中途保存 | `memory-checkpoint` | checkpoint, 存檔 |
| 結束工作 | `session-end` | 收工, 下班, bye |

**完整導航：** 見 `.claude/skills/master-workflow/SKILL.md`

---

## 可用 Skills

位於 `.claude/skills/` 目錄：

### 工作流 Skills（核心）
- **master-workflow** - 工作流導航中心（入口點）
- **session-start** - 工作階段開始，恢復上下文
- **session-end** - 工作階段結束，保存狀態
- **task-workflow** - 單一任務執行流程
- **debug-workflow** - 系統化除錯流程
- **feature-delivery** - 功能完整交付
- **project-audit** - 專案全面審計

### 文檔維護 Skills
- **git-precommit** - Git 提交前編排器
- **memory-updater** - Memory Bank 同步
- **memory-checkpoint** - 記憶檢查點（Summarize 前外部化）
- **readme-updater** - README 智能更新
- **changelog-updater** - CHANGELOG 自動更新
- **roadmap-updater** - ROADMAP 狀態追蹤

### 程式碼品質 Skills
- **ddd-architect** - DDD 架構輔助與檢查
- **code-refactor** - 主動重構與模組化
- **code-reviewer** - 程式碼審查
- **test-generator** - 測試生成（Unit/Integration/E2E）
- **project-init** - 專案初始化

### MCP 資料分析 Skills（本專案核心）
- **data-analysis-workflow** - 資料探索分析流程 (EDA, Table One)
- **ml-training-workflow** - ML 模型訓練流程 (AutoML)
- **statistical-analysis-workflow** - 進階統計分析 (存活、PSM、ROC)
- **data-cleaning-workflow** - 資料清理前處理
- **mcp-tools-reference** - MCP 工具速查參考

---

## 💸 Memory Checkpoint 規則

為避免對話被 Summarize 壓縮時遺失重要上下文：

### 主動觸發時機
1. 對話超過 **10 輪**
2. 累積修改超過 **5 個檔案**
3. 完成一個 **重要功能/修復**
4. 使用者說要 **離開/等等**

### 執行指令
- 「記憶檢查點」「checkpoint」「存檔」
- 「保存記憶」「sync memory」

### 必須記錄
- 當前工作焦點
- 變更的檔案列表（完整路徑）
- 待解決事項
- 下一步計畫

---

## 回應風格

- 使用**繁體中文**
- 提供清晰的步驟說明
- 引用相關法規條文
- 執行操作後更新 Memory Bank
