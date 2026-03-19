#!/usr/bin/env bash
# =============================================================================
# setup-vscode-mcp.sh — 為任意 VS Code 專案設定 automl-stat-mcp 連線
# =============================================================================
#
# Usage:
#   # 幫當前目錄的專案設定
#   bash /path/to/automl-stat-mcp/scripts/setup-vscode-mcp.sh
#
#   # 幫指定目錄設定
#   bash /path/to/automl-stat-mcp/scripts/setup-vscode-mcp.sh /path/to/my-project
#
#   # 自訂 MCP Server 位址（遠端機器）
#   MCP_URL=http://192.168.1.100:8002/sse bash scripts/setup-vscode-mcp.sh
#
# =============================================================================

set -euo pipefail

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

TARGET_DIR="${1:-.}"
MCP_URL="${MCP_URL:-http://localhost:8002/sse}"
VSCODE_DIR="$TARGET_DIR/.vscode"
MCP_JSON="$VSCODE_DIR/mcp.json"

echo -e "${BLUE}🔧 AutoML Stat MCP — VS Code 設定工具${NC}"
echo ""

# 確認目標目錄存在
if [ ! -d "$TARGET_DIR" ]; then
    echo -e "${RED}❌ 目錄不存在: $TARGET_DIR${NC}"
    exit 1
fi

# 建立 .vscode/ 目錄
mkdir -p "$VSCODE_DIR"

# 檢查是否已有 mcp.json
if [ -f "$MCP_JSON" ]; then
    # 檢查是否已經設定過 automl-stat-mcp
    if grep -q "automl-stat-mcp" "$MCP_JSON" 2>/dev/null; then
        echo -e "${YELLOW}⚠️  mcp.json 已包含 automl-stat-mcp 設定${NC}"
        echo -e "   檔案: $MCP_JSON"
        echo ""
        read -rp "是否覆蓋？(y/N) " answer
        if [[ ! "$answer" =~ ^[Yy]$ ]]; then
            echo "已取消。"
            exit 0
        fi
    fi

    # 已有 mcp.json — 用 python 安全合併
    python3 -c "
import json, sys
with open('$MCP_JSON', 'r') as f:
    config = json.load(f)
if 'servers' not in config:
    config['servers'] = {}
config['servers']['automl-stat-mcp'] = {
    'url': '$MCP_URL',
    'type': 'sse'
}
with open('$MCP_JSON', 'w') as f:
    json.dump(config, f, indent=2)
print('已合併到現有 mcp.json')
" 2>/dev/null || {
        # Python 失敗時直接寫入
        echo -e "${YELLOW}⚠️  無法合併，將覆蓋 mcp.json${NC}"
        cat > "$MCP_JSON" << MCPEOF
{
  "servers": {
    "automl-stat-mcp": {
      "url": "$MCP_URL",
      "type": "sse"
    }
  }
}
MCPEOF
    }
else
    # 全新建立
    cat > "$MCP_JSON" << MCPEOF
{
  "servers": {
    "automl-stat-mcp": {
      "url": "$MCP_URL",
      "type": "sse"
    }
  }
}
MCPEOF
fi

echo -e "${GREEN}✅ 設定完成！${NC}"
echo ""
echo -e "${BLUE}📄 $MCP_JSON:${NC}"
cat "$MCP_JSON"
echo ""
echo -e "${BLUE}📝 下一步:${NC}"
echo "  1. 確認 MCP 服務運行中:"
echo "     curl -s http://localhost:8002/health"
echo ""
echo "  2. 在 VS Code 中重新開啟此專案"
echo "     Copilot Agent 會自動偵測 .vscode/mcp.json"
echo ""
echo "  3. 測試: 叫 Copilot 「用 smart_analyze 分析 iris.csv」"
echo ""
echo -e "${YELLOW}💡 如果 MCP 在遠端機器:${NC}"
echo "   MCP_URL=http://YOUR_IP:8002/sse bash $0 $TARGET_DIR"
