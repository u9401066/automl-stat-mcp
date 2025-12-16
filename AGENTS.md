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

## 可用 Skills

位於 `.claude/skills/` 目錄：

- **git-precommit** - Git 提交前編排器
- **ddd-architect** - DDD 架構輔助與檢查
- **code-refactor** - 主動重構與模組化
- **memory-updater** - Memory Bank 同步
- **memory-checkpoint** - 記憶檢查點（Summarize 前外部化）
- **readme-updater** - README 智能更新
- **changelog-updater** - CHANGELOG 自動更新
- **roadmap-updater** - ROADMAP 狀態追蹤
- **code-reviewer** - 程式碼審查
- **test-generator** - 測試生成（Unit/Integration/E2E）
- **project-init** - 專案初始化

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
