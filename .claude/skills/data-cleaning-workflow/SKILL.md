---
name: data-cleaning-workflow
description: Data cleaning and preprocessing workflow using MCP tools. Triggers: 資料清理, data cleaning, 缺失值, 處理資料, preprocess.
---

# Data Cleaning Workflow 技能 (資料清理流程)

## 描述
使用 MCP 工具進行資料清理和前處理的標準流程。

## 觸發條件
- 「清理資料」「data cleaning」
- 「處理缺失值」「處理資料」
- 「前處理」「preprocess」

---

## 🎯 資料清理流程

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Data Cleaning Workflow                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   [1] 診斷問題        →  get_column_info / analyze_missing_values   │
│         ↓                                                           │
│   [2] 處理缺失值      →  handle_missing_values                       │
│         ↓                                                           │
│   [3] 欄位操作        →  remove_columns / rename_columns            │
│         ↓                                                           │
│   [4] 資料轉換        →  convert_to_binary / encode_categorical     │
│         ↓                                                           │
│   [5] 篩選資料        →  filter_rows                                │
│         ↓                                                           │
│   [6] 驗證結果        →  direct_preview_data / get_quick_stats      │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📋 Step 1: 診斷資料問題

### 1.1 取得欄位資訊

```python
mcp_automl_get_column_info(
    csv_path="/data/sample_data/titanic.csv"
)
```

**輸出包含：**
- 欄位名稱
- 資料類型
- 非空值數量
- 缺失值比例

### 1.2 分析缺失值

```python
mcp_automl_analyze_missing_values(
    csv_path="/data/sample_data/titanic.csv"
)
```

**輸出包含：**
- 各欄位缺失值數量和比例
- 缺失模式分析
- 處理建議

### 1.3 預覽資料

```python
mcp_automl_direct_preview_data(
    csv_path="/data/sample_data/titanic.csv",
    n_rows=20
)
```

---

## 📋 Step 2: 處理缺失值

### 2.1 缺失值處理策略

```python
mcp_automl_handle_missing_values(
    csv_path="/data/sample_data/titanic.csv",
    strategy="mean",          # 處理策略
    columns=["age"],          # 指定欄位（可選）
    output_path="/data/projects/my_project/titanic_cleaned.csv"
)
```

**可用策略：**

| 策略 | 說明 | 適用場景 |
|------|------|----------|
| `mean` | 平均值填補 | 數值欄位，常態分佈 |
| `median` | 中位數填補 | 數值欄位，有極端值 |
| `mode` | 眾數填補 | 類別欄位 |
| `constant` | 固定值填補 | 有意義的預設值 |
| `drop` | 刪除含缺失值的列 | 缺失比例低 |

### 2.2 不同欄位不同策略

```python
# 數值欄位用中位數
mcp_automl_handle_missing_values(
    csv_path="/data/sample_data/titanic.csv",
    strategy="median",
    columns=["age", "fare"],
    output_path="/data/projects/step1.csv"
)

# 類別欄位用眾數
mcp_automl_handle_missing_values(
    csv_path="/data/projects/step1.csv",
    strategy="mode",
    columns=["embarked"],
    output_path="/data/projects/step2.csv"
)
```

---

## 📋 Step 3: 欄位操作

### 3.1 移除欄位

```python
mcp_automl_remove_columns(
    csv_path="/data/sample_data/titanic.csv",
    columns=["cabin", "ticket", "name"],  # 移除無用欄位
    output_path="/data/projects/titanic_reduced.csv"
)
```

### 3.2 重新命名欄位

```python
mcp_automl_rename_columns(
    csv_path="/data/sample_data/my_data.csv",
    mapping={
        "old_name1": "new_name1",
        "old_name2": "new_name2",
        "性別": "gender",
        "年齡": "age"
    },
    output_path="/data/projects/data_renamed.csv"
)
```

---

## 📋 Step 4: 資料轉換

### 4.1 轉換為二元變數

```python
mcp_automl_convert_to_binary(
    csv_path="/data/sample_data/titanic.csv",
    column="sex",
    mapping={
        "male": 0,
        "female": 1
    },
    output_path="/data/projects/titanic_binary.csv"
)
```

### 4.2 類別變數編碼

```python
mcp_automl_encode_categorical(
    csv_path="/data/sample_data/titanic.csv",
    columns=["embarked", "pclass"],
    method="onehot",      # onehot, label, target
    output_path="/data/projects/titanic_encoded.csv"
)
```

**編碼方法：**

| 方法 | 說明 | 適用場景 |
|------|------|----------|
| `onehot` | 獨熱編碼 | 無序類別 |
| `label` | 標籤編碼 | 有序類別或樹模型 |
| `target` | 目標編碼 | 高基數類別 |

---

## 📋 Step 5: 篩選資料

### 5.1 條件篩選

```python
mcp_automl_filter_rows(
    csv_path="/data/sample_data/titanic.csv",
    condition="age >= 18",     # Python 表達式
    output_path="/data/projects/titanic_adults.csv"
)
```

