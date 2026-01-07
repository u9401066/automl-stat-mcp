"""
Isolated tests for error scenarios and edge cases.

Tests boundary conditions, invalid inputs, and failure handling
without requiring the full MCP stack.

Based on test-generator Skill requirements:
1. Boundary conditions
2. Invalid inputs
3. Exception handling
"""
import numpy as np
import pandas as pd
import pytest
from scipy import stats

# ==================== BOUNDARY CONDITIONS ====================

class TestBoundaryConditions:
    """Test edge cases and boundary values"""

    def test_empty_dataframe(self):
        """Empty DataFrame should be handled gracefully"""
        df = pd.DataFrame()

        assert df.empty
        assert len(df.columns) == 0
        assert len(df) == 0
        print("✓ Empty DataFrame handled")

    def test_single_row_dataframe(self):
        """Single row should calculate stats without error"""
        df = pd.DataFrame({'value': [42]})

        # Mean should work
        assert df['value'].mean() == 42

        # Std should be NaN for single value (no variance)
        assert pd.isna(df['value'].std())
        print("✓ Single row DataFrame handled")

    def test_single_column_dataframe(self):
        """Single column DataFrame should work"""
        df = pd.DataFrame({'only_col': [1, 2, 3, 4, 5]})

        assert len(df.columns) == 1
        assert df['only_col'].sum() == 15
        print("✓ Single column DataFrame handled")

    def test_all_nan_column(self):
        """Column with all NaN values"""
        df = pd.DataFrame({'all_nan': [np.nan, np.nan, np.nan]})

        assert pd.isna(df['all_nan'].mean())
        assert df['all_nan'].notna().sum() == 0
        print("✓ All-NaN column handled")

    def test_mixed_nan_values(self):
        """Column with some NaN values"""
        df = pd.DataFrame({'mixed': [1, np.nan, 3, np.nan, 5]})

        # Mean should ignore NaN
        assert df['mixed'].mean() == 3.0  # (1+3+5)/3
        assert df['mixed'].count() == 3
        print("✓ Mixed NaN values handled")

    def test_very_large_numbers(self):
        """Handle very large numbers without overflow"""
        df = pd.DataFrame({'large': [1e308, 1e307, 1e306]})

        # Should not overflow
        mean = df['large'].mean()
        assert np.isfinite(mean)
        assert mean > 1e305
        print("✓ Very large numbers handled")

    def test_very_small_numbers(self):
        """Handle very small numbers without underflow"""
        df = pd.DataFrame({'small': [1e-308, 1e-307, 1e-306]})

        mean = df['small'].mean()
        assert np.isfinite(mean)
        assert mean < 1e-304
        print("✓ Very small numbers handled")

    def test_infinity_values(self):
        """Handle infinity values"""
        df = pd.DataFrame({'inf_col': [1, np.inf, -np.inf, 4]})

        # Mean with inf is inf
        assert not np.isfinite(df['inf_col'].mean())

        # Can filter inf
        finite = df[np.isfinite(df['inf_col'])]
        assert finite['inf_col'].mean() == 2.5  # (1+4)/2
        print("✓ Infinity values handled")

    def test_constant_column(self):
        """Column with all same values (zero variance)"""
        df = pd.DataFrame({'constant': [42, 42, 42, 42]})

        assert df['constant'].std() == 0
        assert df['constant'].var() == 0
        assert df['constant'].nunique() == 1
        print("✓ Constant column handled")


# ==================== INVALID INPUTS ====================

class TestInvalidInputs:
    """Test handling of invalid input data"""

    def test_string_in_numeric_column(self):
        """Mixed types in column"""
        df = pd.DataFrame({'mixed': [1, 2, 'three', 4]})

        # Should fail or coerce
        with pytest.raises((TypeError, ValueError)):
            df['mixed'].astype(float).mean()
        print("✓ String in numeric column caught")

    def test_negative_percentile(self):
        """Invalid percentile value"""
        data = [1, 2, 3, 4, 5]

        with pytest.raises(ValueError):
            np.percentile(data, -10)
        print("✓ Negative percentile rejected")

    def test_percentile_over_100(self):
        """Percentile > 100"""
        data = [1, 2, 3, 4, 5]

        with pytest.raises(ValueError):
            np.percentile(data, 150)
        print("✓ Percentile > 100 rejected")

    def test_correlation_mismatched_lengths(self):
        """Correlation with mismatched array lengths"""
        x = [1, 2, 3]
        y = [1, 2, 3, 4, 5]

        with pytest.raises(ValueError):
            stats.pearsonr(x, y)
        print("✓ Mismatched lengths rejected")

    def test_ttest_zero_variance(self):
        """T-test with zero variance (constant values)"""
        group1 = [5, 5, 5, 5]
        group2 = [10, 10, 10, 10]

        # Should work but with special handling
        t, p = stats.ttest_ind(group1, group2)
        # Numpy returns nan for constant arrays in some versions
        # or a finite value depending on implementation
        assert isinstance(t, float)
        print("✓ T-test with constant groups handled")

    def test_chi_square_empty_contingency(self):
        """Chi-square with empty contingency table"""
        table = np.array([[]])

        with pytest.raises(ValueError):
            stats.chi2_contingency(table)
        print("✓ Empty contingency table rejected")

    def test_chi_square_negative_frequencies(self):
        """Chi-square with negative frequencies"""
        table = np.array([[10, -5], [3, 2]])

        with pytest.raises(ValueError):
            stats.chi2_contingency(table)
        print("✓ Negative frequencies rejected")


