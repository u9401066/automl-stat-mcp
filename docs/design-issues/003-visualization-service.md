# Design Issue #003: Visualization Service - 圖表生成功能

**Status**: 🟡 Planned  
**Priority**: High  
**Created**: 2025-12-09  
**Category**: Visualization / ML Analysis / Statistical Reporting

---

## 📋 問題描述

目前 AutoML/AutoStat 系統**只返回數據（figure_data）**，但**不生成實際圖片**。用戶需要：
1. ML 分析完成時看到 ROC/AUC 曲線、PR 曲線、SHAP 等視覺化圖表
2. 統計分析完成時看到直條圖+p-value、生存曲線、森林圖等
3. 結果中包含**多張圖片的連結**，而非只有數據點

### 現狀分析

| 功能 | 現狀 | 缺口 |
|------|------|------|
| ROC 分析 | 返回 `figure_data` (座標點) | ❌ 不生成圖片 |
| Kaplan-Meier | 返回 `survival_curve` (座標點) | ❌ 不生成圖片 |
| Cox 回歸 | 返回 `hazard_ratio` (數值) | ❌ 無森林圖 |
| AutoML 比較 | 返回 `leaderboard` | ❌ 無比較圖 |
| TableOne | 返回表格數據 | ❌ 無視覺化 |
| Power Analysis | 返回計算結果 | ❌ 無 power curve |

### 目標輸出範例

分析完成後，返回的 JSON 應包含：
```json
{
  "status": "success",
  "results": { ... },
  "visualizations": [
    {
      "type": "roc_curve",
      "title": "ROC Curve (AUC = 0.85)",
      "url": "http://minio:9000/automl-results/user123/job456/roc_curve.png",
      "format": "png",
      "description": "Receiver Operating Characteristic curve with AUC and 95% CI"
    },
    {
      "type": "pr_curve", 
      "title": "Precision-Recall Curve",
      "url": "http://minio:9000/automl-results/user123/job456/pr_curve.png",
      "format": "png"
    },
    {
      "type": "shap_summary",
      "title": "SHAP Feature Importance",
      "url": "http://minio:9000/automl-results/user123/job456/shap_summary.png",
      "format": "png"
    }
  ]
}
```

---

## 🎯 需求分析

### AutoML 視覺化需求

| 分析類型 | 圖表 | 優先級 |
|---------|------|--------|
| **模型評估** | ROC 曲線 (AUC + 95% CI) | P0 |
| | PR 曲線 (PR-AUC) | P0 |
| | 混淆矩陣 | P1 |
| | 校準曲線 | P1 |
| **模型比較** | 多模型 ROC 疊加 | P0 |
| | 模型排行榜 (bar chart) | P1 |
| **特徵重要性** | SHAP Summary Plot | P0 |
| | SHAP Dependence Plot | P2 |
| | Feature Importance Bar | P1 |
| **預測分析** | 預測 vs 實際 (迴歸) | P1 |
| | 殘差圖 | P2 |

### AutoStat 視覺化需求

| 分析類型 | 圖表 | 優先級 |
|---------|------|--------|
| **組間比較** | 直條圖 + p-value 標註 | P0 |
| | 箱形圖 + 統計顯著性 | P0 |
| | 小提琴圖 | P2 |
| **存活分析** | Kaplan-Meier 生存曲線 | P0 |
| | Log-rank p-value | P0 |
| | 風險表 (Number at risk) | P1 |
| **Cox 回歸** | 森林圖 (HR + 95% CI) | P0 |
| | Hazard ratio table | P1 |
| **相關性分析** | 相關係數熱力圖 | P1 |
| | 散點圖矩陣 | P2 |
| **ROC 分析** | ROC 曲線 + 最佳閾值 | P0 |
| | DeLong 比較結果 | P1 |
| **Power Analysis** | Power vs Sample Size 曲線 | P2 |
| **Meta-Analysis** | 森林圖 (Forest plot) | P1 (future) |
| | 漏斗圖 (Funnel plot) | P1 (future) |

---