### 5.2 複合條件

```python
mcp_automl_filter_rows(
    csv_path="/data/sample_data/titanic.csv",
    condition="(age >= 18) & (pclass == 1)",
    output_path="/data/projects/titanic_adult_first.csv"
)
```

### 5.3 常用篩選條件

```python
# 移除極端值
condition="(age > 0) & (age < 100)"

# 保留非空值
condition="age.notna()"

# 特定類別
condition="embarked == 'S'"

# 數值範圍
condition="(fare >= 10) & (fare <= 500)"
```

---

## 📋 Step 6: 驗證結果

### 6.1 預覽清理後的資料

```python
mcp_automl_direct_preview_data(
    csv_path="/data/projects/titanic_cleaned.csv",
    n_rows=10
)
```

### 6.2 檢查統計摘要

```python
mcp_automl_get_quick_stats(
    csv_path="/data/projects/titanic_cleaned.csv"
)
```

### 6.3 再次檢查缺失值

```python
mcp_automl_analyze_missing_values(
    csv_path="/data/projects/titanic_cleaned.csv"
)
```

---

## 🎯 完整範例

### 範例：Titanic 資料清理

```
User: "清理 titanic.csv 準備做 ML"

Agent 執行：

1. 診斷資料
   mcp_automl_get_column_info(csv_path="/data/sample_data/titanic.csv")
   
   發現問題：
   - age: 177 個缺失值
   - cabin: 687 個缺失值（太多，移除）
   - embarked: 2 個缺失值

2. 移除無用欄位
   mcp_automl_remove_columns(
       csv_path="/data/sample_data/titanic.csv",
       columns=["cabin", "ticket", "name", "passengerid"],
       output_path="/data/projects/titanic/step1.csv"
   )

3. 處理 age 缺失值（用中位數）
   mcp_automl_handle_missing_values(
       csv_path="/data/projects/titanic/step1.csv",
       strategy="median",
       columns=["age"],
       output_path="/data/projects/titanic/step2.csv"
   )

4. 處理 embarked 缺失值（用眾數）
   mcp_automl_handle_missing_values(
       csv_path="/data/projects/titanic/step2.csv",
       strategy="mode",
       columns=["embarked"],
       output_path="/data/projects/titanic/step3.csv"
   )

5. 轉換 sex 為二元
   mcp_automl_convert_to_binary(
       csv_path="/data/projects/titanic/step3.csv",
       column="sex",
       mapping={"male": 0, "female": 1},
       output_path="/data/projects/titanic/step4.csv"
   )

6. 編碼類別變數
   mcp_automl_encode_categorical(
       csv_path="/data/projects/titanic/step4.csv",
       columns=["embarked"],
       method="onehot",
       output_path="/data/projects/titanic/titanic_cleaned.csv"
   )

7. 驗證
   mcp_automl_get_quick_stats(
       csv_path="/data/projects/titanic/titanic_cleaned.csv"
   )

回報使用者：
"✅ 資料清理完成！

清理步驟：
1. 移除欄位：cabin, ticket, name, passengerid
2. age 缺失值：用中位數 (28) 填補
3. embarked 缺失值：用眾數 (S) 填補
4. sex：轉換為 0/1
5. embarked：獨熱編碼

清理後資料：
- 路徑：/data/projects/titanic/titanic_cleaned.csv
- 筆數：891
- 欄位：10
- 缺失值：0

可以開始訓練模型了！"
```

---

## 📁 輸出路徑規則

### 建議的目錄結構

```
/data/projects/{project_name}/
├── data/
│   ├── raw/              # 原始資料
│   ├── interim/          # 中間處理結果
│   └── processed/        # 最終清理資料
├── models/               # 訓練的模型
└── reports/              # 分析報告
```

### 命名建議

```
原始：   {dataset}.csv
清理後： {dataset}_cleaned.csv
編碼後： {dataset}_encoded.csv
最終：   {dataset}_final.csv
```

---

## ⚠️ 常見錯誤

### 1. 輸出路徑不存在
```python
# ❌ 錯誤：目錄不存在
output_path="/data/projects/new_folder/file.csv"

# ✅ 正確：確保目錄存在，或用已存在的目錄
output_path="/data/projects/titanic_cleaned.csv"
```

### 2. 欄位名稱錯誤
```python
# 先確認欄位名稱
mcp_automl_get_column_info(...)
# 使用正確的大小寫
```

### 3. 策略不適用
```python
# ❌ 錯誤：對類別欄位用 mean
strategy="mean", columns=["sex"]

# ✅ 正確：類別用 mode
strategy="mode", columns=["sex"]
```

---

## 💡 最佳實踐

### 1. 保留原始資料
- 永遠不要覆蓋原始檔案
- 每一步輸出到不同檔案

### 2. 先診斷再處理
- 先了解資料問題
- 再決定處理策略

### 3. 逐步驗證
- 每一步後檢查結果
- 確認處理正確再繼續

### 4. 記錄清理步驟
- 記錄每個處理步驟
- 方便重現和回溯
