# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.4.0] - 2025-12-16

### Added

#### AI Development Framework Integration
- Integrated `template-is-all-you-need` framework for AI-assisted development
- `.claude/skills/` - 12 Claude Skills for automation:
  - `git-precommit` - Git commit workflow orchestrator
  - `memory-checkpoint` - Memory checkpoint before context loss
  - `memory-updater` - Memory Bank synchronization
  - `test-generator` - Auto-generate tests
  - `code-reviewer` - Code review
  - `ddd-architect` - DDD architecture assistant
  - `code-refactor` - Code refactoring
  - `readme-updater` - README updates
  - `changelog-updater` - CHANGELOG updates
  - `roadmap-updater` - ROADMAP updates
  - `readme-i18n` - README internationalization
  - `project-init` - Project initialization

#### Project Governance
- `CONSTITUTION.md` - Project constitution (highest principles)
  - Chapter 1: DDD Architecture Principles
  - Chapter 2: Memory Bank Principles
  - Chapter 3: Documentation Principles
  - Chapter 4: Bylaw Authorization
- `.github/bylaws/` - 4 bylaws for detailed regulations:
  - `ddd-architecture.md` - DDD implementation guide
  - `git-workflow.md` - Git workflow rules
  - `memory-bank.md` - Memory Bank usage rules
  - `python-environment.md` - Python environment (uv-first)
- `AGENTS.md` - VS Code Copilot Agent guidelines
- `.vscode/settings.json` - Claude Skills enabled

## [1.3.0] - 2025-12-12

### Added

#### Result Persistence System
- `automl-mcp-server/src/infrastructure/mcp/handlers/result_storage.py`
  - `ResultStorage` class for saving analysis results
  - `NumpyJSONEncoder` for handling numpy types in JSON serialization
  - Dual storage: Redis (7-day TTL) + MinIO (permanent)
  - Result ID pattern: `stat_{analysis_type}_{uuid8}`
  - MinIO path: `{user_id}/{analysis_type}/{timestamp}_{result_id}.json`

- `stats-service/src/routes/storage.py`
  - `POST /storage/redis/set` - Save to Redis
  - `GET /storage/redis/get` - Get from Redis
  - `GET /storage/redis/keys` - List Redis keys
  - `POST /storage/minio/upload` - Save to MinIO
  - `GET /storage/minio/download` - Get from MinIO
  - `GET /storage/minio/list` - List MinIO objects

#### Enhanced Statistics Tools
- `compare_groups` - Now returns `result_id` and `result_path`
- `analyze_correlations` - Now returns `result_id` and `result_path`
- `generate_tableone_directly` - Now returns `result_id` and `result_path`

### Changed
- `stats-service/src/infrastructure/redis_client.py` - Added generic get/set methods
- `stats-service/src/infrastructure/minio_client.py` - Added `put_object`, `get_object` methods

---

## [1.2.0] - 2025-12-09

### Added

#### Phase 8: Visualization System

**Phase 8A: Foundation**
- `stats-worker/src/visualization/storage.py` - MinIO storage utilities
- `stats-worker/src/visualization/style.py` - Publication-quality matplotlib styles
- `stats-worker/src/visualization/schemas.py` - VisualizationResult schemas

**Phase 8B: Survival Analysis Plots**
- `stats-worker/src/visualization/survival.py` - Kaplan-Meier curves, forest plots

**Phase 8C: ROC/PR Curve Plots**
- `stats-worker/src/visualization/roc.py` - ROC, PR, calibration curves
- `plot_confusion_matrix()`, `plot_threshold_analysis()`

**Phase 8D: Group Comparison Plots**
- `stats-worker/src/visualization/group_comparison.py`
- Box/violin/bar plots with p-value annotations (statannotations)

**Phase 8E: AutoML Plots**
- `stats-worker/src/visualization/automl.py`
- Feature importance, SHAP, learning curves, model comparison

**Phase 8F: Local Results Management**
- `stats-worker/src/results/manager.py` - JobResultsManager
- Local directory: `/results/{user_id}/{job_name}_{timestamp}/`
- HTML report generation

#### Phase 7: Data Cleaning Service
- `convert_to_binary` - Convert column to 0/1
- `encode_categorical` - Label/OneHot encoding
- `handle_missing_values` - Missing value strategies
- `remove_columns` - Drop columns
- `filter_rows` - Filter data rows
- `rename_columns` - Rename columns
- `get_column_info` - Column information

### Changed
- Updated `docker-compose.yml` - Mount `./results:/data/results`
- Enhanced ROC job to save results locally with HTML reports

---

## [1.1.0] - 2025-12-08

### Added
- **Phase 6 Complete: Power Analysis** - 19 MCP tools
  - T-test sample size/power
  - Proportion sample size/power
  - ANOVA sample size/power/effect size
  - Chi-square sample size/power/effect size
  - Survival sample size/power

### Fixed
- Fixed 23 broken `stats_worker_tasks` imports in MCP
- Power Analysis tools now use stats_client API calls
- Added scipy to MCP container

---

## [1.0.0] - 2025-12-01

### Added
- Initial release
- AutoML training with AutoGluon 1.3.1
- MCP server for AI agent integration
- Statistical analysis (EDA, TableOne)
- Propensity score analysis (PSM, IPTW)
- Survival analysis (Kaplan-Meier, Cox regression)
- ROC/AUC analysis with DeLong test
- Multi-user isolation
- Redis job queue
- MinIO object storage
