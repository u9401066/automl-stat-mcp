#!/bin/bash
# AutoML Stat MCP - 停止腳本

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}⏹️  停止 AutoML Stat MCP 服務...${NC}"

# 停止所有 profile 的服務
docker compose --profile full --profile ml down

echo ""
echo -e "${GREEN}✅ 所有服務已停止${NC}"
echo ""
echo "如需完全清理 (包含資料)，執行:"
echo "  docker compose --profile full --profile ml down -v"
