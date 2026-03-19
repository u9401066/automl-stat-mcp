# AutoML MCP System - Testing Strategy

> Last Updated: 2025-12-12

## 📊 Current Test Status

| Service | LOC | Existing Tests | Coverage | Target |
|---------|-----|----------------|----------|--------|
| stats-worker | 17,846 | 265+ tests | ~60% | 90% |
| automl-mcp-server | 17,694 | 84 tests | ~15% | 90% |
| stats-service | 5,460 | 0 tests | 0% | 90% |
| automl-service | 3,914 | 1 test file | ~10% | 90% |
| automl-worker | 379 | 0 tests | 0% | 90% |
| **Total** | **45,293** | **~350+** | **~30%** | **90%** |

## 🧪 Isolated Tests (No Docker Required)

automl-mcp-server 現在有隔離測試可以本地執行：

```bash
# 執行所有隔離測試
cd automl-mcp-server
./run_tests.sh --isolated

# 或簡寫
./run_tests.sh -i
```

| 測試檔案 | 測試數量 | 覆蓋範圍 |
|---------|---------|---------|
| test_result_storage_isolated.py | 27 | NumpyJSONEncoder, ResultStorage |
| test_cleaning_isolated.py | 23 | CSV parsing, missing values, encoding |
| test_statistics_isolated.py | 34 | Descriptive stats, tests, correlations |

## 🎯 Testing Pyramid

```
                    ┌─────────────┐
                    │   E2E (5%)  │  ← 晚點做
                    ├─────────────┤
                    │Integration  │  ← 服務間整合
                    │   (15%)     │
                    ├─────────────┤
                    │             │
                    │  Unit Tests │  ← 主要重點
                    │   (80%)     │
                    │             │
                    └─────────────┘
```

## 🔧 測試工具

```python
# requirements-test.txt
pytest>=7.0.0
pytest-asyncio>=0.21.0
pytest-cov>=4.0.0
pytest-mock>=3.10.0
httpx>=0.24.0          # For async API testing
fakeredis>=2.0.0       # Redis mocking
moto>=4.0.0            # S3/MinIO mocking (optional)
factory-boy>=3.2.0     # Test data factories
```

## 📋 Priority Order

### Phase 1: Unit Tests for Core Logic (Week 1-2)

**Priority 1: automl-mcp-server (最多 tools)**
```
src/infrastructure/mcp/handlers/
├── result_storage.py      ← NEW, needs tests
├── statistics_tools.py    ← 4000+ LOC, critical
├── cleaning_tools.py      ← Data cleaning logic
├── upload_tools.py        ← File handling
└── stats_client.py        ← API client
```

**Priority 2: stats-service**
```
src/routes/
├── storage.py            ← NEW, needs tests
├── cleaning.py           ← Cleaning API
└── stats.py              ← Stats API
```

**Priority 3: automl-service**
```
src/
├── application/services/ ← Business logic
├── domain/              ← Domain models
└── interface/routes/    ← API routes
```

### Phase 2: Integration Tests (Week 3)

```
tests/integration/
├── test_mcp_to_stats_service.py
├── test_mcp_to_automl_service.py
├── test_stats_service_to_worker.py
└── test_result_persistence.py
```

---

## 🧪 Unit Test Templates

### 1. MCP Tool Tests (statistics_tools.py)

```python
# tests/unit/test_statistics_tools.py
import pytest
from unittest.mock import Mock, patch, AsyncMock
import pandas as pd
import numpy as np

class TestCompareGroups:
    """Test compare_groups tool"""

    @pytest.fixture
    def sample_df(self):
        return pd.DataFrame({
            'group': [0, 0, 0, 1, 1, 1],
            'value': [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
        })

    @pytest.fixture
    def csv_path(self, tmp_path, sample_df):
        path = tmp_path / "test.csv"
        sample_df.to_csv(path, index=False)
        return str(path)

    @pytest.mark.asyncio
    async def test_compare_groups_ttest(self, csv_path):
        """Test t-test for 2 groups"""
        from src.infrastructure.mcp.handlers.statistics_tools import register_statistics_tools

        # Create mock MCP server
        mcp = Mock()
        tools = {}
        mcp.tool = lambda: lambda f: tools.__setitem__(f.__name__, f) or f

        register_statistics_tools(mcp)
        result = await tools['compare_groups'](
            csv_path=csv_path,
            numeric_column='value',
            group_column='group'
        )

        assert result['status'] == 'success'
        assert result['n_groups'] == 2
        assert 'main_test' in result
        assert result['main_test']['test'] == 'Independent t-test'

    @pytest.mark.asyncio
    async def test_compare_groups_invalid_column(self, csv_path):
        """Test error handling for invalid column"""
        # ... test error case

    @pytest.mark.asyncio
    async def test_compare_groups_with_save(self, csv_path):
        """Test result persistence"""
        with patch('src.infrastructure.mcp.handlers.result_storage.get_result_storage') as mock:
            mock.return_value.save_result = AsyncMock(return_value=Mock(
                result_id='test_123',
                minio_path='bucket/path/test.json'
            ))
            # ... test save_result=True


class TestAnalyzeCorrelations:
    """Test analyze_correlations tool"""

    @pytest.mark.asyncio
    async def test_pearson_correlation(self, csv_path):
        """Test Pearson correlation"""
        pass

    @pytest.mark.asyncio
    async def test_spearman_correlation(self, csv_path):
        """Test Spearman correlation"""
        pass


class TestGenerateTableone:
    """Test generate_tableone_directly tool"""

    @pytest.mark.asyncio
    async def test_basic_tableone(self, csv_path):
        """Test basic Table 1 generation"""
        pass

    @pytest.mark.asyncio
    async def test_grouped_tableone(self, csv_path):
        """Test grouped Table 1"""
        pass
```

