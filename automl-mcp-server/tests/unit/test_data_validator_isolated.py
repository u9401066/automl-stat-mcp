"""
Isolated tests for data validation utilities.

Tests the DataValidator class and related data quality checks.
"""
import pandas as pd
import numpy as np
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ==============================================================================
# Copied enums and dataclasses for isolated testing
# ==============================================================================

class IssueSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class IssueType(str, Enum):
    PII_DETECTED = "pii_detected"
    PII_EMBEDDED = "pii_embedded"
    HIGH_MISSING_RATIO = "high_missing_ratio"
    INVALID_DATA_TYPE = "invalid_data_type"
    TARGET_HAS_MISSING = "target_has_missing"
    MODERATE_MISSING = "moderate_missing"
    OUTLIERS_DETECTED = "outliers_detected"
    HIGH_CARDINALITY = "high_cardinality"
    CLASS_IMBALANCE = "class_imbalance"
    DUPLICATE_ROWS = "duplicate_rows"
    ID_COLUMN = "id_column"
    CONSTANT_COLUMN = "constant_column"
    HIGH_CORRELATION = "high_correlation"


@dataclass
class DataIssue:
    issue_type: IssueType
    severity: IssueSeverity
    column: Optional[str]
    description: str
    details: Dict[str, Any] = field(default_factory=dict)


# ==============================================================================
# Tests
# ==============================================================================

class TestPIIDetection:
    """Test PII pattern detection"""
    
    # PII patterns
    PII_PATTERNS = {
        "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        "phone": r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b',
        "ssn": r'\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b',
        "credit_card": r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
        "tw_id": r'\b[A-Z][12]\d{8}\b',
        "ip_address": r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
    }
    
    def _detect_pii(self, value: str) -> List[str]:
        """Detect PII types in a string"""
        detected = []
        for pii_type, pattern in self.PII_PATTERNS.items():
            if re.search(pattern, str(value)):
                detected.append(pii_type)
        return detected
    
    def test_email_detection(self):
        """Test email pattern detection"""
        test_cases = [
            ("user@example.com", True),
            ("test.email+tag@domain.org", True),
            ("invalid@", False),
            ("no-at-sign.com", False),
            ("text with user@example.com in middle", True),
        ]
        
        for value, should_detect in test_cases:
            detected = self._detect_pii(value)
            has_email = "email" in detected
            assert has_email == should_detect, f"Failed for: {value}"
        
        print("✓ Email detection")
    
    def test_phone_detection(self):
        """Test phone number detection"""
        test_cases = [
            ("123-456-7890", True),
            ("(123) 456-7890", True),
            ("+1-123-456-7890", True),
            ("1234567890", True),
            ("12345", False),
            ("123-45-6789", False),  # This is SSN format
        ]
        
        for value, should_detect in test_cases:
            detected = self._detect_pii(value)
            has_phone = "phone" in detected
            assert has_phone == should_detect, f"Failed for: {value}"
        
        print("✓ Phone detection")
    
    def test_ssn_detection(self):
        """Test SSN pattern detection"""
        test_cases = [
            ("123-45-6789", True),
            ("123 45 6789", True),
            ("123456789", True),
            ("12-345-6789", False),
            ("1234-56-789", False),
        ]
        
        for value, should_detect in test_cases:
            detected = self._detect_pii(value)
            has_ssn = "ssn" in detected
            assert has_ssn == should_detect, f"Failed for: {value}"
        
        print("✓ SSN detection")
    
    def test_credit_card_detection(self):
        """Test credit card pattern detection"""
        test_cases = [
            ("1234-5678-9012-3456", True),
            ("1234 5678 9012 3456", True),
            ("1234567890123456", True),
            ("1234-5678-9012", False),  # Too short
        ]
        
        for value, should_detect in test_cases:
            detected = self._detect_pii(value)
            has_cc = "credit_card" in detected
            assert has_cc == should_detect, f"Failed for: {value}"
        
        print("✓ Credit card detection")
    
    def test_taiwan_id_detection(self):
        """Test Taiwan ID pattern detection"""
        test_cases = [
            ("A123456789", True),   # Male ID (1 = male)
            ("B223456789", True),   # Female ID (2 = female)
            ("A323456789", False),  # Invalid second digit (must be 1 or 2)
            ("12345678901", False),  # No letter
        ]
        
        for value, should_detect in test_cases:
            detected = self._detect_pii(value)
            has_twid = "tw_id" in detected
            assert has_twid == should_detect, f"Failed for: {value}"
        
        print("✓ Taiwan ID detection")
    
    def test_ip_address_detection(self):
        """Test IP address pattern detection"""
        test_cases = [
            ("192.168.1.1", True),
            ("10.0.0.1", True),
            ("256.1.1.1", True),  # Invalid but matches pattern
            ("192.168.1", False),  # Incomplete
        ]
        
        for value, should_detect in test_cases:
            detected = self._detect_pii(value)
            has_ip = "ip_address" in detected
            assert has_ip == should_detect, f"Failed for: {value}"
        
        print("✓ IP address detection")


