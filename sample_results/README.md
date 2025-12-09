# Sample Results

E2E 測試結果存放目錄

## 設計原則

**所有分析結果都歸屬於其來源資料集！**

即使是 Power Analysis 這種「純計算」工具，其參數（effect size, n, 比例等）
也是從特定資料集計算/估計而來，所以結果應該放在該資料集目錄下。

## 目錄結構

```
sample_results/
├── README.md
├── iris/                           # 資料集名稱
│   ├── _meta.json                  # 資料集元資訊
│   ├── eda/                        # EDA 分析
│   │   ├── correlations.json
│   │   ├── missing_values.json
│   │   └── distributions.json
│   ├── tableone/                   # Table 1
│   │   └── tableone.json
│   ├── power_analysis/             # Power Analysis (基於此資料集的參數)
│   │   ├── ttest_sample_size.json
│   │   └── ttest_power.json
│   └── ml/                         # ML 訓練結果
│       └── automl_result.json
├── titanic/
├── heart_disease/
├── breast_cancer/
├── medical_study/                  # 含 survival 分析
│   ├── survival/
│   │   ├── kaplan_meier.json
│   │   └── cox_regression.json
│   └── ...
└── test_summary.json               # 所有測試總結
```

## 每個測試結果都包含

```json
{
  "dataset": "iris",
  "dataset_file": "/sample_data/iris.csv",
  "test_type": "power_analysis/ttest",
  "input_params": { ... },
  "result": { ... },
  "timestamp": "2025-12-09T..."
}
```

## 測試日期

- 2025-12-09: 初始測試
