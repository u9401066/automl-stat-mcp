# 子法：Docker 與服務操作規範

> 依據憲法第 7.2 條「環境即程式碼」訂定

---

## 第 1 條：服務架構概覽

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Docker Compose Stack                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐           │
│  │ automl-mcp  │────▶│ automl-api  │────▶│automl-worker│ (x4)      │
│  │   :8002     │     │   :8001     │     │   (no port) │           │
│  └─────────────┘     └─────────────┘     └─────────────┘           │
│         │                   │                   │                   │
│         │            ┌──────┴──────┐           │                   │
│         │            ▼             ▼           │                   │
│         │     ┌───────────┐ ┌───────────┐     │                   │
│         │     │   Redis   │ │   MinIO   │◀────┘                   │
│         │     │   :6379   │ │ (external)│                         │
│         │     └───────────┘ └───────────┘                         │
│         │                          ▲                               │
│         │     ┌─────────────┐     │                               │
│         └────▶│stats-service│─────┘                               │
│               │   :8003     │                                      │
│               └──────┬──────┘                                      │
│                      │                                             │
│               ┌──────▼──────┐                                      │
│               │stats-worker │ (x2)                                 │
│               │  (no port)  │                                      │
│               └─────────────┘                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 第 2 條：服務啟動與停止

### 2.1 完整啟動

```bash
# 基本啟動（4 個 automl-worker, 2 個 stats-worker）
docker compose up -d

# 查看狀態
docker compose ps

# 查看日誌
docker compose logs -f
```

### 2.2 停止服務

```bash
# 停止但保留資料
docker compose stop

# 停止並移除容器
docker compose down

# 停止並移除所有資料（危險！）
docker compose down -v
```

### 2.3 重啟單一服務

```bash
# 重啟 MCP Server
docker compose restart automl-mcp

# 重建並啟動（程式碼變更後）
docker compose up -d --build automl-mcp
```

---

## 第 3 條：Worker 擴展

### 3.1 調整 Worker 數量

```bash
# 增加 AutoML Worker 到 8 個（大量訓練任務）
docker compose up -d --scale automl-worker=8

# 增加 Stats Worker 到 4 個（大量統計分析）
docker compose up -d --scale stats-worker=4

# 減少 Worker（節省資源）
docker compose up -d --scale automl-worker=2 --scale stats-worker=1
```

### 3.2 GPU 支援

```bash
# 使用 GPU 版本（需要 NVIDIA Docker）
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
```

---

## 第 4 條：MinIO 操作

### 4.1 環境變數配置

```bash
# .env 檔案
MINIO_ENDPOINT=192.168.1.102:9000    # MinIO 伺服器位址
MINIO_ACCESS_KEY=your-access-key     # 存取金鑰
MINIO_SECRET_KEY=your-secret-key     # 密鑰
MINIO_SECURE=false                   # 是否使用 HTTPS
MINIO_DATASET_BUCKET=automl-datasets # 資料集 bucket
MINIO_MODEL_BUCKET=automl-models     # 模型 bucket
MINIO_REPORTS_BUCKET=stats-reports   # 報告 bucket
```

### 4.2 驗證 MinIO 連線

```bash
# 使用 mc 客戶端測試
mc alias set myminio http://192.168.1.102:9000 ACCESS_KEY SECRET_KEY
mc ls myminio/

# 或透過 API 測試
curl http://localhost:8001/health
```

### 4.3 Bucket 管理

```bash
# 列出 buckets
mc ls myminio/

# 建立 bucket
mc mb myminio/automl-datasets
mc mb myminio/automl-models
mc mb myminio/stats-reports

# 列出 bucket 內容
mc ls myminio/automl-datasets/
```

### 4.4 常見 MinIO 錯誤

| 錯誤 | 原因 | 解決方案 |
|------|------|----------|
| `Connection refused` | MinIO 未啟動或網路不通 | 確認 MinIO 服務運行中 |
| `Access Denied` | 金鑰錯誤 | 檢查 .env 中的 ACCESS_KEY/SECRET_KEY |
| `Bucket not found` | Bucket 不存在 | 使用 `mc mb` 建立 |
| `NoSuchKey` | 物件不存在 | 確認路徑正確 |

---

## 第 5 條：Redis 操作

