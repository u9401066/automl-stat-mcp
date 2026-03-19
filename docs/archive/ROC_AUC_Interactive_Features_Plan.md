# ROC/AUC 分析互動功能規劃

## 📊 Phase 5 現有功能總結

### 已實現功能
| 功能 | MCP Tool | 說明 |
|------|----------|------|
| ROC 曲線計算 | `compute_roc_curve` | AUC + DeLong CI + 最佳閾值 |
| 模型比較 | `compare_roc_curves` | DeLong 檢定比較兩個 AUC |
| 閾值選擇 | `find_optimal_threshold` | Youden, F1, 成本基礎等方法 |
| 校準分析 | `analyze_calibration` | Brier Score, H-L Test, ECE |
| 完整評估 | `full_classifier_evaluation` | 整合所有分析 |

---

## 🚀 建議新增的互動功能

### 1. 批量模型比較 (Multi-Model Comparison)

**功能描述**: 同時比較 3+ 個模型，生成完整的排名和兩兩比較矩陣

```python
# 建議 API
compare_multiple_models(
    y_true,
    models: Dict[str, np.ndarray],  # {"Model A": scores_a, "Model B": scores_b, ...}
    correction: str = "bonferroni",  # 多重比較校正
) -> Dict
```

**輸出**:
- 模型排名表 (按 AUC 排序)
- 兩兩比較 p-value 矩陣
- 多重比較校正後的顯著性
- 最佳模型推薦

---

### 2. 交互式閾值調整 (Interactive Threshold Tuning)

**功能描述**: 提供不同閾值下的完整指標，支援臨床決策

```python
# 建議 API
threshold_analysis(
    y_true,
    y_score,
    thresholds: List[float] = None,  # 自訂閾值列表
    target_metric: str = "sensitivity",  # 要優化的指標
    target_value: float = 0.90,  # 目標值
) -> Dict
```

**輸出**:
- 各閾值下的 Sens, Spec, PPV, NPV, F1, Accuracy
- 達到目標指標所需的閾值
- 閾值變化對其他指標的影響

**臨床應用場景**:
- 篩檢測試：「我需要至少 95% 靈敏度，對應的閾值和特異度是多少？」
- 確診測試：「我需要至少 95% 特異度，對應的閾值是多少？」

---

### 3. 亞組分析 (Subgroup Analysis)

**功能描述**: 分析模型在不同亞組中的表現

```python
# 建議 API
subgroup_roc_analysis(
    y_true,
    y_score,
    subgroup_col,  # 分組變數 (如性別、年齡組)
    compare_subgroups: bool = True,
) -> Dict
```

**輸出**:
- 各亞組的 AUC 和 CI
- 亞組間 AUC 差異檢定
- 各亞組的最佳閾值
- 偏差警告 (如某亞組表現顯著較差)

---

### 4. 時間序列 ROC 分析 (Time-Dependent ROC)

**功能描述**: 用於存活分析中的時間相依 ROC

```python
# 建議 API
time_dependent_roc(
    time,  # 存活時間
    event,  # 事件狀態
    marker,  # 預測標記值
    predict_times: List[float],  # 預測時間點 [1, 3, 5 年]
    method: str = "nearest_neighbor",  # 或 "recursive"
) -> Dict
```

**輸出**:
- 各時間點的 AUC
- 時間相依 ROC 曲線
- 動態預測能力評估

---

### 5. 決策曲線分析增強 (Decision Curve Analysis)

**功能描述**: 完整的決策曲線分析，支援臨床實用性評估

```python
# 建議 API
decision_curve_analysis(
    y_true,
    models: Dict[str, np.ndarray],
    thresholds: np.ndarray = np.arange(0, 1, 0.01),
    harm_to_benefit_ratio: float = None,
) -> Dict
```

**輸出**:
- Net Benefit 曲線 (模型 vs Treat All vs Treat None)
- 臨床有用閾值範圍
- 在特定閾值下的 Net Benefit 比較
- 最佳決策策略建議

---

### 6. 置信帶 ROC 曲線 (ROC with Confidence Bands)

**功能描述**: 計算 ROC 曲線的置信帶

```python
# 建議 API
roc_with_confidence_bands(
    y_true,
    y_score,
    method: str = "bootstrap",  # 或 "simultaneous"
    n_bootstrap: int = 1000,
    confidence_level: float = 0.95,
) -> Dict
```

**輸出**:
- ROC 曲線點
- 各點的置信區間 (TPR 和 FPR)
- 用於繪圖的數據

---

### 7. 重新校準 (Recalibration)

**功能描述**: 當模型校準不佳時，提供重新校準功能

```python
# 建議 API
recalibrate_model(
    y_true,
    y_score,
    method: str = "platt",  # "platt", "isotonic", "beta"
    cv_folds: int = 5,  # 交叉驗證
) -> Dict
```

