---
name: project-audit
description: Comprehensive project audit checking compliance with CONSTITUTION, bylaws, architecture, and best practices. Use when reviewing project health, preparing for major releases, or onboarding. Triggers: AUDIT, 審計, 檢查專案, 健康檢查, 整理專案, review project, 專案檢查, compliance, 檢核, 品質檢查, health check.
---

# Project Audit 技能 (專案審計)

## 描述
根據 CONSTITUTION.md 和所有子法對專案進行全面審計。

## 觸發條件
- 「審計專案」「專案審計」
- 「檢查專案」「健康檢查」
- 「整理專案」「review project」

---

## 🎯 審計流程

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Project Audit Workflow                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   [1] DDD 架構審計     ──▶ .github/bylaws/ddd-architecture.md       │
│   [2] Memory Bank 審計 ──▶ .github/bylaws/memory-bank.md            │
│   [3] Python 環境審計  ──▶ .github/bylaws/python-environment.md     │
│   [4] Git 工作流審計   ──▶ .github/bylaws/git-workflow.md           │
│   [5] 檔案路徑審計     ──▶ .github/bylaws/file-paths.md             │
│   [6] Docker 服務審計  ──▶ .github/bylaws/docker-operations.md      │
│   [7] 文檔完整性審計   ──▶ README, CHANGELOG, ROADMAP               │
│   [8] 測試覆蓋審計     ──▶ tests/, {service}/tests/                 │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📋 [1] DDD 架構審計

### 檢查命令

```bash
# 檢查服務目錄結構
ls -la */src/

# 應該看到 DDD 分層
# domain/, application/, infrastructure/, interface/
```

### 合規標準

| 服務 | 必要分層 | 例外 |
|------|----------|------|
| automl-service | domain, application, infrastructure, interface | 無 |
| stats-service | domain, application, infrastructure, interface | 無 |
| automl-mcp-server | infrastructure | MCP 適配器例外 |
| automl-worker | - | Worker 簡化結構 |
| stats-worker | - | Worker 簡化結構 |

### 檢查項目

```
DDD 架構審計

□ 核心服務有完整 DDD 分層
□ Domain 層無外部依賴
□ Infrastructure 實現 Repository Pattern
□ 依賴方向：Presentation → Application → Domain ← Infrastructure
```

---

## 📋 [2] Memory Bank 審計

### 檢查命令

```bash
ls -la memory-bank/
```

### 必要檔案

| 檔案 | 用途 | 必要 |
|------|------|------|
| activeContext.md | 當前工作焦點 | ✅ |
| progress.md | 進度追蹤 | ✅ |
| decisionLog.md | 決策記錄 | ✅ |
| productContext.md | 產品上下文 | ✅ |
| projectBrief.md | 專案簡介 | ✅ |
| architect.md | 架構記錄 | ✅ |
| systemPatterns.md | 系統模式 | ✅ |

### 檢查項目

```
Memory Bank 審計

□ 7 個必要檔案都存在
□ progress.md 有最新進度
□ activeContext.md 反映當前狀態
□ decisionLog.md 記錄重大決策
```

---

## 📋 [3] Python 環境審計

### 檢查命令

```bash
# 檢查依賴管理檔案
find . -name "pyproject.toml" -o -name "requirements*.txt" -o -name "uv.lock"

# 檢查虛擬環境
ls -la .venv/
```

### 合規標準

| 項目 | 標準 | 降級條件 |
|------|------|----------|
| 套件管理器 | uv 優先 | CI 環境可用 pip |
| 虛擬環境 | 必須使用 | 無 |
| pyproject.toml | 必須有 | 無 |
| uv.lock | 應該有 | uv 未安裝可省略 |

### 檢查項目

```
Python 環境審計

□ 根目錄有 pyproject.toml
□ Docker 容器可用 requirements.txt（合規降級）
□ 虛擬環境存在 (.venv)
□ 依賴版本已鎖定
```