## 🛠️ 技術方案

### 🚀 發現：有現成的自動繪圖套件！

經調研，以下套件可以**大幅加速開發**（避免 sklearn 依賴）：

| 套件 | 功能 | 自動繪圖能力 | sklearn 依賴 |
|------|------|-------------|-------------|
| **lifelines** | 存活分析 | ✅ `KaplanMeierFitter.plot()`, `CoxPHFitter.plot()` 內建 | ❌ 無 |
| **statannotations** | 統計註解 | ✅ 自動在 seaborn 圖上加 p-value 星號/數值 | ❌ 無 |
| **pingouin** | 統計分析 | ✅ `pg.plot_paired()`, `pg.qqplot()` | ❌ 無 |
| **matplotlib** | 基礎繪圖 | ✅ 我們現有 ROC 數據，直接畫 | ❌ 無 |
| **seaborn** | 美化圖表 | ✅ heatmap, boxplot | ❌ 無 |

### ⚠️ 避免的套件（依賴 sklearn）

| 套件 | 問題 |
|------|------|
| ~~scikit-plot~~ | 依賴 sklearn |
| ~~yellowbrick~~ | 依賴 sklearn |
| ~~sklearn.metrics~~ | 就是 sklearn |

### ROC/PR 曲線：使用現有數據 + 純 matplotlib

我們的 `stats-worker/src/tasks/roc/` 已經用 **numpy + scipy** 實作完整 ROC 分析：
- `ROCAnalyzer` 計算 ROC 曲線座標
- `PrecisionRecallAnalyzer` 計算 PR 曲線座標
- `DeLongTest` 計算 AUC 比較

**只需加一個繪圖函數**：

```python
import matplotlib.pyplot as plt

def plot_roc_from_result(roc_result: ROCCurveResult, ax=None):
    """用現有 ROC 計算結果畫圖 - 純 matplotlib，無 sklearn"""
    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 6))
    
    # 從現有結果取座標
    fpr = [p.fpr for p in roc_result.curve_points]
    tpr = [p.tpr for p in roc_result.curve_points]
    
    ax.plot(fpr, tpr, lw=2, label=f'ROC (AUC = {roc_result.auc:.3f})')
    ax.plot([0, 1], [0, 1], 'k--', lw=1, label='Random')
    ax.fill_between(fpr, tpr, alpha=0.3)
    
    # 標記最佳閾值點
    ax.scatter([roc_result.optimal_threshold_fpr], 
               [roc_result.optimal_threshold_tpr], 
               marker='o', s=100, c='red', label='Optimal')
    
    ax.set_xlabel('False Positive Rate (1 - Specificity)')
    ax.set_ylabel('True Positive Rate (Sensitivity)')
    ax.set_title('Receiver Operating Characteristic')
    ax.legend(loc='lower right')
    
    return ax
```

### 各套件自動繪圖示例

#### 1. lifelines - 存活分析 (已有依賴，無 sklearn)
```python
from lifelines import KaplanMeierFitter, CoxPHFitter

# KM 曲線 - 一行搞定！
kmf = KaplanMeierFitter()
kmf.fit(durations, event_observed, label='Treatment')
ax = kmf.plot_survival_function()  # 自動出圖！

# Cox 森林圖 - 一行搞定！
cph = CoxPHFitter()
cph.fit(df, duration_col='T', event_col='E')
cph.plot()  # 自動出森林圖！
```

#### 2. statannotations - 直條圖 + p-value (無 sklearn)
```python
from statannotations.Annotator import Annotator
import seaborn as sns

ax = sns.boxplot(data=df, x='group', y='value')
annotator = Annotator(ax, pairs=[("A", "B"), ("A", "C")], data=df, x='group', y='value')
annotator.configure(test='Mann-Whitney', text_format='star')
annotator.apply_and_annotate()  # 自動計算 + 標註 p-value！
```

