#!/bin/bash
# AutoML Stat MCP - 快速啟動腳本
# Usage: ./start.sh [default|ml|full]

set -e

# 顏色定義
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Logo
echo -e "${BLUE}"
cat << "EOF"
    ___         __       __  ____   ______        __     __  __________
   /   | __  __/ /_____/  |/  / /  / ____/_____ _/ /_   /  |/  / ____/ __ \
  / /| |/ / / / __/ __ \  / / /    / /   /  __ `/ __/  / /|_/ / /   / /_/ /
 / ___ / /_/ / /_/ /_/ / / / /___ / /___/ /_/ / /_   / /  / / /___/ ____/
/_/  |_\__,_/\__/\____/_/_/_____/ \____/\__,_/\__/  /_/  /_/\____/_/

AutoML + Statistics + MCP - AI-Powered Research Platform
EOF
echo -e "${NC}"

# 檢查 Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker 未安裝，請先安裝 Docker${NC}"
    exit 1
fi

if ! command -v docker compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose 未安裝或版本過舊${NC}"
    exit 1
fi

# 解析參數
MODE=${1:-default}

case $MODE in
    default|stats)
        echo -e "${GREEN}🚀 啟動預設服務 (統計分析 + MCP)${NC}"
        PROFILE=""
        ;;
    ml|automl)
        echo -e "${GREEN}🚀 啟動 ML 服務 (含 AutoML 訓練)${NC}"
        PROFILE="--profile ml"
        ;;
    full|all)
        echo -e "${GREEN}🚀 啟動完整服務 (含 MinIO 儲存)${NC}"
        PROFILE="--profile full"
        ;;
    *)
        echo -e "${RED}❌ 未知模式: $MODE${NC}"
        echo ""
        echo "Usage: $0 [default|ml|full]"
        echo ""
        echo "Modes:"
        echo "  default - 統計分析 + MCP (預設)"
        echo "  ml      - 包含 AutoML 訓練"
        echo "  full    - 完整服務 + MinIO"
        exit 1
        ;;
esac

# 檢查 .env
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        echo -e "${YELLOW}⚠️  未找到 .env 檔案，從 .env.example 複製...${NC}"
        cp .env.example .env
    fi
fi

# 啟動服務
echo ""
echo -e "${BLUE}📦 正在啟動容器...${NC}"
docker compose $PROFILE up -d

# 等待服務啟動
echo ""
echo -e "${BLUE}⏳ 等待服務準備就緒...${NC}"
sleep 5

# 健康檢查
echo ""
echo -e "${BLUE}🏥 健康檢查:${NC}"

check_service() {
    local name=$1
    local url=$2
    echo -n "  $name: "
    if curl -sf "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ OK${NC}"
        return 0
    else
        echo -e "${RED}❌ Down${NC}"
        return 1
    fi
}

check_service "Stats Service (8003)" "http://localhost:8003/health"
check_service "MCP Server (8002)" "http://localhost:8002/health"

# Redis 檢查
echo -n "  Redis: "
if docker compose exec -T automl-redis redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✅ OK${NC}"
else
    echo -e "${RED}❌ Down${NC}"
fi

# 顯示容器狀態
echo ""
echo -e "${BLUE}📊 服務狀態:${NC}"
docker compose ps

# 完成訊息
echo ""
echo -e "${GREEN}✅ 啟動完成！${NC}"
echo ""
echo -e "${BLUE}📚 快速指令:${NC}"
echo "  查看日誌:     docker compose logs -f"
echo "  查看 MCP:     docker compose logs -f automl-mcp"
echo "  停止服務:     docker compose down"
echo "  重啟服務:     docker compose restart"
echo ""
echo -e "${BLUE}🔗 服務端點:${NC}"
echo "  MCP Server:   http://localhost:8002"
echo "  Stats API:    http://localhost:8003"
if [[ "$MODE" == "ml" || "$MODE" == "automl" ]]; then
    echo "  AutoML API:   http://localhost:8001"
fi
if [[ "$MODE" == "full" || "$MODE" == "all" ]]; then
    echo "  MinIO:        http://localhost:9001"
fi
echo ""
echo -e "${BLUE}📖 使用 Makefile 更方便:${NC}"
echo "  make help     - 查看所有指令"
echo "  make logs     - 即時日誌"
echo "  make health   - 健康檢查"
echo ""
