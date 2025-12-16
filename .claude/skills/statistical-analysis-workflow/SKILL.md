---
name: statistical-analysis-workflow
description: Advanced statistical analysis including survival analysis (Kaplan-Meier, Cox), propensity score matching (PSM), ROC curve analysis, and power/sample size calculations. Use when doing clinical research analysis, comparing treatment effects, evaluating diagnostic tests, or planning study sample sizes. Triggers: 統計分析, 存活分析, 傾向分數, ROC, power analysis, Kaplan-Meier, Cox, survival, PSM, 配對, AUC, sensitivity, specificity, 敏感度, 特異度, sample size, 樣本數.
---

# Statistical Analysis Workflow 技能 (進階統計分析流程)

## 描述
使用 MCP 工具進行進階統計分析，包含存活分析、傾向分數、ROC 分析、檢定力分析。

## 觸發條件
- 「存活分析」「survival analysis」「KM 曲線」
- 「傾向分數」「PSM」「propensity」
- 「ROC」「AUC」「閾值分析」
- 「power analysis」「樣本數計算」

---

## 🎯 進階統計分析類型

```
┌─────────────────────────────────────────────────────────────────────┐
│                Advanced Statistical Analysis                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   [A] 存活分析        →  Kaplan-Meier, Cox Regression               │
│   [B] 傾向分數分析    →  PSM, IPTW, ATT/ATE                         │
│   [C] ROC/分類評估    →  ROC, DeLong Test, Calibration              │
│   [D] 檢定力分析      →  Sample Size, Power Calculation              │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📋 [A] 存活分析 (Survival Analysis)

### A.1 Kaplan-Meier 曲線

```python
mcp_automl_kaplan_meier_survival(
    csv_path="/data/sample_data/rossi_recidivism.csv",
    time_column="week",           # 時間欄位
    event_column="arrest",        # 事件欄位 (1=事件發生)
    group_column="fin"            # 可選：分組欄位
)
```

**輸出包含：**
- 存活曲線數據
- 中位存活時間
- 各時間點存活率

### A.2 存活曲線比較 (Log-rank test)

```python
mcp_automl_compare_survival(
    csv_path="/data/sample_data/rossi_recidivism.csv",
    time_column="week",
    event_column="arrest",
    group_column="fin"
)
```

**輸出包含：**
- Log-rank test p-value
- 各組中位存活時間
- 風險比 (Hazard Ratio)

### A.3 Cox 比例風險迴歸

```python
mcp_automl_cox_proportional_hazards(
    csv_path="/data/sample_data/rossi_recidivism.csv",
    time_column="week",
    event_column="arrest",
    covariates=["fin", "age", "race", "mar", "prio"]
)
```

**輸出包含：**
- 各變數 HR (Hazard Ratio)
- 95% CI
- p-value
- Concordance Index (C-index)

### A.4 存活資料摘要

```python
mcp_automl_survival_data_summary(
    csv_path="/data/sample_data/stanford_heart.csv",
    time_column="time",
    event_column="status"
)
```

---

## 📋 [B] 傾向分數分析 (Propensity Score)

### B.1 估計傾向分數

```python
mcp_automl_estimate_propensity_scores(
    csv_path="/data/sample_data/medical_study_200.csv",
    treatment_column="treatment",       # 治療組欄位
    covariates=["age", "gender", "bmi", "comorbidity"]
)
```

### B.2 傾向分數配對 (PSM)

```python
mcp_automl_match_propensity_scores(
    csv_path="/data/sample_data/medical_study_200.csv",
    treatment_column="treatment",
    covariates=["age", "gender", "bmi"],
    method="nearest",     # nearest, caliper
    caliper=0.2           # 可選
)
```

### B.3 治療效果估計 (IPTW)

```python
mcp_automl_estimate_treatment_effect(
    csv_path="/data/sample_data/medical_study_200.csv",
    treatment_column="treatment",
    outcome_column="outcome",
    covariates=["age", "gender", "bmi"],
    method="iptw"   # iptw, matching
)
```

**輸出包含：**
- ATE (Average Treatment Effect)
- ATT (Average Treatment Effect on Treated)
- 95% CI
- p-value

### B.4 共變數平衡評估

```python
mcp_automl_assess_covariate_balance(
    csv_path="/data/sample_data/medical_study_200.csv",
    treatment_column="treatment",
    covariates=["age", "gender", "bmi"],
    after_matching=True  # 配對後評估
)
```

**輸出包含：**
- 標準化差異 (Standardized Mean Difference)
- 配對前後比較

### B.5 完整傾向分數分析（一鍵）

```python
mcp_automl_run_propensity_analysis(
    csv_path="/data/sample_data/medical_study_200.csv",
    treatment_column="treatment",
    outcome_column="outcome",
    covariates=["age", "gender", "bmi", "comorbidity"]
)
```

---

## 📋 [C] ROC 分析 (ROC/AUC Analysis)

### C.1 計算 ROC 曲線

```python
mcp_automl_compute_roc_curve(
    csv_path="/data/sample_data/predictions.csv",
    y_true_column="actual",     # 真實值 (0/1)
    y_score_column="predicted"  # 預測機率
)
```

### C.2 比較兩個 ROC (DeLong Test)

```python
mcp_automl_compare_roc_curves(
    csv_path="/data/sample_data/model_comparison.csv",
    y_true_column="actual",
    y_score1_column="model_a_prob",
    y_score2_column="model_b_prob"
)
```

**輸出包含：**
- 兩個 AUC
- AUC 差異
- DeLong test p-value

### C.3 比較多個模型

```python
mcp_automl_compare_multiple_roc_curves(
    csv_path="/data/sample_data/multi_model.csv",
    y_true_column="actual",
    y_score_columns=["model_a", "model_b", "model_c"]
)
```

### C.4 找最佳閾值

```python
mcp_automl_find_optimal_threshold(
    csv_path="/data/sample_data/predictions.csv",
    y_true_column="actual",
    y_score_column="predicted",
    method="youden"   # youden, f1, cost
)
```

**輸出包含：**
- 最佳閾值
- 該閾值下的 Sensitivity, Specificity
- 混淆矩陣

### C.5 校準分析

```python
mcp_automl_analyze_calibration(
    csv_path="/data/sample_data/predictions.csv",
    y_true_column="actual",
    y_score_column="predicted"
)
```

### C.6 完整分類器評估

```python
mcp_automl_full_classifier_evaluation(
    csv_path="/data/sample_data/predictions.csv",
    y_true_column="actual",
    y_score_column="predicted"
)
```

---

## 📋 [D] 檢定力分析 (Power Analysis)

### D.1 T-test 樣本數計算

```python
mcp_automl_calculate_ttest_sample_size(
    effect_size=0.5,      # Cohen's d
    alpha=0.05,
    power=0.8,
    alternative="two-sided"
)
```

### D.2 T-test 檢定力計算

```python
mcp_automl_calculate_ttest_power(
    effect_size=0.5,
    n=50,                 # 每組樣本數
    alpha=0.05
)
```

### D.3 比例檢定樣本數

```python
mcp_automl_calculate_proportion_sample_size(
    p1=0.3,               # 組 1 比例
    p2=0.5,               # 組 2 比例
    alpha=0.05,
    power=0.8
)
```

### D.4 ANOVA 樣本數計算

```python
mcp_automl_calculate_anova_sample_size(
    effect_size=0.25,     # Cohen's f
    k_groups=3,           # 組數
    alpha=0.05,
    power=0.8
)
```

### D.5 卡方檢定樣本數

```python
mcp_automl_calculate_chisquare_sample_size(
    effect_size=0.3,      # Cohen's w
    df=2,                 # 自由度
    alpha=0.05,
    power=0.8
)
```

### D.6 存活分析樣本數

```python
mcp_automl_calculate_survival_sample_size(
    hazard_ratio=1.5,
    alpha=0.05,
    power=0.8,
    event_prob=0.3,       # 預期事件發生率
    dropout_rate=0.1
)
```

### D.7 從中位存活時間計算

```python
mcp_automl_calculate_survival_from_medians(
    median_control=12,    # 對照組中位存活（月）
    median_treatment=18,  # 實驗組中位存活（月）
    alpha=0.05,
    power=0.8
)
```

---

## 🎯 完整範例

### 範例 1：存活分析研究

```
User: "分析再犯資料 rossi_recidivism.csv 的存活曲線"

