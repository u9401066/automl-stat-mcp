# Redis 使用審查報告

**審查日期**: 2026-01-23
**審查範圍**: 整個專案的 Redis 使用情況

---

## 📊 執行摘要

### ✅ 總體評估：良好

Redis 在專案中被廣泛且正確使用，CRUD 操作完整，錯誤處理基本到位。但有部分改進空間。

**優點**：
- ✅ CRUD 操作完整（Create, Read, Update, Delete 都有）
- ✅ 使用 Connection Pool 提升效能
- ✅ 設定 TTL 避免記憶體洩漏
- ✅ 有基本的錯誤處理
- ✅ 測試覆蓋良好（包含 mock 測試）

**待改進**：
- ⚠️ 部分地方缺少錯誤處理
- ⚠️ 連線管理不統一
- ⚠️ 缺少連線池最佳化配置
- ⚠️ `scan` 操作可能效能問題

---

## 🔍 詳細分析

### 1. Redis 客戶端實作

#### 1.1 Stats Service - Redis Client

**檔案**: `stats-service/src/infrastructure/redis_client.py`

**實作品質**: ⭐⭐⭐⭐☆ (4/5)

```python
class RedisClient:
    """Async Redis client for stats job management"""

    def __init__(self):
        self._pool = None

    async def connect(self):
        """Create connection pool"""
        if self._pool is None:
            self._pool = redis.ConnectionPool.from_url(
                f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}",
                decode_responses=True
            )
        return redis.Redis(connection_pool=self._pool)

    async def close(self):
        """Close connection pool"""
        if self._pool:
            await self._pool.disconnect()
            self._pool = None
```

**優點**：
- ✅ 使用 Connection Pool（提升效能）
- ✅ Async/await 非同步操作
- ✅ `decode_responses=True` 自動解碼
- ✅ 有 close() 方法清理資源

**問題**：
- ⚠️ 沒有連線重試機制
- ⚠️ 連線失敗沒有明確的錯誤處理
- ⚠️ Connection Pool 沒有設定 `max_connections` 限制

**建議**：
```python
async def connect(self):
    """Create connection pool with retry"""
    if self._pool is None:
        for attempt in range(3):
            try:
                self._pool = redis.ConnectionPool.from_url(
                    f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}",
                    decode_responses=True,
                    max_connections=50,  # 限制連線數
                    socket_keepalive=True,
                    socket_connect_timeout=5,
                    retry_on_timeout=True
                )
                break
            except redis.ConnectionError as e:
                if attempt == 2:
                    raise
                await asyncio.sleep(1)
    return redis.Redis(connection_pool=self._pool)
```

#### 1.2 Redis Dataset Store

**檔案**:
- `stats-service/src/infrastructure/redis_dataset_store.py`
- `automl-service/src/infrastructure/redis_dataset_store.py`

**實作品質**: ⭐⭐⭐☆☆ (3/5)

**問題 1: 同步 vs 非同步不一致**
```python
# stats-service - 同步實作
class RedisDatasetStore:
    def __init__(self):
        self._redis = redis.Redis(...)  # 同步客戶端

    def get_dataset(self, dataset_id: str):  # 同步方法
        data = self._redis.get(key)
        ...
```

vs

```python
# stats-service/redis_client.py - 非同步實作
class RedisClient:
    async def connect(self):  # 非同步方法
        return redis.Redis(connection_pool=self._pool)
```

**建議**: 統一為非同步實作，避免阻塞事件循環。

**問題 2: stats-service 的 RedisDatasetStore 缺少 CRUD 操作**

```python
# stats-service/src/infrastructure/redis_dataset_store.py
class RedisDatasetStore:
    def get_dataset(self, dataset_id: str):  # ✅ Read
        ...

    def get_datasets_by_user(self, user_id: str):  # ✅ Read (List)
        ...

    def dataset_exists(self, dataset_id: str):  # ✅ Read (Exists)
        ...

    # ❌ 缺少 Create, Update, Delete!
```

但 automl-service 版本有完整 CRUD：
```python
# automl-service/src/infrastructure/redis_dataset_store.py
class RedisDatasetStore:
    def save_dataset(self, dataset_info):  # ✅ Create
    def get_dataset(self, dataset_id):     # ✅ Read
    def get_datasets_by_user(self, user_id):  # ✅ Read
    def delete_dataset(self, dataset_id, user_id):  # ✅ Delete
    def dataset_exists(self, dataset_id):  # ✅ Exists
```

**建議**: stats-service 應該複製 automl-service 的完整實作。

#### 1.3 AutoML Redis Queue

