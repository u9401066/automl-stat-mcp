---
name: mcp-tools-reference
description: Quick reference for all AutoML MCP tools. Triggers: MCP 工具, 有什麼工具, 工具清單, tools reference.
---

# MCP Tools Reference 技能 (MCP 工具速查)

## 描述
所有 AutoML MCP 工具的快速參照，幫助選擇正確的工具。

## 觸發條件
- 「有什麼工具」「工具清單」
- 「MCP 工具」「tools reference」

---

## 📊 工具總覽

| 類別 | 數量 | 主要用途 |
|------|------|----------|
| 資料管理 | 9 | 上傳、列出、預覽資料 |
| 資料清理 | 9 | 缺失值、編碼、篩選 |
| 基本統計 | 12 | 統計摘要、Table One |
| 進階統計 | 15 | 存活、傾向分數、ROC |
| 檢定力分析 | 19 | 樣本數、Power |
| ML 訓練 | 11 | AutoML、模型管理 |
| 工作管理 | 8 | 狀態、結果、取消 |
| **總計** | **83+** | |

---

## 🔧 資料管理工具

### 檔案操作

| 工具 | 用途 | 範例參數 |
|------|------|----------|
| `list_available_files` | 列出可用檔案 | `directory="/data/sample_data"` |
| `direct_preview_data` | 預覽資料 | `csv_path, n_rows=10` |
| `get_column_info` | 欄位資訊 | `csv_path` |
| `get_upload_help` | 上傳說明 | - |

### 資料集操作

| 工具 | 用途 | 範例參數 |
|------|------|----------|
| `upload_dataset` | 上傳資料集 | `name, source_type, source_path, user_id` |
| `register_dataset` | 從 MinIO 註冊 | `name, minio_path, user_id` |
| `list_datasets` | 列出資料集 | `user_id` |
| `delete_dataset` | 刪除資料集 | `dataset_id, user_id` |
| `analyze_dataset` | 分析資料集 | `dataset_id` |

---

## 🧹 資料清理工具

| 工具 | 用途 | 關鍵參數 |
|------|------|----------|
| `handle_missing_values` | 處理缺失值 | `csv_path, strategy, columns, output_path` |
| `remove_columns` | 移除欄位 | `csv_path, columns, output_path` |
| `rename_columns` | 重新命名 | `csv_path, mapping, output_path` |
| `convert_to_binary` | 轉換 0/1 | `csv_path, column, mapping, output_path` |
| `encode_categorical` | 類別編碼 | `csv_path, columns, method, output_path` |
| `filter_rows` | 篩選資料 | `csv_path, condition, output_path` |

**缺失值策略：** `mean`, `median`, `mode`, `constant`, `drop`
**編碼方法：** `onehot`, `label`, `target`

---

## 📈 基本統計工具

### 快速分析

| 工具 | 用途 | 輸出 |
|------|------|------|
| `get_quick_stats` | 快速統計摘要 | 基本統計 |
| `auto_analyze` | 智能自動分析 | 完整分析 |
| `run_quick_auto_analyze` | 快速自動分析 | 精簡分析 |
| `analyze_csv_directly` | 直接分析 CSV | 詳細分析 |

### Table One

| 工具 | 用途 | 關鍵參數 |
|------|------|----------|
| `generate_tableone_directly` | 生成 Table 1 | `csv_path, group_column, categorical, pval` |
| `get_tableone_preview` | Table One 預覽 | `csv_path, group_column` |
| `run_quick_tableone` | 快速 Table One | `csv_path, group_column` |
| `get_column_suggestions` | 欄位建議 | `csv_path` |

### 相關性與比較

| 工具 | 用途 | 關鍵參數 |
|------|------|----------|
| `compare_groups` | 組間比較 | `csv_path, numeric_column, group_column` |
| `analyze_correlations` | 相關性分析 | `csv_path, columns, method` |
| `check_multicollinearity` | VIF 分析 | `csv_path, columns, vif_threshold` |
| `analyze_missing_values` | 缺失值分析 | `csv_path` |

---

## 🔬 進階統計工具

### 存活分析

| 工具 | 用途 | 關鍵參數 |
|------|------|----------|
| `kaplan_meier_survival` | KM 曲線 | `csv_path, time_column, event_column, group_column` |
| `compare_survival` | 存活比較 (Log-rank) | 同上 |
| `cox_proportional_hazards` | Cox 迴歸 | `csv_path, time_column, event_column, covariates` |
| `survival_data_summary` | 存活資料摘要 | `csv_path, time_column, event_column` |

### 傾向分數分析

| 工具 | 用途 | 關鍵參數 |
|------|------|----------|
| `estimate_propensity_scores` | 估計 PS | `csv_path, treatment_column, covariates` |
| `match_propensity_scores` | PSM 配對 | `csv_path, treatment_column, covariates, method` |
| `estimate_treatment_effect` | 治療效果 | `csv_path, treatment_column, outcome_column, method` |
| `assess_covariate_balance` | 共變數平衡 | `csv_path, treatment_column, covariates` |
| `run_propensity_analysis` | 完整 PSA | 同上 |

