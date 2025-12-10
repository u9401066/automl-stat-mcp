# 完整測試覆蓋計劃

## 📋 測試分類

### Phase 1: Unit Tests (單元測試)
本地執行，不需要 Docker 服務

| Module | Test File | 狀態 |
|--------|-----------|------|
| Results Manager | `stats-worker/tests/test_results_manager.py` | 🔄 新建 |
| Visualization - Survival | `stats-worker/tests/test_survival_visualization.py` | ✅ 已有 |
| Visualization - ROC | `stats-worker/tests/test_roc_visualization.py` | ✅ 已有 |
| Visualization - Group | `stats-worker/tests/test_group_comparison_visualization.py` | ✅ 已有 |
| Visualization - AutoML | `stats-worker/tests/test_automl_visualization.py` | ✅ 已有 |
| Power Analysis | `stats-worker/tests/test_power_analysis.py` | ✅ 已有 |
| TableOne | `stats-worker/tests/test_tableone_generator.py` | ✅ 已有 |
| ROC Analysis | `stats-worker/tests/test_roc_analysis.py` | ✅ 已有 |
| Survival Analysis | `stats-worker/tests/test_survival_analysis.py` | ✅ 已有 |

### Phase 2: Integration Tests (整合測試)
需要 Docker 服務運行

| Test | Test File | 狀態 |
|------|-----------|------|
| Worker + Results Integration | `stats-worker/tests/test_worker_integration.py` | 🔄 新建 |
| Stats Service API | `tests/test_stats_service.py` | 🔄 新建 |

### Phase 3-6: E2E Tests (端到端測試)
完整系統流程測試

| Phase | Test | Test File | 狀態 |
|-------|------|-----------|------|
| 3 | Data Upload Flow | `tests/test_e2e_data.py` | 🔄 新建 |
| 4 | AutoStat Flow | `tests/test_e2e_stats.py` | 🔄 新建 |
| 5 | AutoML Flow | `tests/test_e2e_automl.py` | 🔄 新建 |
| 6 | Visualization Flow | `tests/test_e2e_visualization.py` | 🔄 新建 |

---

## 🎯 Phase 1: Unit Tests 詳細內容

### test_results_manager.py (~20 tests)

```python
class TestJobResultsManager:
    """Test JobResultsManager core functionality."""
    
    def test_init_creates_manager()
    def test_sanitize_name()
    def test_ensure_dirs_creates_structure()
    def test_save_source_info()
    def test_save_source_info_with_metadata()
    def test_save_figure_png()
    def test_save_figure_svg()
    def test_save_figure_closes_by_default()
    def test_save_result_json()
    def test_save_html_report()
    def test_finalize_creates_metadata()
    def test_finalize_with_error()
    def test_get_summary()
    def test_cleanup()
    
class TestSourceInfo:
    """Test SourceInfo dataclass."""
    def test_to_dict()
    def test_to_dict_excludes_none()

class TestJobMetadata:
    """Test JobMetadata dataclass."""
    def test_to_dict()
    def test_to_dict_with_source_info()

class TestWorkerResultsMixin:
    """Test WorkerResultsMixin integration."""
    def test_create_results_manager()
    def test_save_source_info_from_job()
    def test_finalize_job_with_local_results()
```

---

## 🎯 Phase 2: Integration Tests 詳細內容

### test_worker_integration.py (~15 tests)

```python
class TestWorkerWithResults:
    """Test Worker processing with local results."""
    
    @pytest.mark.integration
    def test_process_job_creates_results_dir()
    def test_process_job_saves_figures()
    def test_process_job_generates_html()
    def test_roc_full_eval_with_results()
    def test_tableone_with_results()
    def test_survival_analysis_with_results()
```

---

## 🎯 Phase 3: E2E Data Upload Tests

### test_e2e_data.py (~10 tests)

```python
class TestDataUploadFlow:
    """Complete data upload workflow."""
    
    @pytest.mark.e2e
    async def test_list_available_files()
    async def test_upload_local_file_temporary()
    async def test_upload_local_file_permanent()
    async def test_upload_with_column_sanitization()
    async def test_upload_generates_metadata()
    async def test_register_minio_file()
    
class TestDataCleaningFlow:
    """Data cleaning workflow."""
    
    async def test_convert_to_binary()
    async def test_encode_categorical()
    async def test_handle_missing_values()
```

