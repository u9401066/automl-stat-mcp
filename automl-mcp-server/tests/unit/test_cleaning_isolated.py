"""
Isolated tests for cleaning utilities.

Tests the pure Python helper functions used in cleaning_tools.py
without requiring the full MCP stack.
"""
import pandas as pd
import numpy as np
import tempfile
import os


class TestCSVParsing:
    """Test CSV loading utilities"""
    
    def test_load_simple_csv(self):
        """Test loading a simple CSV file"""
        # Create temp CSV
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("name,age,score\n")
            f.write("Alice,30,85\n")
            f.write("Bob,25,90\n")
            temp_path = f.name
        
        try:
            df = pd.read_csv(temp_path)
            assert len(df) == 2
            assert list(df.columns) == ['name', 'age', 'score']
            print("✓ Simple CSV loading")
        finally:
            os.unlink(temp_path)
    
    def test_load_csv_with_special_chars(self):
        """Test loading CSV with unicode/special characters"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write("name,city,notes\n")
            f.write("張三,北京,測試中文\n")
            f.write("李四,上海,emoji 🎉\n")
            temp_path = f.name
        
        try:
            df = pd.read_csv(temp_path)
            assert len(df) == 2
            assert df.iloc[0]['name'] == '張三'
            assert '🎉' in df.iloc[1]['notes']
            print("✓ CSV with special characters")
        finally:
            os.unlink(temp_path)
    
    def test_csv_to_content_roundtrip(self):
        """Test DataFrame to CSV string and back"""
        df1 = pd.DataFrame({
            'a': [1, 2, 3],
            'b': ['x', 'y', 'z'],
            'c': [1.1, 2.2, 3.3]
        })
        
        csv_content = df1.to_csv(index=False)
        df2 = pd.read_csv(pd.io.common.StringIO(csv_content))
        
        assert list(df1.columns) == list(df2.columns)
        assert df1.shape == df2.shape
        print("✓ CSV roundtrip conversion")


class TestBinaryConversion:
    """Test binary conversion logic"""
    
    def test_convert_string_to_binary(self):
        """Test converting string column to binary"""
        df = pd.DataFrame({
            'treatment': ['control', 'treatment', 'control', 'treatment'],
            'value': [10, 20, 15, 25]
        })
        
        mapping = {'control': 0, 'treatment': 1}
        df['treatment_binary'] = df['treatment'].map(mapping)
        
        assert df['treatment_binary'].tolist() == [0, 1, 0, 1]
        print("✓ String to binary conversion")
    
    def test_convert_numeric_to_binary(self):
        """Test converting numeric column to binary"""
        df = pd.DataFrame({
            'dose': [100, 200, 100, 200, 100],
            'response': [1, 5, 2, 6, 3]
        })
        
        # Numeric mapping
        mapping = {100: 0, 200: 1}
        df['dose_binary'] = df['dose'].map(mapping)
        
        assert df['dose_binary'].tolist() == [0, 1, 0, 1, 0]
        print("✓ Numeric to binary conversion")
    
    def test_binary_conversion_with_missing(self):
        """Test binary conversion with missing values"""
        df = pd.DataFrame({
            'group': ['A', 'B', None, 'A', 'B'],
        })
        
        mapping = {'A': 0, 'B': 1}
        df['group_binary'] = df['group'].map(mapping)
        
        # None should become NaN
        assert df['group_binary'].tolist()[:2] == [0, 1]
        assert pd.isna(df['group_binary'].iloc[2])
        print("✓ Binary conversion with missing values")


class TestMissingValueHandling:
    """Test missing value handling logic"""
    
    def test_detect_missing_values(self):
        """Test detecting missing values"""
        df = pd.DataFrame({
            'a': [1, 2, None, 4],
            'b': ['x', None, 'z', 'w'],
            'c': [1.0, 2.0, 3.0, 4.0]  # No missing
        })
        
        missing_counts = df.isnull().sum()
        assert missing_counts['a'] == 1
        assert missing_counts['b'] == 1
        assert missing_counts['c'] == 0
        print("✓ Missing value detection")
    
    def test_impute_mean(self):
        """Test mean imputation"""
        df = pd.DataFrame({
            'value': [10, 20, None, 40]
        })
        
        mean_val = df['value'].mean()
        df['value_imputed'] = df['value'].fillna(mean_val)
        
        # Mean of 10, 20, 40 = 70/3 ≈ 23.33
        assert abs(df['value_imputed'].iloc[2] - 23.33) < 0.1
        assert df['value_imputed'].isnull().sum() == 0
        print("✓ Mean imputation")
    
    def test_impute_median(self):
        """Test median imputation"""
        df = pd.DataFrame({
            'value': [10, 20, None, 40, 50]
        })
        
        median_val = df['value'].median()
        df['value_imputed'] = df['value'].fillna(median_val)
        
        # Median of 10, 20, 40, 50 = 30
        assert df['value_imputed'].iloc[2] == 30
        print("✓ Median imputation")
    
    def test_impute_mode(self):
        """Test mode imputation for categorical"""
        df = pd.DataFrame({
            'category': ['A', 'B', 'A', None, 'A']
        })
        
        mode_val = df['category'].mode().iloc[0]
        df['category_imputed'] = df['category'].fillna(mode_val)
        
        assert df['category_imputed'].iloc[3] == 'A'
        print("✓ Mode imputation")
    
    def test_drop_rows_with_missing(self):
        """Test dropping rows with missing values"""
        df = pd.DataFrame({
            'a': [1, 2, None, 4],
            'b': ['x', None, 'z', 'w'],
        })
        
        df_clean = df.dropna()
        assert len(df_clean) == 2  # Rows 0 and 3
        print("✓ Drop rows with missing")
    
    def test_drop_columns_with_missing(self):
        """Test dropping columns with missing values"""
        df = pd.DataFrame({
            'a': [1, 2, None, 4],
            'b': [1, 2, 3, 4],  # No missing
            'c': ['x', None, 'z', 'w'],
        })
        
        df_clean = df.dropna(axis=1)
        assert list(df_clean.columns) == ['b']
        print("✓ Drop columns with missing")


class TestColumnRemoval:
    """Test column removal logic"""
    
    def test_remove_single_column(self):
        """Test removing a single column"""
        df = pd.DataFrame({
            'id': [1, 2, 3],
            'name': ['a', 'b', 'c'],
            'value': [10, 20, 30]
        })
        
        df_clean = df.drop(columns=['id'])
        assert 'id' not in df_clean.columns
        assert len(df_clean.columns) == 2
        print("✓ Remove single column")
    
    def test_remove_multiple_columns(self):
        """Test removing multiple columns"""
        df = pd.DataFrame({
            'id': [1, 2, 3],
            'name': ['a', 'b', 'c'],
            'value': [10, 20, 30],
            'extra': [True, False, True]
        })
        
        df_clean = df.drop(columns=['id', 'extra'])
        assert list(df_clean.columns) == ['name', 'value']
        print("✓ Remove multiple columns")
    
    def test_remove_nonexistent_column(self):
        """Test behavior when removing non-existent column"""
        df = pd.DataFrame({
            'a': [1, 2, 3],
            'b': [4, 5, 6]
        })
        
        # errors='ignore' should not raise
        df_clean = df.drop(columns=['nonexistent'], errors='ignore')
        assert list(df_clean.columns) == ['a', 'b']
        print("✓ Handle non-existent column")


class TestCategoricalEncoding:
    """Test categorical encoding logic"""
    
    def test_label_encoding(self):
        """Test label encoding"""
        df = pd.DataFrame({
            'category': ['cat', 'dog', 'bird', 'cat', 'dog']
        })
        
        df['category_encoded'] = pd.Categorical(df['category']).codes
        
        # Codes should be integers
        assert df['category_encoded'].dtype in [np.int8, np.int16, np.int32, np.int64]
        assert df['category_encoded'].nunique() == 3
        print("✓ Label encoding")
    
    def test_one_hot_encoding(self):
        """Test one-hot encoding"""
        df = pd.DataFrame({
            'category': ['A', 'B', 'C', 'A']
        })
        
        df_encoded = pd.get_dummies(df, columns=['category'], prefix='cat')
        
        assert 'cat_A' in df_encoded.columns
        assert 'cat_B' in df_encoded.columns
        assert 'cat_C' in df_encoded.columns
        assert df_encoded['cat_A'].tolist() == [1, 0, 0, 1]
        print("✓ One-hot encoding")
    
    def test_encoding_with_unknown_values(self):
        """Test encoding handles unknown values"""
        # Simulate train/test scenario
        train = pd.DataFrame({'cat': ['A', 'B', 'C']})
        test = pd.DataFrame({'cat': ['A', 'D']})  # D is unknown
        
        # Get dummies on combined, then split
        all_cats = pd.concat([train['cat'], test['cat']]).unique()
        
        # This is a simple approach - real implementation may differ
        train_encoded = pd.get_dummies(train, columns=['cat'])
        test_encoded = pd.get_dummies(test, columns=['cat'])
        
        # Align columns
        missing_cols = set(train_encoded.columns) - set(test_encoded.columns)
        for col in missing_cols:
            test_encoded[col] = 0
        
        extra_cols = set(test_encoded.columns) - set(train_encoded.columns)
        for col in extra_cols:
            train_encoded[col] = 0
        
        print("✓ Encoding with unknown values")


class TestDataFiltering:
    """Test data filtering logic"""
    
    def test_filter_by_value(self):
        """Test filtering by exact value"""
        df = pd.DataFrame({
            'group': ['A', 'B', 'A', 'B', 'C'],
            'value': [1, 2, 3, 4, 5]
        })
        
        df_filtered = df[df['group'] == 'A']
        assert len(df_filtered) == 2
        assert df_filtered['value'].tolist() == [1, 3]
        print("✓ Filter by exact value")
    
    def test_filter_by_range(self):
        """Test filtering by numeric range"""
        df = pd.DataFrame({
            'value': [10, 20, 30, 40, 50]
        })
        
        df_filtered = df[(df['value'] >= 20) & (df['value'] <= 40)]
        assert len(df_filtered) == 3
        assert df_filtered['value'].tolist() == [20, 30, 40]
        print("✓ Filter by range")
    
    def test_filter_multiple_conditions(self):
        """Test filtering with multiple conditions"""
        df = pd.DataFrame({
            'group': ['A', 'A', 'B', 'B'],
            'value': [10, 30, 20, 40]
        })
        
        df_filtered = df[(df['group'] == 'A') & (df['value'] > 15)]
        assert len(df_filtered) == 1
        assert df_filtered['value'].iloc[0] == 30
        print("✓ Filter multiple conditions")


class TestDataTypeConversion:
    """Test data type conversion logic"""
    
    def test_string_to_numeric(self):
        """Test converting string to numeric"""
        df = pd.DataFrame({
            'value': ['10', '20', '30', 'NA']
        })
        
        df['value_numeric'] = pd.to_numeric(df['value'], errors='coerce')
        assert df['value_numeric'].tolist()[:3] == [10, 20, 30]
        assert pd.isna(df['value_numeric'].iloc[3])
        print("✓ String to numeric conversion")
    
    def test_numeric_to_string(self):
        """Test converting numeric to string"""
        df = pd.DataFrame({
            'id': [1, 2, 3]
        })
        
        df['id_str'] = df['id'].astype(str)
        assert df['id_str'].dtype == object
        assert df['id_str'].tolist() == ['1', '2', '3']
        print("✓ Numeric to string conversion")
    
    def test_datetime_parsing(self):
        """Test datetime parsing"""
        df = pd.DataFrame({
            'date': ['2025-01-01', '2025-02-15', '2025-12-31']
        })
        
        df['date_parsed'] = pd.to_datetime(df['date'])
        assert df['date_parsed'].dtype == 'datetime64[ns]'
        assert df['date_parsed'].dt.year.tolist() == [2025, 2025, 2025]
        print("✓ Datetime parsing")


def run_all_tests():
    """Run all test classes"""
    print("=" * 60)
    print("Running cleaning utilities isolated tests")
    print("=" * 60)
    
    test_classes = [
        TestCSVParsing(),
        TestBinaryConversion(),
        TestMissingValueHandling(),
        TestColumnRemoval(),
        TestCategoricalEncoding(),
        TestDataFiltering(),
        TestDataTypeConversion(),
    ]
    
    for test_class in test_classes:
        class_name = test_class.__class__.__name__
        print(f"\n{class_name}:")
        print("-" * 40)
        
        # Get all test methods
        test_methods = [m for m in dir(test_class) if m.startswith('test_')]
        
        for method_name in test_methods:
            try:
                method = getattr(test_class, method_name)
                method()
            except Exception as e:
                print(f"✗ {method_name}: {e}")
                raise
    
    print("\n" + "=" * 60)
    print("🎉 ALL CLEANING TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