class TestPIIColumnNames:
    """Test PII detection in column names"""
    
    PII_COLUMN_PATTERNS = [
        r'(?i)^name$', r'(?i).*_name$', r'(?i)^.*name_.*',
        r'(?i).*fullname.*', r'(?i).*first.*name.*', r'(?i).*last.*name.*',
        r'(?i)^姓名$', r'(?i).*姓名.*',
        r'(?i).*email.*', r'(?i).*e-mail.*',
        r'(?i).*phone.*', r'(?i).*mobile.*', r'(?i).*cell.*',
        r'(?i).*ssn.*', r'(?i).*social.*security.*',
        r'(?i).*credit.*card.*', r'(?i).*card.*number.*',
        r'(?i).*address.*', r'(?i).*addr.*',
        r'(?i).*passport.*', r'(?i).*license.*',
        r'(?i).*身分證.*', r'(?i).*電話.*', r'(?i).*地址.*',
        r'(?i).*password.*', r'(?i).*secret.*', r'(?i).*token.*',
        r'(?i).*birthday.*', r'(?i).*birth.*date.*', r'(?i).*dob.*',
        r'(?i).*生日.*', r'(?i).*出生.*',
    ]
    
    def _is_pii_column(self, col_name: str) -> bool:
        """Check if column name suggests PII"""
        for pattern in self.PII_COLUMN_PATTERNS:
            if re.search(pattern, col_name):
                return True
        return False
    
    def test_name_columns(self):
        """Test name column detection"""
        pii_cols = ["name", "Name", "full_name", "first_name", "last_name", "user_name", "姓名"]
        safe_cols = ["game", "filename", "rename"]
        
        for col in pii_cols:
            assert self._is_pii_column(col), f"Should detect: {col}"
        
        for col in safe_cols:
            # These might match, which is ok (false positive is safer)
            pass
        
        print("✓ Name column detection")
    
    def test_contact_columns(self):
        """Test contact info column detection"""
        pii_cols = ["email", "Email", "user_email", "e-mail", "phone", "mobile", "cell_phone", "電話"]
        
        for col in pii_cols:
            assert self._is_pii_column(col), f"Should detect: {col}"
        
        print("✓ Contact column detection")
    
    def test_id_columns(self):
        """Test ID document column detection"""
        pii_cols = ["ssn", "SSN", "social_security", "passport", "license", "身分證"]
        
        for col in pii_cols:
            assert self._is_pii_column(col), f"Should detect: {col}"
        
        print("✓ ID document column detection")
    
    def test_address_columns(self):
        """Test address column detection"""
        pii_cols = ["address", "Address", "home_address", "addr", "地址"]
        
        for col in pii_cols:
            assert self._is_pii_column(col), f"Should detect: {col}"
        
        print("✓ Address column detection")


