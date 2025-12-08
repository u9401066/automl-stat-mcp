#!/bin/bash
# =============================================================================
# Docker Compose Smart Start Script
# =============================================================================
#
# 處理常見問題：
#   1. Container 名稱衝突 - 自動檢測並處理
#   2. 網路/Volume 衝突 - 提供清理選項
#   3. 服務健康檢查 - 確認服務正常啟動
#
# Usage:
#   ./scripts/docker-start.sh          # 智慧啟動
#   ./scripts/docker-start.sh --clean  # 清理後啟動
#   ./scripts/docker-start.sh --status # 只檢查狀態
#
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.yml"

# Auto-detect if we need sudo for docker
DOCKER_CMD="docker"
COMPOSE_CMD="docker compose"
if ! docker ps > /dev/null 2>&1; then
    if sudo docker ps > /dev/null 2>&1; then
        DOCKER_CMD="sudo docker"
        COMPOSE_CMD="sudo docker compose"
    else
        echo "ERROR: Cannot connect to Docker daemon"
        exit 1
    fi
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
echo_success() { echo -e "${GREEN}[OK]${NC} $1"; }
echo_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
echo_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# =============================================================================
# Check existing containers
# =============================================================================
check_existing_containers() {
    echo_info "Checking existing containers..."
    
    # Container names we use
    CONTAINERS=("automl-redis" "automl-api" "automl-mcp" "stats-service")
    
    for container in "${CONTAINERS[@]}"; do
        if $DOCKER_CMD ps -a --format '{{.Names}}' | grep -q "^${container}$"; then
            STATUS=$($DOCKER_CMD inspect -f '{{.State.Status}}' "$container" 2>/dev/null || echo "unknown")
            if [ "$STATUS" == "running" ]; then
                echo_success "$container is already running"
            else
                echo_warn "$container exists but status=$STATUS"
            fi
        fi
    done
}

# =============================================================================
# Check if services are healthy
# =============================================================================
check_services_health() {
    echo_info "Checking services health..."
    
    # Check stats-service
    if curl -s http://localhost:8003/health > /dev/null 2>&1; then
        echo_success "stats-service (8003) is healthy"
    else
        echo_warn "stats-service (8003) not responding"
    fi
    
    # Check automl-api
    if curl -s http://localhost:8001/health > /dev/null 2>&1; then
        echo_success "automl-api (8001) is healthy"
    else
        echo_warn "automl-api (8001) not responding"
    fi
    
    # Check MCP server
    if curl -s http://localhost:8002/health > /dev/null 2>&1; then
        echo_success "automl-mcp (8002) is healthy"
    else
        echo_warn "automl-mcp (8002) not responding"
    fi
    
    # Check Redis
    if $DOCKER_CMD exec automl-redis redis-cli ping > /dev/null 2>&1; then
        echo_success "Redis is healthy"
    else
        echo_warn "Redis not responding"
    fi
}

# =============================================================================
# Smart start - reuse existing or start new
# =============================================================================
smart_start() {
    echo_info "Smart starting services..."
    
    # Check if Redis is already running (from another project)
    if $DOCKER_CMD ps --format '{{.Names}}' | grep -q "automl-redis"; then
        echo_success "Redis already running, will reuse"
        
        # Start other services without redis
        $COMPOSE_CMD -f "$COMPOSE_FILE" up -d --no-deps automl-api automl-worker automl-mcp stats-service stats-worker 2>&1 || {
            echo_warn "Some services may have conflicts, checking..."
        }
    else
        # Start all services
        $COMPOSE_CMD -f "$COMPOSE_FILE" up -d 2>&1 || {
            echo_error "Failed to start services"
            echo_info "Trying to resolve conflicts..."
            resolve_conflicts
        }
    fi
}

# =============================================================================
# Resolve container name conflicts
# =============================================================================
resolve_conflicts() {
    echo_info "Resolving container conflicts..."
    
    # Find conflicting containers
    CONTAINERS=("automl-redis" "automl-api" "automl-mcp" "stats-service")
    
    for container in "${CONTAINERS[@]}"; do
        if $DOCKER_CMD ps -a --format '{{.Names}}' | grep -q "^${container}$"; then
            STATUS=$($DOCKER_CMD inspect -f '{{.State.Status}}' "$container" 2>/dev/null || echo "unknown")
            
            if [ "$STATUS" == "running" ]; then
                echo_success "$container is running, keeping it"
            elif [ "$STATUS" == "exited" ] || [ "$STATUS" == "created" ]; then
                echo_info "Removing stopped container: $container"
                $DOCKER_CMD rm "$container" 2>/dev/null || true
            fi
        fi
    done
    
    echo_info "Retrying docker compose up..."
    $COMPOSE_CMD -f "$COMPOSE_FILE" up -d
}

# =============================================================================
# Clean start - remove all and restart
# =============================================================================
clean_start() {
    echo_warn "Clean start - removing all project containers..."
    
    $COMPOSE_CMD -f "$COMPOSE_FILE" down -v 2>/dev/null || true
    
    # Also remove any orphaned containers with our names
    for container in automl-redis automl-api automl-mcp stats-service; do
        $DOCKER_CMD rm -f "$container" 2>/dev/null || true
    done
    
    echo_info "Starting fresh..."
    $COMPOSE_CMD -f "$COMPOSE_FILE" up -d
}

# =============================================================================
# Show status
# =============================================================================
show_status() {
    echo ""
    echo "=============================================="
    echo "         Service Status Summary"
    echo "=============================================="
    echo ""
    
    check_existing_containers
    echo ""
    check_services_health
    
    echo ""
    echo "=============================================="
    echo "         Container Details"
    echo "=============================================="
    $DOCKER_CMD ps --filter "name=automl" --filter "name=stats" --filter "name=minio" \
        --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "No containers found"
}

# =============================================================================
# Main
# =============================================================================
main() {
    cd "$PROJECT_DIR"
    
    case "${1:-}" in
        --clean)
            clean_start
            sleep 5
            show_status
            ;;
        --status)
            show_status
            ;;
        --help|-h)
            echo "Usage: $0 [--clean|--status|--help]"
            echo ""
            echo "  (no args)  Smart start - reuse running containers if healthy"
            echo "  --clean    Stop all and start fresh"
            echo "  --status   Show current status only"
            echo "  --help     Show this help"
            ;;
        *)
            smart_start
            sleep 3
            show_status
            ;;
    esac
}

main "$@"
