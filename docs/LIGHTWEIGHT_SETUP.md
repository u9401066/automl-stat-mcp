# 輕量版啟動指南 (不使用 Docker)

本指南說明如何在本地直接啟動服務，適合開發、測試或資源受限的環境。

---

## 📋 先決條件

- Python 3.10+
- Redis (用於任務隊列)
- 至少 4GB RAM

---

## 🚀 快速啟動

### 1. 安裝 Redis

```bash
# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis

# macOS
brew install redis
brew services start redis

# 或使用 Docker 只啟動 Redis
docker run -d -p 6379:6379 redis:7-alpine
```

### 2. 安裝依賴

**使用 uv (推薦)**：
```bash
# 根目錄安裝所有依賴
cd /home/eric/workspace251204
uv venv
uv sync --all-extras

# 安裝本地 hook（建議）
uv run pre-commit install --install-hooks
```

### 3. 環境變數設定

創建 `.env.local` 檔案：
```bash
# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Storage (本地模式)
STORAGE_MODE=local
DATA_ROOT=/home/eric/workspace251204

# Stats Service
STATS_SERVICE_HOST=0.0.0.0
STATS_SERVICE_PORT=8003

# AutoML Service (可選)
AUTOML_API_HOST=0.0.0.0
AUTOML_API_PORT=8001

# MCP Server
MCP_HOST=0.0.0.0
MCP_PORT=8002

# Celery Workers
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

### 4. 啟動服務

**最小配置（僅統計分析）**：

```bash
# Terminal 1: Stats Service
cd stats-service
export STORAGE_MODE=local DATA_ROOT=/home/eric/workspace251204
uv run python -m src.main

# Terminal 2: Stats Worker
cd stats-worker
uv run celery -A src.celery_app worker --loglevel=info --pool=solo

# Terminal 3: MCP Server
cd automl-mcp-server
uv run python src/main.py --mode sse --host 0.0.0.0 --port 8002
```

**完整配置（含 AutoML）**：

```bash
# Terminal 4: AutoML Service
cd automl-service
uv run python -m src.main

# Terminal 5: AutoML Worker (需要更多 RAM)
cd automl-worker
uv run celery -A src.celery_app worker --loglevel=info --pool=solo --concurrency=1
```

### 5. 驗證服務

```bash
# 檢查服務健康狀態
curl http://localhost:8003/health  # Stats Service
curl http://localhost:8002/health  # MCP Server
curl http://localhost:8001/health  # AutoML Service (if started)

# 測試基本功能
curl -X POST http://localhost:8003/api/direct/quick-stats \
  -H "Content-Type: application/json" \
  -d '{"csv_path": "/home/eric/workspace251204/sample_data/iris.csv"}'
```

---

## 🎯 推薦的輕量版配置

### 配置 A: 純統計分析（最輕量）

**記憶體需求**: ~1GB

```bash
# 只啟動這 3 個服務
1. Redis (docker run -d -p 6379:6379 redis:7-alpine)
2. Stats Service (python -m src.main)
3. MCP Server (python src/main.py)
```

**功能**：
- ✅ 51 個統計分析工具
- ✅ Table One, EDA, 相關性分析
- ✅ 存活分析 (KM, Cox)
- ✅ ROC, PSM, Power 分析
- ❌ 不支援 ML 訓練

### 配置 B: 統計 + MCP（開發測試）

**記憶體需求**: ~1.5GB

```bash
1. Redis
2. Stats Service (port 8003)
3. Stats Worker (1 worker)
4. MCP Server (port 8002)
```

**功能**：
- ✅ 完整統計分析
- ✅ 非同步任務處理
- ✅ MCP 工具集成
- ❌ 不支援 ML 訓練

### 配置 C: 完整功能（需要較多資源）

**記憶體需求**: ~4GB+

```bash
1. Redis
2. Stats Service + Worker
3. AutoML Service + Worker
4. MCP Server
```

**功能**：
- ✅ 完整統計分析
- ✅ AutoML 訓練
- ✅ 所有 51+ MCP 工具

---

## 📊 資料路徑配置

本地模式使用絕對路徑，與 Docker 模式不同：

| 使用場景 | Docker 路徑 | 本地路徑 |
|---------|-------------|----------|
| 範例資料 | `/data/sample_data/iris.csv` | `/home/eric/workspace251204/sample_data/iris.csv` |
| 使用者專案 | `/data/projects/study1/` | `/home/eric/workspace251204/projects/study1/` |
| 分析結果 | `/data/results/` | `/home/eric/workspace251204/local-results/` |

**設定環境變數**：
```bash
export DATA_ROOT=/home/eric/workspace251204
export STORAGE_MODE=local
```

**MCP 工具路徑處理**：
- MCP Server 會自動根據 `DATA_ROOT` 轉換路徑
- API 呼叫使用相對路徑：`iris.csv` → `{DATA_ROOT}/sample_data/iris.csv`

---

## 🧪 測試建議

### 1. 單元測試
```bash
# Stats Service
cd stats-service && pytest tests/

# AutoML MCP Server
cd automl-mcp-server && pytest tests/unit/