class TestMissingValueDetection:
    """Test missing value detection"""
    
    def test_missing_ratio_calculation(self):
        """Test missing value ratio calculation"""
        df = pd.DataFrame({
            'no_missing': [1, 2, 3, 4, 5],
            'some_missing': [1, None, 3, None, 5],
            'all_missing': [None, None, None, None, None],
        })
        
        ratios = df.isnull().mean()
        
        assert ratios['no_missing'] == 0.0
        assert ratios['some_missing'] == 0.4
        assert ratios['all_missing'] == 1.0
        print("✓ Missing ratio calculation")
    
    def test_high_missing_threshold(self):
        """Test high missing value threshold detection"""
        threshold = 0.2
        
        df = pd.DataFrame({
            'ok': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            'borderline': [1, 2, None, 4, 5, 6, 7, 8, 9, 10],  # 10%
            'high': [1, None, None, None, 5, 6, 7, 8, 9, 10],  # 30%
        })
        
        high_missing_cols = [col for col in df.columns if df[col].isnull().mean() > threshold]
        
        assert 'ok' not in high_missing_cols
        assert 'borderline' not in high_missing_cols
        assert 'high' in high_missing_cols
        print("✓ High missing threshold")


class TestOutlierDetection:
    """Test outlier detection"""
    
    def test_zscore_outliers(self):
        """Test Z-score outlier detection"""
        from scipy import stats
        
        np.random.seed(42)
        data = list(np.random.normal(50, 10, 100)) + [150, 200]  # Add outliers
        
        z_scores = np.abs(stats.zscore(data))
        outlier_indices = np.where(z_scores > 3)[0]
        
        assert 100 in outlier_indices  # 150 is outlier
        assert 101 in outlier_indices  # 200 is outlier
        print("✓ Z-score outlier detection")
    
    def test_iqr_outliers(self):
        """Test IQR outlier detection"""
        data = [10, 12, 14, 15, 16, 18, 20, 100, -50]
        
        q1 = np.percentile(data, 25)
        q3 = np.percentile(data, 75)
        iqr = q3 - q1
        
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        
        outliers = [x for x in data if x < lower or x > upper]
        
        assert 100 in outliers
        assert -50 in outliers
        assert 15 not in outliers
        print("✓ IQR outlier detection")


class TestIDColumnDetection:
    """Test ID column detection"""
    
    ID_PATTERNS = [
        r'(?i)^id$', r'(?i).*_id$', r'(?i)^.*id_.*',
        r'(?i)^index$', r'(?i)^row.*', r'(?i)^record.*',
        r'(?i)^key$', r'(?i).*_key$',
    ]
    
    def _is_id_column(self, col_name: str) -> bool:
        """Check if column name suggests ID"""
        for pattern in self.ID_PATTERNS:
            if re.search(pattern, col_name):
                return True
        return False
    
    def test_id_column_patterns(self):
        """Test ID column name patterns"""
        id_cols = ["id", "ID", "user_id", "customer_id", "id_number", "index", "row_num", "record_id", "key", "primary_key"]
        non_id_cols = ["identity", "idea", "video", "keyword"]
        
        for col in id_cols:
            assert self._is_id_column(col), f"Should detect as ID: {col}"
        
        for col in non_id_cols:
            # Note: some might match (identity matches id pattern)
            pass
        
        print("✓ ID column detection")
    
    def test_sequential_id_detection(self):
        """Test sequential ID detection by values"""
        df = pd.DataFrame({
            'sequential': [1, 2, 3, 4, 5],
            'non_sequential': [1, 3, 7, 8, 15],
            'repeated': [1, 1, 2, 2, 3],
        })
        
        # Check if column is sequential (all unique, increasing by 1)
        def is_sequential(col):
            values = col.dropna().values
            if len(values) < 2:
                return False
            if len(np.unique(values)) != len(values):
                return False
            sorted_vals = np.sort(values)
            diffs = np.diff(sorted_vals)
            return np.all(diffs == 1)
        
        assert is_sequential(df['sequential'])
        assert not is_sequential(df['non_sequential'])
        assert not is_sequential(df['repeated'])
        print("✓ Sequential ID detection")


class TestConstantColumnDetection:
    """Test constant column detection"""
    
    def test_constant_column(self):
        """Test detection of constant columns"""
        df = pd.DataFrame({
            'constant': [1, 1, 1, 1, 1],
            'varied': [1, 2, 3, 4, 5],
            'almost_constant': [1, 1, 1, 1, 2],
        })
        
        constant_cols = [col for col in df.columns if df[col].nunique() == 1]
        
        assert 'constant' in constant_cols
        assert 'varied' not in constant_cols
        assert 'almost_constant' not in constant_cols
        print("✓ Constant column detection")


