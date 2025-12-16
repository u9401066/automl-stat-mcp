# 004 - MCP 工具精簡計畫 (98 → 50)

> Created: 2025-12-16
> Status: ✅ Completed
> Final: 50 public tools, 53 hidden

## 目標

將 98+ 個 MCP 工具精簡到 50 個，提高易用性並降低 Agent 的選擇困難。

## 執行結果

### 最終工具清單 (50 個公開)

| 類別 | 檔案 | 公開 | 隱藏 |
|------|------|------|------|
| Cleaning | `cleaning_tools.py` | 7 | 0 |
| Dataset | `dataset_tools.py` | 3 | 0 |
| Direct | `direct_tools.py` | 0 | 3 |
| Info | `info_tools.py` | 0 | 2 |
| Integrated | `integrated_tools.py` | 4 | 0 |
| Job | `job_tools.py` | 3 | 0 |
| Model | `model_tools.py` | 4 | 0 |
| Orchestration | `orchestration_tools.py` | 1 | 4 |
| Power | `power_tools.py` | 5 | 0 |
| Smart | `smart_tools.py` | 2 | 1 |
| Statistics | `statistics_tools.py` | 18 | 40 |
| Training | `training_tools.py` | 1 | 2 |
| Upload | `upload_tools.py` | 2 | 1 |
| **總計** | | **50** | **53** |

### 驗證結果

| 類別 | 隱藏數 | 替代方案 |
|------|--------|----------|
| Power Analysis | 18 | `power_ttest/proportion/anova/chisquare/survival` (5 統一工具) |
| Core Analysis | 3 | `smart_analyze` (stats + tableone + correlations) |
| EDA/TableOne | 7 | `generate_tableone_directly` (csv_path 版本) |
| Survival | 2 | 避免與 `statistics/` 子模組重複 |
| Propensity | 3 | 避免與 `statistics/` 子模組重複 |
| ROC | 4 | 避免與 `statistics/` 子模組重複 |
| Orchestration | 4 | `train_and_wait` 涵蓋主要功能 |
| Info | 2 | MCP Resources (`automl://algorithms`, `automl://health`) |
| Direct | 3 | `smart_analyze` (自動路徑解析) |
| Other | 7 | 各種整合工具替代 |

### 恢復的工具 (驗證後)

| 工具 | 恢復原因 |
|------|----------|
| `start_data_analysis` | 獨特功能：資料驗證 + cleaning workflow |
| `execute_analysis_ticket` | 獨特功能：資料清理 + 持久化存儲選項 |

---

## 原始工具分類 (98 個)