### 5.1 連線到 Redis

```bash
# 透過 Docker
docker compose exec redis redis-cli

# 或直接連線
redis-cli -h localhost -p 6379
```

### 5.2 常用 Redis 命令

```bash
# 查看所有 keys
KEYS *

# 查看 job 狀態
GET automl:job:abc123

# 查看 job queue
LRANGE automl:queue 0 -1

# 清除所有資料（危險！）
FLUSHALL
```

### 5.3 監控 Job 狀態

```bash
# 監控 job 變化（即時）
MONITOR

# 查看特定 pattern 的 keys
KEYS automl:job:*
KEYS stats:job:*
```

### 5.4 常見 Redis 錯誤

| 錯誤 | 原因 | 解決方案 |
|------|------|----------|
| `Connection refused` | Redis 未啟動 | `docker compose up -d redis` |
| `NOAUTH` | 需要密碼但未提供 | 預設無密碼，檢查配置 |
| `OOM` | 記憶體不足 | 增加 Redis 記憶體限制 |

---

## 第 6 條：開發與測試流程

### 6.1 本機開發（不需 Docker）

```bash
# 啟動虛擬環境
source .venv/bin/activate

# 安裝依賴
uv sync --all-extras

# 執行單元測試（隔離，不需服務）
pytest automl-mcp-server/tests/unit/ -v

# 靜態分析
ruff check .
```

### 6.2 整合測試（需要 Docker）

```bash
# 啟動所有服務
docker compose up -d

# 等待服務就緒
sleep 10

# 執行 E2E 測試
pytest tests/test_e2e.py -v

# 完整 E2E 測試
pytest tests/test_e2e_full.py -v
```

### 6.3 測試環境變數

```bash
# tests/.env
MINIO_ENDPOINT=192.168.1.102:9000
MINIO_ACCESS_KEY=your-key
MINIO_SECRET_KEY=your-secret

# 載入方式（test_e2e.py）
from dotenv import load_dotenv
load_dotenv()
```

---

## 第 7 條：日誌與除錯

### 7.1 查看服務日誌

```bash
# 查看所有日誌
docker compose logs -f

# 查看特定服務
docker compose logs -f automl-mcp
docker compose logs -f automl-worker
docker compose logs -f stats-worker

# 查看最近 100 行
docker compose logs --tail=100 automl-api
```

### 7.2 進入容器除錯

```bash
# 進入 MCP Server 容器
docker compose exec automl-mcp /bin/bash

# 進入 Stats Worker 容器
docker compose exec stats-worker /bin/bash

# 測試容器內路徑
docker compose exec automl-mcp ls /data/sample_data/
```

### 7.3 健康檢查

```bash
# API 健康檢查
curl http://localhost:8001/health  # automl-api
curl http://localhost:8003/health  # stats-service

# MCP Server（SSE 端點）
curl http://localhost:8002/sse
```

---

## 第 8 條：常見問題排查

### 8.1 服務無法啟動

```bash
# 1. 檢查日誌
docker compose logs automl-api

# 2. 檢查端口占用
lsof -i :8001

# 3. 檢查依賴服務
docker compose ps redis
```

### 8.2 Worker 無法處理 Job

```bash
# 1. 檢查 Worker 狀態
docker compose ps | grep worker

# 2. 檢查 Redis 連線
docker compose exec automl-worker redis-cli -h redis ping

# 3. 檢查 Job queue
docker compose exec redis redis-cli LRANGE automl:queue 0 -1
```

### 8.3 檔案找不到

```bash
# 1. 確認掛載
docker compose exec automl-mcp ls /data/

# 2. 確認檔案存在（Host）
ls -la ./sample_data/

# 3. 確認權限
docker compose exec automl-mcp stat /data/sample_data/iris.csv
```

---

## 附則

### 第 9 條：環境變數完整清單

```bash
# .env.example
# MinIO Configuration
MINIO_ENDPOINT=192.168.1.102:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_SECURE=false
MINIO_DATASET_BUCKET=automl-datasets
MINIO_MODEL_BUCKET=automl-models
MINIO_REPORTS_BUCKET=stats-reports

# Redis Configuration (optional, defaults work for local)
REDIS_HOST=redis
REDIS_PORT=6379

# Logging
LOG_LEVEL=INFO
```
