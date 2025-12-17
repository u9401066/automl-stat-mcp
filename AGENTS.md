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

**路徑自動轉換規則：**
| 使用者輸入 | 正確轉換 |
|------------|----------|
| `iris.csv` | `/data/sample_data/iris.csv` |
| `sample_data/xxx.csv` | `/data/sample_data/xxx.csv` |
| `projects/study1/data.csv` | `/data/projects/study1/data.csv` |
| `/home/eric/.../sample_data/xxx.csv` | `/data/sample_data/xxx.csv` |

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

## 🎯 專案操作流程（最核心！）

### 標準流程概覽

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    AutoML 專案標準操作流程                                │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   [Step 0] 檢視可用資料                                                   │
│       └─→ list_available_files("/data/sample_data")                     │
│       └─→ quick_preview("iris.csv")                                     │
│                   ↓                                                      │
│   [Step 1] 建立專案目錄（可選）                                            │
│       └─→ create_project_workspace(project_name, user_id, template)     │
│       └─→ 返回: /data/projects/{project_name}/                          │
│                   ↓                                                      │
│   [Step 2] 移動/上傳資料                                                  │
│       └─→ upload_dataset(source_path, storage_mode)                     │
│       └─→ 返回: dataset_id (永久) 或 job_id (暫存)                        │
│                   ↓                                                      │
│   [Step 3] 資料品質檢查                                                   │
│       └─→ quality_check 或 quick_stats (include_quality_check=True)     │
│       └─→ 返回: warnings, transform_suggestions, analysis_readiness     │
│                   ↓                                                      │
│   [Step 4] 執行分析/訓練                                                  │
│       ├─→ [分析] smart_analyze / generate_tableone_directly             │
│       ├─→ [統計] kaplan_meier_survival / cox_proportional_hazards       │
│       └─→ [ML] submit_automl_job / quick_train                          │
│                   ↓                                                      │
│   [Step 5] 取得結果與圖表                                                 │
│       └─→ get_analysis_result(result_id)                                │
│       └─→ get_model_leaderboard(model_id)                               │
│       └─→ list_analysis_results(user_id)                                │
│                   ↓                                                      │
│   [Step 6] 產生報告（可選）                                               │
│       └─→ generate_analysis_report(result_ids)                          │
│       └─→ 結果儲存於 MinIO: automl-results/{user_id}/                    │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### Step 0：檢視可用資料

```python
# 列出 sample_data 目錄檔案
list_available_files(directory="/data/sample_data")

# 快速預覽資料（自動路徑轉換）
quick_preview(csv_path="iris.csv")  # → /data/sample_data/iris.csv
```

**可用範例資料集：**
| 檔案 | 類型 | 目標變數 |
|------|------|----------|
| `iris.csv` | 多類別分類 | species |
| `titanic.csv` | 二元分類 | survived |
| `heart_disease.csv` | 二元分類 | target |
| `breast_cancer.csv` | 二元分類 | diagnosis |
| `medical_study_200.csv` | 醫學研究 | treatment_group |
| `rossi_recidivism.csv` | 存活分析 | arrest, week |
| `stanford_heart.csv` | 存活分析 | status, time |

### Step 1：建立專案目錄（正式研究）

```python
create_project_workspace(
    project_name="my_breast_cancer_study",
    user_id="eric",
    template="medical_study"  # default / medical_study / ml_project
)
```

**產生目錄結構：**
```
/data/projects/my_breast_cancer_study/
├── data/
│   ├── raw/           # 原始資料
│   └── processed/     # 清理後資料
├── analysis/          # 分析結果
├── reports/           # 報告
└── figures/           # 圖表
```

### Step 2：上傳資料

```python
# 方式 A：暫存模式（快速分析用）
upload_dataset(
    name="quick_analysis",
    source_type="local",
    source_path="/data/sample_data/breast_cancer.csv",
    storage_mode="temporary",  # 存 Redis，7天後過期
    user_id="eric"
)
# 返回: job_id（用於單次分析）

# 方式 B：永久模式（正式研究/ML 訓練）
upload_dataset(
    name="breast_cancer_study",
    source_type="local",
    source_path="/data/projects/my_study/data/raw/data.csv",
    storage_mode="permanent",  # 存 MinIO，永久保留
    user_id="eric"
)
# 返回: dataset_id（用於 ML 訓練）
```

### Step 3：資料品質檢查

```python
# 方式 A：專用品質檢查端點
quality_check(csv_path="/data/sample_data/breast_cancer.csv")

# 方式 B：整合在 quick_stats 中
quick_stats(
    csv_path="/data/sample_data/breast_cancer.csv",
    include_quality_check=True
)
```

**品質檢查輸出：**
- `warnings`: 問題警告 (ALL_NAN, CONSTANT, HIGH_MISSING 等)
- `transform_suggestions`: 轉換建議 (log, zscore 等)
- `analysis_readiness`: ready / needs_review / not_ready

### Step 4：執行分析

**路徑 A：描述性分析**
```python
# 推薦！一站式分析
smart_analyze(csv_path="breast_cancer.csv", group_column="diagnosis")

# 或分步執行
quick_stats(csv_path="breast_cancer.csv")
generate_tableone_directly(csv_path="...", group_column="diagnosis")
analyze_correlations(csv_path="...")
```