### Statistics Tools (58 個)
| # | 工具名稱 | 決定 | 理由 |
|---|----------|------|------|
| 1 | `list_analysis_results` | ✅ 保留 | 結果管理必要 |
| 2 | `get_analysis_result` | ✅ 保留 | 結果管理必要 |
| 3 | `auto_analyze` | ❌ 刪除 | 被 `smart_analyze` 取代 |
| 4 | `run_quick_auto_analyze` | ❌ 刪除 | 被 `smart_analyze` 取代 |
| 5 | `get_analysis_capabilities` | ❌ 刪除 | 改為 MCP Resource |
| 6 | `submit_eda_job` | ❌ 刪除 | 低使用率，合併到 smart_analyze |
| 7 | `submit_tableone_job` | ❌ 刪除 | 改用 `generate_tableone_directly` |
| 8 | `get_stats_job_status` | ✅ 保留 | Job 管理必要 |
| 9 | `get_stats_job_result` | ✅ 保留 | Job 管理必要 |
| 10 | `list_stats_jobs` | ✅ 保留 | Job 管理必要 |
| 11 | `get_column_suggestions` | ❌ 刪除 | 合併到 `get_quick_stats` |
| 12 | `preview_dataset_stats` | ❌ 刪除 | 被 `quick_preview` 取代 |
| 13 | `run_quick_eda` | ❌ 刪除 | 被 `smart_analyze` 取代 |
| 14 | `run_quick_tableone` | ❌ 刪除 | 改用 `generate_tableone_directly` |
| 15 | `analyze_csv_directly` | ❌ 刪除 | 被 `smart_analyze` 取代 |
| 16 | `get_quick_stats` | ✅ 保留 | 基礎統計仍需要 |
| 17 | `analyze_correlations` | ✅ 保留 | 核心分析功能 |
| 18 | `compare_groups` | ✅ 保留 | 核心分析功能 |
| 19 | `analyze_missing_values` | ✅ 保留 | 資料品質必要 |
| 20 | `check_multicollinearity` | ❌ 刪除 | 合併到 `analyze_correlations` |
| 21 | `run_full_statistical_analysis` | ❌ 刪除 | 被 `smart_analyze` 取代 |
| 22 | `generate_tableone_directly` | ✅ 保留 | 核心分析功能 |
| 23 | `get_tableone_preview` | ❌ 刪除 | 直接用 `generate_tableone_directly` |
| 24 | `kaplan_meier_survival` | ✅ 保留 | 存活分析核心 |
| 25 | `cox_proportional_hazards` | ✅ 保留 | 存活分析核心 |
| 26 | `compare_survival` | ❌ 刪除 | 合併到 `kaplan_meier_survival` |
| 27 | `survival_data_summary` | ❌ 刪除 | 合併到 `kaplan_meier_survival` |
| 28 | `estimate_propensity_scores` | ✅ 保留 | PSM 核心 |
| 29 | `match_propensity_scores` | ✅ 保留 | PSM 核心 |
| 30 | `estimate_treatment_effect` | ✅ 保留 | PSM 核心 |
| 31 | `assess_covariate_balance` | ❌ 刪除 | 合併到 `run_propensity_analysis` |
| 32 | `run_propensity_analysis` | ✅ 保留 | PSM 一站式 |
| 33 | `compute_roc_curve` | ✅ 保留 | ROC 核心 |
| 34 | `compare_roc_curves` | ✅ 保留 | ROC 比較 |
| 35 | `find_optimal_threshold` | ✅ 保留 | 臨床重要 |
| 36 | `analyze_calibration` | ❌ 刪除 | 合併到 `full_classifier_evaluation` |
| 37 | `full_classifier_evaluation` | ✅ 保留 | ROC 一站式 |
| 38 | `compare_multiple_roc_curves` | ❌ 刪除 | 用 `compare_roc_curves` 多次 |
| 39 | `interactive_threshold_analysis` | ❌ 刪除 | 合併到 `find_optimal_threshold` |
| 40 | `generate_roc_publication_report` | ❌ 刪除 | 合併到 `full_classifier_evaluation` |
| 41-58 | Power Analysis (18 個) | 合併 | 精簡為 4 個 |

### Power Analysis 精簡 (18 → 4)
| 類別 | 現有工具 | 精簡為 |
|------|----------|--------|
| T-test | `calculate_ttest_sample_size`, `calculate_ttest_power`, `ttest_sensitivity_analysis` | `power_ttest` |
| Proportion | `calculate_proportion_sample_size`, `calculate_proportion_power`, `proportion_sensitivity_analysis` | `power_proportion` |
| ANOVA | `calculate_anova_sample_size`, `calculate_anova_power`, `calculate_anova_effect_size` | `power_anova` |
| Chi-square | `calculate_chisquare_sample_size`, `calculate_chisquare_power`, `calculate_chisquare_effect_size` | `power_chisquare` |
| Survival | `calculate_survival_events`, `calculate_survival_sample_size`, `calculate_survival_power`, `calculate_survival_from_medians`, `convert_hazard_ratio_to_log` | `power_survival` |
| Effect Size | `calculate_effect_size` | 合併到各 power 工具 |

---