# Storage Factory
cd stats-service && pytest tests/test_storage_factory.py -v
```

### 2. 整合測試
```bash
# 需要服務運行
pytest tests/test_service_communication.py -v
pytest tests/test_dataflow_integrity.py -v
```

### 3. E2E 測試（需要服務運行）
```bash
# 統計分析
pytest tests/test_e2e_stats.py -v

# 資料處理
pytest tests/test_e2e_data.py -v

# AutoML (需要 AutoML Service)
pytest tests/test_e2e_automl.py -v

# 視覺化結果
pytest tests/test_e2e_visualization.py -v
```

### 4. 資料集完整測試計畫
```bash
# 參考 tests/E2E_TEST_PLAN.md
# 測試 10 個公開資料集的完整流程
```

---

## 🔧 開發模式

### 熱重載（Hot Reload）

```bash
# Stats Service (自動重載)
cd stats-service
uvicorn src.main:app --reload --host 0.0.0.0 --port 8003

# AutoML Service
cd automl-service
uvicorn src.main:app --reload --host 0.0.0.0 --port 8001

# MCP Server (需手動重啟)
cd automl-mcp-server
python src/main.py --mode sse
```

### 除錯模式

```bash
# 設定詳細日誌
export LOG_LEVEL=DEBUG

# 使用 pytest 除錯
pytest tests/test_xxx.py -v -s --pdb

# 使用 Python debugger
python -m pdb src/main.py
```

---

## 📈 效能建議

### Memory 優化

1. **Stats Worker**: 使用 `--pool=solo` 避免 fork
2. **AutoML Worker**: 限制 `--concurrency=1`
3. **Redis**: 設定 `maxmemory-policy allkeys-lru`

### CPU 優化

```bash
# 限制 Worker 數量
celery -A src.celery_app worker --concurrency=2

# 使用 gevent pool (更輕量)
celery -A src.celery_app worker --pool=gevent --concurrency=10
```

---

## ⚠️ 已知限制

### 輕量版 vs Docker 版

| 功能 | 輕量版 | Docker 版 |
|------|-------|-----------|
| 啟動速度 | ⚡ 快 (秒級) | 🐢 慢 (需 build) |
| 記憶體 | 💚 低 (1-2GB) | 📦 高 (4-8GB) |
| 隔離性 | ❌ 無 | ✅ 完整隔離 |
| 部署便利 | ⚠️ 需手動配置 | ✅ 一鍵啟動 |
| 適合場景 | 開發、測試 | 生產、分散式 |

### 不支援功能（輕量版）

- ❌ MinIO 物件儲存（僅支援本地檔案）
- ❌ 分散式 Worker（需 Docker Swarm 或 K8s）
- ❌ HTTPS/反向代理（需自行配置 Nginx）
- ❌ GPU 加速（需 Docker + NVIDIA Runtime）

---

## 🛠️ 故障排除

### Redis 連線失敗
```bash
# 檢查 Redis 是否運行
redis-cli ping
# 應該回應: PONG

# 檢查端口
netstat -tlnp | grep 6379
```

### 服務啟動失敗
```bash
# 檢查端口佔用
lsof -i :8003  # Stats Service
lsof -i :8002  # MCP Server

# 檢查依賴
pip list | grep fastapi
pip list | grep celery
```

### Worker 無法處理任務
```bash
# 檢查 Celery Broker 連線
celery -A src.celery_app inspect ping

# 檢查隊列狀態
celery -A src.celery_app inspect active_queues
```

---

## 📚 相關文檔

- [Docker 部署指南](../README.md)
- [測試策略](TESTING_STRATEGY.md)
- [架構文檔](ARCHITECTURE.md)
- [E2E 測試計畫](../tests/E2E_TEST_PLAN.md)

---

## 🎓 使用範例

### Example 1: 快速分析 Iris 資料集

```python
import requests

# 1. Quick Stats
response = requests.post(
    "http://localhost:8003/api/direct/quick-stats",
    json={"csv_path": "/home/eric/workspace251204/sample_data/iris.csv"}
)
print(response.json())

# 2. Table One
response = requests.post(
    "http://localhost:8003/api/tableone/generate-direct",
    json={
        "csv_path": "/home/eric/workspace251204/sample_data/iris.csv",
        "group_column": "target"
    }
)
print(response.json())
```

### Example 2: 存活分析

```python
# Kaplan-Meier
response = requests.post(
    "http://localhost:8003/api/survival/kaplan-meier",
    json={
        "csv_path": "/home/eric/workspace251204/sample_data/rossi_recidivism.csv",
        "time_col": "week",
        "event_col": "arrest"
    }
)
print(response.json())
```

### Example 3: ROC 分析

```python
# Compute ROC
response = requests.post(
    "http://localhost:8003/api/roc/compute",
    json={
        "csv_path": "/home/eric/workspace251204/sample_data/predictions.csv",
        "y_true_col": "true_label",
        "y_score_col": "predicted_prob"
    }
)
print(response.json())
```

---

**建議**: 開發測試時使用輕量版，生產部署使用 Docker 版本。
