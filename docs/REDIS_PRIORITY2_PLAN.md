# Redis Priority 2 修復計畫

**日期**: 2026-01-23  
**目標**: 完成 Redis 架構重構，提升效能和可維護性

---

## 📋 當前測試覆蓋情況

### ✅ 已有測試

| 測試類型 | 檔案 | 覆蓋範圍 |
|---------|------|----------|
| **Unit Tests** | `automl-mcp-server/tests/unit/test_service_mock_isolated.py` | ✅ Redis 基本操作（set/get/delete）<br>✅ 連線錯誤處理<br>✅ Key 不存在處理 |
| **E2E Tests** | `tests/test_e2e_visualization.py` | ✅ Redis storage set/get |
| **Benchmark** | `tests/test_benchmark.py` | ✅ Redis set/get 效能 |

### ❌ 缺少的測試

| 測試需求 | 狀態 | 優先級 |
|---------|------|--------|
| **RedisManager singleton 測試** | ❌ 缺失 | High |
| **連線池管理測試** | ❌ 缺失 | High |
| **非同步操作測試** | ❌ 缺失 | High |
| **list_jobs 效能測試** | ❌ 缺失 | Medium |
| **Sorted Set 索引測試** | ❌ 缺失 | Medium |
| **RedisClient 單元測試** | ❌ 缺失 | High |
| **RedisDatasetStore 單元測試** | ❌ 缺失 | High |
| **RedisJobQueue 單元測試** | ❌ 缺失 | High |

---

## 🎯 Priority 2 修復項目

### 1. 建立 RedisManager Singleton

**目標**: 統一管理所有 Redis 連線，避免重複建立連線池

**影響範圍**:
- `stats-service/src/infrastructure/redis_client.py`
- `stats-service/src/infrastructure/redis_dataset_store.py`
- `automl-service/src/infrastructure/redis_dataset_store.py`
- `automl-service/src/infrastructure/queue/redis_queue.py`
- `stats-service/src/routes/*.py` (7 個檔案)

**實作步驟**:

```python
# 新檔案: shared/infrastructure/redis_manager.py
class RedisManager:
    """Singleton Redis connection manager for all services"""
    
    _instance = None
    _pool = None
    _lock = asyncio.Lock()
    
    @classmethod
    async def get_instance(cls):
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
                    await cls._instance._initialize_pool()
        return cls._instance
    
    async def _initialize_pool(self):
        """Create connection pool with retry"""
        for attempt in range(3):
            try:
                self._pool = redis.ConnectionPool.from_url(
                    f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}",
                    decode_responses=True,
                    max_connections=50,
                    socket_keepalive=True,
                    socket_connect_timeout=5,
                    retry_on_timeout=True,
                )
                logger.info("Redis connection pool created")
                break
            except Exception as e:
                if attempt == 2:
                    raise
                await asyncio.sleep(1)
    
    async def get_client(self) -> redis.Redis:
        """Get Redis client from pool"""
        if self._pool is None:
            await self._initialize_pool()
        return redis.Redis(connection_pool=self._pool)
    
    async def close(self):
        """Close connection pool"""
        if self._pool:
            await self._pool.disconnect()
            self._pool = None
```

**測試需求**:
```python
# tests/unit/test_redis_manager.py
class TestRedisManager:
    async def test_singleton_pattern()
    async def test_connection_pool_shared()
    async def test_connection_retry()
    async def test_close_pool()
    async def test_multiple_clients_same_pool()
```

**預估工作量**: 4 小時
- 實作 RedisManager: 1 小時
- 重構所有使用處: 2 小時
- 測試編寫: 1 小時

---

### 2. 改為完全非同步實作

**目標**: 所有 Redis 操作使用 `redis.asyncio`，避免阻塞事件循環

**當前問題**:
```python
# ❌ 同步實作（阻塞）
class RedisDatasetStore:
    def __init__(self):
        self._redis = redis.Redis(...)  # 同步客戶端
    
    def get_dataset(self, dataset_id):  # 同步方法
        data = self._redis.get(key)  # 同步調用
```

