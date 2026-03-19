# AutoML MCP System - Roadmap

> Last Updated: 2026-01-27

## 🎯 Vision

建立完整的 AI Agent 可存取的自動化機器學習與統計分析平台，讓使用者透過自然語言即可完成從資料分析到模型部署的完整流程。

---

## 📊 Current Status (v1.8-dev)

### ✅ 已完成功能

| 模組 | 功能 | 工具數 | 狀態 |
|------|------|--------|------|
| **MCP Progress** | SSE 即時進度通知 | - | ✅ NEW |
| **Test Suite** | 720 tests, 0 failures | - | ✅ NEW |
| **Docker Infra** | STORAGE_MODE local-first, 全服務健康 | - | ✅ NEW |
| **DDD Refactor** | automl-service 完整 DDD 架構 | - | ✅ NEW |
| **RedisManager** | 統一連線池 Singleton | - | ✅ NEW |
| **Quality Audit** | Ruff 0 報錯, MyPy 類型修正, uv 遷移 | - | ✅ |
| **Data Quality** | 品質偵測、轉換建議、準備度評估 | 2 | ✅ |
| **AI Framework** | Claude Skills, Constitution-Bylaw | 12 Skills | ✅ |
| **Project Mgmt** | 專案目錄、視覺化列表、報告產生 | 4 | ✅ |
| **AutoML Core** | 資料集管理、模型訓練、預測 | 26 | ✅ |
| **Statistics Core** | EDA、TableOne、智能分析 | 12 | ✅ |
| **Smart Workflow** | 引導式分析流程 | 3 | ✅ |
| **Upload Tools** | 檔案上傳 + 欄位清理 | 3 | ✅ |
| **Data Cleaning** | 資料清理工具 | 9 | ✅ |
| **Enhanced Stats** | 相關性、分布、VIF | 4 | ✅ |
| **TableOne** | 統計表格生成 | 3 | ✅ |
| **Survival** | Kaplan-Meier, Cox | 4 | ✅ |
| **Propensity** | PSM, IPTW | 5 | ✅ |
| **ROC/AUC** | DeLong, 校準, 閾值分析 | 10 | ✅ |
| **Power Analysis** | T-test, ANOVA, Chi-square, Survival | 19 | ✅ |
| **Visualization** | 出版品質圖表 | - | ✅ |
| **Result Persistence** | Redis + MinIO 儲存 | - | ✅ |

**總計: 104+ MCP 工具**

### 🆕 2026-01-27 更新

- **MCP Progress Notifications** (SSE 即時進度)
  - `wait_for_completion()` 透過 `ctx.report_progress()` 串流 worker 進度
  - `smart_analyze`, `analyze_medical_study` 分段進度回報
  - MCP SDK 1.25.0 `Context.report_progress(progress, total, message)`

- **完整測試套件** (720 tests, 0 failures)
  - MCP server: 446 passed, 1 skipped
  - Root tests: 274 passed, 33 skipped
  - 修復所有 flaky tests (httpx module binding 污染)

- **Docker Infrastructure 修復**
  - stats-worker STORAGE_MODE 支援
  - shared module Dockerfile COPY 修正
  - 全服務健康：automl-mcp, stats-service, stats-worker x2, redis

- **DDD 架構重構** (automl-service)
  - Domain models, Application use_cases, Infrastructure repositories

- **RedisManager Singleton** (共享連線池)
  - 從 4+ 獨立連線池 → 1 共享池，減少 50%+ 連線

### 🆕 2026-01-06 更新

- **全專案代碼品質審計完成**
  - **Ruff Clean**: 達成 `automl-service` 與 `stats-service` 路由層零報錯。
  - **MyPy Typing**: 修復 `cleaning.py`, `power.py`, `direct.py` 的深層類型推斷問題。
  - **uv 遷移**: 完成從 pip 到 `uv` 的環境管理遷移。

### 🆕 2025-12-17 更新

- **DataQualityAnalyzer 完成**
  - 統一品質分析模組
  - 6 種問題偵測：ALL_NAN, CONSTANT, HIGH_CARDINALITY_ID, HIGH_MISSING, SKEWED, OUTLIERS
  - Transform 建議：log, log1p, zscore
  - 分析準備度評估
  - 新增 `/direct/quality-check` 端點

- **測試框架強化**
  - 214 tests passed, 12 skipped
  - 25 個 DataQuality 專屬測試
  - 40 個 EDA 邊界案例測試

### 🆕 2025-12-16 更新

