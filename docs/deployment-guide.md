# AutoML MCP 完整部署指南

本文件提供三種部署情境的完整教學。

---

## 目錄

0. [安裝 MinIO（如果沒有現成的）](#0-安裝-minio)
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
- MinIO 伺服器（參考章節 0 安裝）

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

## 0. 安裝 MinIO

如果你已經有 MinIO 伺服器，可以跳過這個章節。

### 0.1 單機 Docker 部署（開發/測試）

```bash
# 建立資料目錄
mkdir -p ~/minio/data

# 啟動 MinIO
docker run -d \
  --name minio \
  --restart unless-stopped \
  -p 9000:9000 \
  -p 9001:9001 \
  -e "MINIO_ROOT_USER=minioadmin" \
  -e "MINIO_ROOT_PASSWORD=minioadmin" \
  -v ~/minio/data:/data \
  quay.io/minio/minio server /data --console-address ":9001"
```

### 0.2 使用 Docker Compose（推薦）

建立 `docker-compose.minio.yml`：

```yaml
# docker-compose.minio.yml
services:
  minio:
    image: quay.io/minio/minio:latest
    container_name: minio
    ports:
      - "9000:9000"  # API
      - "9001:9001"  # Console
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER:-minioadmin}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD:-minioadmin}
    volumes:
      - minio-data:/data
    command: server /data --console-address ":9001"
    healthcheck:
      test: ["CMD", "mc", "ready", "local"]
      interval: 30s
      timeout: 20s
      retries: 3
    restart: unless-stopped

volumes:
  minio-data:
```

啟動：

```bash
docker compose -f docker-compose.minio.yml up -d
```

### 0.3 驗證安裝

```bash
# 檢查容器狀態
docker ps | grep minio

# 測試 API
curl http://localhost:9000/minio/health/live
# 應該回傳空白（200 OK）
```

### 0.4 存取 MinIO Console

開啟瀏覽器：http://localhost:9001

- 帳號：`minioadmin`（或你設定的 MINIO_ROOT_USER）
- 密碼：`minioadmin`（或你設定的 MINIO_ROOT_PASSWORD）

### 0.5 建立 Bucket（可選）

AutoML 會自動建立 bucket，但你也可以手動建立：

#### 方法 A：使用 Console

1. 登入 http://localhost:9001
2. 點選「Buckets」→「Create Bucket」
3. 建立 `automl-datasets` 和 `automl-models`

#### 方法 B：使用 mc 命令行

```bash
# 安裝 mc（MinIO Client）
docker run --rm -it --entrypoint /bin/sh minio/mc -c "
  mc alias set myminio http://host.docker.internal:9000 minioadmin minioadmin
  mc mb myminio/automl-datasets
  mc mb myminio/automl-models
  mc ls myminio
"
```

### 0.6 設定 .env

確認你的 MinIO 連線資訊：

```bash
# 本機 MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_SECURE=false

# 如果 MinIO 在其他主機
MINIO_ENDPOINT=192.168.1.100:9000
MINIO_ACCESS_KEY=your-access-key
MINIO_SECRET_KEY=your-secret-key
```

### 0.7 生產環境建議

對於生產環境，建議：

1. **修改預設密碼**：
   ```bash
   MINIO_ROOT_USER=your-secure-username
   MINIO_ROOT_PASSWORD=your-very-secure-password-at-least-8-chars
   ```

2. **啟用 HTTPS**：
   ```bash
   docker run -d \
     --name minio \
     -p 9000:9000 \
     -p 9001:9001 \
     -v ~/minio/data:/data \
     -v ~/minio/certs:/root/.minio/certs \
     -e "MINIO_ROOT_USER=admin" \
     -e "MINIO_ROOT_PASSWORD=securepassword" \
     quay.io/minio/minio server /data --console-address ":9001"
   ```
   
   將憑證放在：
   - `~/minio/certs/public.crt`
   - `~/minio/certs/private.key`

3. **建立專用 Access Key**（不要用 root）：
   - 登入 Console → Access Keys → Create Access Key
   - 記下 Access Key 和 Secret Key
   - 在 .env 中使用這組金鑰

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