**修復後**:
```python
# ✅ 非同步實作
class RedisDatasetStore:
    def __init__(self):
        self._manager = None
    
    async def _get_client(self):
        if self._manager is None:
            self._manager = await RedisManager.get_instance()
        return await self._manager.get_client()
    
    async def get_dataset(self, dataset_id):  # 非同步方法
        client = await self._get_client()
        data = await client.get(key)  # 非同步調用
```

**影響範圍**:
- `stats-service/src/infrastructure/redis_dataset_store.py` - 全部改非同步
- `automl-service/src/infrastructure/redis_dataset_store.py` - 全部改非同步
- `automl-service/src/infrastructure/queue/redis_queue.py` - 全部改非同步
- 所有調用這些類別的地方都需要加 `await`

**實作步驟**:
1. 修改 RedisDatasetStore 為非同步
2. 修改 RedisJobQueue 為非同步
3. 更新所有調用處（路由、工具函數）
4. 更新測試

**測試需求**:
```python
# tests/unit/test_redis_async.py
class TestAsyncRedisOperations:
    async def test_dataset_store_async_operations()
    async def test_job_queue_async_operations()
    async def test_no_blocking_calls()
    async def test_concurrent_operations()
```

**預估工作量**: 6 小時
- 修改 RedisDatasetStore (兩個服務): 2 小時
- 修改 RedisJobQueue: 1.5 小時
- 更新調用處: 2 小時
- 測試編寫: 0.5 小時

**風險**: 高（破壞性變更，需要完整測試）

---

### 3. 優化 list_jobs 效能

**目標**: 使用 Sorted Set 建立索引，避免 SCAN 全表掃描

**當前問題**:
```python
# ❌ 效能差（N+1 查詢）
async def list_jobs(self, user_id):
    jobs = []
    cursor = 0
    while True:
        cursor, keys = await client.scan(cursor, match=f"{PREFIX}*")  # 全表掃描
        for key in keys:
            data = await client.get(key)  # N+1 查詢
            job = json.loads(data)
            if job["user_id"] == user_id:
                jobs.append(job)
```

**修復後**:
```python
# ✅ 效能優（索引 + Pipeline）
async def save_job(self, job):
    # 儲存 Job
    await client.set(f"job:{job_id}", json.dumps(job), ex=TTL)
    
    # 建立用戶索引（Sorted Set，score = timestamp）
    timestamp = datetime.utcnow().timestamp()
    await client.zadd(f"user:{user_id}:jobs", {job_id: timestamp})
    await client.expire(f"user:{user_id}:jobs", TTL)

async def list_jobs(self, user_id, limit=50):
    # 從索引取得 Job ID（已排序）
    job_ids = await client.zrevrange(f"user:{user_id}:jobs", 0, limit - 1)
    
    # 批次取得資料（Pipeline）
    pipe = client.pipeline()
    for job_id in job_ids:
        pipe.get(f"job:{job_id}")
    results = await pipe.execute()
    
    # 解析
    jobs = [json.loads(r) for r in results if r]
    return jobs
```

**索引結構**:
```
# Job 資料
job:abc123 → {"id": "abc123", "user_id": "eric", ...}

# 用戶索引（Sorted Set）
user:eric:jobs → {
    "abc123": 1706000000.0,  # score = timestamp
    "def456": 1706000100.0,
    "ghi789": 1706000200.0
}

# 按類型索引（可選）
user:eric:jobs:tableone → {...}
user:eric:jobs:eda → {...}
```

**效能提升**:
- 原本: O(N) scan + O(M) get（N = 所有 job，M = 符合條件的 job）
- 優化: O(log N) + O(M)（使用 Sorted Set + Pipeline）
- **預估提升**: 10-100x（大量 job 時）

**實作步驟**:
1. 修改 `create_job()` - 建立索引
2. 修改 `list_jobs()` - 使用索引查詢
3. 修改 `delete_job()` - 同時刪除索引
4. 數據遷移腳本（可選）

**測試需求**:
```python
# tests/unit/test_redis_performance.py
class TestRedisPerformance:
    async def test_list_jobs_with_index()
    async def test_index_created_on_save()
    async def test_index_deleted_on_delete()
    async def test_large_dataset_performance()
    
# tests/benchmark/test_list_jobs_benchmark.py
def test_list_jobs_old_vs_new(benchmark):
    # 比較 SCAN vs Sorted Set
```