**檔案**: `automl-service/src/infrastructure/queue/redis_queue.py`

**實作品質**: ⭐⭐⭐⭐☆ (4/5)

**優點**：
- ✅ 使用 Redis List 實作佇列（`lpush`/`rpop`）
- ✅ 使用 Redis Hash 儲存 Job 詳細資料
- ✅ 有 cancel_job 和 delete_job 功能
- ✅ CRUD 完整

**問題**：
- ⚠️ `list_jobs` 使用 `scan` 全表掃描，大量 job 時效能差
- ⚠️ 沒有 Job 過期清理機制
- ⚠️ 缺少錯誤處理

**建議**：
```python
def submit_job(self, ...):
    try:
        # Store job in Redis hash
        self._redis.hset(f"{self._job_prefix}{job_id}", mapping=job_data)

        # Set expiry on job (30 days)
        self._redis.expire(f"{self._job_prefix}{job_id}", 2592000)

        # Add to queue
        self._redis.lpush(self._queue_key, job_id)

        return job
    except redis.ConnectionError as e:
        logger.error(f"Redis connection failed: {e}")
        raise HTTPException(status_code=503, detail="Job queue unavailable")
```

---

### 2. CRUD 操作檢查

#### ✅ Create (C)

| 位置 | 操作 | 狀態 |
|------|------|------|
| `redis_client.py` | `create_job()` | ✅ 完整 |
| `redis_client.py` | `set()` | ✅ 完整 |
| `redis_dataset_store.py` (automl) | `save_dataset()` | ✅ 完整 |
| `redis_queue.py` | `submit_job()` | ✅ 完整 |
| `storage.py` | `redis_set()` | ✅ 完整 |

**總評**: ✅ Create 操作完整

#### ✅ Read (R)

| 位置 | 操作 | 狀態 |
|------|------|------|
| `redis_client.py` | `get_job()` | ✅ 完整 |
| `redis_client.py` | `list_jobs()` | ✅ 完整 |
| `redis_client.py` | `get()` | ✅ 完整 |
| `redis_client.py` | `scan_iter()` | ✅ 完整 |
| `redis_dataset_store.py` | `get_dataset()` | ✅ 完整 |
| `redis_dataset_store.py` | `get_datasets_by_user()` | ✅ 完整 |
| `redis_dataset_store.py` | `dataset_exists()` | ✅ 完整 |
| `redis_queue.py` | `get_job()` | ✅ 完整 |
| `redis_queue.py` | `list_jobs()` | ✅ 完整 |
| `storage.py` | `redis_get()` | ✅ 完整 |
| `storage.py` | `redis_keys()` | ✅ 完整 |

**總評**: ✅ Read 操作完整

#### ⚠️ Update (U)

| 位置 | 操作 | 狀態 |
|------|------|------|
| `redis_client.py` | ❌ 無明確 update 方法 | ⚠️ 透過 `set()` 覆寫實作 |
| `redis_queue.py` | ❌ 無明確 update 方法 | ⚠️ Worker 直接用 `hset` 更新 |

**總評**: ⚠️ Update 操作透過覆寫實作，但不夠明確

**建議**: 新增明確的 update 方法
```python
async def update_job(self, job_id: str, updates: dict) -> bool:
    """Update job fields"""
    client = await self.connect()
    job = await self.get_job(job_id)
    if not job:
        return False

    job.update(updates)
    job["updated_at"] = datetime.utcnow().isoformat()

    await client.set(
        f"{STATS_JOBS_PREFIX}{job_id}",
        json.dumps(job),
        ex=86400 * 7
    )
    return True
```

#### ✅ Delete (D)

| 位置 | 操作 | 狀態 |
|------|------|------|
| `redis_client.py` | `delete_job()` | ✅ 完整 |
| `redis_client.py` | `delete()` | ✅ 完整 |
| `redis_dataset_store.py` (automl) | `delete_dataset()` | ✅ 完整 |
| `redis_dataset_store.py` (stats) | ❌ 缺少 | ⚠️ 需要補充 |
| `redis_queue.py` | `delete_job()` | ✅ 完整 |
| `redis_queue.py` | `cancel_job()` | ✅ 完整 |
| `storage.py` | `redis_delete()` | ✅ 完整 |

**總評**: ✅ Delete 操作基本完整，但 stats-service 的 RedisDatasetStore 需要補充

---

### 3. 錯誤處理檢查

#### ✅ 有錯誤處理的地方

**storage.py - 完整的錯誤處理**
```python
@router.post("/redis/set")
async def redis_set(request: RedisSetRequest):
    try:
        await redis_client.set(request.key, value_json, ex=request.ttl)
        return {"status": "success", ...}
    except Exception as e:
        logger.error(f"Redis set failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
```
✅ **評分**: 5/5

