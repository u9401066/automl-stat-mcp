# AutoML Stat MCP - Makefile
# 簡化常用命令

.PHONY: help start stop restart logs status clean test test-all lint format typecheck check hooks-install hooks-run health

# 預設顯示幫助
help:
	@echo "🚀 AutoML Stat MCP - 快速啟動指令"
	@echo ""
	@echo "📦 服務管理:"
	@echo "  make start          - 啟動預設服務 (stats + MCP)"
	@echo "  make start-ml       - 啟動含 ML 訓練的服務"
	@echo "  make start-full     - 啟動完整服務 (含 MinIO)"
	@echo "  make stop           - 停止所有服務"
	@echo "  make restart        - 重啟服務"
	@echo "  make restart-mcp    - 只重啟 MCP 服務"
	@echo ""
	@echo "📊 監控:"
	@echo "  make logs           - 查看所有日誌"
	@echo "  make logs-mcp       - 查看 MCP 服務日誌"
	@echo "  make logs-stats     - 查看統計服務日誌"
	@echo "  make status         - 查看服務狀態"
	@echo "  make health         - 健康檢查"
	@echo ""
	@echo "🔧 開發:"
	@echo "  make hooks-install  - 安裝 pre-commit hooks"
	@echo "  make hooks-run      - 執行所有 pre-commit hooks"
	@echo "  make format         - 執行 Ruff formatter"
	@echo "  make lint           - 執行 Ruff lint"
	@echo "  make typecheck      - 執行 MyPy"
	@echo "  make check          - lint + typecheck"
	@echo "  make rebuild        - 重建並啟動"
	@echo "  make rebuild-mcp    - 只重建 MCP 服務"
	@echo "  make shell-mcp      - 進入 MCP 容器"
	@echo "  make test           - 執行快速 smoke tests"
	@echo "  make test-all       - 執行完整 pytest"
	@echo ""
	@echo "🧹 清理:"
	@echo "  make clean          - 停止並清理容器"
	@echo "  make clean-all      - 完全清理 (含 volumes)"
	@echo ""
	@echo "📈 擴展:"
	@echo "  make scale-stats    - 擴展統計 worker (預設4個)"
	@echo "  make scale-ml       - 擴展 ML worker (預設8個)"

# ==================== 服務管理 ====================

start:
	@echo "🚀 啟動預設服務..."
	docker compose up -d
	@make health

start-ml:
	@echo "🚀 啟動 ML 服務..."
	docker compose --profile ml up -d
	@make health

start-full:
	@echo "🚀 啟動完整服務..."
	docker compose --profile full up -d
	@make health

stop:
	@echo "⏹️  停止所有服務..."
	docker compose --profile full --profile ml down

restart:
	@echo "🔄 重啟服務..."
	docker compose restart

restart-mcp:
	@echo "🔄 重啟 MCP 服務..."
	docker compose restart automl-mcp

# ==================== 監控 ====================

logs:
	docker compose logs -f

logs-mcp:
	docker compose logs -f automl-mcp

logs-stats:
	docker compose logs -f stats-service stats-worker

status:
	@echo "📊 服務狀態:"
	@docker compose ps

health:
	@echo "🏥 健康檢查..."
	@echo -n "Stats Service (8003): "
	@curl -s http://localhost:8003/health > /dev/null && echo "✅ OK" || echo "❌ Down"
	@echo -n "MCP Server (8002): "
	@curl -s http://localhost:8002/health > /dev/null && echo "✅ OK" || echo "❌ Down"
	@echo -n "Redis: "
	@docker compose exec -T automl-redis redis-cli ping > /dev/null 2>&1 && echo "✅ OK" || echo "❌ Down"

# ==================== 開發 ====================

rebuild:
	@echo "🔨 重建所有服務..."
	docker compose build
	docker compose up -d
	@make health

rebuild-mcp:
	@echo "🔨 重建 MCP 服務..."
	docker compose build automl-mcp
	docker compose up -d automl-mcp
	@make health

shell-mcp:
	@echo "🐚 進入 MCP 容器..."
	docker compose exec automl-mcp /bin/bash

shell-stats:
	@echo "🐚 進入統計服務容器..."
	docker compose exec stats-service /bin/bash

test:
	@echo "🧪 執行快速 smoke tests..."
	@./scripts/run_tests.sh quick

test-all:
	@echo "🧪 執行完整測試..."
	@uv run pytest

format:
	@uv run ruff format .

lint:
	@uv run ruff check .

typecheck:
	@uv run mypy automl-mcp-server/src automl-service/src stats-service/src shared

check: lint typecheck

hooks-install:
	@uv run pre-commit install --install-hooks

hooks-run:
	@uv run pre-commit run --all-files

# ==================== 清理 ====================

clean:
	@echo "🧹 清理容器..."
	docker compose --profile full --profile ml down

clean-all:
	@echo "🧹 完全清理 (含 volumes)..."
	@read -p "⚠️  將刪除所有資料，確定嗎? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker compose --profile full --profile ml down -v; \
		echo "✅ 清理完成"; \
	else \
		echo "❌ 取消清理"; \
	fi

# ==================== 擴展 ====================

scale-stats:
	@echo "📈 擴展統計 workers 到 4 個..."
	docker compose up -d --scale stats-worker=4

scale-ml:
	@echo "📈 擴展 ML workers 到 8 個..."
	docker compose --profile ml up -d --scale automl-worker=8 --scale stats-worker=4

# ==================== 快速工具 ====================

ps:
	@docker compose ps

top:
	@docker compose top

tail:
	@docker compose logs --tail=50 -f
