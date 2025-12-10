# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

#### Phase 8: Visualization System (December 2025)

**Phase 8A: Foundation**
- `stats-worker/src/visualization/storage.py` - MinIO storage utilities for figures
- `stats-worker/src/visualization/style.py` - Publication-quality matplotlib styles
- `stats-worker/src/visualization/schemas.py` - VisualizationResult, VisualizationType schemas

**Phase 8B: Survival Analysis Plots**
- `stats-worker/src/visualization/survival.py` - Kaplan-Meier curves, forest plots, hazard ratio plots
- `create_survival_visualizations()` - High-level helper for survival analysis

**Phase 8C: ROC/PR Curve Plots**
- `stats-worker/src/visualization/roc.py` - ROC curves, PR curves, calibration curves
- `plot_roc_curve()`, `plot_pr_curve()`, `plot_calibration_curve()`
- `plot_confusion_matrix()`, `plot_threshold_analysis()`
- `create_roc_visualizations()` - High-level helper

**Phase 8D: Group Comparison Plots**
- `stats-worker/src/visualization/group_comparison.py` - Statistical comparison plots
- `plot_group_comparison()` - Box/violin/bar plots with p-value annotations
- `plot_anova_results()`, `plot_contingency_heatmap()`
- `plot_ttest_result()`, `plot_correlation_heatmap()`
- Uses `statannotations` for automatic p-value annotations

**Phase 8E: AutoML Plots**
- `stats-worker/src/visualization/automl.py` - AutoML result visualizations
- `plot_feature_importance()` - Bar chart from Dict/DataFrame/Series
- `plot_shap_summary()`, `plot_shap_waterfall()` - SHAP explanations
- `plot_learning_curve()` - Train/val performance with overfitting diagnosis
- `plot_model_comparison()` - Leaderboard visualization
- `plot_prediction_vs_actual()`, `plot_residuals()` - Regression diagnostics
- `create_automl_visualizations()` - High-level helper

**Phase 8F: Local Results Management**
- `stats-worker/src/results/manager.py` - JobResultsManager for local storage
- `stats-worker/src/results/worker_mixin.py` - Integration with StatsWorker
- Local directory structure: `/results/{user_id}/{job_name}_{timestamp}/`
- Automatic HTML report generation
- Source data tracking with `source_info.json`

### Changed

- Updated `docker-compose.yml` to mount `./results:/data/results` volume
- Updated `stats-worker/src/worker.py` to integrate with JobResultsManager
- Updated `stats-worker/src/config.py` to add `RESULTS_BASE_PATH` setting
- Enhanced `process_roc_full_eval_job()` to save results locally with HTML reports

### Technical Details

**Dependencies Added (stats-worker):**
- `matplotlib>=3.7.0` - Base plotting
- `seaborn>=0.12.0` - Enhanced visualizations
- `statannotations>=0.6.0` - Auto p-value annotations
- `lifelines>=0.27.0` - Survival analysis (already present)

**Storage Architecture:**
```
MinIO (stats-reports bucket)     → Agent accessible via URLs
Local (/data/results/)           → User accessible via file browser
```

**Test Coverage:**
- `tests/test_automl_visualization.py` - 39 tests, 10 test classes
- `tests/test_roc_visualization.py` - ROC visualization tests
- `tests/test_group_comparison_visualization.py` - Group comparison tests

---

## [1.0.0] - 2025-12-01

### Added
- Initial release with AutoML and Stats analysis capabilities
- MCP server for AI agent integration
- AutoGluon-based model training
- Statistical analysis with ydata-profiling and tableone
- Propensity score analysis
- Survival analysis (Kaplan-Meier, Cox regression)
- ROC analysis and calibration
