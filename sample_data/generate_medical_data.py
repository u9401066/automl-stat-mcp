"""
生成 200 人醫學研究模擬資料
用於測試 AutoML 統計分析功能
"""

import random

import numpy as np
import pandas as pd

# 設定隨機種子確保可重現
np.random.seed(42)
random.seed(42)

n = 200

# ============================================================================
# 基本人口統計資料
# ============================================================================
data = {
    "patient_id": [f"P{str(i).zfill(4)}" for i in range(1, n + 1)],
    # 性別 (略微不平衡)
    "gender": np.random.choice(["Male", "Female"], n, p=[0.45, 0.55]),
    # 年齡 (常態分佈，平均55歲)
    "age": np.clip(np.random.normal(55, 15, n), 18, 90).astype(int),
    # BMI (略右偏)
    "bmi": np.clip(np.random.gamma(5, 5, n) + 15, 16, 45).round(1),
    # 吸菸狀態
    "smoking_status": np.random.choice(["Never", "Former", "Current"], n, p=[0.45, 0.35, 0.20]),
    # 教育程度
    "education": np.random.choice(["High School", "Bachelor", "Master", "PhD"], n, p=[0.30, 0.40, 0.20, 0.10]),
}

df = pd.DataFrame(data)

# ============================================================================
# 臨床測量值
# ============================================================================
# 收縮壓 (與年齡、BMI相關)
df["systolic_bp"] = (100 + df["age"] * 0.5 + df["bmi"] * 0.8 + np.random.normal(0, 12, n)).round(0).astype(int)

# 舒張壓
df["diastolic_bp"] = (60 + df["age"] * 0.2 + df["bmi"] * 0.4 + np.random.normal(0, 8, n)).round(0).astype(int)

# 空腹血糖 (mg/dL) - 右偏分佈
df["fasting_glucose"] = np.clip(np.random.gamma(10, 10, n) + 70, 65, 350).round(0).astype(int)

# 總膽固醇 (mg/dL)
df["total_cholesterol"] = (150 + df["age"] * 0.8 + df["bmi"] * 1.5 + np.random.normal(0, 30, n)).round(0).astype(int)

# HDL 膽固醇 (女性較高)
df["hdl_cholesterol"] = (
    (
        45
        + (df["gender"] == "Female").astype(int) * 10
        + np.random.normal(0, 12, n)
        - (df["smoking_status"] == "Current").astype(int) * 5
    )
    .round(0)
    .astype(int)
)

# LDL 膽固醇
df["ldl_cholesterol"] = (
    (df["total_cholesterol"] - df["hdl_cholesterol"] - df["fasting_glucose"] / 5).round(0).astype(int)
)

# HbA1c (與血糖相關)
df["hba1c"] = (4.5 + (df["fasting_glucose"] - 90) * 0.02 + np.random.normal(0, 0.5, n)).round(1)
df["hba1c"] = np.clip(df["hba1c"], 4.0, 14.0)

# 肌酸酐 (mg/dL)
df["creatinine"] = np.clip(np.random.gamma(15, 0.07, n) + 0.5, 0.5, 4.0).round(2)

# ============================================================================
# 治療分組 (用於比較分析)
# ============================================================================
# 隨機分配到治療組或對照組
df["treatment_group"] = np.random.choice(["Treatment", "Control"], n, p=[0.5, 0.5])

# 治療後血壓變化 (治療組效果較好)
treatment_effect = (df["treatment_group"] == "Treatment").astype(int) * -8
df["bp_change"] = (treatment_effect + np.random.normal(-2, 10, n)).round(1)

# ============================================================================
# 疾病狀態 (與其他變數相關)
# ============================================================================
# 糖尿病 (與血糖、HbA1c、BMI相關)
diabetes_prob = 1 / (
    1 + np.exp(-(-5 + (df["fasting_glucose"] - 100) * 0.05 + (df["hba1c"] - 5.7) * 0.8 + (df["bmi"] - 25) * 0.1))
)
df["diabetes"] = (np.random.random(n) < diabetes_prob).astype(int)

# 高血壓 (與血壓、年齡相關)
hypertension_prob = 1 / (1 + np.exp(-(-6 + (df["systolic_bp"] - 120) * 0.05 + (df["age"] - 50) * 0.03)))
df["hypertension"] = (np.random.random(n) < hypertension_prob).astype(int)

# 心血管疾病風險分數 (複合指標)
df["cv_risk_score"] = (
    df["age"] * 0.5
    + (df["gender"] == "Male").astype(int) * 5
    + df["systolic_bp"] * 0.1
    + df["total_cholesterol"] * 0.02
    + df["diabetes"] * 8
    + (df["smoking_status"] == "Current").astype(int) * 10
    - df["hdl_cholesterol"] * 0.1
).round(1)

# ============================================================================
# 加入一些缺失值 (模擬真實情況)
# ============================================================================
# 隨機將 5% 的 HDL 設為缺失
missing_idx = np.random.choice(n, int(n * 0.05), replace=False)
df.loc[missing_idx, "hdl_cholesterol"] = np.nan

# 隨機將 3% 的 HbA1c 設為缺失
missing_idx = np.random.choice(n, int(n * 0.03), replace=False)
df.loc[missing_idx, "hba1c"] = np.nan

# 隨機將 2% 的 education 設為缺失
missing_idx = np.random.choice(n, int(n * 0.02), replace=False)
df.loc[missing_idx, "education"] = np.nan

# ============================================================================
# 加入一些異常值 (測試異常值檢測)
# ============================================================================
# 加入 2 個血壓異常值
df.loc[10, "systolic_bp"] = 220
df.loc[50, "systolic_bp"] = 85

# 加入 1 個極端 BMI
df.loc[100, "bmi"] = 52.0

# ============================================================================
# 儲存資料
# ============================================================================
output_path = "/home/eric/workspace251202/sample_data/medical_study_200.csv"
df.to_csv(output_path, index=False)

print(f"✅ 已生成 {len(df)} 筆醫學研究資料")
print(f"📁 儲存至: {output_path}")
print("\n📊 資料概覽:")
print(f"   欄位數: {len(df.columns)}")
print(f"   數值欄位: {len(df.select_dtypes(include=[np.number]).columns)}")
print(f"   類別欄位: {len(df.select_dtypes(include=['object']).columns)}")
print("\n📋 欄位清單:")
for col in df.columns:
    dtype = df[col].dtype
    missing = df[col].isna().sum()
    print(f"   - {col}: {dtype}" + (f" (缺失: {missing})" if missing > 0 else ""))

print("\n🔬 治療組分佈:")
print(df["treatment_group"].value_counts().to_string())

print("\n🏥 疾病分佈:")
print(f"   糖尿病: {df['diabetes'].sum()} ({df['diabetes'].mean() * 100:.1f}%)")
print(f"   高血壓: {df['hypertension'].sum()} ({df['hypertension'].mean() * 100:.1f}%)")