#### 3. 純 matplotlib - ROC/PR 曲線
```python
# 使用我們現有的 ROC 計算結果
from .tasks.roc.functions import compute_roc_curve

result = compute_roc_curve(y_true, y_scores)
fig, ax = plt.subplots()

# 畫 ROC 曲線
fpr = [p['fpr'] for p in result['curve_points']]
tpr = [p['tpr'] for p in result['curve_points']]
ax.plot(fpr, tpr, label=f"AUC = {result['auc']:.3f}")
```

#### 4. SHAP - 特徵重要性 (AutoML worker 專用)
```python
import shap
# SHAP 不依賴 sklearn，只依賴 numpy
explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X)
shap.summary_plot(shap_values, X)  # 自動出圖！
```

### 修訂後的技術選型

| 方案 | 優點 | sklearn 依賴 | 建議 |
|------|------|-------------|------|
| **A. lifelines 內建 plot** | 零開發成本 | ❌ 無 | ✅ 存活分析 |
| **B. matplotlib + 現有數據** | 完全控制 | ❌ 無 | ✅ ROC/PR |
| **C. statannotations** | 自動 p-value | ❌ 無 | ✅ 組間比較 |
| **D. seaborn** | 美觀 | ❌ 無 | ✅ 熱力圖等 |

### 需要新增的依賴

```python
# stats-worker/requirements.txt 新增
lifelines>=0.27.0        # 已有，確認版本
statannotations>=0.6.0   # 新增 - 自動 p-value 標註
matplotlib>=3.7.0        # 新增 - 基礎繪圖
seaborn>=0.12.0          # 新增 - 美觀圖表

# automl-worker/requirements.txt 新增  
matplotlib>=3.7.0
shap>=0.42.0             # SHAP 解釋圖 (不依賴 sklearn)
```

### 推薦架構

```
┌─────────────────────────────────────────────────────────┐
│                     MCP Server                          │
│   (返回 JSON + visualization URLs)                      │
└───────────────────────┬─────────────────────────────────┘
                        │ 呼叫
                        ▼
┌─────────────────────────────────────────────────────────┐
│              Stats/AutoML Worker                        │
│   ┌─────────────────────────────────────────────────┐   │
│   │          Visualization Module                   │   │
│   │   ├── matplotlib_plots.py (ROC, KM, Forest)   │   │
│   │   ├── seaborn_plots.py (heatmap, boxplot)     │   │
│   │   └── plot_utils.py (style, export)           │   │
│   └─────────────────────────────────────────────────┘   │
│                        │                                │
│                        ▼ 存檔                           │
│   ┌─────────────────────────────────────────────────┐   │
│   │              MinIO Storage                      │   │
│   │   automl-results/{user}/{job}/                  │   │
│   │   ├── roc_curve.png                             │   │
│   │   ├── pr_curve.png                              │   │
│   │   ├── shap_summary.png                          │   │
│   │   └── ...                                       │   │
│   └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### 依賴套件

```python
# stats-worker/requirements.txt & automl-worker/requirements.txt 新增
matplotlib>=3.7.0
seaborn>=0.12.0
shap>=0.42.0        # AutoML worker only (SHAP plots)
lifelines>=0.27.0   # Survival plots (KaplanMeierFitter.plot)
```

---

## 📅 開發計畫 - 分階段實施（使用現成套件加速）

### Phase 8A: 基礎設施 (Foundation) - 1.5 天 ⚡️ (原 3 天)

**目標**: 建立圖表存儲的基礎架構

| 任務 | 檔案 | 工作量 |
|------|------|--------|
| 更新 requirements.txt | 各 worker | 0.25d |
| 實作 MinIO 圖片上傳 util | `visualization/storage.py` | 0.5d |
| 定義標準圖表風格 | `visualization/style.py` | 0.25d |
| 建立圖表返回格式標準 | `visualization/schemas.py` | 0.25d |
| 基礎單元測試 | `tests/test_visualization.py` | 0.25d |

**Deliverable**: 
- `save_figure_to_minio(fig, job_id, filename)` → 返回 MinIO URL
- 統一的 matplotlib rcParams 設定

---

### Phase 8B: 存活分析圖表 (lifelines 內建) - 1 天 ⚡️ (原 2 天)

**使用 lifelines 內建繪圖功能！**

| 圖表 | 實作方式 | 程式碼 |
|------|---------|--------|
| KM 生存曲線 | `kmf.plot_survival_function()` | 5 行 |
| Cox 森林圖 | `cph.plot()` | 3 行 |
| 多組 KM 比較 | 迴圈 + `ax` 疊加 | 10 行 |

```python
# 範例：修改 kaplan_meier_analysis 函數
def kaplan_meier_analysis(..., generate_plot=True):
    kmf = KaplanMeierFitter()
    kmf.fit(...)
    
    if generate_plot:
        fig, ax = plt.subplots(figsize=(8, 6))
        kmf.plot_survival_function(ax=ax)
        plot_url = save_figure_to_minio(fig, job_id, 'km_curve.png')
    
    return {..., "visualizations": [{"type": "km_curve", "url": plot_url}]}
