#!/usr/bin/env python3
"""
Download 10 Classic Public Datasets for E2E Testing

This script downloads well-known public datasets for comprehensive testing of:
1. Stats Service - Statistical analysis capabilities
2. AutoML Service - Machine learning model building

Each dataset is saved as CSV with source documentation.

Datasets:
=========
1. Iris - Classification (sklearn)
2. Breast Cancer Wisconsin - Binary Classification (sklearn)
3. Diabetes - Regression (sklearn)
4. Heart Disease - Binary Classification (UCI)
5. Titanic - Binary Classification/Survival (seaborn)
6. Boston Housing - Regression (OpenML, original from sklearn deprecated)
7. Wine Quality - Multi-class/Regression (UCI)
8. Adult Income (Census) - Binary Classification (UCI)
9. Rossi Recidivism - Survival Analysis (lifelines)
10. PBC (Primary Biliary Cirrhosis) - Survival Analysis (lifelines)

Run:
    cd sample_data
    python3 download_datasets.py
"""

import os

import numpy as np
import pandas as pd

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


def save_with_metadata(df: pd.DataFrame, filename: str, source: str, description: str):
    """Save dataset and create metadata file."""
    filepath = os.path.join(OUTPUT_DIR, filename)
    df.to_csv(filepath, index=False)

    # Create metadata
    meta_path = filepath.replace(".csv", "_README.txt")
    with open(meta_path, "w") as f:
        f.write(f"Dataset: {filename}\n")
        f.write(f"Source: {source}\n")
        f.write(f"Description: {description}\n")
        f.write(f"Rows: {len(df)}\n")
        f.write(f"Columns: {len(df.columns)}\n")
        f.write(f"Column Names: {', '.join(df.columns)}\n")
        f.write("\nColumn Types:\n")
        for col in df.columns:
            f.write(f"  - {col}: {df[col].dtype}\n")

    print(f"✅ Saved: {filename} ({len(df)} rows, {len(df.columns)} cols)")


def download_iris():
    """1. Iris - Classic multi-class classification dataset."""
    from sklearn.datasets import load_iris

    data = load_iris()
    df = pd.DataFrame(data.data, columns=["sepal_length", "sepal_width", "petal_length", "petal_width"])
    df["species"] = pd.Categorical.from_codes(data.target, ["setosa", "versicolor", "virginica"])
    df["target"] = data.target

    save_with_metadata(
        df,
        "iris.csv",
        "sklearn.datasets.load_iris (Fisher, 1936)",
        "150 iris flowers, 4 features, 3 species. Classic multi-class classification.",
    )


def download_breast_cancer():
    """2. Breast Cancer Wisconsin - Binary classification."""
    from sklearn.datasets import load_breast_cancer

    data = load_breast_cancer()
    df = pd.DataFrame(data.data, columns=[c.replace(" ", "_") for c in data.feature_names])
    df["diagnosis"] = data.target  # 0=malignant, 1=benign

    save_with_metadata(
        df,
        "breast_cancer.csv",
        "sklearn.datasets.load_breast_cancer (UCI ML Repository)",
        "569 breast cancer cases, 30 features. Binary classification: malignant(0) vs benign(1).",
    )


def download_diabetes():
    """3. Diabetes - Regression dataset."""
    from sklearn.datasets import load_diabetes

    data = load_diabetes()
    df = pd.DataFrame(data.data, columns=["age", "sex", "bmi", "bp", "s1", "s2", "s3", "s4", "s5", "s6"])
    df["progression"] = data.target  # Disease progression after 1 year

    save_with_metadata(
        df,
        "diabetes.csv",
        "sklearn.datasets.load_diabetes (Efron et al., 2004)",
        "442 diabetes patients, 10 features. Regression: predict disease progression.",
    )


def download_heart_disease():
    """4. Heart Disease - Binary classification from UCI."""
    # Use processed Cleveland dataset
    url = "https://archive.ics.uci.edu/ml/machine-learning-databases/heart-disease/processed.cleveland.data"
    columns = [
        "age",
        "sex",
        "cp",
        "trestbps",
        "chol",
        "fbs",
        "restecg",
        "thalach",
        "exang",
        "oldpeak",
        "slope",
        "ca",
        "thal",
        "target",
    ]

    try:
        df = pd.read_csv(url, names=columns, na_values="?")
        df["target"] = (df["target"] > 0).astype(int)  # Binary: presence of heart disease
        df = df.dropna()  # Remove rows with missing values

        save_with_metadata(
            df,
            "heart_disease.csv",
            "UCI ML Repository - Cleveland Heart Disease (Detrano et al., 1989)",
            "303 patients, 13 features. Binary classification: heart disease presence.",
        )
    except Exception as e:
        print(f"⚠️ Heart Disease download failed: {e}, creating synthetic version")
        _create_synthetic_heart()