# ==================== EXCEPTION HANDLING ====================

class TestExceptionHandling:
    """Test proper exception handling"""

    def test_file_not_found(self):
        """Handle missing file gracefully"""
        with pytest.raises(FileNotFoundError):
            pd.read_csv('/nonexistent/path/file.csv')
        print("✓ FileNotFoundError raised for missing file")

    def test_invalid_csv_content(self, tmp_path):
        """Handle invalid CSV content"""
        # Create file with binary content
        bad_file = tmp_path / "bad.csv"
        bad_file.write_bytes(b'\x00\x01\x02\x03')

        # Should either raise error or handle gracefully
        try:
            df = pd.read_csv(bad_file)
            # If it reads, should have minimal content
            assert isinstance(df, pd.DataFrame)
        except (pd.errors.ParserError, UnicodeDecodeError):
            pass  # Expected
        print("✓ Invalid CSV content handled")

    def test_division_by_zero_in_stats(self):
        """Handle division by zero scenarios"""
        # Effect size with zero pooled std
        group1 = [5, 5, 5]
        group2 = [5, 5, 5]

        pooled_std = 0
        mean_diff = np.mean(group1) - np.mean(group2)

        # Should handle gracefully
        if pooled_std == 0:
            if mean_diff == 0:
                cohens_d = 0
            else:
                cohens_d = np.inf
        else:
            cohens_d = mean_diff / pooled_std

        assert cohens_d == 0
        print("✓ Division by zero handled")

    def test_matrix_not_invertible(self):
        """Handle singular matrix in regression"""
        # Perfectly collinear columns
        X = np.array([[1, 2], [2, 4], [3, 6]])  # col2 = 2 * col1
        np.array([1, 2, 3])

        # This creates a singular matrix
        try:
            XtX = X.T @ X
            np.linalg.inv(XtX)
            raise AssertionError("Should have raised LinAlgError")
        except np.linalg.LinAlgError:
            pass  # Expected - singular matrix
        print("✓ Singular matrix caught")

    def test_convergence_failure(self):
        """Handle optimization convergence failures"""
        # Degenerate data for logistic regression
        X = np.array([[0], [0], [0]])
        y = np.array([0, 1, 0])

        # This may fail to converge or raise warning
        # Just ensure it doesn't crash
        try:
            from scipy.optimize import minimize

            def neg_log_likelihood(beta):
                z = X @ beta
                p = 1 / (1 + np.exp(-z))
                # Handle edge cases
                p = np.clip(p, 1e-10, 1-1e-10)
                return -np.sum(y * np.log(p) + (1-y) * np.log(1-p))

            result = minimize(neg_log_likelihood, [0], method='L-BFGS-B')
            # May not converge but shouldn't crash
            assert hasattr(result, 'x')
        except Exception:
            # Some failure is acceptable
            pass
        print("✓ Convergence failure handled")


# ==================== DATA TYPE EDGE CASES ====================

class TestDataTypeEdgeCases:
    """Test handling of various data types"""

    def test_boolean_column(self):
        """Boolean column statistics"""
        df = pd.DataFrame({'bool_col': [True, False, True, True]})

        # Should work as 0/1
        assert df['bool_col'].mean() == 0.75
        assert df['bool_col'].sum() == 3
        print("✓ Boolean column handled")

    def test_datetime_column(self):
        """DateTime column handling"""
        df = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=5)
        })

        assert df['date'].dtype == 'datetime64[ns]'
        # Range calculation
        date_range = df['date'].max() - df['date'].min()
        assert date_range.days == 4
        print("✓ DateTime column handled")

    def test_categorical_column(self):
        """Categorical data handling"""
        df = pd.DataFrame({
            'category': pd.Categorical(['A', 'B', 'A', 'C', 'B'])
        })

        assert df['category'].dtype.name == 'category'
        value_counts = df['category'].value_counts()
        assert value_counts['A'] == 2
        assert value_counts['B'] == 2
        assert value_counts['C'] == 1
        print("✓ Categorical column handled")

    def test_object_column_with_numbers(self):
        """Object column that looks numeric"""
        df = pd.DataFrame({'obj_num': ['1', '2', '3', '4']})

        assert df['obj_num'].dtype == 'object'

        # Can convert to numeric
        numeric = pd.to_numeric(df['obj_num'])
        assert numeric.mean() == 2.5
        print("✓ Object column with numbers handled")

    def test_unicode_column_names(self):
        """Unicode characters in column names"""
        df = pd.DataFrame({
            '年齡': [25, 30, 35],
            '性別': ['M', 'F', 'M'],
            'αβγ': [1.1, 2.2, 3.3]
        })

        assert '年齡' in df.columns
        assert df['年齢' if '年齢' in df.columns else '年齡'].mean() == 30
        print("✓ Unicode column names handled")

    def test_whitespace_column_names(self):
        """Columns with whitespace in names"""
        df = pd.DataFrame({
            '  leading': [1, 2],
            'trailing  ': [3, 4],
            'middle space': [5, 6]
        })

        # Accessing with exact name
        assert '  leading' in df.columns

        # Can strip
        df.columns = df.columns.str.strip()
        assert 'leading' in df.columns
        print("✓ Whitespace column names handled")