Agent 執行：

1. 預覽資料結構
   mcp_automl_direct_preview_data(
       csv_path="/data/sample_data/rossi_recidivism.csv"
   )

2. Kaplan-Meier 曲線
   mcp_automl_kaplan_meier_survival(
       csv_path="/data/sample_data/rossi_recidivism.csv",
       time_column="week",
       event_column="arrest",
       group_column="fin"
   )

3. 比較組間差異
   mcp_automl_compare_survival(
       csv_path="/data/sample_data/rossi_recidivism.csv",
       time_column="week",
       event_column="arrest",
       group_column="fin"
   )

4. Cox 迴歸
   mcp_automl_cox_proportional_hazards(
       csv_path="/data/sample_data/rossi_recidivism.csv",
       time_column="week",
       event_column="arrest",
       covariates=["fin", "age", "prio"]
   )

回報使用者：
"📊 存活分析結果：

KM 曲線分析：
- 有經濟援助組 (fin=1): 中位存活 > 52 週
- 無經濟援助組 (fin=0): 中位存活 = 32 週
- Log-rank test p = 0.012

Cox 迴歸結果：
| 變數 | HR | 95% CI | p-value |
|------|-----|--------|---------|
| fin | 0.68 | (0.50-0.92) | 0.012 |
| age | 0.96 | (0.94-0.98) | 0.001 |