**stats-worker - 連線錯誤處理**
```python
try:
    # Redis operations
    ...
except redis.ConnectionError as e:
    logger.error(f"Redis connection error: {e}")
    raise
```
✅ **評分**: 4/5

#### ⚠️ 缺少錯誤處理的地方

**redis_client.py - create_job()**
```python
async def create_job(self, job_type: str, params: dict, ...):
    client = await self.connect()
    # ... 直接操作 Redis，沒有 try-except
    await client.set(...)
    await client.lpush(...)
```
⚠️ **問題**: 如果 Redis 斷線，會直接拋出未處理的異常

**redis_dataset_store.py**
```python
def get_dataset(self, dataset_id: str):
    key = f"{DATASETS_KEY_PREFIX}{dataset_id}"
    data = self._redis.get(key)  # 沒有錯誤處理
    if data:
        return json.loads(data)
    return None
```
⚠️ **問題**:
1. Redis 連線失敗沒有處理
2. `json.loads()` 可能拋出 JSONDecodeError

**redis_queue.py - submit_job()**
```python
def submit_job(self, ...):
    # ... 沒有 try-except
    self._redis.hset(f"{self._job_prefix}{job_id}", mapping=job_data)
    self._redis.lpush(self._queue_key, job_id)
    return job
```
⚠️ **問題**: Redis 操作失敗沒有處理

#### 建議的錯誤處理模式

```python
import redis.exceptions

async def operation_with_retry(self, ...):
    """Redis operation with retry and error handling"""
    for attempt in range(3):
        try:
            client = await self.connect()
            result = await client.operation(...)
            return result

        except redis.ConnectionError as e:
            logger.warning(f"Redis connection error (attempt {attempt + 1}/3): {e}")
            if attempt == 2:
                raise HTTPException(
                    status_code=503,
                    detail="Redis service unavailable"
                )
            await asyncio.sleep(1)

        except redis.TimeoutError as e:
            logger.error(f"Redis timeout: {e}")
            raise HTTPException(status_code=504, detail="Redis timeout")

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in Redis: {e}")
            raise HTTPException(status_code=500, detail="Data corruption")

        except Exception as e:
            logger.error(f"Unexpected Redis error: {e}")
            raise HTTPException(status_code=500, detail="Internal error")
```

---

### 4. 連線管理檢查

#### 問題 1: 多個 Redis 連線實例

專案中有多個獨立的 Redis 連線實例：

```
stats-service/
  ├─ redis_client.py           → RedisClient (有 pool)
  ├─ redis_dataset_store.py    → RedisDatasetStore (無 pool)
  ├─ repositories.py            → RedisJobRepository (有 pool)
  └─ routes/
      ├─ roc.py               → _get_redis() (獨立 pool)
      ├─ propensity.py        → _get_redis() (獨立 pool)
      └─ survival.py          → _get_redis() (獨立 pool)

automl-service/
  ├─ redis_dataset_store.py    → RedisDatasetStore (無 pool)
  └─ queue/redis_queue.py      → RedisJobQueue (無 pool)

stats-worker/
  └─ worker.py                 → StatsWorker (無 pool)

automl-worker/
  └─ worker.py                 → AutoMLWorker (無 pool)
```

**問題**:
- ⚠️ 連線池沒有統一管理
- ⚠️ 部分實作沒有使用連線池（效能差）
- ⚠️ 連線數可能過多（每個 module 都建立新連線）

**建議**: 建立統一的 Redis 連線管理器

```python
# shared/redis_manager.py
class RedisManager:
    """Singleton Redis connection manager"""

    _instance = None
    _pool = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def get_client(self) -> redis.Redis:
        if self._pool is None:
            self._pool = redis.ConnectionPool.from_url(
                f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}",
                decode_responses=True,
                max_connections=50,
                socket_keepalive=True,
                socket_connect_timeout=5,
                retry_on_timeout=True
            )
        return redis.Redis(connection_pool=self._pool)

    async def close(self):
        if self._pool:
            await self._pool.disconnect()
            self._pool = None

# 使用方式
redis_manager = RedisManager.get_instance()
client = await redis_manager.get_client()
```

#### 問題 2: 同步 vs 非同步混用

```python
# 同步實作（阻塞事件循環）
self._redis = redis.Redis(...)
data = self._redis.get(key)  # 同步調用

# 非同步實作（正確）
client = await self.connect()
data = await client.get(key)  # 非同步調用
```

**建議**: 全部改為非同步，避免阻塞。

