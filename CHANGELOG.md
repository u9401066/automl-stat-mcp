# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.7.0] - 2026-01-23

### Added
- **Storage Abstraction Layer**: Implemented `storage_factory.py` with pluggable storage backends
  - `LocalStorageService`: Default local file storage at `/data` (no external dependencies)
  - `MinIOStorageService`: Optional MinIO S3-compatible object storage
  - Singleton factory pattern with `get_storage()` API
  - Configurable via `STORAGE_MODE` environment variable (local/minio)

### Changed
- **stats-service Migration**: Replaced direct `minio_client` calls with `storage_factory`
  - Updated 5 route files: main.py, storage.py, tableone.py, eda.py, jobs.py
  - Startup logs now show: `Storage backend initialized: LocalStorageService`
- **automl-service Migration**: Replaced `MinIOStorageService()` instantiation with `get_storage()`
  - Updated `dependencies.py` DI container to use storage factory
  - Updated `main.py` with storage initialization logging
- **Docker Compose Profiles**: Enhanced documentation for storage mode selection
- **Default Storage Mode**: Changed from MinIO-required to local-first architecture

### Fixed
- Syntax error in `stats-service/src/routes/tableone.py` (duplicate closing parenthesis)
- Integration tests now pass with local storage mode (32 passed)

### Technical Details
- Volume mounts: `./sample_data` → `/data/sample_data`, `./projects` → `/data/projects`
- Path resolution: Automatic conversion from user input to container paths
- Storage selection: `STORAGE_MODE=local` (default) or `STORAGE_MODE=minio` (requires profile: full)

## [1.6.0] - 2026-01-06

### Added
- **uv Workspace 管理**: 全面遷移至 `uv` 進行虛擬環境與多服務工作空間管理。
- **全專案代碼品質審計**: 
  - 達成 `automl-service` 與 `stats-service` 路由層 Ruff 零報錯 (Select: E, W, F, I, B, C4)。
  - 系統性修復了所有的 `B904` (Exception chaining) 並優化異常堆疊追蹤。
- **深層類型安全 (MyPy)**:
  - 為 `cleaning.py` 與 `direct.py` 中的複雜字典物件添加了適當的類型註解。
  - 為 `power.py` 統計回傳值添加了明確的轉型與 Null 檢查。

### Changed
- 統一了 `stats-service` 的導入風格，解決了 Ruff `F401` 與 `I001` 報錯。
- 移除了過渡性的自動化修復腳本，改為高品質的「外科手術式」手動修正。

## [1.5.0] - 2025-12-17

### Added

#### DataQualityAnalyzer - 資料品質分析模組
- `stats-service/src/domain/services/data_quality.py` - 統一資料品質分析模組
- **6 種問題偵測類型：**
  - ALL_NAN (critical) - 全空值欄位
  - CONSTANT (warning) - 常數欄位
  - HIGH_CARDINALITY_ID (warning) - 高基數 ID 欄位
  - HIGH_MISSING (warning) - 高缺失率 (>30%)
  - SKEWED (info) - 偏態分布
  - OUTLIERS (info) - 極端異常值
- **Transform 建議：** log, log1p, zscore 自動建議
- **分析準備度評估：** ready / needs_review / not_ready
- 新增 `/direct/quality-check` API 端點
- 整合到 `/direct/quick-stats` 回應

#### EDA Edge Case Testing
- `stats-worker/tests/test_eda_edge_cases.py` - 40 個邊界案例測試
- 覆蓋：空 DataFrame、單列/單欄、全空值、常數欄位、極端分布等

### Fixed
- numpy int64/float64 序列化問題
- boolean 欄位在數值分析中的處理

## [1.4.0] - 2025-12-16

### Added

#### MCP Project Management Tools (New)
- `create_project_workspace` - 建立研究專案目錄結構（支援 default, medical_study, ml_project 模板）
- `list_project_workspaces` - 列出 /data/projects/ 下的所有專案
- `list_user_visualizations` - 列出 MinIO 中的視覺化圖片（PNG, SVG）
- `generate_analysis_report` - 從分析結果生成 Markdown 報告

#### E2E Testing Framework
- E2E 測試全數通過：43 passed, 40 skipped, 0 failed
- 覆蓋率測試：84% overall (unit tests: tool_logic, dataflow, service)
- 修復 httpx AsyncClient fixture 問題
- 修復 Power Analysis API 回應格式

#### MCP Data Analysis Skills (New)
- `.claude/skills/data-analysis-workflow/` - 資料探索分析流程 (EDA, Table One, 相關性)
- `.claude/skills/ml-training-workflow/` - ML 模型訓練流程 (AutoML, 預測)
- `.claude/skills/statistical-analysis-workflow/` - 進階統計分析 (存活、PSM、ROC、Power)
- `.claude/skills/data-cleaning-workflow/` - 資料清理前處理 (缺失值、編碼、篩選)
- `.claude/skills/result-delivery-workflow/` - 結果交付與專案管理 (下載報告、MinIO API)
- `.claude/skills/mcp-tools-reference/` - MCP 工具速查參考 (98+ 工具完整分類)

#### Workflow Skills (New)
- `.claude/skills/master-workflow/` - 工作流導航中心
- `.claude/skills/session-start/` - 工作階段開始（恢復上下文）
- `.claude/skills/session-end/` - 工作階段結束（保存狀態）
- `.claude/skills/task-workflow/` - 單一任務執行流程
- `.claude/skills/debug-workflow/` - 系統化除錯流程
- `.claude/skills/feature-delivery/` - 功能完整交付
- `.claude/skills/project-audit/` - 專案全面審計

#### Project Governance - New Bylaws
- `.github/bylaws/file-paths.md` - 檔案路徑規範子法
  - Host vs Container 路徑區分
  - 測試檔案放置規則
  - MCP 工具路徑驗證
  - 範例資料集清單
- `.github/bylaws/docker-operations.md` - Docker 操作規範子法
  - 服務架構圖
  - 啟動/停止/擴展命令
  - MinIO/Redis 操作指南
  - 日誌與除錯方法
  - 常見問題排查

#### CONSTITUTION.md 新增條款
- 第 7.4 條：檔案路徑原則
- 第 7.5 條：Docker 服務原則

#### Comprehensive Testing Framework
- Static analysis with `ruff`: Fixed 7 bugs (B006, E722, F841) + 659 formatting issues
- `automl-mcp-server/tests/unit/test_error_scenarios_isolated.py` - 36 error scenario tests
- `automl-mcp-server/tests/unit/test_service_mock_isolated.py` - 29 service mock tests
- `tests/test_e2e.py` & `tests/test_e2e_full.py` - E2E tests (12 passed, 1 skipped)
- Total: 421 isolated unit tests passing

### Changed
- Removed `scikit-learn` dependency from E2E tests (use local CSV files)
- E2E tests now use remote MinIO (configurable via `.env`)
- Fixed API formats: `x-user-id` headers, trailing slashes

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