---

## 📋 [4] Git 工作流審計

### 檢查命令

```bash
# 檢查最近 commit
git log --oneline -10

# 檢查未提交變更
git status --short

# 檢查分支
git branch -a
```

### 合規標準

**Commit Message 格式：**
```
<type>(<scope>): <subject>
```

Type: feat, fix, docs, refactor, test, chore

### 檢查項目

```
Git 工作流審計

□ Commit Message 符合格式
□ 無遺留未提交的重要變更
□ 分支策略適當（可為單一 main/master）
```

---

## 📋 [5] 檔案路徑審計

### 檢查命令

```bash
# 搜尋可能的路徑問題
grep -r "/home/" --include="*.py" */src/
grep -r "sample_data" --include="*.py" */src/

# 檢查測試位置
find . -name "test_*.py" -o -name "*_test.py"
```

### 合規標準

| 使用情境 | 正確路徑 | 錯誤路徑 |
|----------|----------|----------|
| MCP 工具參數 | `/data/sample_data/` | `/home/eric/...` |
| 容器內程式碼 | `/data/...` | `./sample_data/` |
| 測試檔案位置 | `tests/`, `{service}/tests/` | 根目錄 |

### 檢查項目

```
檔案路徑審計

□ MCP 工具使用 Container 路徑
□ 無測試檔案在根目錄
□ 測試資料在 sample_data/ 或 fixtures/
```

---

## 📋 [6] Docker 服務審計

### 檢查命令

```bash
# 檢查服務狀態
docker compose ps

# 檢查配置
cat docker-compose.yml | head -50

# 檢查環境變數
cat .env 2>/dev/null || echo ".env not found"
```

### 檢查項目

```
Docker 服務審計

□ docker-compose.yml 存在且正確
□ .env 或 .env.example 存在
□ 服務可正常啟動
□ Volume 掛載正確
```

---

## 📋 [7] 文檔完整性審計

### 檢查命令

```bash
# 檢查主要文件
head -50 README.md
head -50 CHANGELOG.md
head -50 docs/ROADMAP.md
```

### 檢查項目

```
文檔完整性審計

□ README.md 反映當前功能
□ CHANGELOG.md 有最新版本記錄
□ ROADMAP.md 有進度標記
□ 安裝/使用說明可執行
```

---

## 📋 [8] 測試覆蓋審計

### 檢查命令

```bash
# 列出測試檔案
find . -path "./.venv" -prune -o -name "test_*.py" -print

# 執行測試
pytest --collect-only

# 覆蓋率
pytest --cov
```

### 檢查項目

```
測試覆蓋審計

□ 單元測試存在
□ 整合測試存在（如適用）
□ E2E 測試存在
□ 測試可通過
```

---

## 📊 審計報告範本

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 專案審計報告
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

日期：YYYY-MM-DD
專案：{project_name}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 合規項目
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

| 類別 | 項目 | 狀態 |
|------|------|------|
| DDD | 核心服務分層 | ✅ |
| Memory Bank | 7 個檔案完整 | ✅ |
| Git | Commit 格式 | ✅ |
| 文檔 | README 最新 | ✅ |

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 待改進項目
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

| 類別 | 問題 | 建議 |
|------|------|------|
| Python | 無 uv.lock | 安裝 uv 後產生 |
| 測試 | 覆蓋率 < 80% | 增加測試 |

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔢 統計數據
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- 測試數量：{N}
- 測試通過率：{X}%
- 程式碼行數：{N}
- Commit 數量：{N}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 行動項目
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. [ ] {待辦 1}
2. [ ] {待辦 2}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 💡 審計最佳實踐

### 定期審計
- 每週一次快速審計
- 每月一次完整審計
- 版本發布前必須審計

### 審計後行動
1. 立即修復嚴重問題
2. 建立 Issue 追蹤中等問題
3. 記錄到 progress.md