**預估工作量**: 4 小時
- 修改 job 操作函數: 2 小時
- 數據遷移腳本: 1 小時
- 效能測試: 1 小時

---

## 📊 實作順序建議

### 方案 A：逐步實施（推薦）

**優點**: 風險低，可逐步驗證  
**缺點**: 時間較長

```
Week 1: RedisManager Singleton
  Day 1-2: 實作 RedisManager + 測試
  Day 3-4: 重構 stats-service
  Day 5: 重構 automl-service
  Day 6-7: 整合測試、修復 bug

Week 2: 完全非同步實作
  Day 1-2: 修改 RedisDatasetStore (兩個服務)
  Day 3: 修改 RedisJobQueue
  Day 4-5: 更新所有調用處
  Day 6-7: 完整測試、效能驗證

Week 3: 效能優化
  Day 1-2: 實作 Sorted Set 索引
  Day 3-4: 測試和效能對比
  Day 5: 數據遷移
  Day 6-7: 文檔和部署
```

### 方案 B：集中實施（不推薦）

**優點**: 快速完成  
**缺點**: 風險高，難以除錯

```
Week 1: 全部實作
Week 2: 測試和修復
```

---

## ⚠️ 風險評估

| 風險 | 等級 | 緩解措施 |
|------|------|----------|
| **破壞現有功能** | 🔴 High | 完整的單元測試和整合測試 |
| **效能不如預期** | 🟡 Medium | Benchmark 測試，對比舊實作 |
| **連線池耗盡** | 🟡 Medium | 設定 max_connections，監控連線數 |
| **非同步改造工作量大** | 🟡 Medium | 分批實施，逐步驗證 |
| **索引過期不一致** | 🟢 Low | 使用相同的 TTL，定期清理 |

---

## ✅ 驗收標準

### 功能測試
- [ ] 所有現有測試通過（84%+ coverage）
- [ ] 新增 RedisManager 單元測試（10+ 測試）
- [ ] 新增非同步操作測試（15+ 測試）
- [ ] 新增效能測試（5+ 測試）

### 效能指標
- [ ] list_jobs 效能提升 10x+（100 jobs 場景）
- [ ] 連線數減少 50%+（不再重複建立連線池）
- [ ] 無阻塞操作（所有 Redis 調用為非同步）

### 程式碼品質
- [ ] Ruff 檢查通過（zero errors）
- [ ] MyPy 類型檢查通過
- [ ] 無 TODO 或 FIXME
- [ ] 完整的 docstring

### 文檔
- [ ] 更新 REDIS_AUDIT_REPORT.md
- [ ] 更新 ARCHITECTURE.md
- [ ] 建立 REDIS_MIGRATION_GUIDE.md
- [ ] 更新 CHANGELOG.md

---

## 📝 決策點

### 是否要執行 Priority 2？

**考量因素**:

✅ **應該執行的理由**:
1. 效能提升明顯（10-100x）
2. 架構更清晰（統一連線管理）
3. 避免阻塞（完全非同步）
4. 減少連線數（節省資源）

❌ **不執行的理由**:
1. 工作量大（~14 小時）
2. 破壞性變更（需要完整測試）
3. 當前系統可用（Priority 1 已修復關鍵問題）
4. 可能引入新 bug

### 建議：**分階段執行**

**立即執行**: 
- ✅ RedisManager Singleton（影響小，收益大）

**近期執行** (本月內):
- ✅ 完全非同步實作（架構改善）

**後續優化** (下個月):
- 🔄 list_jobs 效能優化（非緊急）

---

## 🚀 開始實作

如果決定執行，建議從 **RedisManager Singleton** 開始：

1. 建立 `shared/infrastructure/redis_manager.py`
2. 編寫單元測試
3. 重構 stats-service
4. 重構 automl-service
5. 執行完整測試
6. 監控效能和連線數

**預估時間**: 4 小時  
**風險等級**: 🟡 Medium  
**價值**: ⭐⭐⭐⭐☆ (4/5)
