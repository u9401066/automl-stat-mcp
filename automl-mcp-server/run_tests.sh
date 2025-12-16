#!/bin/bash
# Run tests for automl-mcp-server
# Usage: ./run_tests.sh [test_file] [pytest_args]
#
# Examples:
#   ./run_tests.sh                           # Run all tests
#   ./run_tests.sh test_result_storage.py    # Run specific test file
#   ./run_tests.sh -v -k "test_numpy"        # Run with verbose, filter by name
#   ./run_tests.sh --isolated                # Run isolated tests only (no Docker)
#   ./run_tests.sh -i                        # Short form for isolated tests

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Set PYTHONPATH
export PYTHONPATH="${SCRIPT_DIR}/src:${PYTHONPATH}"

# Check for isolated tests (can run locally without Docker)
if [[ "$1" == "--isolated" || "$1" == "-i" ]]; then
    shift
    echo "=============================================="
    echo "Running ALL isolated tests (no Docker required)"
    echo "=============================================="
    echo ""
    
    # Find and run all isolated test files
    ISOLATED_TESTS=(
        "tests/unit/test_result_storage_isolated.py"
        "tests/unit/test_cleaning_isolated.py"
        "tests/unit/test_statistics_isolated.py"
        "tests/unit/test_data_validator_isolated.py"
        "tests/unit/test_upload_isolated.py"
        "tests/unit/test_roc_isolated.py"
        "tests/unit/test_power_isolated.py"
        "tests/unit/test_survival_isolated.py"
        "tests/unit/test_propensity_isolated.py"
        "tests/unit/test_tableone_isolated.py"
        "tests/unit/test_automl_workflow_isolated.py"
        "tests/unit/test_dataset_isolated.py"
        "tests/unit/test_model_isolated.py"
        "tests/unit/test_smart_tools_isolated.py"
        "tests/unit/test_orchestration_isolated.py"
    )
    
    PASSED=0
    FAILED=0
    
    for test_file in "${ISOLATED_TESTS[@]}"; do
        if [[ -f "$test_file" ]]; then
            echo ">>> Running: $test_file"
            if python3 "$test_file"; then
                PASSED=$((PASSED + 1))
            else
                FAILED=$((FAILED + 1))
            fi
            echo ""
        fi
    done
    
    echo "=============================================="
    echo "Summary: $PASSED passed, $FAILED failed"
    echo "=============================================="
    
    if [[ $FAILED -gt 0 ]]; then
        exit 1
    fi
    exit 0
fi

# Check if pytest is available
if ! command -v pytest &> /dev/null; then
    echo "pytest not found. Installing test dependencies..."
    pip install -r requirements-test.txt
fi

# Run pytest
echo "Running pytest..."
python3 -m pytest tests/ "$@"