```

---

### Phase 8C: ROC/PR 曲線 (純 matplotlib) - 1 天 ⚡️ (原 2 天)

**使用現有 ROC 計算結果 + 純 matplotlib（無 sklearn）**

| 圖表 | 實作方式 | 程式碼 |
|------|---------|--------|
| ROC 曲線 | 現有 `ROCCurveResult` + matplotlib | 15 行 |
| PR 曲線 | 現有 `PrecisionRecallResult` + matplotlib | 15 行 |
| 多模型 ROC 比較 | 疊加多條曲線 | 20 行 |
| 混淆矩陣 | seaborn heatmap | 10 行 |

```python
# 範例：用現有 ROC 數據畫圖（無 sklearn）
from .tasks.roc.core import ROCAnalyzer

analyzer = ROCAnalyzer()
roc_result = analyzer.compute_roc(y_true, y_scores)

fig, ax = plt.subplots(figsize=(8, 6))
fpr = [p.fpr for p in roc_result.curve_points]
tpr = [p.tpr for p in roc_result.curve_points]

ax.plot(fpr, tpr, lw=2, label=f'AUC = {roc_result.auc:.3f} (95% CI: {roc_result.auc_ci_lower:.3f}-{roc_result.auc_ci_upper:.3f})')
ax.plot([0, 1], [0, 1], 'k--', alpha=0.5)
ax.fill_between(fpr, tpr, alpha=0.2)
ax.set_xlabel('1 - Specificity')
ax.set_ylabel('Sensitivity')
ax.legend(loc='lower right')

plot_url = save_figure_to_minio(fig, job_id, 'roc_curve.png')
```

---

### Phase 8D: 組間比較 (statannotations) - 1 天 ⚡️ (原 3 天)

**使用 statannotations 自動標註 p-value！**

| 圖表 | 實作方式 | 程式碼 |
|------|---------|--------|
| 箱形圖 + p-value | `Annotator` + seaborn | 15 行 |
| 直條圖 + p-value | `Annotator` + seaborn | 15 行 |
| 小提琴圖 + p-value | `Annotator` + seaborn | 15 行 |

```python
# 範例：自動加 p-value 的組間比較圖
import seaborn as sns
from statannotations.Annotator import Annotator

fig, ax = plt.subplots(figsize=(8, 6))
sns.boxplot(data=df, x=group_col, y=value_col, ax=ax)

pairs = [(groups[i], groups[j]) for i in range(len(groups)) for j in range(i+1, len(groups))]
annotator = Annotator(ax, pairs, data=df, x=group_col, y=value_col)
annotator.configure(test='Mann-Whitney', text_format='star', loc='outside')
annotator.apply_and_annotate()

