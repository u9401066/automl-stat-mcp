# AutoML MCP System - Roadmap

> Last Updated: 2025-12-09

## 🎯 Vision

建立一個完整的 AI Agent 可存取的自動化機器學習與統計分析平台，讓使用者透過自然語言即可完成從資料分析到模型部署的完整流程。

---

## 📊 Current Status (v1.2)

### ✅ 已完成功能

| 模組 | 功能 | 工具數 | 測試 |
|------|------|--------|------|
| **AutoML Core** | 資料集管理、模型訓練、預測 | 23 | ✅ |
| **Statistics Core** | EDA、TableOne、智能分析 | 12 | ✅ |
| **Smart Workflow** | 引導式分析流程 | 3 | ✅ |
| **Upload Tools** | 檔案上傳 (Volume/MinIO) + 欄位自動清理 | 3 | ✅ |
| **Data Cleaning** | 資料清理工具 | 9 | ✅ |
| **Phase 1** | 增強統計分析 (相關性、分布、VIF) | 4 | ✅ |
| **Phase 2** | TableOne 生成器 | 3 | ✅ |
| **Phase 3** | 存活分析 (Kaplan-Meier, Cox) | 4 | ✅ |
| **Phase 4** | 傾向性分數分析 (PSM, IPTW) | 5 | ✅ |
| **Phase 5** | ROC/AUC 分析 (DeLong, 校準) | 7 | ✅ |
| **Phase 5+** | ROC 增強 (多模型比較、閾值分析、發表報告) | - | ✅ |
| **Phase 6** | Power Analysis (T-test, Proportion, ANOVA, Chi-square, Survival) | 19 | ✅ |
| **DDD Refactoring** | 代碼重構 (statistics_tools, power_analysis, roc_analysis, advanced_analysis) | - | ✅ |

**總計: 98+ MCP 工具 (26 AutoML + 3 Upload + 9 Cleaning + 57 Stats + 3 Workflow)**

### 🆕 2025-12-09 更新
- **Data Cleaning Tools 完成 (Phase 7)**
  - `convert_to_binary` - 轉換欄位為 0/1（傾向分數分析必需）✅
  - `encode_categorical` - 類別編碼 (Label/OneHot) ✅
  - `handle_missing_values` - 缺失值處理 ✅
  - `remove_columns` - 移除欄位 ✅
  - `filter_rows` - 篩選資料列 ✅
  - `rename_columns` - 重新命名欄位 ✅
  - `get_column_info` - 取得欄位資訊 ✅
  - `auto_clean` - 自動清理 (新) ✅
  - Stats Service 9 個 API endpoints 實作完成
- **Worker 結果優化**
  - Propensity score 結果改為統計摘要（不再儲存完整分數陣列）
  - 新增 JSON sanitization 處理 NaN/Infinity 值
  - 減少 MinIO 存儲空間使用
- **上傳功能增強**
  - 欄位名稱自動清理（Excel 特殊符號處理）
  - Metadata JSON 生成（原始↔清理後欄位對照）
  - 預覽截斷（2 rows, 10 columns）

### 🆕 2025-12-08 更新
- **Phase 6 完成: MCP 統計工具修復**
  - 修復 23 個損壞的 `stats_worker_tasks` imports
  - Power Analysis (17 工具) → stats_client API 呼叫
  - EDA Tools (6 工具) → 本地 pandas/scipy fallback
  - stats-service power.py → 實際 statsmodels 計算
  - 加入 scipy 到 MCP 容器
- MCP 檔案上傳架構重構 (Volume Mount + 雙儲存模式)
- stats-worker dataset_id bug 修復
- TableOne tuple key 序列化修復

---

## 🗺️ Roadmap

### ✅ Phase 7: Data Cleaning Service (完成)

> 設計文件: [docs/design-issues/001-data-cleaning-workflow.md](design-issues/001-data-cleaning-workflow.md)

| 功能 | 描述 | 狀態 |
|------|------|------|
| Stats Service 擴充 | 新增 9 個 cleaning routes | ✅ |
| MCP Tools 更新 | 呼叫 Stats Service API | ✅ |
| Binary 轉換 | 支援傾向分數分析 | ✅ |
| 自動清理 | 一鍵處理常見問題 | ✅ |
| Worker 優化 | 結果存統計摘要，不存原始陣列 | ✅ |

### 🆕 Phase 8: Visualization Service (計畫中)

> 設計文件: [docs/design-issues/003-visualization-service.md](design-issues/003-visualization-service.md)

**目標**: 分析完成時自動生成出版品質圖表，返回 MinIO 圖片 URL

**🚀 使用現成套件加速開發** (無 sklearn 依賴): 
- lifelines (存活曲線內建)
- statannotations (p-value 標註)  
- matplotlib (ROC/PR 用現有數據畫)
- shap (特徵解釋)