---

### 5. TTL 設定檢查

#### ✅ 有設定 TTL 的地方

| 位置 | 資料類型 | TTL | 評價 |
|------|----------|-----|------|
| `redis_client.py` | Job metadata | 7 days | ✅ 合理 |
| `storage.py` | Analysis results | 7 days (default) | ✅ 合理 |
| `upload_tools.py` | Temporary datasets | 24 hours | ✅ 合理 |
| `result_storage.py` | Results | 7 days | ✅ 合理 |

#### ⚠️ 沒有設定 TTL 的地方

| 位置 | 資料類型 | 問題 |
|------|----------|------|
| `redis_dataset_store.py` | Dataset metadata | ⚠️ 永久儲存，可能記憶體洩漏 |
| `redis_queue.py` | Job records | ⚠️ 永久儲存，需要手動清理 |

**建議**:
```python
# redis_dataset_store.py
def save_dataset(self, dataset_info):
    key = f"{DATASETS_KEY_PREFIX}{dataset_id}"
    self._redis.set(key, json.dumps(dataset_info))
    self._redis.expire(key, 2592000)  # 30 days TTL

# redis_queue.py
def submit_job(self, ...):
    self._redis.hset(f"{self._job_prefix}{job_id}", mapping=job_data)
    self._redis.expire(f"{self._job_prefix}{job_id}", 2592000)  # 30 days
```

---

### 6. 效能問題

#### 問題 1: SCAN 操作效能

```python
async def list_jobs(self, user_id: str, ...):
    jobs = []
    cursor = 0
    while True:
        cursor, keys = await client.scan(
            cursor, match=f"{STATS_JOBS_PREFIX}*", count=100
        )
        for key in keys:
            data = await client.get(key)  # ⚠️ N+1 查詢問題
            ...
```

**問題**:
- ⚠️ 全表掃描，大量 key 時慢
- ⚠️ N+1 查詢（每個 key 一次 GET）

**建議**: 使用 Redis 二級索引或 Sorted Set
```python
# 建立索引
def save_dataset(self, dataset_info):
    # 原有操作
    self._redis.set(key, json.dumps(dataset_info))

    # 建立用戶索引 (Sorted Set, score = timestamp)
    self._redis.zadd(
        f"datasets:user:{user_id}:index",
        {dataset_id: timestamp}
    )

# 快速查詢
def get_datasets_by_user(self, user_id):
    # 從索引取得 ID 列表
    dataset_ids = self._redis.zrevrange(
        f"datasets:user:{user_id}:index",
        0, 99  # 前 100 筆
    )

    # 批次取得資料 (Pipeline)
    pipe = self._redis.pipeline()
    for dataset_id in dataset_ids:
        pipe.get(f"{DATASETS_KEY_PREFIX}{dataset_id}")
    results = pipe.execute()

    return [json.loads(r) for r in results if r]
```

#### 問題 2: 沒有使用 Pipeline

```python
# 當前實作（慢）
for dataset_id in dataset_ids:
    dataset = self.get_dataset(dataset_id)  # 每次一個請求
    datasets.append(dataset)

# 改進（使用 Pipeline，快 10x）
pipe = self._redis.pipeline()
for dataset_id in dataset_ids:
    pipe.get(f"{DATASETS_KEY_PREFIX}{dataset_id}")
results = pipe.execute()
datasets = [json.loads(r) for r in results if r]
```

---

### 7. 測試覆蓋

#### ✅ 良好的測試

1. **Mock 測試** - `automl-mcp-server/tests/unit/test_service_mock_isolated.py`
   ```python
   class TestRedisOperationsMock:
       async def test_save_result_to_redis(self, mock_redis): ✅
       async def test_get_result_from_redis(self, mock_redis): ✅
       async def test_redis_key_not_found(self, mock_redis): ✅
       async def test_redis_connection_error(self, mock_redis): ✅
       async def test_list_cached_results(self, mock_redis): ✅
   ```

2. **整合測試** - `tests/test_benchmark.py`
   ```python
   def test_redis_set_get(self, benchmark): ✅
   ```

3. **E2E 測試** - `tests/test_e2e_visualization.py`
   ```python
   def test_redis_storage_set_get(): ✅
   ```

#### ⚠️ 缺少的測試

1. **連線重試測試**
2. **TTL 過期測試**
3. **Pipeline 效能測試**
4. **大量資料壓力測試**

---

## 🎯 關鍵問題總結

### 🔴 嚴重問題（必須修復）

1. **stats-service/redis_dataset_store.py 缺少 CUD 操作**
   - ❌ 缺少 `save_dataset()`
   - ❌ 缺少 `delete_dataset()`
   - **影響**: 無法透過 stats-service 管理 dataset