結論：經濟援助顯著降低再犯風險 (HR=0.68, p=0.012)"
```

### 範例 2：傾向分數配對

```
User: "用 PSM 分析治療效果"

Agent 執行：

1. 估計傾向分數
   mcp_automl_estimate_propensity_scores(...)

2. 進行配對
   mcp_automl_match_propensity_scores(
       method="nearest",
       caliper=0.2
   )

3. 評估平衡
   mcp_automl_assess_covariate_balance(after_matching=True)

4. 估計效果
   mcp_automl_estimate_treatment_effect(method="iptw")

回報使用者：
"📊 傾向分數分析結果：

配對結果：
- 配對前樣本：200
- 配對後樣本：150 (75 對)

共變數平衡 (SMD)：
| 變數 | 配對前 | 配對後 |
|------|--------|--------|
| age | 0.35 | 0.05 |
| bmi | 0.42 | 0.08 |

治療效果：
- ATE = 0.15 (95% CI: 0.05-0.25)
- p-value = 0.003

結論：治療有顯著效果"
```

---

## 📊 適用資料集

| 分析類型 | 推薦資料集 |
|----------|------------|
| 存活分析 | rossi_recidivism.csv, stanford_heart.csv |
| 傾向分數 | medical_study_200.csv |
| ROC 分析 | 需要有預測機率的資料 |
| 檢定力分析 | 不需要資料，只需參數 |

---

## ⚠️ 注意事項

### 存活分析
- 時間欄位必須是數值
- 事件欄位必須是 0/1

### 傾向分數
- 治療欄位必須是 0/1
- 共變數需要是治療前的變數

### ROC 分析
- 需要真實標籤和預測機率
- 預測值應該在 0-1 之間

### 檢定力分析
- 效果量需要根據文獻或預試驗估計
- alpha 通常設為 0.05
- power 通常設為 0.8
