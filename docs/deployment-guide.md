# AutoML MCP 完整部署指南

本文件提供三種部署情境的完整教學。

---

## 目錄

1. [快速開發部署](#1-快速開發部署)
2. [生產環境部署](#2-生產環境部署)
3. [企業安全部署 (HTTPS + POST-only)](#3-企業安全部署)
4. [連接 AI Agent](#4-連接-ai-agent)
5. [疑難排解](#5-疑難排解)

---

## 前置需求

### 所有環境都需要

- Docker Engine 24.0+
- Docker Compose v2.20+
- 外部 MinIO 伺服器（或修改 compose 使用本地 MinIO）

### 企業部署額外需要

- SSL 憑證（由 CA 簽發或自簽）
- 開放 443 port

### 硬體建議

| 環境 | CPU | RAM | 說明 |
|------|-----|-----|------|
| 開發 | 4 核 | 8 GB | 1 個 worker |
| 生產 | 8 核 | 32 GB | 4 個 workers |
| 高負載 | 16 核 | 64 GB | 8+ workers |

---

## 1. 快速開發部署

適用於本機開發和測試。

### 1.1 Clone 專案

```bash
git clone <your-repo-url> automl-mcp
cd automl-mcp
```

### 1.2 設定環境變數

```bash
# 複製範例設定
cp .env.example .env

# 編輯設定
nano .env
```

填入你的 MinIO 資訊：

```bash
# .env
MINIO_ENDPOINT=your-minio-host:9000
MINIO_ACCESS_KEY=your-access-key
MINIO_SECRET_KEY=your-secret-key
MINIO_SECURE=false
```

### 1.3 啟動服務

```bash
docker compose up -d
```

### 1.4 驗證

```bash
# 檢查容器狀態
docker ps

# 應該看到：
# - automl-redis
# - automl-api
# - automl-mcp
# - automl-worker (x4)

# 測試 API
curl http://localhost:8001/health
# {"status":"healthy","version":"1.0.0"}

# 測試 MCP
curl http://localhost:8002/health 2>/dev/null || echo "MCP running (SSE mode)"
```

### 1.5 查看日誌

```bash
# 全部服務
docker compose logs -f

# 特定服務
docker compose logs -f automl-api
docker compose logs -f automl-worker
```

---

## 2. 生產環境部署

適用於內網生產環境（不需要 HTTPS）。

### 2.1 設定環境變數

```bash
cp .env.example .env
nano .env
```

```bash
# .env - 生產設定
MINIO_ENDPOINT=minio.internal.company.com:9000
MINIO_ACCESS_KEY=prod-access-key
MINIO_SECRET_KEY=prod-secret-key
MINIO_SECURE=false

# 日誌等級
LOG_LEVEL=INFO

# Worker 數量
WORKER_REPLICAS=4
```

### 2.2 啟動

```bash
docker compose up -d
```

### 2.3 擴展 Worker

```bash
# 擴展到 8 個 workers
docker compose up -d --scale automl-worker=8

# 或修改 .env
WORKER_REPLICAS=8
docker compose up -d
```

### 2.4 監控

```bash
# 查看資源使用
docker stats

# 檢查 Redis 佇列
docker exec automl-redis redis-cli LLEN automl:jobs:pending
```

---

## 3. 企業安全部署

適用於需要 HTTPS 和 POST-only API 的企業環境。

### 3.1 架構圖

```
                    ┌─────────────────────────────────────────┐
                    │            外部網路 (Internet)           │
                    └────────────────┬────────────────────────┘
                                     │ HTTPS only (443)
                                     ▼
                    ┌─────────────────────────────────────────┐
                    │              Nginx Proxy                │
                    │  • TLS 1.2/1.3 termination              │
                    │  • POST-only enforcement                │
                    │  • Rate limiting (10 req/s)             │
                    │  • Security headers (HSTS, CSP...)      │
                    └────────────────┬────────────────────────┘
                                     │ HTTP (內部網路)
            ┌────────────────────────┼────────────────────────┐
            │                        │                        │
            ▼                        ▼                        ▼
    ┌──────────────┐        ┌──────────────┐        ┌──────────────┐
    │  AutoML API  │◄──────►│    Redis     │◄──────►│   Workers    │
    │  (內部:8001) │        │  (內部:6379) │        │   (x4)       │
    └──────────────┘        └──────────────┘        └──────────────┘
            │                                              │
            │                                              ▼
            │                                       ┌──────────────┐
            └──────────────────────────────────────►│    MinIO     │
                                                    │  (HTTPS)     │
                                                    └──────────────┘
```

### 3.2 準備 SSL 憑證

#### 選項 A：使用組織憑證（推薦）

```bash
# 建立 SSL 目錄
mkdir -p nginx/ssl

# 複製你的憑證
cp /path/to/your/certificate.crt nginx/ssl/server.crt
cp /path/to/your/private.key nginx/ssl/server.key

# 設定權限
chmod 600 nginx/ssl/server.key
```

#### 選項 B：自簽憑證（僅測試用）

```bash
mkdir -p nginx/ssl

openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/server.key \
  -out nginx/ssl/server.crt \
  -subj "/C=TW/ST=Taiwan/L=Taipei/O=YourOrg/CN=automl.local"

chmod 600 nginx/ssl/server.key
```

### 3.3 設定環境變數

```bash
cp .env.example .env
nano .env
```

```bash
# .env - 企業安全設定

# MinIO (使用 HTTPS)
MINIO_ENDPOINT=minio.company.com:9000
MINIO_ACCESS_KEY=secure-access-key
MINIO_SECRET_KEY=secure-secret-key
MINIO_SECURE=true

# 日誌
LOG_LEVEL=INFO

# Worker 數量
WORKER_REPLICAS=4

# HTTPS Ports（可選，預設 443/80）
# HTTPS_PORT=443
# HTTP_PORT=80
```

### 3.4 啟動 HTTPS 堆疊

```bash
docker compose -f docker-compose.https.yml up -d
```

### 3.5 驗證

```bash
# 檢查容器
docker ps
# 應該看到：automl-nginx, automl-redis, automl-api, automl-mcp, automl-worker

# 測試 HTTPS (忽略自簽憑證錯誤)
curl -k https://localhost/api/health
# {"status":"healthy","version":"1.0.0"}

# 測試 POST-only（GET 應該被拒絕）
curl -k https://localhost/api/v1/jobs/list
# 403 Forbidden

# 使用 POST
curl -k -X POST https://localhost/api/v1/jobs/list \
  -H "Content-Type: application/json" \
  -H "X-User-Id: test-user" \
  -d '{}'
# {"jobs":[]}
```

### 3.6 防火牆設定

```bash
# 只開放 HTTPS
sudo ufw allow 443/tcp
sudo ufw deny 80/tcp   # 或允許，會自動重導到 HTTPS
sudo ufw deny 8001/tcp # 不對外開放內部 API
sudo ufw deny 8002/tcp # 不對外開放 MCP
sudo ufw deny 6379/tcp # 不對外開放 Redis
```

---

## 4. 連接 AI Agent

### 4.1 VS Code Copilot

已內建設定在 `.vscode/mcp.json`，直接使用即可。

### 4.2 Claude Desktop（開發環境）

編輯 Claude Desktop 設定：

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "automl": {
      "type": "sse",
      "url": "http://localhost:8002/sse"
    }
  }
}
```

### 4.3 Claude Desktop（企業 HTTPS）

```json
{
  "mcpServers": {
    "automl": {
      "type": "streamable-http",
      "url": "https://your-server.company.com/mcp/"
    }
  }
}
```

### 4.4 驗證連線

在 Claude 中測試：

```
User: 列出可用的 AutoML 工具

Claude: (should list 20 tools including register_dataset, 
         submit_automl_job, predict, etc.)
```

---

## 5. 疑難排解

### 5.1 容器無法啟動

```bash
# 查看詳細錯誤
docker compose logs automl-api

# 常見問題：
# - MinIO 連線失敗：檢查 MINIO_ENDPOINT 是否可達
# - Redis 連線失敗：等待 Redis 健康檢查通過
```

### 5.2 MinIO 連線問題

```bash
# 從容器內測試 MinIO
docker exec automl-api python -c "
from minio import Minio
import os
client = Minio(
    os.environ['MINIO_ENDPOINT'],
    access_key=os.environ['MINIO_ACCESS_KEY'],
    secret_key=os.environ['MINIO_SECRET_KEY'],
    secure=os.environ.get('MINIO_SECURE', 'false').lower() == 'true'
)
print('Buckets:', [b.name for b in client.list_buckets()])
"
```

### 5.3 Worker 沒有處理任務

```bash
# 檢查 Worker 日誌
docker compose logs -f automl-worker

# 檢查 Redis 佇列
docker exec automl-redis redis-cli LLEN automl:jobs:pending

# 重啟 Workers
docker compose restart automl-worker
```

### 5.4 HTTPS 憑證問題

```bash
# 檢查憑證
openssl x509 -in nginx/ssl/server.crt -text -noout

# 檢查 Nginx 錯誤
docker logs automl-nginx

# 常見問題：
# - 憑證過期
# - 憑證和金鑰不匹配
# - 權限問題（key 需要 600）
```

### 5.5 記憶體不足

```bash
# 檢查記憶體使用
docker stats --no-stream

# 減少 Worker 數量
docker compose up -d --scale automl-worker=2

# 或調整記憶體限制（在 docker-compose.yml）
deploy:
  resources:
    limits:
      memory: 4G  # 從 8G 降到 4G
```

### 5.6 重置所有資料

```bash
# 停止並刪除所有容器和 volumes
docker compose down -v

# 重新開始
docker compose up -d
```

---

## 附錄

### A. 端口對照表

| 服務 | 內部 Port | 開發環境外部 | 企業環境外部 |
|------|-----------|-------------|-------------|
| Nginx | - | - | 443 (HTTPS) |
| AutoML API | 8001 | 8001 | 僅內部 |
| MCP Server | 8002 | 8002 | 僅內部 |
| Redis | 6379 | 6379 | 僅內部 |

### B. 環境變數完整列表

| 變數 | 必填 | 預設值 | 說明 |
|------|------|--------|------|
| `MINIO_ENDPOINT` | ✅ | - | MinIO 伺服器位址 |
| `MINIO_ACCESS_KEY` | ✅ | - | MinIO 存取金鑰 |
| `MINIO_SECRET_KEY` | ✅ | - | MinIO 密鑰 |
| `MINIO_SECURE` | ❌ | `false` | 使用 HTTPS 連線 MinIO |
| `MINIO_DATASET_BUCKET` | ❌ | `automl-datasets` | 資料集 bucket |
| `MINIO_MODEL_BUCKET` | ❌ | `automl-models` | 模型 bucket |
| `LOG_LEVEL` | ❌ | `INFO` | 日誌等級 |
| `WORKER_REPLICAS` | ❌ | `4` | Worker 數量 |
| `HTTPS_PORT` | ❌ | `443` | HTTPS 對外 port |
| `HTTP_PORT` | ❌ | `80` | HTTP 對外 port（會重導到 HTTPS） |

### C. API 端點對照（企業 POST-only）

| 原始端點 | 企業 POST 端點 | Request Body |
|----------|---------------|--------------|
| `GET /datasets` | `POST /api/v1/datasets/list` | `{}` |
| `GET /datasets/{id}` | `POST /api/v1/datasets/get` | `{"dataset_id": "..."}` |
| `GET /jobs` | `POST /api/v1/jobs/list` | `{}` |
| `GET /jobs/{id}` | `POST /api/v1/jobs/get` | `{"job_id": "..."}` |
| `GET /models` | `POST /api/v1/models/list` | `{}` |
| `GET /models/{id}` | `POST /api/v1/models/get` | `{"model_id": "..."}` |
| `GET /models/{id}/leaderboard` | `POST /api/v1/models/leaderboard` | `{"model_id": "..."}` |

原本就是 POST 的端點（training, predict 等）維持不變。