| 子階段 | 功能 | 使用套件 | 工作量 |
|--------|------|----------|--------|
| **8A: 基礎設施** | MinIO 存儲, 風格設定 | matplotlib | 1.5d |
| **8B: 存活分析** | KM 曲線, Cox 森林圖 | lifelines 內建 | 1d |
| **8C: ROC/PR** | ROC, PR, 混淆矩陣 | matplotlib + 現有數據 | 1d |
| **8D: 組間比較** | 箱形圖/直條圖 + p-value | statannotations | 1d |
| **8E: AutoML** | SHAP, 校準曲線 | shap | 1.5d |
| **8F: 整合測試** | E2E 測試, 文檔 | - | 1d |

**總計**: ~7 天 (原 16 天，節省 56%)

**預期產出**:
- 12+ 種圖表類型
- 300dpi 出版品質 PNG
- 返回結果包含 `visualizations` 陣列 (多圖片 URL)

---

### Q1 2026 - 進階分析能力

#### Phase 5B ROC 進階
| 功能 | 描述 |
|------|------|
| 亞組分析 | 不同群體的模型表現 |
| 模型重新校準 | Platt scaling, Isotonic |
| 決策曲線分析 | Net Benefit, 臨床實用性 |

#### Phase 9: Meta-Analysis
| 功能 | 描述 |
|------|------|
| 固定效應模型 | Mantel-Haenszel |
| 隨機效應模型 | DerSimonian-Laird |
| 森林圖生成 | 標準化視覺呈現 |
| 發表偏倚 | Funnel plot, Egger's test |

### Q2 2026 - 專業統計與 AI 強化

#### Phase 5C ROC 專業
| 功能 | 描述 |
|------|------|
| 時間相依 ROC | 存活分析預測評估 |
| 外部驗證 | 多中心驗證報告 |
| 置信帶 ROC | Bootstrap 信賴區間 |

#### Phase 8: Bayesian Statistics
| 功能 | 描述 |
|------|------|
| Bayesian 推論 | 先驗/後驗分布 |
| MCMC 採樣 | PyMC3/Stan 整合 |
| Bayes Factor | 假設比較 |
| 視覺化 | 後驗分布圖 |

---

## 🔧 技術債與改進

### Design Issues 待決策
| Issue | 描述 | 狀態 |
|-------|------|------|
| #001 | Data Cleaning Workflow | ✅ Done |
| #003 | Visualization Service (圖表生成) | 🟡 Planned |
| - | PII 處理策略 (整欄 vs 內嵌) | 待討論 |
| - | 缺失值預設處理方式 | 待討論 |

### 基礎設施改進
- [ ] 監控儀表板 (Grafana)
- [ ] 日誌集中化 (ELK/Loki)
- [ ] 模型版本控制 (MLflow 整合)
- [ ] CI/CD 自動化測試

---

## 📈 MCP 工具演進

```
v1.1 (Current) ✅
├── AutoML Tools (23)
│   ├── Dataset: register, list, delete, analyze
│   ├── Training: automl, specific, compare, wait
│   ├── Models: list, leaderboard, predict, delete
│   └── Smart: quick_train, train_and_wait, summary
├── Stats Tools (57)
│   ├── Core: EDA, TableOne, AutoAnalyze, Direct (12)
│   ├── Phase 1-2: Enhanced Stats, TableOne Generator (7)
│   ├── Phase 3-4: Survival, Propensity Score (9)
│   ├── Phase 5/5+: ROC/AUC Analysis (10)
│   └── Phase 6: Power Analysis (19)
└── Workflow Tools (3)
    ├── start_data_analysis
    ├── execute_analysis_ticket
    └── check_analysis_progress

v1.2 (Phase 8 - Visualization) 🟡 Planned
├── 既有工具增強
│   ├── ROC 分析 → +ROC/PR 曲線圖
│   ├── Survival 分析 → +KM 曲線圖
│   ├── Cox 回歸 → +森林圖
│   └── 組間比較 → +直條圖/箱形圖 + p-value
├── AutoML 增強
│   ├── Leaderboard → +模型比較圖
│   └── 新增 explain_model → SHAP 圖
└── 返回格式
    └── 新增 visualizations[] (多圖片 URL)

v2.0 (Planned - Q1/Q2 2026)
├── Meta-Analysis (5)
│   ├── fixed_effects_meta
│   ├── random_effects_meta
│   ├── forest_plot
│   ├── funnel_plot
│   └── publication_bias
└── Bayesian (4)
    ├── bayesian_inference
    ├── mcmc_sampling
    ├── bayes_factor
    └── posterior_visualization
```

---

## 🎯 Success Metrics

| Metric | v1.0 | v1.1 (Current) | Target v2.0 |
|--------|------|----------------|-------------|
| MCP Tools | 38 | 82 ✅ | 100+ |
| Test Coverage | 188 | 297 ✅ | 400+ |
| Supported Analyses | 15+ | 35+ ✅ | 50+ |
| Max File Lines | 3407 | 1258 ✅ | <1000 |

---

## 📚 相關文件

- [README.md](../README.md) - 快速入門
- [Deployment Guide](deployment-guide.md) - 部署教學
- [ROC/AUC Features Plan](ROC_AUC_Interactive_Features_Plan.md) - Phase 5+ 詳細規劃
- [Design Issue #001](design-issues/001-data-cleaning-workflow.md) - 資料清理流程設計
