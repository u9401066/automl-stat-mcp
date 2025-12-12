# AutoML MCP Server - Tools Inventory

> Last Updated: 2025-12-12

## 📊 Overview

| Category | Count | Status |
|----------|-------|--------|
| AutoML | 26 | ✅ Ready |
| Statistics | 57+ | ✅ Ready |
| Data Cleaning | 9 | ✅ Ready |
| Workflow | 3 | ✅ Ready |
| **Total** | **98+** | |

---

## ✅ AutoML Tools (26)

### Dataset Management
| Tool | Description | Returns |
|------|-------------|---------|
| `list_available_files` | 列出本地可用檔案 | files[] |
| `upload_dataset` | 上傳/註冊資料集 | dataset_id |
| `list_datasets` | 列出已註冊資料集 | datasets[] |
| `delete_dataset` | 刪除資料集 | success |
| `register_dataset` | 從 MinIO 註冊 | dataset_id |
| `analyze_dataset` | 分析資料集特性 | analysis |

### Training
| Tool | Description | Returns |
|------|-------------|---------|
| `submit_automl_job` | 提交 AutoML 訓練 | job_id |
| `submit_specific_job` | 指定演算法訓練 | job_id |
| `submit_compare_job` | 比較多個演算法 | job_id |
| `train_and_wait` | 訓練並等待完成 | model_id, result |
| `quick_train` | 一鍵訓練 | model_id |

### Job Management
| Tool | Description | Returns |
|------|-------------|---------|
| `get_job_status` | 查詢工作狀態 | status, progress |
| `wait_for_job` | 等待工作完成 | result |
| `list_jobs` | 列出所有工作 | jobs[] |
| `cancel_job` | 取消工作 | success |

### Model Management
| Tool | Description | Returns |
|------|-------------|---------|
| `list_models` | 列出所有模型 | models[] |
| `get_model_leaderboard` | 取得模型排行榜 | leaderboard |
| `predict` | 使用模型預測 | predictions |
| `delete_model` | 刪除模型 | success |
| `list_algorithms` | 列出可用演算法 | algorithms[] |

### Orchestration
| Tool | Description | Returns |
|------|-------------|---------|
| `get_training_summary` | 訓練總覽 | summary |
| `get_upload_help` | 上傳說明 | help |
| `health_check` | 服務健康檢查 | status |

---

## ✅ Statistics Tools (57+)

### Core Analysis
| Tool | Description | Result Persistence |
|------|-------------|-------------------|
| `auto_analyze` | 智能自動分析 | ✅ |
| `run_quick_auto_analyze` | 快速分析 | ✅ |
| `analyze_csv_directly` | 直接分析 CSV | - |
| `get_quick_stats` | 快速統計 | - |
| `direct_ml_analyze` | ML 前置分析 | - |

### Correlations & Groups
| Tool | Description | Result Persistence |
|------|-------------|-------------------|
| `analyze_correlations` | 相關性分析 | ✅ `result_id`, `result_path` |
| `compare_groups` | 組間比較 | ✅ `result_id`, `result_path` |
| `check_multicollinearity` | VIF 分析 | - |

### Missing Values
| Tool | Description | Result Persistence |
|------|-------------|-------------------|
| `analyze_missing_values` | 缺失值分析 | - |
| `run_full_statistical_analysis` | 完整統計分析 | - |

### TableOne
| Tool | Description | Result Persistence |
|------|-------------|-------------------|
| `generate_tableone_directly` | 生成 Table 1 | ✅ `result_id`, `result_path` |
| `submit_tableone_job` | 提交 TableOne 工作 | - |
| `get_tableone_preview` | TableOne 預覽 | - |
| `run_quick_tableone` | 快速 TableOne | - |
| `get_column_suggestions` | 欄位建議 | - |

### EDA
| Tool | Description | Result Persistence |
|------|-------------|-------------------|
| `submit_eda_job` | 提交 EDA 工作 | - |
| `run_quick_eda` | 快速 EDA | - |
| `get_analysis_capabilities` | 分析能力 | - |

### ROC/AUC Analysis
| Tool | Description |
|------|-------------|
| `compute_roc_curve` | 計算 ROC 曲線 |
| `compare_roc_curves` | 比較兩個 ROC (DeLong) |
| `compare_multiple_roc_curves` | 多模型比較 |
| `find_optimal_threshold` | 最佳閾值 |
| `full_classifier_evaluation` | 完整分類評估 |
| `analyze_calibration` | 校準分析 |
| `interactive_threshold_analysis` | 互動式閾值 |
| `generate_roc_publication_report` | ROC 報告 |