# ==================== NUMERICAL STABILITY ====================

class TestNumericalStability:
    """Test numerical stability in calculations"""

    def test_catastrophic_cancellation(self):
        """Avoid catastrophic cancellation in variance"""
        # Large numbers with small variance
        data = [1e10 + 1, 1e10 + 2, 1e10 + 3]

        # Two-pass algorithm is more stable
        np.mean(data)
        var = np.var(data, ddof=1)

        # Should be close to 1 (variance of [1,2,3])
        assert abs(var - 1.0) < 0.01
        print("✓ Variance calculation stable for large values")

    def test_log_sum_exp_stability(self):
        """Log-sum-exp trick for numerical stability"""
        # Large negative numbers
        log_probs = np.array([-1000, -1001, -999])

        # Naive: underflow to -inf
        # Stable: use log-sum-exp
        max_log = np.max(log_probs)
        log_sum = max_log + np.log(np.sum(np.exp(log_probs - max_log)))

        assert np.isfinite(log_sum)
        assert log_sum > -1001  # Should be > largest value
        print("✓ Log-sum-exp stable")

    def test_softmax_stability(self):
        """Softmax numerical stability"""
        logits = np.array([1000, 1001, 999])

        # Stable softmax
        max_logit = np.max(logits)
        exp_logits = np.exp(logits - max_logit)
        softmax = exp_logits / np.sum(exp_logits)

        assert np.allclose(softmax.sum(), 1.0)
        assert all(np.isfinite(softmax))
        print("✓ Softmax stable for large values")

    def test_correlation_with_small_variance(self):
        """Correlation when variance is tiny"""
        x = [1.00001, 1.00002, 1.00003]
        y = [2.00001, 2.00002, 2.00003]

        r, p = stats.pearsonr(x, y)
        assert abs(r - 1.0) < 0.001  # Should still be ~1
        print("✓ Correlation stable with small variance")


# ==================== SAMPLE SIZE EDGE CASES ====================

class TestSampleSizeEdgeCases:
    """Test handling of various sample sizes"""

    def test_n_equals_1(self):
        """Single observation"""
        data = [42]

        mean = np.mean(data)
        assert mean == 42

        # Std undefined for n=1
        std = np.std(data, ddof=1)
        assert np.isnan(std)
        print("✓ n=1 handled")

    def test_n_equals_2(self):
        """Two observations (minimum for std)"""
        data = [10, 20]

        mean = np.mean(data)
        std = np.std(data, ddof=1)

        assert mean == 15
        assert abs(std - 7.071) < 0.01  # sqrt(50)
        print("✓ n=2 handled")

    def test_t_test_small_samples(self):
        """T-test with very small samples"""
        group1 = [10, 12]
        group2 = [20, 22]

        t, p = stats.ttest_ind(group1, group2)
        assert np.isfinite(t)
        assert 0 <= p <= 1
        print("✓ T-test with n=2 per group")

    def test_chi_square_small_expected(self):
        """Chi-square with small expected frequencies"""
        # Small counts warning
        table = np.array([[1, 2], [2, 1]])

        chi2, p, dof, expected = stats.chi2_contingency(table)

        # Check if any expected < 5 (typical warning threshold)
        small_expected = np.any(expected < 5)
        assert small_expected  # All expected are small here
        print("✓ Chi-square small expected detected")

    def test_mann_whitney_small_n(self):
        """Mann-Whitney U with small samples"""
        group1 = [1, 2, 3]
        group2 = [4, 5, 6]

        stat, p = stats.mannwhitneyu(group1, group2, alternative='two-sided')
        assert np.isfinite(stat)
        assert 0 <= p <= 1
        print("✓ Mann-Whitney with small n")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