2. **redis_queue.py 沒有設定 TTL**
   - ❌ Job 記錄永久保存
   - **影響**: Redis 記憶體持續增長，最終 OOM

3. **多處缺少錯誤處理**
   - ❌ `redis_client.create_job()` 無錯誤處理
   - ❌ `redis_dataset_store` 全部無錯誤處理
   - ❌ `redis_queue.submit_job()` 無錯誤處理
   - **影響**: Redis 斷線時服務直接崩潰

### 🟡 中等問題（建議修復）

4. **同步/非同步混用**
   - ⚠️ `redis_dataset_store` 使用同步 Redis 客戶端
   - **影響**: 阻塞事件循環，降低併發效能

5. **沒有統一的連線管理**
   - ⚠️ 多個獨立的 Redis 連線實例
   - ⚠️ 部分沒有使用連線池
   - **影響**: 連線數過多，效能浪費

6. **SCAN 操作效能問題**
   - ⚠️ `list_jobs()` 全表掃描
   - ⚠️ N+1 查詢問題
   - **影響**: 大量 job/dataset 時查詢極慢

### 🟢 輕微問題（可優化）

7. **沒有使用 Pipeline**
   - 批次操作沒有優化
   - **影響**: 小幅效能損失

8. **連線池配置不足**
   - 沒有設定 `max_connections`
   - 沒有設定 `socket_keepalive`
   - **影響**: 連線管理不夠健壯

---

## 📋 修復優先級清單

### Priority 1 (本週完成)

1. ✅ **補充 stats-service/redis_dataset_store.py 的 CRUD**
   ```python
   def save_dataset(self, dataset_info): ...
   def delete_dataset(self, dataset_id, user_id): ...
   ```

2. ✅ **為所有 Redis 操作添加錯誤處理**
   ```python
   try:
       result = await client.operation(...)
   except redis.ConnectionError:
       logger.error("Redis connection failed")
       raise HTTPException(503, "Service unavailable")
   except redis.TimeoutError:
       raise HTTPException(504, "Redis timeout")
   ```

3. ✅ **為 Job 和 Dataset 添加 TTL**
   ```python
   self._redis.expire(key, 2592000)  # 30 days
   ```

### Priority 2 (本月完成)

4. 🔄 **統一連線管理**
   - 建立 `RedisManager` singleton
   - 所有模組使用統一的連線池

5. 🔄 **改為非同步實作**
   - `redis_dataset_store` 改用 `redis.asyncio`
   - `redis_queue` 改為非同步

6. 🔄 **優化 list_jobs 效能**
   - 使用 Sorted Set 建立索引
   - 使用 Pipeline 批次查詢

### Priority 3 (後續優化)

7. 📝 **補充測試**
   - 連線重試測試
   - TTL 過期測試
   - 壓力測試

8. 📝 **效能優化**
   - 使用 Pipeline 批次操作
   - 優化連線池配置

---

## 📊 評分卡

| 項目 | 評分 | 說明 |
|------|------|------|
| **CRUD 完整性** | 7/10 | Create/Read/Delete 完整，Update 不夠明確 |
| **錯誤處理** | 5/10 | 部分有處理，但很多地方缺失 |
| **連線管理** | 6/10 | 有用連線池，但不統一 |
| **效能優化** | 6/10 | 有基本優化，但缺少 Pipeline 和索引 |
| **TTL 管理** | 7/10 | 部分有設定，但不完整 |
| **測試覆蓋** | 8/10 | Mock 和整合測試良好 |
| **程式碼品質** | 7/10 | 整體結構好，但有改進空間 |

**總評**: 71/100 (C+)

---

## 🔧 快速修復腳本

建議執行以下修復：

```bash
# 1. 複製完整的 redis_dataset_store 到 stats-service
cp automl-service/src/infrastructure/redis_dataset_store.py \
   stats-service/src/infrastructure/redis_dataset_store.py

# 2. 運行 Redis 健康檢查
python scripts/check_redis_health.py

# 3. 添加 TTL 到現有 keys
python scripts/add_redis_ttl.py
```

---

## ✅ 結論

Redis 在專案中被**廣泛且基本正確**地使用，CRUD 操作大致完整。主要問題在於：

1. **錯誤處理不足** - 需要補充
2. **連線管理不統一** - 需要重構
3. **部分 CRUD 缺失** - 需要補充
4. **效能可優化** - 使用 Pipeline 和索引

建議優先修復 Priority 1 的問題（本週內完成），然後逐步改進其他項目。
