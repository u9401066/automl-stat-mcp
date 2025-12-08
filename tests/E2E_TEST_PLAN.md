# E2E 測試計劃 - 10 個公開資料集

## 📦 資料集清單

每個資料集會進行 2 個測試任務：
1. **統計分析 (Stats)** - 使用 stats-service 進行 EDA、假設檢定、生存分析等
2. **AutoML 建模 (ML)** - 使用 automl-service 進行模型訓練和評估

---

### 1. 🌸 Iris (鳶尾花)
- **檔案**: `iris.csv`
- **來源**: sklearn (Fisher, 1936)
- **類型**: 多類別分類
- **大小**: 150 rows × 6 columns
- **目標**: `target` (species: 0=setosa, 1=versicolor, 2=virginica)

| Task | 測試內容 |
|------|----------|
| Stats | TableOne (按species分組), ANOVA (花瓣/花萼比較), 相關性分析 |
| ML | 多類別分類模型, 特徵重要性 |

---

### 2. 🎀 Breast Cancer (乳癌)
- **檔案**: `breast_cancer.csv`
- **來源**: UCI ML Repository (sklearn)
- **類型**: 二元分類
- **大小**: 569 rows × 31 columns
- **目標**: `diagnosis` (0=malignant, 1=benign)

| Task | 測試內容 |
|------|----------|
| Stats | ROC 分析, 特徵相關性, VIF 多重共線性檢測 |
| ML | 二元分類模型, AUC 評估, 特徵篩選 |

---

### 3. 💉 Diabetes (糖尿病)
- **檔案**: `diabetes.csv`
- **來源**: sklearn (Efron et al., 2004)
- **類型**: 迴歸
- **大小**: 442 rows × 11 columns
- **目標**: `progression` (一年後疾病進展程度)

| Task | 測試內容 |
|------|----------|
| Stats | 多元迴歸分析, 相關性矩陣, 常態性檢定 |
| ML | 迴歸模型, R² 評估, 殘差分析 |

---

### 4. ❤️ Heart Disease (心臟病)
- **檔案**: `heart_disease.csv`
- **來源**: UCI Cleveland (Detrano et al., 1989)
- **類型**: 二元分類
- **大小**: 297 rows × 14 columns
- **目標**: `target` (0=no disease, 1=disease)

| Task | 測試內容 |
|------|----------|
| Stats | TableOne (按心臟病分組), 卡方檢定, 邏輯迴歸係數 |
| ML | 二元分類模型, 風險因子分析 |

---

### 5. 🚢 Titanic (鐵達尼號)
- **檔案**: `titanic.csv`
- **來源**: Kaggle/seaborn
- **類型**: 二元分類 / 生存分析
- **大小**: 891 rows × 11 columns
- **目標**: `survived` (0=died, 1=survived)

| Task | 測試內容 |
|------|----------|
| Stats | TableOne (按生存分組), 卡方檢定 (性別/艙等), 傾向分數匹配 |
| ML | 二元分類模型, 特徵工程效果 |

---

### 6. 🏠 California Housing (加州房價)
- **檔案**: `california_housing.csv`
- **來源**: sklearn (Pace & Barry, 1997)
- **類型**: 迴歸
- **大小**: 1000 rows × 9 columns
- **目標**: `median_house_value`

| Task | 測試內容 |
|------|----------|
| Stats | 描述性統計, 地理特徵相關性, 分布檢定 |
| ML | 迴歸模型, MAE/RMSE 評估 |

---

### 7. 🍷 Wine Quality (紅酒品質)
- **檔案**: `wine_quality.csv`
- **來源**: UCI (Cortez et al., 2009)
- **類型**: 迴歸 / 多類別分類
- **大小**: 1599 rows × 12 columns
- **目標**: `quality` (評分 3-8)

| Task | 測試內容 |
|------|----------|
| Stats | 相關性分析, 分布比較, 多重比較 (Tukey HSD) |
| ML | 迴歸或分類模型, 特徵重要性 |

---