### ROC 分析

| 工具 | 用途 | 關鍵參數 |
|------|------|----------|
| `compute_roc_curve` | 計算 ROC | `csv_path, y_true_column, y_score_column` |
| `compare_roc_curves` | 比較 ROC (DeLong) | `csv_path, y_true_column, y_score1_column, y_score2_column` |
| `compare_multiple_roc_curves` | 多模型比較 | `csv_path, y_true_column, y_score_columns` |
| `find_optimal_threshold` | 最佳閾值 | `csv_path, y_true_column, y_score_column, method` |
| `full_classifier_evaluation` | 完整評估 | `csv_path, y_true_column, y_score_column` |
| `analyze_calibration` | 校準分析 | 同上 |

---

## 📐 檢定力分析工具

### T-test

| 工具 | 用途 |
|------|------|
| `calculate_ttest_sample_size` | 樣本數計算 |
| `calculate_ttest_power` | 檢定力計算 |
| `calculate_effect_size` | 效果量計算 |
| `ttest_sensitivity_analysis` | 敏感度分析 |

### 比例/卡方

| 工具 | 用途 |
|------|------|
| `calculate_proportion_sample_size` | 比例檢定樣本數 |
| `calculate_proportion_power` | 比例檢定力 |
| `calculate_chisquare_sample_size` | 卡方樣本數 |
| `calculate_chisquare_power` | 卡方檢定力 |
| `calculate_chisquare_effect_size` | 卡方效果量 |

### ANOVA

| 工具 | 用途 |
|------|------|
| `calculate_anova_sample_size` | ANOVA 樣本數 |
| `calculate_anova_power` | ANOVA 檢定力 |
| `calculate_anova_effect_size` | ANOVA 效果量 |

### 存活分析

| 工具 | 用途 |
|------|------|
| `calculate_survival_sample_size` | 存活分析樣本數 |
| `calculate_survival_power` | 存活分析檢定力 |
| `calculate_survival_events` | 所需事件數 |
| `calculate_survival_from_medians` | 從中位存活計算 |
| `convert_hazard_ratio_to_log` | HR 轉 log |

---

## 🤖 ML 訓練工具

### 訓練

| 工具 | 用途 | 關鍵參數 |
|------|------|----------|
| `submit_automl_job` | 提交 AutoML | `dataset_id, target_column, problem_type, time_limit, presets` |
| `submit_specific_job` | 指定演算法 | `dataset_id, target_column, algorithms` |
| `submit_compare_job` | 比較演算法 | `dataset_id, target_column, algorithms` |
| `quick_train` | 一鍵訓練 | `csv_path, target_column` |
| `train_and_wait` | 訓練並等待 | 同 submit_automl_job |

### 模型管理

| 工具 | 用途 | 關鍵參數 |
|------|------|----------|
| `list_models` | 列出模型 | `user_id` |
| `get_model_leaderboard` | 模型排行榜 | `model_id` |
| `list_algorithms` | 可用演算法 | - |
| `predict` | 預測 | `model_id, dataset_id` |
| `delete_model` | 刪除模型 | `model_id, user_id` |
| `get_training_summary` | 訓練摘要 | `model_id` |

---

## 📋 工作管理工具

| 工具 | 用途 | 關鍵參數 |
|------|------|----------|
| `get_job_status` | 工作狀態 | `job_id, user_id` |
| `wait_for_job` | 等待完成 | `job_id, timeout, user_id` |
| `list_jobs` | 列出工作 | `user_id` |
| `cancel_job` | 取消工作 | `job_id, user_id` |
| `health_check` | 健康檢查 | - |

### 結果管理

| 工具 | 用途 | 關鍵參數 |
|------|------|----------|
| `list_analysis_results` | 列出結果 | `user_id, analysis_type` |
| `get_analysis_result` | 取得結果 | `result_id` |

---

## 🎯 常用工具組合

### 快速探索資料
```
list_available_files → direct_preview_data → get_quick_stats
```

### 完整資料分析
```
get_column_info → analyze_missing_values → auto_analyze → generate_tableone_directly
```

### ML 訓練流程
```
upload_dataset → submit_automl_job → get_job_status → get_model_leaderboard → predict
```

### 資料清理流程
```
get_column_info → handle_missing_values → encode_categorical → filter_rows
```

### 存活分析流程
```
survival_data_summary → kaplan_meier_survival → compare_survival → cox_proportional_hazards
```

### 傾向分數分析
```
estimate_propensity_scores → match_propensity_scores → assess_covariate_balance → estimate_treatment_effect
```

---

## ⚠️ 重要提醒

### 路徑規則
- 永遠使用 Container 路徑：`/data/sample_data/` 或 `/data/projects/`
- 不要使用 Host 路徑：`/home/...`

### user_id
- 大多數操作需要 `user_id`
- 用於資源隔離和追蹤

### 非同步工作
- `submit_*_job` 返回 `job_id`
- 需要用 `get_job_status` 或 `wait_for_job` 取得結果

### 結果儲存
- 部分工具支援 `save_result=True`
- 結果存到 Redis (7 天) + MinIO (永久)