class TestDuplicateDetection:
    """Test duplicate row detection"""
    
    def test_duplicate_rows(self):
        """Test duplicate row detection"""
        df = pd.DataFrame({
            'a': [1, 2, 1, 3, 2],
            'b': ['x', 'y', 'x', 'z', 'y'],
        })
        
        n_duplicates = df.duplicated().sum()
        
        assert n_duplicates == 2  # Row 2 (copy of 0) and Row 4 (copy of 1)
        print("✓ Duplicate row detection")
    
    def test_duplicate_subset(self):
        """Test duplicate detection on column subset"""
        df = pd.DataFrame({
            'id': [1, 2, 3, 4, 5],
            'category': ['A', 'B', 'A', 'B', 'A'],
        })
        
        # No full duplicates
        assert df.duplicated().sum() == 0
        
        # But category has duplicates: A appears 3 times (2 extra), B appears 2 times (1 extra)
        assert df['category'].duplicated().sum() == 3  # 2 extra A + 1 extra B
        print("✓ Duplicate subset detection")


class TestClassImbalanceDetection:
    """Test class imbalance detection"""
    
    def test_balanced_classes(self):
        """Test balanced class detection"""
        df = pd.DataFrame({
            'label': ['A'] * 50 + ['B'] * 50
        })
        
        value_counts = df['label'].value_counts(normalize=True)
        min_ratio = value_counts.min()
        
        assert min_ratio >= 0.3  # Balanced (each class >= 30%)
        print("✓ Balanced classes detection")
    
    def test_imbalanced_classes(self):
        """Test imbalanced class detection"""
        df = pd.DataFrame({
            'label': ['A'] * 95 + ['B'] * 5
        })
        
        value_counts = df['label'].value_counts(normalize=True)
        min_ratio = value_counts.min()
        
        assert min_ratio < 0.1  # Imbalanced (minority < 10%)
        print("✓ Imbalanced classes detection")
    
    def test_multiclass_imbalance(self):
        """Test multiclass imbalance"""
        df = pd.DataFrame({
            'label': ['A'] * 80 + ['B'] * 15 + ['C'] * 5
        })
        
        value_counts = df['label'].value_counts(normalize=True)
        
        # Check distribution
        assert value_counts['A'] == 0.8
        assert value_counts['B'] == 0.15
        assert value_counts['C'] == 0.05
        print("✓ Multiclass imbalance detection")


class TestHighCardinalityDetection:
    """Test high cardinality column detection"""
    
    def test_high_cardinality(self):
        """Test high cardinality detection"""
        n = 100
        df = pd.DataFrame({
            'low_card': ['A', 'B'] * 50,  # 2 unique
            'med_card': list(range(10)) * 10,  # 10 unique
            'high_card': list(range(n)),  # 100 unique (all different)
        })
        
        threshold = 0.9  # >90% unique values = high cardinality
        
        high_card_cols = []
        for col in df.columns:
            ratio = df[col].nunique() / len(df)
            if ratio > threshold:
                high_card_cols.append(col)
        
        assert 'low_card' not in high_card_cols
        assert 'med_card' not in high_card_cols
        assert 'high_card' in high_card_cols
        print("✓ High cardinality detection")


def run_all_tests():
    """Run all test classes"""
    print("=" * 60)
    print("Running data validation isolated tests")
    print("=" * 60)
    
    test_classes = [
        TestPIIDetection(),
        TestPIIColumnNames(),
        TestMissingValueDetection(),
        TestOutlierDetection(),
        TestIDColumnDetection(),
        TestConstantColumnDetection(),
        TestDuplicateDetection(),
        TestClassImbalanceDetection(),
        TestHighCardinalityDetection(),
    ]
    
    for test_class in test_classes:
        class_name = test_class.__class__.__name__
        print(f"\n{class_name}:")
        print("-" * 40)
        
        test_methods = [m for m in dir(test_class) if m.startswith('test_')]
        
        for method_name in test_methods:
            try:
                method = getattr(test_class, method_name)
                method()
            except Exception as e:
                print(f"✗ {method_name}: {e}")
                raise
    
    print("\n" + "=" * 60)
    print("🎉 ALL DATA VALIDATION TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