- **Project Management 完成**
  - `create_project_workspace` - 建立專案目錄結構
  - `list_project_workspaces` - 列出專案
  - `list_user_visualizations` - 查詢視覺化圖片
  - `generate_analysis_report` - 產生分析報告

- **E2E 測試完善**
  - 43 tests passed, 40 skipped
  - 84% 測試覆蓋率
  - 修復 httpx fixture 和 Power Analysis 回應格式

### 🆕 2025-12-12 更新

- **Result Persistence 完成**
  - 所有分析結果自動存到 Redis (7天) + MinIO (永久)
  - 返回 `result_id` 和 `result_path`
  - 支援 numpy 類型 JSON 序列化
  - 新增 `/storage/*` API endpoints

### 🆕 2025-12-09 更新

- **Phase 8: Visualization 完成**
  - ROC/PR 曲線、KM 曲線、森林圖
  - SHAP 解釋圖、特徵重要性
  - 組間比較圖 + p-value 標註
  - 本地結果管理 + HTML 報告

---

## 🗺️ Future Roadmap

### Q1 2026 - 進階分析

#### Phase 9: Meta-Analysis
| 功能 | 描述 |
|------|------|
| 固定效應模型 | Mantel-Haenszel |
| 隨機效應模型 | DerSimonian-Laird |
| 森林圖生成 | 標準化視覺呈現 |
| 發表偏倚 | Funnel plot, Egger's test |

#### Phase 10: Advanced ROC
| 功能 | 描述 |
|------|------|
| 亞組分析 | 不同群體的模型表現 |
| 模型重新校準 | Platt scaling, Isotonic |
| 決策曲線分析 | Net Benefit, 臨床實用性 |
| 時間相依 ROC | 存活分析預測評估 |

### Q2 2026 - 專業統計與 AI 強化

#### Phase 11: Bayesian Statistics
| 功能 | 描述 |
|------|------|
| Bayesian 推論 | 先驗/後驗分布 |
| MCMC 採樣 | PyMC3/Stan 整合 |
| Bayes Factor | 假設比較 |
| 視覺化 | 後驗分布圖 |

---

## 🔧 技術改進計畫

### Infrastructure
- [ ] 監控儀表板 (Grafana)
- [ ] 日誌集中化 (Loki)
- [x] CI/CD 自動化測試 ✅ 2025-12-16
- [ ] 模型版本控制 (MLflow)

### Code Quality
- [x] 更多 E2E 測試覆蓋 ✅ 149 passed (92%)
- [x] API 文檔自動生成 ✅ FastAPI Swagger
- [x] Performance benchmarks ✅ ~30ms avg

### Security
- [x] 路徑遍歷漏洞修復 ✅ 2025-12-16
- [x] 輸入驗證強化 ✅ Power Analysis validators
- [x] 安全測試套件 ✅ 24 tests

---

## 📈 MCP 工具演進

```
v1.3 ✅
├── AutoML Tools (26)
├── Stats Tools (57+)
├── Cleaning Tools (9)
├── Workflow Tools (3)
└── Total: 98+ tools

v1.5 (Current) 🚧 Tool Consolidation
├── Integrated Tools (4 NEW)
│   ├── smart_analyze (replaces 4 tools)
│   ├── analyze_medical_study (replaces 5 tools)
│   ├── compare_treatment_groups (simplified)
│   └── quick_preview (replaces 2 tools)
├── MCP Resources (6 NEW)
│   └── Static info without tool calls
├── REMOVED: Redundant tools (~48 tools)
└── Target: 50 tools total

v2.0 (Planned Q1/Q2 2026)
├── Meta-Analysis (5)
└── Bayesian Stats (4)
```

---

## 🎯 Success Metrics

| Metric | v1.0 | v1.3 | v1.5 (Current) | Target v2.0 |
|--------|------|------|----------------|-------------|
| MCP Tools | 38 | 98+ | **50** 🎯 | 55 |
| Tool Calls/Workflow | - | 4-6 | **1** | 1 |
| Test Coverage | 188 | 300+ | 300+ | 400+ |
| Analysis Types | 15 | 40+ | 40+ | 50+ |
| Result Persistence | ❌ | ✅ | ✅ | ✅ |

---

## 📚 相關文件

- [README.md](../README.md) - 快速入門
- [ARCHITECTURE.md](ARCHITECTURE.md) - 系統架構
- [MCP_TOOLS_INVENTORY.md](MCP_TOOLS_INVENTORY.md) - 工具清單
- [deployment-guide.md](deployment-guide.md) - 部署教學