**輸出**:
- 校準前後的 Brier Score 比較
- 校準參數 (如 Platt scaling 的 A, B)
- 校準後的預測概率
- 校準曲線比較圖數據

---

### 8. 外部驗證報告 (External Validation Report)

**功能描述**: 模型外部驗證的完整報告

```python
# 建議 API
external_validation_report(
    y_true_dev,  # 開發集
    y_score_dev,
    y_true_val,  # 驗證集
    y_score_val,
) -> Dict
```

**輸出**:
- 開發集 vs 驗證集的 AUC 比較
- 校準漂移評估
- 表現下降的警告
- 是否需要更新模型的建議

---

### 9. 發表品質報告生成 (Publication-Ready Report)

**功能描述**: 生成符合期刊要求的標準化報告

```python
# 建議 API
generate_publication_report(
    y_true,
    y_score,
    model_name: str,
    outcome_name: str,
    include_forest_plot: bool = False,
) -> Dict
```

**輸出**:
```
Results:
The [model_name] achieved an AUC of 0.85 (95% CI: 0.82-0.88) for
predicting [outcome_name]. Using Youden's J statistic, the optimal
cut-off was 0.45, yielding a sensitivity of 0.82 (95% CI: 0.78-0.86)
and specificity of 0.75 (95% CI: 0.71-0.79). The positive predictive
value was 0.68 and negative predictive value was 0.86. The model
showed good calibration (Hosmer-Lemeshow p=0.34, Brier score=0.15).
```

---

### 10. 閾值敏感度分析 (Threshold Sensitivity Analysis)

**功能描述**: 分析結果對閾值選擇的穩健性

```python
# 建議 API
threshold_sensitivity_analysis(
    y_true,
    y_score,
    threshold_range: Tuple[float, float] = (0.3, 0.7),
    step: float = 0.05,
) -> Dict
```

**輸出**:
- 各閾值下的 NNS (Number Needed to Screen)
- 各閾值下的 NND (Number Needed to Diagnose)
- 錯誤分類的成本分析
- 穩健閾值範圍建議

---

## 🎨 視覺化功能規劃

### 建議新增的圖表類型

| 圖表 | 用途 | 輸出格式 |
|------|------|----------|
| ROC 曲線 (含 CI 帶) | 模型鑑別力展示 | Plotly/Matplotlib JSON |
| 校準曲線 | 預測概率準確性 | Plotly/Matplotlib JSON |
| 決策曲線 | 臨床實用性 | Plotly/Matplotlib JSON |
| 閾值-指標曲線 | 閾值選擇輔助 | Plotly/Matplotlib JSON |
| 混淆矩陣熱圖 | 分類結果展示 | Plotly/Matplotlib JSON |
| 多模型比較森林圖 | AUC 比較 | Plotly/Matplotlib JSON |

---

## 📋 實施優先級

### Phase 5A (高優先級 - 臨床常用)
1. ✅ 批量模型比較
2. ✅ 交互式閾值調整
3. ✅ 發表品質報告生成

### Phase 5B (中優先級 - 進階分析)
4. 亞組分析
5. 重新校準
6. 決策曲線分析增強

### Phase 5C (低優先級 - 專業需求)
7. 時間序列 ROC
8. 外部驗證報告
9. 閾值敏感度分析
10. 置信帶 ROC

---

## 💻 MCP 工具整合建議

### 新增 MCP Tools

```python
# 高優先級
async def compare_multiple_roc_curves(...)  # 多模型比較
async def interactive_threshold_analysis(...)  # 交互式閾值
async def generate_roc_report(...)  # 發表報告

# 中優先級
async def subgroup_roc_analysis(...)  # 亞組分析
async def recalibrate_predictions(...)  # 重新校準
async def decision_curve_analysis(...)  # 決策曲線

# 低優先級
async def time_dependent_roc(...)  # 時間相依 ROC
async def external_validation(...)  # 外部驗證
```

---

## 📊 預期效益

### 臨床研究者
- 一鍵生成發表品質的統計報告
- 快速比較多個預測模型
- 根據臨床需求選擇最佳閾值

### 資料科學家
- 完整的模型評估 pipeline
- 自動化的模型選擇建議
- 可重現的分析結果

### 醫院 AI 部署
- 外部驗證的標準化流程
- 模型漂移監控
- 決策支援系統的閾值優化

---

## 🔧 技術實現要點

### 數值穩定性
- 處理極端預測值 (0 或 1)
- 小樣本情況的 CI 估計
- 類別不平衡的處理

### 效能優化
- Bootstrap 的並行計算
- 大數據集的記憶體管理
- 快取常用計算結果

### 互操作性
- 支援 pandas DataFrame 輸入
- 與 scikit-learn 兼容
- JSON 序列化輸出
