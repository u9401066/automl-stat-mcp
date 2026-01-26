#!/bin/bash
# 測試執行腳本 - 方便運行不同類型的測試

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║          AutoML Stat MCP - 測試執行腳本                        ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# 檢查 pytest 是否已安裝
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}❌ pytest 未安裝${NC}"
    echo "請執行: uv pip install pytest pytest-asyncio pytest-cov"
    exit 1
fi

# 顯示菜單
show_menu() {
    echo -e "${YELLOW}請選擇測試類型:${NC}"
    echo ""
    echo "  ${GREEN}1)${NC} 快速測試 (fast tests only)"
    echo "  ${GREEN}2)${NC} 單元測試 (unit tests)"
    echo "  ${GREEN}3)${NC} 整合測試 (integration tests)"
    echo "  ${GREEN}4)${NC} E2E 測試 (end-to-end workflows)"
    echo "  ${GREEN}5)${NC} 邊界測試 (edge cases)"
    echo "  ${GREEN}6)${NC} 性能測試 (performance & load)"
    echo "  ${GREEN}7)${NC} 安全測試 (security & injection)"
    echo "  ${GREEN}8)${NC} 全部測試 (all tests)"
    echo "  ${GREEN}9)${NC} 覆蓋率報告 (coverage report)"
    echo "  ${GREEN}0)${NC} 自訂 (custom pytest args)"
    echo ""
}

# 執行測試
run_test() {
    local test_cmd="$1"
    local test_name="$2"
    
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}執行: ${test_name}${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    if eval "$test_cmd"; then
        echo ""
        echo -e "${GREEN}✅ 測試通過: ${test_name}${NC}"
        return 0
    else
        echo ""
        echo -e "${RED}❌ 測試失敗: ${test_name}${NC}"
        return 1
    fi
}

# 主邏輯
if [ "$#" -eq 0 ]; then
    # 互動模式
    show_menu
    read -p "請選擇 (0-9): " choice
    
    case $choice in
        1)
            run_test "pytest -m 'not slow' tests/" "快速測試"
            ;;
        2)
            run_test "pytest -m unit tests/" "單元測試"
            ;;
        3)
            run_test "pytest -m integration tests/" "整合測試"
            ;;
        4)
            run_test "pytest -m e2e tests/e2e/" "E2E 測試"
            ;;
        5)
            run_test "pytest -m edge_case tests/edge_cases/" "邊界測試"
            ;;
        6)
            run_test "pytest -m performance tests/performance/" "性能測試"
            ;;
        7)
            run_test "pytest -m security tests/security/" "安全測試"
            ;;
        8)
            run_test "pytest tests/" "全部測試"
            ;;
        9)
            run_test "pytest --cov=. --cov-report=html --cov-report=term tests/" "覆蓋率報告"
            echo ""
            echo -e "${GREEN}📊 HTML 報告已生成: htmlcov/index.html${NC}"
            ;;
        0)
            read -p "輸入 pytest 參數: " custom_args
            run_test "pytest $custom_args" "自訂測試"
            ;;
        *)
            echo -e "${RED}無效選擇${NC}"
            exit 1
            ;;
    esac
else
    # 命令列模式
    case "$1" in
        fast)
            run_test "pytest -m 'not slow' tests/" "快速測試"
            ;;
        unit)
            run_test "pytest -m unit tests/" "單元測試"
            ;;
        integration)
            run_test "pytest -m integration tests/" "整合測試"
            ;;
        e2e)
            run_test "pytest -m e2e tests/e2e/" "E2E 測試"
            ;;
        edge)
            run_test "pytest -m edge_case tests/edge_cases/" "邊界測試"
            ;;
        perf|performance)
            run_test "pytest -m performance tests/performance/" "性能測試"
            ;;
        sec|security)
            run_test "pytest -m security tests/security/" "安全測試"
            ;;
        all)
            run_test "pytest tests/" "全部測試"
            ;;
        cov|coverage)
            run_test "pytest --cov=. --cov-report=html --cov-report=term tests/" "覆蓋率報告"
            echo ""
            echo -e "${GREEN}📊 HTML 報告已生成: htmlcov/index.html${NC}"
            ;;
        help|--help|-h)
            echo "使用方式:"
            echo "  ./run_tests.sh              # 互動模式"
            echo "  ./run_tests.sh <類型>       # 直接執行"
            echo ""
            echo "可用類型:"
            echo "  fast         - 快速測試"
            echo "  unit         - 單元測試"
            echo "  integration  - 整合測試"
            echo "  e2e          - E2E 測試"
            echo "  edge         - 邊界測試"
            echo "  performance  - 性能測試"
            echo "  security     - 安全測試"
            echo "  all          - 全部測試"
            echo "  coverage     - 覆蓋率報告"
            ;;
        *)
            echo -e "${RED}未知類型: $1${NC}"
            echo "執行 './run_tests.sh help' 查看幫助"
            exit 1
            ;;
    esac
fi

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                    測試執行完成                                 ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