**路徑 B：統計分析**
```python
# 存活分析
kaplan_meier_survival(csv_path="rossi.csv", time_col="week", event_col="arrest")
cox_proportional_hazards(csv_path="rossi.csv", time_col="week", event_col="arrest")

# ROC 分析
compute_roc_curve(csv_path="...", y_true_col="target", y_score_col="probability")
```

**路徑 C：機器學習**
```python
# Step 4a: 提交訓練
submit_automl_job(
    dataset_id="dataset-xxx",
    target_column="diagnosis",
    problem_type="binary",
    time_limit=300,
    user_id="eric"
)
# 返回: job_id

# Step 4b: 等待完成
wait_for_job(job_id="job-xxx", user_id="eric")
# 返回: model_id

# Step 4c: 查看結果
get_model_leaderboard(model_id="model-xxx", user_id="eric")
```

### Step 5：取得結果

```python
# 列出所有分析結果
list_analysis_results(user_id="eric", analysis_type="tableone")

# 取得特定結果
get_analysis_result(result_id="stat_tableone_abc123")

# ML 模型排行榜
get_model_leaderboard(model_id="model-xxx", user_id="eric")
```

### Step 6：產生報告（可選）

```python
generate_analysis_report(
    result_ids=["stat_tableone_xxx", "stat_roc_yyy"],
    user_id="eric"
)
# 報告存於: automl-results/eric/reports/
```

### 速查：依使用者需求選流程

| 使用者說... | 執行流程 |
|-------------|----------|
| 「看看這個資料」 | Step 0 → Step 3 |
| 「快速分析」 | Step 0 → Step 2(暫存) → Step 4A |
| 「正式研究專案」 | Step 0 → Step 1 → Step 2(永久) → Step 3 → Step 4 → Step 5 → Step 6 |
| 「訓練模型」 | Step 0 → Step 2(永久) → Step 4C → Step 5 |
| 「存活分析」 | Step 0 → Step 4B |

**完整流程 Skill：** `.claude/skills/project-workflow/SKILL.md`

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
- **project-workflow** - 🆕 專案完整操作流程（建立→上傳→分析→報告）
- **mcp-quick-analysis** - 快速分析流程（自動路徑轉換、智能工具選擇）
- **data-analysis-workflow** - 資料探索分析流程 (EDA, Table One)
- **ml-training-workflow** - ML 模型訓練流程 (AutoML)
- **statistical-analysis-workflow** - 進階統計分析 (存活、PSM、ROC)
- **data-cleaning-workflow** - 資料清理前處理
- **result-delivery-workflow** - 結果交付與專案管理 (下載報告、檔案分享)
- **mcp-tools-reference** - MCP 工具速查參考 (51 個工具)

---

## 🔧 MCP 工具使用指南 (51 個工具)

### 預設參數（減少重複輸入）

```python
# 除非使用者指定，一律使用：
user_id = "eric"
storage_mode = "temporary"  # 快速分析用
```

### 工具選擇速查表（精簡版）

| 使用者說... | 推薦工具 | 備註 |
|-------------|----------|------|
| 「看看資料」「有什麼欄位」 | `quick_preview` | 自動路徑解析 |
| 「分析這個資料」 | `smart_analyze` | ⭐ 一站式推薦 |
| 「醫學研究分析」 | `analyze_medical_study` | RCT 完整流程 |
| 「比較兩組」「治療效果」 | `compare_treatment_groups` | 簡化版 |
| 「Table One」 | `generate_tableone_directly` | 出版級表格 |
| 「相關性」「變數關係」 | `analyze_correlations` | |
| 「VIF」「共線性」 | `check_multicollinearity` | 迴歸前診斷 |
| 「訓練模型」「預測」 | `train_and_wait` | 一站式訓練 |
| 「存活分析」「KM 曲線」 | `kaplan_meier_survival` | |
| 「傾向分數」「PSM」 | `run_propensity_analysis` | |
| 「ROC」「AUC」 | `compute_roc_curve` | |
| 「樣本數計算」 | `power_ttest` | mode="sample_size" |

### 整合工具（推薦入口）

| 工具 | 功能 | 自動路徑 |
|------|------|----------|
| `smart_analyze` | stats + tableone + correlations | ✅ |
| `analyze_medical_study` | 醫學研究完整分析 | ✅ |
| `quick_preview` | 快速資料預覽 | ✅ |
| `compare_treatment_groups` | 組間比較 | ✅ |

### Power 分析（統一版）

| 工具 | mode 選項 |
|------|-----------|
| `power_ttest` | sample_size / power / sensitivity / effect_size |
| `power_proportion` | sample_size / power / sensitivity |
| `power_anova` | sample_size / power / effect_size |
| `power_chisquare` | sample_size / power / effect_size |
| `power_survival` | sample_size / power / events / from_medians |

### 故障排除

| 錯誤 | 原因 | 解法 |
|------|------|------|
| `auto_analyze` 失敗 | 有缺失值/類型問題 | 改用 `generate_tableone_directly` |
| `'<' not supported` | NaN 比較 | 先 `handle_missing_values` |
| 找不到檔案 | 路徑錯誤 | 確認用 `/data/...` 開頭 |
| 工具不存在 | 工具被整併 | 查看 `mcp-tools-reference` Skill |

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