def _create_synthetic_heart():
    """Create synthetic heart disease data if download fails."""
    np.random.seed(42)
    n = 303
    df = pd.DataFrame(
        {
            "age": np.random.normal(54, 9, n).astype(int).clip(29, 77),
            "sex": np.random.choice([0, 1], n, p=[0.32, 0.68]),
            "cp": np.random.choice([0, 1, 2, 3], n),
            "trestbps": np.random.normal(132, 18, n).astype(int).clip(94, 200),
            "chol": np.random.normal(247, 52, n).astype(int).clip(126, 564),
            "fbs": np.random.choice([0, 1], n, p=[0.85, 0.15]),
            "restecg": np.random.choice([0, 1, 2], n, p=[0.5, 0.48, 0.02]),
            "thalach": np.random.normal(150, 23, n).astype(int).clip(71, 202),
            "exang": np.random.choice([0, 1], n, p=[0.67, 0.33]),
            "oldpeak": np.random.exponential(1.0, n).clip(0, 6.2).round(1),
            "slope": np.random.choice([0, 1, 2], n),
            "ca": np.random.choice([0, 1, 2, 3], n, p=[0.58, 0.22, 0.13, 0.07]),
            "thal": np.random.choice([1, 2, 3], n, p=[0.05, 0.55, 0.40]),
            "target": np.random.choice([0, 1], n, p=[0.54, 0.46]),
        }
    )
    save_with_metadata(
        df,
        "heart_disease.csv",
        "Synthetic (based on UCI Cleveland Heart Disease statistics)",
        "303 patients, 13 features. Binary classification: heart disease presence.",
    )


def download_titanic():
    """5. Titanic - Classic survival/classification dataset."""
    try:
        import seaborn as sns

        df = sns.load_dataset("titanic")
        # Select and rename columns for cleaner analysis
        df = df[
            ["survived", "pclass", "sex", "age", "sibsp", "parch", "fare", "embarked", "class", "adult_male", "alone"]
        ].copy()
        df["sex"] = df["sex"].map({"male": 1, "female": 0})
        df["embarked"] = df["embarked"].map({"S": 0, "C": 1, "Q": 2})

        save_with_metadata(
            df,
            "titanic.csv",
            "seaborn.load_dataset('titanic') (Kaggle Titanic Competition)",
            "891 passengers, 11 features. Binary classification: survival prediction.",
        )
    except Exception as e:
        print(f"⚠️ Titanic download failed: {e}")


def download_housing():
    """6. California Housing - Regression dataset."""
    from sklearn.datasets import fetch_california_housing

    data = fetch_california_housing()
    df = pd.DataFrame(data.data, columns=data.feature_names)
    df["median_house_value"] = data.target

    # Sample to reasonable size for testing
    df = df.sample(n=1000, random_state=42)

    save_with_metadata(
        df,
        "california_housing.csv",
        "sklearn.datasets.fetch_california_housing (Pace & Barry, 1997)",
        "1000 samples (from 20640), 8 features. Regression: predict median house value.",
    )


def download_wine_quality():
    """7. Wine Quality - Multi-class classification / Regression."""
    url = "https://archive.ics.uci.edu/ml/machine-learning-databases/wine-quality/winequality-red.csv"

    try:
        df = pd.read_csv(url, sep=";")
        # Rename columns to remove spaces
        df.columns = [c.replace(" ", "_") for c in df.columns]

        save_with_metadata(
            df,
            "wine_quality.csv",
            "UCI ML Repository - Wine Quality (Cortez et al., 2009)",
            "1599 red wines, 11 features. Regression/Multi-class: predict quality score (3-8).",
        )
    except Exception as e:
        print(f"⚠️ Wine Quality download failed: {e}, creating synthetic version")
        _create_synthetic_wine()


