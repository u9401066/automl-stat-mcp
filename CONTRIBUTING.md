# Contributing to Clinical AutoML MCP

Thank you for your interest in contributing to Clinical AutoML MCP! This document provides guidelines and instructions for contributing.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)

---

## 📜 Code of Conduct

This project follows a standard code of conduct. Please be respectful and constructive in all interactions.

**Core principles:**
- Be respectful and inclusive
- Focus on constructive feedback
- Accept responsibility for mistakes
- Prioritize the community's best interests

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- Docker & Docker Compose
- Git
- (Optional) CUDA-capable GPU for ML training

### Fork and Clone

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/clinical-automl-mcp.git
cd clinical-automl-mcp

# Add upstream remote
git remote add upstream https://github.com/ORIGINAL_OWNER/clinical-automl-mcp.git
```

---

## 🛠️ Development Setup

### 1. Create Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows
```

### 2. Install Dependencies

```bash
# Install with development dependencies
pip install -e ".[dev]"

# Or install each service separately
cd stats-service && pip install -e ".[dev]"
cd automl-mcp-server && pip install -e ".[dev]"
```

### 3. Start Development Services

```bash
# Start with Docker (recommended)
docker compose up -d redis

# Or run services locally
cd stats-service
uvicorn src.main:app --reload --port 8003
```

### 4. Run Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=src tests/

# Run specific test file
pytest tests/test_statistics.py -v
```

---

## 🤝 How to Contribute

### Types of Contributions

| Type | Description |
|------|-------------|
| 🐛 Bug Reports | Report issues with detailed reproduction steps |
| ✨ Feature Requests | Suggest new features or improvements |
| 📝 Documentation | Improve docs, examples, or translations |
| 🧪 Tests | Add or improve test coverage |
| 🔧 Bug Fixes | Fix reported issues |
| 🚀 New Features | Implement approved features |

### Reporting Bugs

1. Search existing issues first
2. Use the bug report template
3. Include:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (OS, Python version, Docker version)
   - Logs or error messages

### Suggesting Features

1. Search existing issues/discussions
2. Use the feature request template
3. Explain the use case and benefits
4. Consider implementation complexity

---

## 📥 Pull Request Process

### 1. Create a Branch

```bash
# Sync with upstream
git fetch upstream
git checkout main
git merge upstream/main

# Create feature branch
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

### 2. Make Changes

- Follow coding standards (see below)
- Add/update tests
- Update documentation if needed

### 3. Commit Changes

```bash
# Use conventional commit format
git commit -m "feat: add survival analysis visualization"
git commit -m "fix: handle missing values in TableOne"
git commit -m "docs: update API documentation"
```

**Commit Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `test`: Adding tests
- `refactor`: Code refactoring
- `chore`: Maintenance tasks

### 4. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub with:
- Clear title describing the change
- Reference to related issues
- Description of what changed and why
- Screenshots if UI changes

### 5. Review Process

- Maintainers will review your PR
- Address feedback with additional commits
- Once approved, maintainers will merge

---

## 📐 Coding Standards

### Python Style

We use [Ruff](https://github.com/astral-sh/ruff) for linting and formatting:

```bash
# Format code
ruff format .

# Check linting
ruff check .

# Auto-fix issues
ruff check --fix .
```

**Key conventions:**
- Line length: 100 characters
- Use type hints for all function signatures
- Docstrings for all public functions (Google style)
- Prefer `pathlib.Path` over `os.path`

### Architecture Principles

This project follows **Domain-Driven Design (DDD)**:

```
src/
├── domain/         # Business logic, entities, interfaces
├── application/    # Use cases, orchestration
├── infrastructure/ # External services, databases, APIs
└── interface/      # API routes, MCP handlers
```

**Key rules:**
1. Domain layer has no external dependencies
2. Infrastructure implements domain interfaces
3. Dependencies flow inward only

### MCP Tool Guidelines

When adding new MCP tools:

```python
@mcp.tool()
async def my_new_tool(
    csv_path: str,  # Required parameters first
    user_id: str = "default",  # Defaults for optional
) -> dict:
    """
    Brief one-line description.

    Detailed description of what the tool does.

    Args:
        csv_path: Path to CSV file (auto-resolved)
        user_id: User ID for result storage

    Returns:
        result: Analysis results
        status: "success" or "error"
    """
    # Implementation
```

---

## 🧪 Testing Guidelines

### Test Structure

```
tests/
├── unit/           # Unit tests (no external deps)
├── integration/    # Integration tests (with services)
└── e2e/            # End-to-end tests
```

### Writing Tests

```python
import pytest
from src.domain.services import AnalysisService

class TestAnalysisService:
    """Tests for AnalysisService."""

    def test_compute_statistics_valid_data(self):
        """Should compute statistics for valid data."""
        # Arrange
        service = AnalysisService()
        data = [1, 2, 3, 4, 5]

        # Act
        result = service.compute_statistics(data)

        # Assert
        assert result["mean"] == 3.0
        assert result["std"] == pytest.approx(1.58, rel=0.01)

    def test_compute_statistics_empty_data(self):
        """Should raise ValueError for empty data."""
        service = AnalysisService()

        with pytest.raises(ValueError, match="Data cannot be empty"):
            service.compute_statistics([])
```

### Test Coverage

- Aim for 80%+ coverage on new code
- Critical paths require 100% coverage
- Use `pytest-cov` to check coverage

```bash
pytest --cov=src --cov-report=html tests/
```

---

## 📚 Documentation

### Code Documentation

- All public functions need docstrings
- Use Google-style docstrings
- Include type hints

```python
def compute_roc_curve(
    y_true: list[int],
    y_score: list[float],
    pos_label: int = 1,
) -> dict[str, Any]:
    """
    Compute ROC curve with AUC and confidence intervals.

    Args:
        y_true: True binary labels (0/1)
        y_score: Predicted probabilities
        pos_label: Label considered positive

    Returns:
        Dictionary containing:
            - auc: Area under the curve
            - auc_ci: 95% confidence interval
            - curve: List of (fpr, tpr, threshold) points

    Raises:
        ValueError: If y_true and y_score have different lengths

    Example:
        >>> result = compute_roc_curve([0, 0, 1, 1], [0.1, 0.4, 0.35, 0.8])
        >>> print(f"AUC: {result['auc']:.3f}")
        AUC: 0.750
    """
```

### User Documentation

- Update README.md for user-facing changes
- Add to `docs/` for detailed guides
- Include examples where possible

---

## ❓ Questions?

- Open a [GitHub Discussion](https://github.com/OWNER/clinical-automl-mcp/discussions)
- Check existing issues and documentation
- Tag maintainers for urgent matters

Thank you for contributing! 🎉