---

## 🎯 Phase 4: E2E AutoStat Tests

### test_e2e_stats.py (~20 tests)

```python
class TestTableOneFlow:
    """TableOne generation workflow."""
    
    async def test_tableone_heart_disease()
    async def test_tableone_with_stratification()
    async def test_tableone_continuous_vs_categorical()
    
class TestEDAFlow:
    """Exploratory Data Analysis workflow."""
    
    async def test_auto_analyze_iris()
    async def test_auto_analyze_with_target()
    async def test_quick_stats()
    
class TestPowerAnalysisFlow:
    """Power Analysis workflow."""
    
    async def test_ttest_power()
    async def test_proportion_power()
    async def test_anova_power()
    async def test_survival_power()
    
class TestSurvivalAnalysisFlow:
    """Survival Analysis workflow."""
    
    async def test_kaplan_meier()
    async def test_cox_regression()
    async def test_log_rank_test()
    
class TestROCAnalysisFlow:
    """ROC Analysis workflow."""
    
    async def test_compute_roc_curve()
    async def test_compare_roc_curves()
    async def test_full_classifier_evaluation()
```

---

## 🎯 Phase 5: E2E AutoML Tests

### test_e2e_automl.py (~15 tests)

```python
class TestAutoMLTrainingFlow:
    """AutoML training workflow."""
    
    async def test_submit_automl_job_iris()
    async def test_submit_automl_job_breast_cancer()
    async def test_wait_for_training()
    async def test_get_leaderboard()
    
class TestSpecificAlgorithmFlow:
    """Specific algorithm training workflow."""
    
    async def test_train_xgboost()
    async def test_train_random_forest()
    async def test_train_lightgbm()
    
class TestPredictionFlow:
    """Model prediction workflow."""
    
    async def test_predict_with_model()
    async def test_batch_prediction()
    
class TestModelManagementFlow:
    """Model management workflow."""
    
    async def test_list_models()
    async def test_get_feature_importance()
    async def test_delete_model()
```

---

## 🎯 Phase 6: E2E Visualization Tests

### test_e2e_visualization.py (~12 tests)

```python
class TestResultsDirectoryFlow:
    """Test local results directory creation."""
    
    async def test_results_dir_created()
    async def test_figures_saved()
    async def test_html_report_generated()
    async def test_metadata_json_correct()
    
class TestVisualizationOutputFlow:
    """Test visualization output in results."""
    
    async def test_roc_curve_saved()
    async def test_survival_curve_saved()
    async def test_feature_importance_saved()
    async def test_shap_summary_saved()
    
class TestHTMLReportFlow:
    """Test HTML report content."""
    
    async def test_html_contains_figures()
    async def test_html_contains_statistics()
    async def test_html_opens_in_browser()
```

---

## 📦 測試資料集

| Dataset | 用途 | Tests |
|---------|------|-------|
| Iris | 多類別分類 | AutoML, TableOne |
| Breast Cancer | 二元分類 | AutoML, ROC |
| Heart Disease | 二元分類 | TableOne, ROC |
| Titanic | 二元分類 | Propensity, Survival |
| Rossi Recidivism | 生存分析 | KM, Cox |
| Diabetes | 迴歸 | AutoML, EDA |
| Wine Quality | 迴歸/分類 | AutoML |

---

## 🚀 執行指令

```bash
# Phase 1: Unit Tests
cd stats-worker
python -m pytest tests/ -v --ignore=tests/test_public_datasets.py

# Phase 2: Integration Tests (需要 Docker)
python -m pytest tests/ -m integration -v

# Phase 3-6: E2E Tests (需要完整系統)
cd tests
python -m pytest test_e2e_*.py -v

# 完整測試報告
python -m pytest --cov=src --cov-report=html

# 只執行快速測試
python -m pytest -m "not slow" -v
```

---

## 📊 目標覆蓋率

| Module | Target | Current |
|--------|--------|---------|
| visualization/ | 80% | ~70% |
| results/ | 90% | 0% (新模組) |
| tasks/ | 70% | ~60% |
| worker.py | 70% | ~50% |
| Overall | 75% | TBD |