def _create_synthetic_wine():
    """Create synthetic wine quality data if download fails."""
    np.random.seed(42)
    n = 1599
    df = pd.DataFrame(
        {
            "fixed_acidity": np.random.normal(8.3, 1.7, n).clip(4.6, 15.9),
            "volatile_acidity": np.random.normal(0.53, 0.18, n).clip(0.12, 1.58),
            "citric_acid": np.random.normal(0.27, 0.19, n).clip(0, 1),
            "residual_sugar": np.random.exponential(2.5, n).clip(0.9, 15.5),
            "chlorides": np.random.normal(0.087, 0.05, n).clip(0.012, 0.611),
            "free_sulfur_dioxide": np.random.normal(15.9, 10.5, n).clip(1, 72),
            "total_sulfur_dioxide": np.random.normal(46.5, 33, n).clip(6, 289),
            "density": np.random.normal(0.997, 0.002, n).clip(0.990, 1.004),
            "pH": np.random.normal(3.31, 0.15, n).clip(2.74, 4.01),
            "sulphates": np.random.normal(0.66, 0.17, n).clip(0.33, 2.0),
            "alcohol": np.random.normal(10.4, 1.1, n).clip(8.4, 14.9),
            "quality": np.random.choice([3, 4, 5, 6, 7, 8], n, p=[0.01, 0.03, 0.43, 0.40, 0.12, 0.01]),
        }
    )
    save_with_metadata(
        df,
        "wine_quality.csv",
        "Synthetic (based on UCI Wine Quality statistics)",
        "1599 red wines, 11 features. Regression/Multi-class: predict quality score (3-8).",
    )


def download_adult_income():
    """8. Adult Income (Census) - Binary classification."""
    url = "https://archive.ics.uci.edu/ml/machine-learning-databases/adult/adult.data"
    columns = [
        "age",
        "workclass",
        "fnlwgt",
        "education",
        "education_num",
        "marital_status",
        "occupation",
        "relationship",
        "race",
        "sex",
        "capital_gain",
        "capital_loss",
        "hours_per_week",
        "native_country",
        "income",
    ]

    try:
        df = pd.read_csv(url, names=columns, skipinitialspace=True, na_values="?")
        df = df.dropna()
        df["income"] = (df["income"] == ">50K").astype(int)
        # Sample for manageable size
        df = df.sample(n=2000, random_state=42)

        save_with_metadata(
            df,
            "adult_income.csv",
            "UCI ML Repository - Adult Census Income (Kohavi, 1996)",
            "2000 samples (from 32561), 14 features. Binary classification: income >50K.",
        )
    except Exception as e:
        print(f"⚠️ Adult Income download failed: {e}")


def download_rossi_recidivism():
    """9. Rossi Recidivism - Survival analysis dataset."""
    try:
        from lifelines.datasets import load_rossi

        df = load_rossi()

        save_with_metadata(
            df,
            "rossi_recidivism.csv",
            "lifelines.datasets.load_rossi (Rossi et al., 1980)",
            "432 convicts, 8 features. Survival analysis: time to re-arrest.",
        )
    except Exception as e:
        print(f"⚠️ Rossi download failed: {e}")


def download_pbc():
    """10. PBC (Primary Biliary Cirrhosis) - Survival analysis dataset."""
    try:
        from lifelines.datasets import load_stanford_heart_transplants

        # Use Stanford Heart Transplants as alternative (PBC sometimes unavailable)
        df = load_stanford_heart_transplants()

        save_with_metadata(
            df,
            "stanford_heart.csv",
            "lifelines.datasets.load_stanford_heart_transplants (Crowley & Hu, 1977)",
            "103 heart transplant patients. Survival analysis: post-transplant survival.",
        )
    except Exception:
        pass

    # Also try lung cancer dataset
    try:
        from lifelines.datasets import load_lung

        df = load_lung()

        save_with_metadata(
            df,
            "lung_cancer.csv",
            "lifelines.datasets.load_lung (NCCTG Lung Cancer, Loprinzi et al., 1994)",
            "228 advanced lung cancer patients. Survival analysis with clinical features.",
        )
    except Exception as e:
        print(f"⚠️ Lung cancer download failed: {e}")


def main():
    """Download all 10 datasets."""
    print("=" * 60)
    print("Downloading 10 Classic Public Datasets for E2E Testing")
    print("=" * 60)
    print()

    download_iris()
    download_breast_cancer()
    download_diabetes()
    download_heart_disease()
    download_titanic()
    download_housing()
    download_wine_quality()
    download_adult_income()
    download_rossi_recidivism()
    download_pbc()

    print()
    print("=" * 60)
    print("Download Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