### 2. Result Storage Tests

```python
# tests/unit/test_result_storage.py
import pytest
from unittest.mock import AsyncMock, patch
import json

class TestResultStorage:
    """Test ResultStorage class"""

    @pytest.fixture
    def storage(self):
        from src.infrastructure.mcp.handlers.result_storage import ResultStorage
        return ResultStorage(
            stats_service_url="http://mock:8003",
            minio_bucket="test-bucket"
        )

    def test_generate_result_id(self, storage):
        """Test result ID generation"""
        result_id = storage._generate_result_id("tableone")
        assert result_id.startswith("stat_tableone_")
        assert len(result_id) == len("stat_tableone_") + 8

    def test_get_minio_path(self, storage):
        """Test MinIO path generation"""
        path = storage._get_minio_path("user1", "roc", "stat_roc_abc123")
        assert path.startswith("user1/roc/")
        assert "stat_roc_abc123" in path

    @pytest.mark.asyncio
    async def test_save_result_success(self, storage):
        """Test successful result save"""
        with patch.object(storage, '_save_to_redis', new_callable=AsyncMock):
            with patch.object(storage, '_save_to_minio', new_callable=AsyncMock):
                metadata = await storage.save_result(
                    result={'status': 'success', 'data': [1, 2, 3]},
                    user_id='test_user',
                    analysis_type='correlation'
                )

                assert metadata.result_id.startswith('stat_correlation_')
                assert metadata.user_id == 'test_user'


class TestNumpyJSONEncoder:
    """Test custom JSON encoder"""

    def test_numpy_int64(self):
        from src.infrastructure.mcp.handlers.result_storage import safe_json_dumps
        import numpy as np

        data = {'value': np.int64(42)}
        result = safe_json_dumps(data)
        assert json.loads(result)['value'] == 42

    def test_numpy_float64(self):
        from src.infrastructure.mcp.handlers.result_storage import safe_json_dumps
        import numpy as np

        data = {'value': np.float64(3.14)}
        result = safe_json_dumps(data)
        assert abs(json.loads(result)['value'] - 3.14) < 0.001

    def test_numpy_array(self):
        from src.infrastructure.mcp.handlers.result_storage import safe_json_dumps
        import numpy as np

        data = {'values': np.array([1, 2, 3])}
        result = safe_json_dumps(data)
        assert json.loads(result)['values'] == [1, 2, 3]

    def test_numpy_bool(self):
        from src.infrastructure.mcp.handlers.result_storage import safe_json_dumps
        import numpy as np

        data = {'flag': np.bool_(True)}
        result = safe_json_dumps(data)
        assert json.loads(result)['flag'] == True
```

### 3. API Route Tests (stats-service)

```python
# stats-service/tests/test_storage_routes.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

@pytest.fixture
def client():
    from src.main import app
    return TestClient(app)

class TestRedisRoutes:
    """Test Redis storage routes"""

    def test_redis_set(self, client):
        """Test POST /storage/redis/set"""
        with patch('src.routes.storage.redis_client') as mock_redis:
            mock_redis.set = AsyncMock()

            response = client.post('/storage/redis/set', json={
                'key': 'test_key',
                'value': {'data': 'test'},
                'ttl': 3600
            })

            assert response.status_code == 200
            assert response.json()['status'] == 'success'

    def test_redis_get_exists(self, client):
        """Test GET /storage/redis/get - key exists"""
        with patch('src.routes.storage.redis_client') as mock_redis:
            mock_redis.get = AsyncMock(return_value='{"data": "test"}')

            response = client.get('/storage/redis/get', params={'key': 'test_key'})

            assert response.status_code == 200
            assert response.json()['exists'] == True

    def test_redis_get_not_exists(self, client):
        """Test GET /storage/redis/get - key not exists"""
        with patch('src.routes.storage.redis_client') as mock_redis:
            mock_redis.get = AsyncMock(return_value=None)

            response = client.get('/storage/redis/get', params={'key': 'missing'})

            assert response.status_code == 200
            assert response.json()['exists'] == False


class TestMinioRoutes:
    """Test MinIO storage routes"""

    def test_minio_upload(self, client):
        """Test POST /storage/minio/upload"""
        with patch('src.routes.storage.minio_client') as mock_minio:
            mock_minio.ensure_bucket = lambda x: None
            mock_minio.put_object = lambda **kwargs: None

            response = client.post('/storage/minio/upload', json={
                'bucket': 'test-bucket',
                'path': 'test/file.json',
                'content': '{"data": "test"}',
                'content_type': 'application/json'
            })

            assert response.status_code == 200
            assert response.json()['full_path'] == 'test-bucket/test/file.json'
```