### Survival Analysis
| Tool | Description |
|------|-------------|
| `kaplan_meier_survival` | KM 曲線 |
| `compare_survival` | 存活比較 |
| `cox_proportional_hazards` | Cox 迴歸 |
| `survival_data_summary` | 存活資料摘要 |

### Propensity Score
| Tool | Description |
|------|-------------|
| `estimate_propensity_scores` | 估計傾向分數 |
| `match_propensity_scores` | PSM 配對 |
| `estimate_treatment_effect` | 治療效果 (IPTW) |
| `assess_covariate_balance` | 共變數平衡 |
| `run_propensity_analysis` | 完整 PSA |

### Power Analysis (19 tools)
| Category | Tools |
|----------|-------|
| T-test | `calculate_ttest_sample_size`, `calculate_ttest_power`, `calculate_effect_size`, `ttest_sensitivity_analysis` |
| Proportion | `calculate_proportion_sample_size`, `calculate_proportion_power`, `proportion_sensitivity_analysis` |
| ANOVA | `calculate_anova_sample_size`, `calculate_anova_power`, `calculate_anova_effect_size` |
| Chi-square | `calculate_chisquare_sample_size`, `calculate_chisquare_power`, `calculate_chisquare_effect_size` |
| Survival | `calculate_survival_sample_size`, `calculate_survival_power`, `calculate_survival_events`, `calculate_survival_from_medians`, `convert_hazard_ratio_to_log` |

### Job Management
| Tool | Description |
|------|-------------|
| `get_stats_job_status` | 統計工作狀態 |
| `get_stats_job_result` | 統計工作結果 |
| `list_stats_jobs` | 列出統計工作 |

### Result Storage (NEW)
| Tool | Description |
|------|-------------|
| `list_analysis_results` | 列出儲存的結果 |
| `get_analysis_result` | 取得儲存的結果 |

---

## ✅ Data Cleaning Tools (9)

| Tool | Description | Input | Output |
|------|-------------|-------|--------|
| `handle_missing_values` | 缺失值處理 | csv_path, strategy | output_path |
| `remove_columns` | 移除欄位 | csv_path, columns | output_path |
| `filter_rows` | 篩選資料 | csv_path, condition | output_path |
| `rename_columns` | 重新命名 | csv_path, mapping | output_path |
| `convert_to_binary` | 轉換為 0/1 | csv_path, column, mapping | output_path |
| `encode_categorical` | 類別編碼 | csv_path, columns, method | output_path |
| `get_column_info` | 欄位資訊 | csv_path | column_info |
| `direct_preview_data` | 資料預覽 | csv_path | preview |
| `preview_dataset_stats` | 資料集統計 | dataset_id | stats |

---

## ✅ Workflow Tools (3)

| Tool | Description |
|------|-------------|
| `start_data_analysis` | 開始分析流程 (返回 ticket) |
| `execute_analysis_ticket` | 執行分析工單 |
| `check_analysis_progress` | 檢查進度 |

---

## 🆕 Result Persistence

Tools with result persistence return:
```json
{
  "result_id": "stat_compare_groups_abc12345",
  "result_path": "automl-results/user/compare_groups/20251212_120000_stat_compare_groups_abc12345.json"
}
```

**Storage Locations:**
- Redis: `stats:result:{result_id}` (7-day TTL)
- MinIO: `{bucket}/{user_id}/{analysis_type}/{timestamp}_{result_id}.json`

**Supported Tools:**
- `compare_groups` ✅
- `analyze_correlations` ✅
- `generate_tableone_directly` ✅

---

## Usage Example

```python
# 1. List available files
files = list_available_files(directory="/data/sample_data")

# 2. Upload dataset
result = upload_dataset(
    name="my_data",
    source_type="local",
    source_path="/data/sample_data/titanic.csv",
    user_id="eric"
)
dataset_id = result["dataset_id"]

# 3. Run analysis with persistence
result = compare_groups(
    csv_path="/data/sample_data/titanic.csv",
    numeric_column="age",
    group_column="survived",
    save_result=True,
    user_id="eric"
)
print(result["result_id"])  # stat_compare_groups_abc12345
print(result["result_path"])  # automl-results/eric/compare_groups/...

# 4. Retrieve saved result later
saved = get_analysis_result(result_id="stat_compare_groups_abc12345")
```