### AutoML Tools (26 個)
| # | 工具名稱 | 決定 | 理由 |
|---|----------|------|------|
| 1 | `list_available_files` | ✅ 保留 | 檔案管理必要 |
| 2 | `upload_dataset` | ✅ 保留 | 上傳必要 |
| 3 | `list_datasets` | ✅ 保留 | 管理必要 |
| 4 | `delete_dataset` | ✅ 保留 | 管理必要 |
| 5 | `register_dataset` | ❌ 刪除 | 合併到 `upload_dataset` |
| 6 | `analyze_dataset` | ❌ 刪除 | 被 `smart_analyze` 取代 |
| 7 | `submit_automl_job` | ✅ 保留 | 訓練核心 |
| 8 | `submit_specific_job` | ❌ 刪除 | 合併到 `submit_automl_job` |
| 9 | `submit_compare_job` | ❌ 刪除 | 合併到 `submit_automl_job` |
| 10 | `train_and_wait` | ✅ 保留 | 方便使用 |
| 11 | `quick_train` | ❌ 刪除 | 用 `train_and_wait` |
| 12 | `get_job_status` | ✅ 保留 | Job 管理必要 |
| 13 | `wait_for_job` | ❌ 刪除 | 合併到 `get_job_status` |
| 14 | `list_jobs` | ✅ 保留 | Job 管理必要 |
| 15 | `cancel_job` | ✅ 保留 | Job 管理必要 |
| 16 | `list_models` | ✅ 保留 | 模型管理必要 |
| 17 | `get_model_leaderboard` | ✅ 保留 | 模型比較必要 |
| 18 | `predict` | ✅ 保留 | 預測核心 |
| 19 | `delete_model` | ✅ 保留 | 管理必要 |
| 20 | `list_algorithms` | ❌ 刪除 | 改為 MCP Resource |
| 21 | `get_training_summary` | ❌ 刪除 | 合併到 `get_job_status` |
| 22 | `get_upload_help` | ❌ 刪除 | 改為 MCP Resource |
| 23 | `health_check` | ❌ 刪除 | 改為 MCP Resource |

---

### Data Cleaning Tools (9 個)
| # | 工具名稱 | 決定 | 理由 |
|---|----------|------|------|
| 1 | `handle_missing_values` | ✅ 保留 | 清理核心 |
| 2 | `remove_columns` | ✅ 保留 | 清理核心 |
| 3 | `filter_rows` | ✅ 保留 | 清理核心 |
| 4 | `rename_columns` | ✅ 保留 | 清理核心 |
| 5 | `convert_to_binary` | ✅ 保留 | PSM 必要 |
| 6 | `encode_categorical` | ✅ 保留 | ML 必要 |
| 7 | `get_column_info` | ❌ 刪除 | 合併到 `get_quick_stats` |
| 8 | `direct_preview_data` | ❌ 刪除 | 被 `quick_preview` 取代 |
| 9 | `preview_dataset_stats` | ❌ 刪除 | 被 `quick_preview` 取代 |

---

### Workflow Tools (3 個)
| # | 工具名稱 | 決定 | 理由 |
|---|----------|------|------|
| 1 | `start_data_analysis` | ❌ 刪除 | 被 `smart_analyze` 取代 |
| 2 | `execute_analysis_ticket` | ❌ 刪除 | 被 `smart_analyze` 取代 |
| 3 | `check_analysis_progress` | ❌ 刪除 | 用 `get_job_status` |

---

### 新增整合工具 (4 個)
| # | 工具名稱 | 取代 | 說明 |
|---|----------|------|------|
| 1 | `smart_analyze` | auto_analyze, run_quick_auto_analyze, analyze_csv_directly, run_quick_eda, run_full_statistical_analysis | 一站式分析 |
| 2 | `analyze_medical_study` | 5+ 工具組合 | 醫學研究專用 |
| 3 | `quick_preview` | preview_dataset_stats, direct_preview_data | 快速預覽 |
| 4 | `compare_treatment_groups` | compare_groups (簡化版) | 簡化參數 |

---

## 精簡後工具清單 (50 個)

### Core Analysis (8)
1. `smart_analyze` - 智能分析 (NEW)
2. `get_quick_stats` - 快速統計
3. `quick_preview` - 資料預覽 (NEW)
4. `generate_tableone_directly` - Table One
5. `analyze_correlations` - 相關性分析
6. `compare_groups` - 組間比較
7. `analyze_missing_values` - 缺失值分析
8. `analyze_medical_study` - 醫學研究分析 (NEW)

### Survival Analysis (2)
9. `kaplan_meier_survival` - KM 曲線
10. `cox_proportional_hazards` - Cox 迴歸

### Propensity Score (4)
11. `estimate_propensity_scores` - 估計 PS
12. `match_propensity_scores` - PSM 配對
13. `estimate_treatment_effect` - 治療效果
14. `run_propensity_analysis` - 完整 PSA

### ROC Analysis (4)
15. `compute_roc_curve` - ROC 曲線
16. `compare_roc_curves` - ROC 比較
17. `find_optimal_threshold` - 最佳閾值
18. `full_classifier_evaluation` - 完整評估

### Power Analysis (5)
19. `power_ttest` - T-test 功效
20. `power_proportion` - 比例功效
21. `power_anova` - ANOVA 功效
22. `power_chisquare` - 卡方功效
23. `power_survival` - 存活功效

