#!/bin/bash
# AutoML Stat MCP - 一鍵安裝腳本
# 自動檢查依賴、安裝並啟動服務

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}"
cat << "EOF"
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║         AutoML Stat MCP - 快速安裝腳本                    ║
║                                                           ║
║  AI-Powered Statistical Analysis & AutoML Platform       ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# ==================== 檢查系統 ====================

echo -e "${BLUE}🔍 檢查系統需求...${NC}"

# 檢查作業系統
OS="$(uname -s)"
echo "  作業系統: $OS"

# 檢查 Docker
echo -n "  Docker: "
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | cut -d',' -f1)
    echo -e "${GREEN}✅ $DOCKER_VERSION${NC}"
else
    echo -e "${RED}❌ 未安裝${NC}"
    echo ""
    echo "請先安裝 Docker:"
    echo "  Ubuntu: sudo apt install docker.io"
    echo "  macOS:  brew install --cask docker"
    echo "  或訪問: https://docs.docker.com/get-docker/"
    exit 1
fi

# 檢查 Docker Compose
echo -n "  Docker Compose: "
if command -v docker compose &> /dev/null; then
    echo -e "${GREEN}✅ 已安裝${NC}"
else
    echo -e "${RED}❌ 未安裝${NC}"
    echo "請升級 Docker 到最新版本"
    exit 1
fi

# 檢查 Docker 服務
echo -n "  Docker 服務: "
if docker info &> /dev/null; then
    echo -e "${GREEN}✅ 運行中${NC}"
else
    echo -e "${RED}❌ 未運行${NC}"
    echo ""
    echo "請啟動 Docker 服務:"
    echo "  Linux: sudo systemctl start docker"
    echo "  macOS: 開啟 Docker Desktop"
    exit 1
fi

# 檢查記憶體
TOTAL_MEM=$(free -g 2>/dev/null | awk '/^Mem:/{print $2}' || echo "未知")
if [ "$TOTAL_MEM" != "未知" ] && [ "$TOTAL_MEM" -lt 8 ]; then
    echo -e "${YELLOW}⚠️  記憶體: ${TOTAL_MEM}GB (建議 8GB 以上)${NC}"
else
    echo "  記憶體: ${TOTAL_MEM}GB"
fi

# 檢查磁碟空間
DISK_FREE=$(df -h . | awk 'NR==2 {print $4}')
echo "  可用磁碟: $DISK_FREE"

echo ""
echo -e "${GREEN}✅ 系統需求檢查完成${NC}"

# ==================== 安裝 ====================

echo ""
echo -e "${BLUE}📥 開始安裝...${NC}"

# 創建 .env
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        echo "  複製環境設定..."
        cp .env.example .env
        echo -e "  ${GREEN}✅ .env 已建立${NC}"
    fi
fi

# 賦予執行權限
echo "  設定腳本權限..."
chmod +x start.sh stop.sh

# 詢問啟動模式
echo ""
echo -e "${YELLOW}選擇啟動模式:${NC}"
echo "  1) 預設 - 僅統計分析 (推薦新手)"
echo "  2) ML   - 包含機器學習訓練"
echo "  3) 完整 - 包含 MinIO 物件儲存"
echo ""
read -p "請選擇 [1-3] (預設: 1): " MODE_CHOICE
MODE_CHOICE=${MODE_CHOICE:-1}

case $MODE_CHOICE in
    1)
        MODE="default"
        ;;
    2)
        MODE="ml"
        ;;
    3)
        MODE="full"
        ;;
    *)
        echo -e "${RED}未知選項，使用預設模式${NC}"
        MODE="default"
        ;;
esac

# 下載 Docker 映像檔
echo ""
echo -e "${BLUE}📦 下載 Docker 映像檔...${NC}"
if [ "$MODE" == "ml" ]; then
    docker compose --profile ml pull
elif [ "$MODE" == "full" ]; then
    docker compose --profile full pull
else
    docker compose pull
fi

# 啟動服務
echo ""
echo -e "${BLUE}🚀 啟動服務...${NC}"
./start.sh $MODE

# ==================== 完成 ====================

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                           ║${NC}"
echo -e "${GREEN}║              🎉 安裝完成！服務已啟動                      ║${NC}"
echo -e "${GREEN}║                                                           ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}📚 下一步:${NC}"
echo ""
echo "1️⃣  在 VS Code 或 Claude Desktop 設定 MCP:"
echo "   {\"mcpServers\": {\"automl\": {\"url\": \"http://localhost:8002/sse\"}}}"
echo ""
echo "2️⃣  試試這些指令:"
echo "   make logs       - 查看日誌"
echo "   make health     - 健康檢查"
echo "   make help       - 所有可用指令"
echo ""
echo "3️⃣  範例資料集位置:"
echo "   sample_data/iris.csv"
echo "   sample_data/heart_disease.csv"
echo ""
echo "4️⃣  停止服務:"
echo "   ./stop.sh       或  make stop"
echo ""
echo -e "${BLUE}📖 完整文檔:${NC} https://github.com/u9401066/automl-stat-mcp"
echo ""