plot_url = save_figure_to_minio(fig, job_id, 'comparison.png')
```

---

### Phase 8E: AutoML 圖表 (SHAP + sklearn) - 1.5 天

| 圖表 | 實作方式 | 程式碼 |
|------|---------|--------|
| SHAP Summary | `shap.summary_plot()` | 10 行 |
| SHAP Dependence | `shap.dependence_plot()` | 5 行 |
| Feature Importance | `shap.plots.bar()` | 5 行 |
| 校準曲線 | `CalibrationDisplay.from_predictions()` | 5 行 |

**新增 MCP 工具**: `explain_model`

---

### Phase 8F: 整合測試 - 1 天 (原 2 天)

| 任務 | 說明 |
|------|------|
| E2E 測試 | 驗證完整流程 |
| 更新文檔 | 說明新的 `visualizations` 返回格式 |

---

## 📊 開發時間比較

| 階段 | 原估計 | 使用現成套件 | 節省 |
|------|--------|-------------|------|
| 8A 基礎設施 | 3d | 1.5d | 50% |
| 8B 存活分析 | 2d | 1d | 50% |
| 8C ROC/PR | 2d | 1d | 50% |
| 8D 組間比較 | 3d | 1d | 67% |
| 8E AutoML | 4d | 1.5d | 63% |
| 8F 整合測試 | 2d | 1d | 50% |
| **總計** | **16d** | **7d** | **56%** |

---

## 📊 輸出規格

### 圖片規格

| 屬性 | 規格 |
|------|------|
| 格式 | PNG (預設), SVG (可選) |
| 解析度 | 300 DPI (出版品質) |
| 尺寸 | 8x6 inches (預設) |
| 字體 | Times New Roman 或 Helvetica |
| 檔案大小 | < 2MB (PNG), < 500KB (SVG) |

### 標準風格

```python
# visualization/style.py
PUBLICATION_STYLE = {
    'figure.figsize': (8, 6),
    'figure.dpi': 300,
    'font.family': 'serif',
    'font.serif': ['Times New Roman'],
    'font.size': 12,
    'axes.labelsize': 14,
    'axes.titlesize': 16,
    'legend.fontsize': 11,
    'lines.linewidth': 2,
    'axes.linewidth': 1.5,
    'axes.spines.top': False,
    'axes.spines.right': False,
}
```

### MinIO 存儲路徑

```
automl-results/
├── {user_id}/
│   ├── {job_id}/
│   │   ├── results.json          # 分析結果
│   │   ├── roc_curve.png         # ROC 曲線
│   │   ├── pr_curve.png          # PR 曲線
│   │   ├── km_curve.png          # 生存曲線
│   │   ├── forest_plot.png       # 森林圖
│   │   └── shap_summary.png      # SHAP 圖
│   └── {job_id}/
│       └── ...
```

---

## 🔗 相關文件

- [ROADMAP.md](../ROADMAP.md) - 開發路線圖
- [MCP_TOOLS_INVENTORY.md](../MCP_TOOLS_INVENTORY.md) - 工具清單
- [001-data-cleaning-workflow.md](001-data-cleaning-workflow.md) - 資料清理設計

---

## 📝 決策記錄

| 日期 | 決策 | 原因 |
|------|------|------|
| 2025-12-09 | 採用 Matplotlib + Seaborn | 出版品質、無需前端 |
| 2025-12-09 | 圖片存 MinIO | 統一存儲、可存取 URL |
| 2025-12-09 | 先 P0 圖表 | ROC/KM/森林圖 最常用 |

---

## ✅ 驗收標準

### Phase 8 完成標準

1. **ROC 分析** 返回 ROC + PR 曲線圖片 URL
2. **存活分析** 返回 KM 曲線圖片 URL
3. **Cox 回歸** 返回森林圖圖片 URL  
4. **組間比較** 返回直條圖/箱形圖 + p-value 標註
5. **AutoML 訓練** 返回模型比較圖 + SHAP 圖
6. 所有圖片為**出版品質** (300dpi)
7. AI Agent 可正確解析 `visualizations` 陣列並顯示圖片

---

## 📈 預期效果

| 指標 | 現狀 | Phase 8 後 |
|------|------|-----------|
| 圖表類型 | 0 | 12+ |
| 用戶理解度 | 低 (純數據) | 高 (視覺化) |
| 報告生成能力 | 無 | 可直接用於論文/報告 |