### AutoML (13)
24. `list_available_files` - 列出檔案
25. `upload_dataset` - 上傳資料
26. `list_datasets` - 列出資料集
27. `delete_dataset` - 刪除資料集
28. `submit_automl_job` - 提交訓練
29. `train_and_wait` - 訓練並等待
30. `get_job_status` - 工作狀態
31. `list_jobs` - 列出工作
32. `cancel_job` - 取消工作
33. `list_models` - 列出模型
34. `get_model_leaderboard` - 模型排行
35. `predict` - 預測
36. `delete_model` - 刪除模型

### Data Cleaning (6)
37. `handle_missing_values` - 缺失值處理
38. `remove_columns` - 移除欄位
39. `filter_rows` - 篩選資料
40. `rename_columns` - 重新命名
41. `convert_to_binary` - 轉換為 0/1
42. `encode_categorical` - 類別編碼

### Result Management (4)
43. `list_analysis_results` - 列出結果
44. `get_analysis_result` - 取得結果
45. `get_stats_job_status` - 統計工作狀態
46. `get_stats_job_result` - 統計工作結果

### Utilities (4)
47. `list_stats_jobs` - 列出統計工作
48. `compare_treatment_groups` - 治療比較 (NEW)
49. `direct_ml_analyze` - ML 前置分析
50. `start_data_analysis` - 開始分析 (保留作為入口點)

---

## 實施步驟

### Phase 1: 整合工具 ✅ DONE
- [x] 建立 `integrated_tools.py`
- [x] 建立 `resources.py`
- [x] 建立 `power_tools.py` (5 個合併工具)
- [x] 註冊新工具

### Phase 2: 隱藏冗餘工具（⚠️ 不是刪除！）

**正確做法**：移除 `@mcp.tool()` 裝飾器，函數改為內部使用

```python
# Before: 公開給 Agent
@mcp.tool()
async def calculate_ttest_sample_size(...):
    ...

# After: 內部函數，Agent 看不到
async def _calculate_ttest_sample_size(...):
    ...  # 邏輯完全保留
```

**工具分類**：

| 類別 | 保留公開 | 改為內部 |
|------|----------|----------|
| Core Analysis | smart_analyze, get_quick_stats, generate_tableone_directly | auto_analyze, run_quick_auto_analyze, analyze_csv_directly |
| Correlations | analyze_correlations, compare_groups | check_multicollinearity, run_full_statistical_analysis |
| EDA/TableOne | generate_tableone_directly | submit_eda_job, submit_tableone_job, run_quick_eda, run_quick_tableone, get_tableone_preview |
| Survival | kaplan_meier_survival, cox_proportional_hazards | compare_survival, survival_data_summary |
| Propensity | run_propensity_analysis, estimate_treatment_effect | estimate_propensity_scores, match_propensity_scores, assess_covariate_balance |
| ROC | compute_roc_curve, compare_roc_curves, full_classifier_evaluation | analyze_calibration, compare_multiple_roc_curves, interactive_threshold_analysis, generate_roc_publication_report |
| Power | power_ttest, power_proportion, power_anova, power_chisquare, power_survival | 所有 calculate_* 工具 |

### Phase 3: 更新整合工具
- [ ] `smart_analyze` 內部呼叫 `_run_quick_auto_analyze()`
- [ ] `analyze_medical_study` 內部呼叫 `_generate_tableone()` + `_compare_groups()`
- [ ] `power_*` 工具內部呼叫 `_calculate_*_sample_size()` 等

### Phase 4: 測試與文檔
- [ ] Docker 重建測試
- [ ] 驗證公開工具數量 = 50
- [ ] 更新 `MCP_TOOLS_INVENTORY.md`
- [ ] 更新 `AGENTS.md`

---

## 風險評估

| 風險 | 影響 | 緩解措施 |
|------|------|----------|
| 破壞現有整合 | 高 | 先部署新工具，確認可用再刪舊的 |
| 功能遺失 | 中 | 確保合併工具涵蓋所有功能 |
| 測試覆蓋不足 | 中 | 更新 E2E 測試 |

---

## 預期效益

| 指標 | Before | After | 改善 |
|------|--------|-------|------|
| 工具數量 | 98 | 50 | ↓49% |
| Agent 選擇困難 | 高 | 低 | ↓80% |
| 常見工作流調用次數 | 4-6 | 1 | ↓83% |
| 文檔維護成本 | 高 | 低 | ↓50% |