### 8. 💰 Adult Income (成人收入)
- **檔案**: `adult_income.csv`
- **來源**: UCI Census (Kohavi, 1996)
- **類型**: 二元分類
- **大小**: 2000 rows × 15 columns
- **目標**: `income` (0=≤50K, 1=>50K)

| Task | 測試內容 |
|------|----------|
| Stats | TableOne (按收入分組), 卡方檢定 (教育/職業), 傾向分數 |
| ML | 二元分類模型, 公平性分析 (性別/種族) |

---

### 9. ⛓️ Rossi Recidivism (再犯率)
- **檔案**: `rossi_recidivism.csv`
- **來源**: lifelines (Rossi et al., 1980)
- **類型**: 生存分析
- **大小**: 432 rows × 9 columns
- **目標**: `week` (時間), `arrest` (事件: 是否再犯)

| Task | 測試內容 |
|------|----------|
| Stats | Kaplan-Meier 曲線, Log-rank 檢定, Cox 迴歸 |
| ML | 生存模型 (如果支援), 風險分層 |

---

### 10. 🫁 Lung Cancer (肺癌)
- **檔案**: `lung_cancer.csv`
- **來源**: lifelines/NCCTG (Loprinzi et al., 1994)
- **類型**: 生存分析
- **大小**: 228 rows × 10 columns
- **目標**: `time` (存活時間), `status` (1=censored, 2=dead)

| Task | 測試內容 |
|------|----------|
| Stats | Kaplan-Meier 曲線, 多變量 Cox 迴歸, 風險因子分析 |
| ML | 生存預測模型 |

---

## 📋 測試執行指令範本

### 給 Agent 的指令格式:

```
請使用 {dataset_name} 資料集執行 E2E 測試:

1. 統計分析:
   - 上傳資料到 stats-service
   - 執行 {stats_tasks}
   - 驗證結果

2. AutoML 建模:
   - 上傳資料到 automl-service
   - 執行 {ml_tasks}
   - 評估模型效能
```

---

## ✅ 測試進度追蹤

| # | Dataset | Stats Test | ML Test | Notes |
|---|---------|------------|---------|-------|
| 1 | Iris | ⬜ | ⬜ | |
| 2 | Breast Cancer | ⬜ | ⬜ | |
| 3 | Diabetes | ⬜ | ⬜ | |
| 4 | Heart Disease | ⬜ | ⬜ | |
| 5 | Titanic | ⬜ | ⬜ | |
| 6 | California Housing | ⬜ | ⬜ | |
| 7 | Wine Quality | ⬜ | ⬜ | |
| 8 | Adult Income | ⬜ | ⬜ | |
| 9 | Rossi Recidivism | ⬜ | ⬜ | |
| 10 | Lung Cancer | ⬜ | ⬜ | |

---

## 🗂️ 檔案結構

```
sample_data/
├── download_datasets.py          # 下載腳本
├── E2E_TEST_PLAN.md             # 本文件
├── iris.csv                      # 1. Iris
├── iris_README.txt
├── breast_cancer.csv             # 2. Breast Cancer
├── breast_cancer_README.txt
├── diabetes.csv                  # 3. Diabetes
├── diabetes_README.txt
├── heart_disease.csv             # 4. Heart Disease
├── heart_disease_README.txt
├── titanic.csv                   # 5. Titanic
├── titanic_README.txt
├── california_housing.csv        # 6. California Housing
├── california_housing_README.txt
├── wine_quality.csv              # 7. Wine Quality
├── wine_quality_README.txt
├── adult_income.csv              # 8. Adult Income
├── adult_income_README.txt
├── rossi_recidivism.csv          # 9. Rossi Recidivism
├── rossi_recidivism_README.txt
├── lung_cancer.csv               # 10. Lung Cancer
├── lung_cancer_README.txt
├── stanford_heart.csv            # Bonus: Stanford Heart
├── stanford_heart_README.txt
├── generate_medical_data.py      # 原有醫學資料生成
└── medical_study_200.csv         # 原有測試資料
```
