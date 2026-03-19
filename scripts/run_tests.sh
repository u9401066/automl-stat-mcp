#!/bin/bash
# =============================================================================
# Test Runner Script
# =============================================================================
# Run different test suites for the AutoML MCP Server project
#
# Usage:
#   ./scripts/run_tests.sh [suite]
#
# Suites:
#   unit      - Local unit tests (no services required)
#   dataflow  - Data flow integrity tests (services required)
#   service   - Service communication tests (services required)
#   e2e       - Full end-to-end tests (services required)
#   all       - Run all tests
#   quick     - Quick smoke test
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Ensure uv is available
if ! command -v uv > /dev/null 2>&1; then
    echo -e "${RED}❌ uv is required. Install uv and run 'uv sync --all-extras'.${NC}"
    exit 1
fi

# Function to print colored output
print_header() {
    echo -e "\n${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}$1${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

run_pytest() {
    uv run pytest "$@"
}

# Check if services are running
check_services() {
    print_header "Checking Services..."

    local services_ok=true

    # Check stats service
    if curl -s http://localhost:8003/health > /dev/null 2>&1; then
        print_success "Stats Service (8003)"
    else
        print_warning "Stats Service (8003) - not available"
        services_ok=false
    fi

    # Check automl service
    if curl -s http://localhost:8001/health > /dev/null 2>&1; then
        print_success "AutoML Service (8001)"
    else
        print_warning "AutoML Service (8001) - not available"
        services_ok=false
    fi

    if [ "$services_ok" = false ]; then
        echo ""
        print_warning "Some services are not available."
        print_warning "Run 'docker compose up -d' to start services."
        echo ""
    fi

    return 0
}

# Run unit tests (no services required)
run_unit_tests() {
    print_header "Running Unit Tests..."
    run_pytest tests/test_tool_logic.py tests/unit/test_redis_manager.py -v --tb=short "$@"
}

# Run data flow tests
run_dataflow_tests() {
    print_header "Running Data Flow Tests..."
    check_services
    run_pytest tests/test_dataflow_integrity.py -v --tb=short "$@"
}

# Run service communication tests
run_service_tests() {
    print_header "Running Service Communication Tests..."
    check_services
    run_pytest tests/test_service_communication.py -v --tb=short "$@"
}

# Run E2E tests
run_e2e_tests() {
    print_header "Running E2E Tests..."
    check_services
    run_pytest tests/test_e2e_*.py -v --tb=short -m "e2e" "$@"
}

# Run all tests
run_all_tests() {
    print_header "Running All Tests..."
    check_services
    run_pytest -v --tb=short "$@"
}

# Quick smoke test
run_quick_tests() {
    print_header "Running Quick Smoke Tests..."
    run_pytest tests/test_tool_logic.py tests/unit/test_redis_manager.py -v --tb=short "$@"
}

# Run with coverage
run_with_coverage() {
    print_header "Running Tests with Coverage..."
    run_pytest tests/test_tool_logic.py tests/test_dataflow_integrity.py tests/test_service_communication.py \
        --cov=. --cov-report=html --cov-report=term-missing \
        -v --tb=short "$@"
    echo ""
    print_success "Coverage report generated: htmlcov/index.html"
}

# Show help
show_help() {
    echo "AutoML MCP Server Test Runner"
    echo ""
    echo "Usage: $0 [suite] [pytest-args...]"
    echo ""
    echo "Suites:"
    echo "  unit      - Local unit tests (no services required)"
    echo "  dataflow  - Data flow integrity tests (services required)"
    echo "  service   - Service communication tests (services required)"
    echo "  e2e       - Full end-to-end tests (services required)"
    echo "  all       - Run all tests"
    echo "  quick     - Quick smoke test"
    echo "  coverage  - Run with coverage report"
    echo "  help      - Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 unit                    # Run unit tests"
    echo "  $0 dataflow -k path        # Run dataflow tests matching 'path'"
    echo "  $0 all -x                  # Run all tests, stop on first failure"
    echo "  $0 coverage                # Run with coverage"
}

# Main
case "${1:-all}" in
    unit)
        shift
        run_unit_tests "$@"
        ;;
    dataflow)
        shift
        run_dataflow_tests "$@"
        ;;
    service)
        shift
        run_service_tests "$@"
        ;;
    e2e)
        shift
        run_e2e_tests "$@"
        ;;
    all)
        shift
        run_all_tests "$@"
        ;;
    quick)
        shift
        run_quick_tests "$@"
        ;;
    coverage)
        shift
        run_with_coverage "$@"
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown suite: $1"
        show_help
        exit 1
        ;;
esac