### 4. Cleaning Tools Tests

```python
# tests/unit/test_cleaning_tools.py
import pytest
import pandas as pd
import numpy as np

class TestHandleMissingValues:
    """Test handle_missing_values tool"""

    @pytest.fixture
    def df_with_missing(self, tmp_path):
        df = pd.DataFrame({
            'a': [1, 2, np.nan, 4],
            'b': ['x', None, 'y', 'z'],
            'c': [1.0, 2.0, 3.0, 4.0]
        })
        path = tmp_path / "test.csv"
        df.to_csv(path, index=False)
        return str(path)

    @pytest.mark.asyncio
    async def test_mean_imputation(self, df_with_missing):
        """Test mean imputation for numeric columns"""
        # ... test implementation

    @pytest.mark.asyncio
    async def test_median_imputation(self, df_with_missing):
        """Test median imputation"""
        pass

    @pytest.mark.asyncio
    async def test_mode_imputation(self, df_with_missing):
        """Test mode imputation for categorical"""
        pass


class TestConvertToBinary:
    """Test convert_to_binary tool"""

    @pytest.mark.asyncio
    async def test_yes_no_mapping(self, tmp_path):
        """Test Yes/No to 1/0 conversion"""
        pass

    @pytest.mark.asyncio
    async def test_custom_mapping(self, tmp_path):
        """Test custom value mapping"""
        pass
```

---

## 🔗 Integration Test Templates

### MCP to Stats Service Integration

```python
# tests/integration/test_mcp_stats_integration.py
import pytest
import httpx
from unittest.mock import patch

class TestMCPStatsIntegration:
    """Integration tests for MCP -> Stats Service"""

    @pytest.fixture
    def stats_service_url(self):
        return "http://localhost:8003"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_storage_save_and_retrieve(self, stats_service_url):
        """Test saving and retrieving results via Stats Service"""
        async with httpx.AsyncClient() as client:
            # Save
            save_response = await client.post(
                f"{stats_service_url}/storage/redis/set",
                json={
                    'key': 'integration_test_key',
                    'value': {'test': 'data'},
                    'ttl': 60
                }
            )
            assert save_response.status_code == 200

            # Retrieve
            get_response = await client.get(
                f"{stats_service_url}/storage/redis/get",
                params={'key': 'integration_test_key'}
            )
            assert get_response.status_code == 200
            assert get_response.json()['value']['test'] == 'data'

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_minio_upload_download(self, stats_service_url):
        """Test MinIO upload and download"""
        pass
```

---

## 🚀 Running Tests

### Unit Tests (Fast, No External Dependencies)

```bash
# Run all unit tests
cd automl-mcp-server
pytest tests/unit/ -v

# Run with coverage
pytest tests/unit/ --cov=src --cov-report=html --cov-report=term-missing

# Run specific test file
pytest tests/unit/test_result_storage.py -v
```

### Integration Tests (Requires Running Services)

```bash
# Start services first
docker compose up -d redis stats-service

# Run integration tests
pytest tests/integration/ -v -m integration

# Or with marker
pytest -m "integration" -v
```

### Coverage Report

```bash
# Generate HTML coverage report
pytest --cov=src --cov-report=html

# Open report
open htmlcov/index.html
```

---

## 📁 Recommended Test Structure

```
automl-mcp-server/
└── tests/
    ├── __init__.py
    ├── conftest.py              # Shared fixtures
    ├── unit/
    │   ├── __init__.py
    │   ├── test_result_storage.py
    │   ├── test_statistics_tools.py
    │   ├── test_cleaning_tools.py
    │   ├── test_upload_tools.py
    │   └── test_stats_client.py
    └── integration/
        ├── __init__.py
        └── test_stats_service.py

stats-service/
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── unit/
    │   ├── test_storage_routes.py
    │   ├── test_cleaning_routes.py
    │   └── test_redis_client.py
    └── integration/
        └── test_minio_client.py
```

---

## 🎯 Coverage Goals by Module

| Module | Current | Week 1 | Week 2 | Week 3 |
|--------|---------|--------|--------|--------|
| result_storage.py | 0% | 90% | 90% | 90% |
| statistics_tools.py | 0% | 40% | 70% | 90% |
| cleaning_tools.py | 0% | 60% | 90% | 90% |
| stats-service/routes | 0% | 50% | 80% | 90% |
| automl-service | 10% | 30% | 60% | 90% |

---

## Next Steps

1. **今天**: 建立測試基礎設施 (conftest.py, fixtures)
2. **Week 1**: 完成 result_storage.py + cleaning_tools.py 測試
3. **Week 2**: 完成 statistics_tools.py 核心功能測試
4. **Week 3**: Integration tests + coverage 達標
