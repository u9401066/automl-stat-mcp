# AutoML MCP System - Roadmap

> Last Updated: 2025-12-04

## 🎯 Vision

建立一個完整的 AI Agent 可存取的自動化機器學習與統計分析平台，讓使用者透過自然語言即可完成從資料分析到模型部署的完整流程。

---

## 📊 Current Status (v1.1)

### ✅ 已完成功能

| 模組 | 功能 | 工具數 | 測試 |
|------|------|--------|------|
| **AutoML Core** | 資料集管理、模型訓練、預測 | 23 | ✅ |
| **Statistics Core** | EDA、TableOne、智能分析 | 12 | ✅ |
| **Smart Workflow** | 引導式分析流程 | 3 | ✅ |
| **Phase 1** | 增強統計分析 (相關性、分布、VIF) | 4 | ✅ |
| **Phase 2** | TableOne 生成器 | 3 | ✅ |
| **Phase 3** | 存活分析 (Kaplan-Meier, Cox) | 4 | ✅ |
| **Phase 4** | 傾向性分數分析 (PSM, IPTW) | 5 | ✅ |
| **Phase 5** | ROC/AUC 分析 (DeLong, 校準) | 7 | ✅ |
| **Phase 5+** | ROC 增強 (多模型比較、閾值分析、發表報告) | - | ✅ |
| **Phase 6** | Power Analysis (T-test, Proportion, ANOVA, Chi-square, Survival) | 19 | ✅ |
| **DDD Refactoring** | 代碼重構 (statistics_tools, power_analysis, roc_analysis, advanced_analysis) | - | ✅ |

**總計: 82 MCP 工具 (26 AutoML + 56 Stats), 297 項測試通過**

---

## 🗺️ Roadmap

### Q1 2026 - 進階分析能力

#### Phase 5B ROC 進階
| 功能 | 描述 |
|------|------|
| 亞組分析 | 不同群體的模型表現 |
| 模型重新校準 | Platt scaling, Isotonic |
| 決策曲線分析 | Net Benefit, 臨床實用性 |

#### Phase 7: Meta-Analysis
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
| #001 | Data Cleaning Workflow | 🔴 Open |
| - | PII 處理策略 (整欄 vs 內嵌) | 待討論 |
| - | 缺失值預設處理方式 | 待討論 |
| - | 自動清理 vs 確認流程 | 待討論 |

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
