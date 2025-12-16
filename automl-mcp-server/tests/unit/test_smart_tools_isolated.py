#!/usr/bin/env python3
"""
Isolated tests for smart_tools.py

Tests the smart workflow utilities without requiring MCP/FastMCP dependencies.
Following the test-generator Skill guidelines.

Test Coverage:
- Ticket generation and structure
- CSV parsing (normal and base64)
- Issue formatting
- Question generation from issues
- Cleaning action defaults
"""

import pytest
import base64
import io
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum


# ============================================================
# Isolated implementations (copied from smart_tools.py)
# ============================================================

class IssueSeverity(Enum):
    """Severity levels for data issues"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class IssueType(Enum):
    """Types of data issues"""
    PII_DETECTED = "pii_detected"
    HIGH_MISSING_RATIO = "high_missing_ratio"
    OUTLIERS_DETECTED = "outliers_detected"
    CONSTANT_COLUMN = "constant_column"
    HIGH_CARDINALITY = "high_cardinality"
    DUPLICATE_ROWS = "duplicate_rows"


@dataclass
class DataIssue:
    """Represents a single data issue"""
    issue_type: IssueType
    severity: IssueSeverity
    column: Optional[str]
    message: str
    details: Dict[str, Any]
    suggested_action: str
    
    def to_dict(self) -> dict:
        return {
            "issue_type": self.issue_type.value,
            "severity": self.severity.value,
            "column": self.column,
            "message": self.message,
            "details": self.details,
            "suggested_action": self.suggested_action,
        }


@dataclass
class ValidationReport:
    """Validation report containing all issues"""
    issues: List[DataIssue]
    
    @property
    def total_issues(self) -> int:
        return len(self.issues)
    
    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == IssueSeverity.CRITICAL)
    
    @property
    def high_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == IssueSeverity.HIGH)
    
    @property
    def medium_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == IssueSeverity.MEDIUM)
    
    @property
    def low_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == IssueSeverity.LOW)
    
    @property
    def can_proceed(self) -> bool:
        return self.critical_count == 0


def parse_csv_content(csv_content: str, is_base64: bool = False) -> 'pd.DataFrame':
    """Parse CSV content into DataFrame"""
    import pandas as pd
    if is_base64:
        decoded = base64.b64decode(csv_content).decode("utf-8")
        return pd.read_csv(io.StringIO(decoded))
    return pd.read_csv(io.StringIO(csv_content))


def format_issues_for_response(report: ValidationReport) -> List[dict]:
    """Convert ValidationReport issues to dict for JSON response"""
    return [issue.to_dict() for issue in report.issues]


def generate_questions_from_issues(report: ValidationReport) -> List[str]:
    """Generate user questions based on detected issues"""
    questions = []
    
    # Critical issues first
    critical_issues = [i for i in report.issues if i.severity == IssueSeverity.CRITICAL]
    if critical_issues:
        pii_issues = [i for i in critical_issues if i.issue_type == IssueType.PII_DETECTED]
        if pii_issues:
            cols = [i.column for i in pii_issues if i.column]
            questions.append(
                f"⚠️ CRITICAL: PII detected in columns: {cols}. "
                "Options: mask (replace with ***), hash (SHA256), or drop these columns?"
            )
    
    # High severity
    high_issues = [i for i in report.issues if i.severity == IssueSeverity.HIGH]
    for issue in high_issues:
        if issue.issue_type == IssueType.HIGH_MISSING_RATIO:
            questions.append(
                f"Missing values found in '{issue.column}' "
                f"({issue.details.get('missing_pct', 0):.1f}% missing). "
                "Options: drop rows, drop column, or impute (mean/median/mode)?"
            )
    
    # Medium severity
    medium_issues = [i for i in report.issues if i.severity == IssueSeverity.MEDIUM]
    outlier_issues = [i for i in medium_issues if i.issue_type == IssueType.OUTLIERS_DETECTED]
    if outlier_issues:
        cols = [i.column for i in outlier_issues if i.column]
        questions.append(
            f"Outliers detected in: {cols[:5]}{'...' if len(cols) > 5 else ''}. "
            "Options: cap to IQR bounds, remove, or keep as-is?"
        )
    
    # Always add storage question
    questions.append(
        "Do you want to save this dataset for future use, or is this a one-time analysis?"
    )
    
    return questions


def generate_ticket_id() -> str:
    """Generate unique ticket ID"""
    return f"analysis-{uuid.uuid4().hex[:12]}"


def create_ticket_structure(
    ticket_id: str,
    user_id: str,
    data_preview: dict,
    validation_report: ValidationReport,
    analysis_purpose: Optional[str] = None,
    target_column: Optional[str] = None,
) -> dict:
    """Create ticket structure"""
    suggested_questions = generate_questions_from_issues(validation_report)
    
    return {
        "ticket_id": ticket_id,
        "ticket_type": "data_analysis",
        "status": "pending_user_decision",
        "created_at": datetime.utcnow().isoformat(),
        "user_id": user_id,
        "data_preview": data_preview,
        "data_issues": {
            "total_issues": validation_report.total_issues,
            "requires_attention": not validation_report.can_proceed,
            "can_proceed": validation_report.can_proceed,
            "summary": {
                "critical": validation_report.critical_count,
                "high": validation_report.high_count,
                "medium": validation_report.medium_count,
                "low": validation_report.low_count,
            },
            "issues": format_issues_for_response(validation_report),
        },
        "analysis_context": {
            "purpose": analysis_purpose,
            "target_column": target_column,
        },
        "suggested_questions": suggested_questions,
    }


def get_default_cleaning_actions(report: ValidationReport) -> Dict[str, Any]:
    """Get default cleaning actions for issues"""
    actions = {
        "missing_values": {},
        "pii": {},
        "outliers": {},
        "invalid_columns": [],
        "duplicates": "keep",
    }
    
    for issue in report.issues:
        if issue.issue_type == IssueType.HIGH_MISSING_RATIO and issue.column:
            actions["missing_values"][issue.column] = "impute_median"
        elif issue.issue_type == IssueType.PII_DETECTED and issue.column:
            actions["pii"][issue.column] = "mask"
        elif issue.issue_type == IssueType.OUTLIERS_DETECTED and issue.column:
            actions["outliers"][issue.column] = "cap_iqr"
        elif issue.issue_type == IssueType.CONSTANT_COLUMN and issue.column:
            actions["invalid_columns"].append(issue.column)
        elif issue.issue_type == IssueType.DUPLICATE_ROWS:
            actions["duplicates"] = "drop"
    
    return actions


# ============================================================
# TEST CLASSES
# ============================================================

class TestCSVParsing:
    """Tests for CSV parsing utilities"""
    
    def test_parse_normal_csv(self):
        """Parse normal CSV string"""
        csv = "name,age,score\nAlice,30,85\nBob,25,90"
        df = parse_csv_content(csv)
        assert len(df) == 2
        assert list(df.columns) == ["name", "age", "score"]
        
    def test_parse_base64_csv(self):
        """Parse base64 encoded CSV"""
        csv = "name,age\nAlice,30\nBob,25"
        encoded = base64.b64encode(csv.encode()).decode()
        df = parse_csv_content(encoded, is_base64=True)
        assert len(df) == 2
        assert "name" in df.columns
        
    def test_parse_csv_with_missing_values(self):
        """Parse CSV with missing values"""
        csv = "a,b,c\n1,,3\n4,5,\n,8,9"
        df = parse_csv_content(csv)
        assert df["a"].isna().sum() == 1
        assert df["b"].isna().sum() == 1
        assert df["c"].isna().sum() == 1
        
    def test_parse_csv_with_unicode(self):
        """Parse CSV with unicode characters"""
        csv = "名字,年齡\n張三,30\n李四,25"
        df = parse_csv_content(csv)
        assert len(df) == 2
        assert "名字" in df.columns


class TestTicketGeneration:
    """Tests for ticket generation"""
    
    def test_ticket_id_format(self):
        """Ticket ID follows expected format"""
        ticket_id = generate_ticket_id()
        assert ticket_id.startswith("analysis-")
        assert len(ticket_id) == 21  # "analysis-" + 12 hex chars
        
    def test_ticket_ids_unique(self):
        """Ticket IDs are unique"""
        ids = [generate_ticket_id() for _ in range(100)]
        assert len(set(ids)) == 100
        
    def test_ticket_structure(self):
        """Ticket has required fields"""
        report = ValidationReport(issues=[])
        ticket = create_ticket_structure(
            ticket_id="analysis-abc123",
            user_id="user1",
            data_preview={"rows": 100, "columns": 5},
            validation_report=report,
        )
        
        assert "ticket_id" in ticket
        assert "ticket_type" in ticket
        assert "status" in ticket
        assert "user_id" in ticket
        assert "data_preview" in ticket
        assert "data_issues" in ticket
        assert "analysis_context" in ticket
        assert "suggested_questions" in ticket
        
    def test_ticket_status_pending(self):
        """New ticket has pending status"""
        report = ValidationReport(issues=[])
        ticket = create_ticket_structure(
            ticket_id="test",
            user_id="user1",
            data_preview={},
            validation_report=report,
        )
        assert ticket["status"] == "pending_user_decision"
        
    def test_ticket_with_analysis_context(self):
        """Ticket includes analysis context"""
        report = ValidationReport(issues=[])
        ticket = create_ticket_structure(
            ticket_id="test",
            user_id="user1",
            data_preview={},
            validation_report=report,
            analysis_purpose="ML training",
            target_column="outcome",
        )
        assert ticket["analysis_context"]["purpose"] == "ML training"
        assert ticket["analysis_context"]["target_column"] == "outcome"


class TestValidationReport:
    """Tests for ValidationReport"""
    
    def test_empty_report(self):
        """Empty report has zero counts"""
        report = ValidationReport(issues=[])
        assert report.total_issues == 0
        assert report.critical_count == 0
        assert report.can_proceed == True
        
    def test_report_with_critical_issue(self):
        """Report with critical issue cannot proceed"""
        issue = DataIssue(
            issue_type=IssueType.PII_DETECTED,
            severity=IssueSeverity.CRITICAL,
            column="email",
            message="PII detected",
            details={},
            suggested_action="mask",
        )
        report = ValidationReport(issues=[issue])
        assert report.critical_count == 1
        assert report.can_proceed == False
        
    def test_report_severity_counts(self):
        """Report correctly counts severities"""
        issues = [
            DataIssue(IssueType.PII_DETECTED, IssueSeverity.CRITICAL, "a", "", {}, ""),
            DataIssue(IssueType.HIGH_MISSING_RATIO, IssueSeverity.HIGH, "b", "", {}, ""),
            DataIssue(IssueType.HIGH_MISSING_RATIO, IssueSeverity.HIGH, "c", "", {}, ""),
            DataIssue(IssueType.OUTLIERS_DETECTED, IssueSeverity.MEDIUM, "d", "", {}, ""),
            DataIssue(IssueType.CONSTANT_COLUMN, IssueSeverity.LOW, "e", "", {}, ""),
        ]
        report = ValidationReport(issues=issues)
        assert report.total_issues == 5
        assert report.critical_count == 1
        assert report.high_count == 2
        assert report.medium_count == 1
        assert report.low_count == 1


class TestIssueFormatting:
    """Tests for issue formatting"""
    
    def test_format_single_issue(self):
        """Format single issue to dict"""
        issue = DataIssue(
            issue_type=IssueType.PII_DETECTED,
            severity=IssueSeverity.CRITICAL,
            column="email",
            message="Email detected",
            details={"pattern": "email"},
            suggested_action="mask",
        )
        report = ValidationReport(issues=[issue])
        formatted = format_issues_for_response(report)
        
        assert len(formatted) == 1
        assert formatted[0]["issue_type"] == "pii_detected"
        assert formatted[0]["severity"] == "critical"
        assert formatted[0]["column"] == "email"
        
    def test_format_multiple_issues(self):
        """Format multiple issues"""
        issues = [
            DataIssue(IssueType.PII_DETECTED, IssueSeverity.CRITICAL, "a", "", {}, ""),
            DataIssue(IssueType.OUTLIERS_DETECTED, IssueSeverity.MEDIUM, "b", "", {}, ""),
        ]
        report = ValidationReport(issues=issues)
        formatted = format_issues_for_response(report)
        assert len(formatted) == 2


class TestQuestionGeneration:
    """Tests for question generation from issues"""
    
    def test_no_issues_storage_question_only(self):
        """No issues generates only storage question"""
        report = ValidationReport(issues=[])
        questions = generate_questions_from_issues(report)
        assert len(questions) == 1
        assert "save" in questions[0].lower()
        
    def test_pii_generates_critical_question(self):
        """PII issue generates critical question"""
        issue = DataIssue(
            issue_type=IssueType.PII_DETECTED,
            severity=IssueSeverity.CRITICAL,
            column="email",
            message="",
            details={},
            suggested_action="",
        )
        report = ValidationReport(issues=[issue])
        questions = generate_questions_from_issues(report)
        
        # Should have PII question + storage question
        assert len(questions) == 2
        assert "CRITICAL" in questions[0]
        assert "PII" in questions[0]
        
    def test_missing_values_question(self):
        """Missing values generate question with percentage"""
        issue = DataIssue(
            issue_type=IssueType.HIGH_MISSING_RATIO,
            severity=IssueSeverity.HIGH,
            column="age",
            message="",
            details={"missing_pct": 25.5},
            suggested_action="",
        )
        report = ValidationReport(issues=[issue])
        questions = generate_questions_from_issues(report)
        
        assert any("Missing" in q for q in questions)
        assert any("25.5%" in q for q in questions)
        
    def test_outliers_question(self):
        """Outliers generate question"""
        issue = DataIssue(
            issue_type=IssueType.OUTLIERS_DETECTED,
            severity=IssueSeverity.MEDIUM,
            column="value",
            message="",
            details={},
            suggested_action="",
        )
        report = ValidationReport(issues=[issue])
        questions = generate_questions_from_issues(report)
        
        assert any("Outlier" in q for q in questions)
        
    def test_multiple_outlier_columns_truncated(self):
        """More than 5 outlier columns are truncated"""
        issues = [
            DataIssue(
                issue_type=IssueType.OUTLIERS_DETECTED,
                severity=IssueSeverity.MEDIUM,
                column=f"col{i}",
                message="",
                details={},
                suggested_action="",
            )
            for i in range(10)
        ]
        report = ValidationReport(issues=issues)
        questions = generate_questions_from_issues(report)
        
        outlier_q = [q for q in questions if "Outlier" in q][0]
        assert "..." in outlier_q


class TestDefaultCleaningActions:
    """Tests for default cleaning action generation"""
    
    def test_empty_report_default_actions(self):
        """Empty report has empty actions"""
        report = ValidationReport(issues=[])
        actions = get_default_cleaning_actions(report)
        assert actions["missing_values"] == {}
        assert actions["pii"] == {}
        
    def test_missing_values_default_impute(self):
        """Missing values default to median imputation"""
        issue = DataIssue(
            issue_type=IssueType.HIGH_MISSING_RATIO,
            severity=IssueSeverity.HIGH,
            column="age",
            message="",
            details={},
            suggested_action="",
        )
        report = ValidationReport(issues=[issue])
        actions = get_default_cleaning_actions(report)
        assert actions["missing_values"]["age"] == "impute_median"
        
    def test_pii_default_mask(self):
        """PII defaults to masking"""
        issue = DataIssue(
            issue_type=IssueType.PII_DETECTED,
            severity=IssueSeverity.CRITICAL,
            column="email",
            message="",
            details={},
            suggested_action="",
        )
        report = ValidationReport(issues=[issue])
        actions = get_default_cleaning_actions(report)
        assert actions["pii"]["email"] == "mask"
        
    def test_outliers_default_cap(self):
        """Outliers default to IQR capping"""
        issue = DataIssue(
            issue_type=IssueType.OUTLIERS_DETECTED,
            severity=IssueSeverity.MEDIUM,
            column="value",
            message="",
            details={},
            suggested_action="",
        )
        report = ValidationReport(issues=[issue])
        actions = get_default_cleaning_actions(report)
        assert actions["outliers"]["value"] == "cap_iqr"
        
    def test_constant_column_marked_invalid(self):
        """Constant columns added to invalid list"""
        issue = DataIssue(
            issue_type=IssueType.CONSTANT_COLUMN,
            severity=IssueSeverity.LOW,
            column="const",
            message="",
            details={},
            suggested_action="",
        )
        report = ValidationReport(issues=[issue])
        actions = get_default_cleaning_actions(report)
        assert "const" in actions["invalid_columns"]
        
    def test_duplicates_default_drop(self):
        """Duplicate rows default to drop"""
        issue = DataIssue(
            issue_type=IssueType.DUPLICATE_ROWS,
            severity=IssueSeverity.LOW,
            column=None,
            message="",
            details={},
            suggested_action="",
        )
        report = ValidationReport(issues=[issue])
        actions = get_default_cleaning_actions(report)
        assert actions["duplicates"] == "drop"


class TestDataIssueToDict:
    """Tests for DataIssue serialization"""
    
    def test_issue_to_dict_all_fields(self):
        """All fields serialized correctly"""
        issue = DataIssue(
            issue_type=IssueType.PII_DETECTED,
            severity=IssueSeverity.CRITICAL,
            column="email",
            message="Email pattern detected",
            details={"pattern": "email", "count": 100},
            suggested_action="mask or hash",
        )
        d = issue.to_dict()
        
        assert d["issue_type"] == "pii_detected"
        assert d["severity"] == "critical"
        assert d["column"] == "email"
        assert d["message"] == "Email pattern detected"
        assert d["details"]["pattern"] == "email"
        assert d["suggested_action"] == "mask or hash"
        
    def test_issue_to_dict_null_column(self):
        """Null column serialized correctly"""
        issue = DataIssue(
            issue_type=IssueType.DUPLICATE_ROWS,
            severity=IssueSeverity.LOW,
            column=None,
            message="Duplicates found",
            details={"count": 5},
            suggested_action="drop",
        )
        d = issue.to_dict()
        assert d["column"] is None


# ============================================================
# RUN TESTS
# ============================================================

def run_tests():
    """Run all tests"""
    test_classes = [
        TestCSVParsing,
        TestTicketGeneration,
        TestValidationReport,
        TestIssueFormatting,
        TestQuestionGeneration,
        TestDefaultCleaningActions,
        TestDataIssueToDict,
    ]
    
    print("=" * 60)
    print("Running smart_tools isolated tests")
    print("=" * 60)
    
    total_passed = 0
    total_failed = 0
    
    for test_class in test_classes:
        print(f"\n{test_class.__name__}:")
        print("-" * 40)
        
        instance = test_class()
        methods = [m for m in dir(instance) if m.startswith("test_")]
        
        for method_name in methods:
            try:
                method = getattr(instance, method_name)
                method()
                print(f"✓ {method_name.replace('test_', '').replace('_', ' ').title()}")
                total_passed += 1
            except Exception as e:
                print(f"✗ {method_name}: {e}")
                total_failed += 1
    
    print("\n" + "=" * 60)
    if total_failed == 0:
        print(f"🎉 ALL SMART TOOLS TESTS PASSED! ({total_passed} tests)")
    else:
        print(f"❌ {total_failed} FAILED, {total_passed} passed")
    print("=" * 60)
    
    return total_failed == 0


if __name__ == "__main__":
    import sys
    success = run_tests()
    sys.exit(0 if success else 1)
