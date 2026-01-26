# 🧪 測試增強計劃 - 邊界測試 & E2E 測試

> 基於現有 350+ 測試，補充邊界測試、端到端測試和特殊場景測試

## 📊 測試缺口分析

### 現有測試覆蓋
- ✅ Unit Tests: 350+ (主要在 stats-worker, automl-mcp-server)
- ✅ Integration Tests: 部分覆蓋
- ⚠️ Edge Cases: **缺少**
- ⚠️ E2E Tests: **僅部分覆蓋**
- ❌ Performance Tests: **無**
- ❌ Security Tests: **無**
- ❌ Chaos/Resilience Tests: **無**

---

## 🎯 Phase 1: 邊界測試 (Edge Cases)

### 1.1 資料邊界測試

```python
# tests/edge_cases/test_data_boundaries.py

class TestDataSizeBoundaries:
    """測試資料大小邊界"""
    
    def test_empty_dataframe(self):
        """空資料集 (0 rows)"""
        df = pd.DataFrame()
        # 預期: 友善錯誤訊息
    
    def test_single_row(self):
        """單一筆資料"""
        df = pd.DataFrame({'a': [1]})
        # 預期: 統計分析應警告樣本數不足
    
    def test_two_rows(self):
        """兩筆資料（最小統計可行集）"""
        df = pd.DataFrame({'a': [1, 2]})
        # 預期: 某些統計可行，某些不可行
    
    def test_huge_dataset(self):
        """超大資料集 (100萬筆)"""
        df = pd.DataFrame({'a': range(1_000_000)})
        # 預期: Memory-efficient 處理，不 crash
    
    def test_single_column(self):
        """單一欄位"""
        df = pd.DataFrame({'a': [1, 2, 3]})
        # 預期: 相關性分析應友善處理
    
    def test_max_columns(self):
        """超多欄位 (1000 columns)"""
        df = pd.DataFrame({f'col_{i}': [1, 2, 3] for i in range(1000)})
        # 預期: VIF/相關性分析應有效能限制


class TestDataTypeBoundaries:
    """測試資料型態邊界"""
    
    def test_all_nan_column(self):
        """完全缺失的欄位"""
        df = pd.DataFrame({'a': [np.nan] * 10})
        # 預期: 友善警告
    
    def test_all_same_value(self):
        """所有值相同（零變異）"""
        df = pd.DataFrame({'a': [1] * 100})
        # 預期: Constant column 警告
    
    def test_mixed_types_in_column(self):
        """混合型態（數字 + 字串）"""
        df = pd.DataFrame({'a': [1, 2, '3', 4]})
        # 預期: 型態轉換或錯誤處理
    
    def test_infinity_values(self):
        """Infinity 和 -Infinity"""
        df = pd.DataFrame({'a': [1, np.inf, -np.inf, 2]})
        # 預期: 應偵測並處理
    
    def test_extreme_outliers(self):
        """極端離群值"""
        df = pd.DataFrame({'a': [1, 2, 3, 1e10]})
        # 預期: 離群值偵測應標記
    
    def test_unicode_special_chars(self):
        """特殊 Unicode 字元"""
        df = pd.DataFrame({'名字': ['測試', '🎉', '中文']})
        # 預期: 正確處理 UTF-8


class TestStatisticalBoundaries:
    """測試統計分析邊界"""
    
    def test_perfect_correlation(self):
        """完美正相關 (r=1.0)"""
        df = pd.DataFrame({'a': [1, 2, 3], 'b': [2, 4, 6]})
        # 預期: 正確計算 r=1.0
    
    def test_zero_variance_group(self):
        """零變異群組（無法計算 t-test）"""
        df = pd.DataFrame({
            'group': [0, 0, 0, 1, 1, 1],
            'value': [1, 1, 1, 2, 3, 4]
        })
        # 預期: 友善錯誤訊息
    
    def test_unbalanced_groups(self):
        """極度不平衡群組 (1:1000)"""
        df = pd.DataFrame({
            'group': [0] + [1] * 1000,
            'value': np.random.randn(1001)
        })
        # 預期: 警告樣本數不平衡
    
    def test_all_same_survival_time(self):
        """所有存活時間相同（無法 KM 分析）"""
        df = pd.DataFrame({
            'time': [10] * 100,
            'event': [1] * 100
        })
        # 預期: 友善處理或警告


class TestMLBoundaries:
    """測試 ML 訓練邊界"""
    
    def test_more_features_than_samples(self):
        """特徵數 > 樣本數 (p >> n)"""
        df = pd.DataFrame(np.random.randn(10, 100))
        # 預期: 警告或自動特徵選擇
    
    def test_perfectly_separable(self):
        """完美可分類資料（過擬合風險）"""
        df = pd.DataFrame({
            'x': [1, 2, 3, 4, 5, 6],
            'y': [0, 0, 0, 1, 1, 1]
        })
        # 預期: 完美準確度，但應警告
    
    def test_imbalanced_classes_extreme(self):
        """極度不平衡類別 (1:10000)"""
        # 預期: 自動使用 class_weight 或警告
```

---

### 1.2 輸入驗證邊界測試

```python
# tests/edge_cases/test_input_validation.py

class TestPathBoundaries:
    """測試檔案路徑邊界"""
    
    def test_empty_path(self):
        """空路徑"""
        # 預期: 明確錯誤訊息
    
    def test_nonexistent_path(self):
        """不存在的檔案"""
        # 預期: FileNotFoundError with helpful message
    
    def test_path_traversal_attack(self):
        """路徑遍歷攻擊 (../../etc/passwd)"""
        # 預期: 安全拒絕
    
    def test_extremely_long_path(self):
        """超長路徑 (4096+ 字元)"""
        # 預期: 優雅處理或限制
    
    def test_special_chars_in_path(self):
        """路徑中的特殊字元"""
        # 預期: 正確轉義或清理


class TestParameterBoundaries:
    """測試參數邊界"""
    
    def test_negative_time_limit(self):
        """負數時間限制"""
        # 預期: 拒絕並提示
    
    def test_zero_time_limit(self):
        """零時間限制"""
        # 預期: 使用預設值或拒絕
    
    def test_huge_time_limit(self):
        """超大時間限制 (9999999)"""
        # 預期: 應有最大值限制
    
    def test_invalid_method_name(self):
        """無效的分析方法名稱"""
        # 預期: 列出可用方法
    
    def test_empty_column_list(self):
        """空欄位列表"""
        # 預期: 使用全部欄位或錯誤
```

---

## 🎯 Phase 2: E2E 測試補充

### 2.1 完整工作流測試

```python
# tests/e2e/test_complete_workflows.py

class TestResearchWorkflowE2E:
    """完整研究工作流 E2E 測試"""
    
    @pytest.mark.e2e
    async def test_medical_rct_full_pipeline(self):
        """
        醫學 RCT 完整流程:
        1. 上傳資料
        2. 資料清理 (missing values)
        3. 生成 Table One
        4. 傾向分數匹配
        5. 治療效果估計
        6. 生成報告
        """
        # Step 1: Upload
        upload_result = await upload_dataset(
            name="rct_study",
            source_path="/data/sample_data/medical_study_200.csv",
            storage_mode="temporary",
            user_id="test_user"
        )
        job_id = upload_result['job_id']
        
        # Step 2: Clean data
        clean_result = await handle_missing_values(
            job_id=job_id,
            strategy="median",
            numeric_columns=["age", "bmi"]
        )
        
        # Step 3: Table One
        tableone_result = await generate_tableone_directly(
            job_id=job_id,
            group_column="treatment_group"
        )
        assert 'html_report' in tableone_result
        
        # Step 4: PSM
        psm_result = await run_propensity_analysis(
            job_id=job_id,
            treatment_col="treatment_group",
            outcome_col="outcome"
        )
        
        # Step 5: Treatment effect
        effect_result = await estimate_treatment_effect(
            job_id=job_id,
            treatment_col="treatment_group",
            outcome_col="outcome"
        )
        
        # Verify end-to-end
        assert effect_result['status'] == 'success'
        assert 'ate' in effect_result
    
    @pytest.mark.e2e
    async def test_ml_training_full_pipeline(self):
        """
        ML 訓練完整流程:
        1. 上傳資料
        2. 資料品質檢查
        3. 特徵工程
        4. 訓練模型
        5. 評估模型
        6. 預測
        """
        # Step 1: Upload permanent
        upload_result = await upload_dataset(
            name="breast_cancer_ml",
            source_path="/data/sample_data/breast_cancer.csv",
            storage_mode="permanent",
            user_id="test_user"
        )
        dataset_id = upload_result['dataset_id']
        
        # Step 2: Quality check
        quality_result = await quality_check(
            csv_path="/data/sample_data/breast_cancer.csv"
        )
        assert quality_result['analysis_readiness'] == 'ready'
        
        # Step 3: Feature engineering
        vif_result = await check_multicollinearity(
            csv_path="/data/sample_data/breast_cancer.csv"
        )
        
        # Step 4: Train
        train_result = await train_and_wait(
            dataset_id=dataset_id,
            target_column="diagnosis",
            problem_type="binary",
            time_limit=60,
            user_id="test_user"
        )
        
        # Step 5: Evaluate
        leaderboard = await get_model_leaderboard(
            model_id=train_result['model_id'],
            user_id="test_user"
        )
        assert len(leaderboard['leaderboard']) > 0
        
        # Step 6: Predict
        predict_result = await predict(
            model_id=train_result['model_id'],
            dataset_id=dataset_id,
            user_id="test_user"
        )
        assert len(predict_result['predictions']) > 0


class TestMultiUserWorkflow:
    """多使用者並行工作流測試"""
    
    @pytest.mark.e2e
    async def test_concurrent_users(self):
        """
        測試多個使用者同時使用系統
        - User A: 訓練模型
        - User B: 統計分析
        - User C: 資料上傳
        """
        import asyncio
        
        async def user_a_workflow():
            # ML training
            result = await upload_dataset(...)
            return await train_and_wait(...)
        
        async def user_b_workflow():
            # Statistical analysis
            result = await upload_dataset(...)
            return await generate_tableone_directly(...)
        
        async def user_c_workflow():
            # Data upload
            return await upload_dataset(...)
        
        # Run concurrent
        results = await asyncio.gather(
            user_a_workflow(),
            user_b_workflow(),
            user_c_workflow()
        )
        
        # All should succeed
        assert all(r['status'] == 'success' for r in results)
```

---

### 2.2 錯誤恢復測試

```python
# tests/e2e/test_error_recovery.py

class TestErrorRecoveryE2E:
    """測試錯誤恢復機制"""
    
    @pytest.mark.e2e
    async def test_resume_after_worker_crash(self):
        """測試 Worker 崩潰後恢復"""
        # Submit job
        job_id = await submit_automl_job(...)
        
        # Kill worker mid-training
        os.system("docker compose kill automl-worker")
        await asyncio.sleep(5)
        
        # Restart worker
        os.system("docker compose up -d automl-worker")
        
        # Job should eventually complete or gracefully fail
        status = await wait_for_job(job_id, timeout=300)
        assert status['status'] in ['completed', 'failed']
        assert 'error_message' in status if status['status'] == 'failed'
    
    @pytest.mark.e2e
    async def test_redis_connection_loss(self):
        """測試 Redis 連線中斷恢復"""
        # Start job
        job_id = await submit_job(...)
        
        # Simulate Redis restart
        os.system("docker compose restart automl-redis")
        
        # System should recover and retry
        await asyncio.sleep(10)
        status = await get_job_status(job_id)
        assert status is not None
    
    @pytest.mark.e2e
    async def test_minio_unavailable(self):
        """測試 MinIO 不可用時的 fallback"""
        # Set storage mode to MinIO
        os.environ['STORAGE_MODE'] = 'minio'
        
        # Submit job while MinIO is down
        with pytest.raises(ConnectionError):
            await upload_dataset(
                storage_mode='permanent',
                ...
            )
        
        # Should gracefully fallback or error
```

---

## 🎯 Phase 3: 性能測試 (Performance Tests)

```python
# tests/performance/test_benchmarks.py

class TestPerformanceBenchmarks:
    """性能基準測試"""
    
    @pytest.mark.performance
    def test_dataset_load_speed(self):
        """
        測試資料載入速度
        - 小資料 (<1MB): <100ms
        - 中資料 (1-10MB): <1s
        - 大資料 (10-100MB): <10s
        """
        import time
        
        # Small dataset
        start = time.time()
        df = pd.read_csv("/data/sample_data/iris.csv")
        elapsed = time.time() - start
        assert elapsed < 0.1, f"Small dataset too slow: {elapsed}s"
        
        # Medium dataset (generate)
        large_df = pd.DataFrame(np.random.randn(100000, 50))
        path = "/tmp/medium.csv"
        large_df.to_csv(path)
        
        start = time.time()
        df = pd.read_csv(path)
        elapsed = time.time() - start
        assert elapsed < 1.0, f"Medium dataset too slow: {elapsed}s"
    
    @pytest.mark.performance
    async def test_concurrent_requests(self):
        """
        測試並行請求處理能力
        - 10 concurrent: <2s total
        - 50 concurrent: <10s total
        """
        import asyncio
        import time
        
        async def single_request():
            return await quick_preview("iris.csv")
        
        # 10 concurrent
        start = time.time()
        tasks = [single_request() for _ in range(10)]
        await asyncio.gather(*tasks)
        elapsed = time.time() - start
        assert elapsed < 2.0, f"10 concurrent too slow: {elapsed}s"
    
    @pytest.mark.performance
    def test_memory_usage_large_dataset(self):
        """
        測試大資料集記憶體使用
        - 應使用 chunking 避免 OOM
        """
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        mem_before = process.memory_info().rss / 1024 / 1024  # MB
        
        # Generate 1GB dataset
        huge_df = pd.DataFrame(np.random.randn(10_000_000, 20))
        
        mem_after = process.memory_info().rss / 1024 / 1024
        mem_increase = mem_after - mem_before
        
        # Should not use more than 2GB for 1GB data
        assert mem_increase < 2000, f"Memory usage too high: {mem_increase}MB"


class TestStressTests:
    """壓力測試"""
    
    @pytest.mark.stress
    async def test_100_sequential_jobs(self):
        """提交 100 個連續任務"""
        job_ids = []
        for i in range(100):
            result = await submit_automl_job(
                dataset_id=f"test_dataset_{i}",
                ...
            )
            job_ids.append(result['job_id'])
        
        # All should be queued or processing
        statuses = [await get_job_status(jid) for jid in job_ids]
        assert all(s['status'] in ['queued', 'processing', 'completed'] for s in statuses)
    
    @pytest.mark.stress
    async def test_memory_leak_detection(self):
        """
        偵測記憶體洩漏
        - 執行 1000 次操作，記憶體不應持續增長
        """
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        mem_samples = []
        
        for i in range(1000):
            await quick_preview("iris.csv")
            
            if i % 100 == 0:
                mem = process.memory_info().rss / 1024 / 1024
                mem_samples.append(mem)
        
        # Memory should stabilize, not keep growing
        mem_growth = mem_samples[-1] - mem_samples[0]
        assert mem_growth < 100, f"Memory leak detected: {mem_growth}MB growth"
```

---

## 🎯 Phase 4: 安全測試 (Security Tests)

```python
# tests/security/test_security_validation.py

class TestSecurityValidation:
    """安全性驗證測試"""
    
    def test_sql_injection_in_column_name(self):
        """SQL 注入攻擊測試（欄位名稱）"""
        malicious_col = "' OR '1'='1'; DROP TABLE users; --"
        
        with pytest.raises(ValueError):
            await generate_tableone_directly(
                csv_path="iris.csv",
                group_column=malicious_col
            )
    
    def test_command_injection_in_path(self):
        """命令注入攻擊測試"""
        malicious_path = "iris.csv; rm -rf /"
        
        with pytest.raises(SecurityError):
            await upload_dataset(
                source_path=malicious_path
            )
    
    def test_xss_in_result(self):
        """XSS 攻擊測試（結果輸出）"""
        df = pd.DataFrame({'name': ['<script>alert("XSS")</script>']})
        result = await generate_tableone_directly(...)
        
        # HTML output should escape special chars
        assert '<script>' not in result['html_report']
        assert '&lt;script&gt;' in result['html_report']
    
    def test_path_traversal_attack(self):
        """路徑遍歷攻擊測試"""
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "/etc/shadow"
        ]
        
        for path in malicious_paths:
            with pytest.raises(SecurityError):
                await upload_dataset(source_path=path)
    
    def test_file_size_limit(self):
        """檔案大小限制測試（防止 DoS）"""
        # 嘗試上傳超大檔案
        huge_df = pd.DataFrame(np.random.randn(100_000_000, 100))
        
        with pytest.raises(FileTooLargeError):
            await upload_dataset(...)
    
    def test_rate_limiting(self):
        """Rate Limiting 測試"""
        # 快速發送 100 個請求
        for i in range(100):
            result = await quick_preview("iris.csv")
        
        # 第 101 個應被限制
        with pytest.raises(RateLimitError):
            await quick_preview("iris.csv")


class TestAuthenticationTests:
    """認證測試（如果啟用認證）"""
    
    def test_unauthorized_access(self):
        """未授權訪問測試"""
        # 不帶 token
        with pytest.raises(Unauthorized):
            await submit_automl_job(...)
    
    def test_user_isolation(self):
        """使用者隔離測試"""
        # User A 的資料
        result_a = await upload_dataset(user_id="user_a", ...)
        
        # User B 不應能存取 User A 的資料
        with pytest.raises(PermissionDenied):
            await get_dataset(
                dataset_id=result_a['dataset_id'],
                user_id="user_b"
            )
```

---

## 🎯 Phase 5: 混沌測試 (Chaos/Resilience Tests)

```python
# tests/chaos/test_resilience.py

class TestChaosEngineering:
    """混沌工程測試"""
    
    @pytest.mark.chaos
    async def test_random_service_failure(self):
        """隨機服務失敗測試"""
        import random
        
        services = ['automl-redis', 'stats-service', 'automl-worker']
        target = random.choice(services)
        
        # Kill random service
        os.system(f"docker compose kill {target}")
        
        # System should gracefully handle
        # ... test continued operation
        
        # Restart service
        os.system(f"docker compose up -d {target}")
    
    @pytest.mark.chaos
    async def test_network_partition(self):
        """網路分區測試（模擬網路故障）"""
        # 模擬服務間網路延遲
        os.system("docker compose exec stats-service tc qdisc add dev eth0 root netem delay 1000ms")
        
        # Should handle with retry
        result = await generate_tableone_directly(...)
        
        # Clean up
        os.system("docker compose exec stats-service tc qdisc del dev eth0 root")
    
    @pytest.mark.chaos
    async def test_disk_full_simulation(self):
        """磁碟空間不足測試"""
        # 應友善處理並提示使用者
        pass
```

---

## 🎯 Phase 6: 回歸測試 (Regression Tests)

```python
# tests/regression/test_regression_suite.py

class TestRegressionSuite:
    """回歸測試套件（確保修改不破壞現有功能）"""
    
    def test_iris_classification_accuracy(self):
        """Iris 分類準確度應保持 >95%"""
        result = await train_and_wait(
            dataset_id="iris",
            target_column="target",
            time_limit=60
        )
        assert result['score'] > 0.95
    
    def test_breast_cancer_roc_auc(self):
        """Breast Cancer ROC-AUC 應保持 >0.97"""
        result = await train_and_wait(
            dataset_id="breast_cancer",
            target_column="diagnosis",
            time_limit=60
        )
        assert result['score'] > 0.97
    
    def test_tableone_output_format(self):
        """Table One 輸出格式應保持一致"""
        result = await generate_tableone_directly(
            csv_path="medical_study_200.csv",
            group_column="treatment_group"
        )
        
        # 檢查必要欄位
        assert 'Total' in result['html_report']
        assert 'Group 0' in result['html_report']
        assert 'p-value' in result['html_report']
```

---

## 📊 測試執行計劃

### Week 1: 邊界測試
```bash
# 建立邊界測試基礎設施
cd tests/edge_cases
pytest test_data_boundaries.py -v
pytest test_input_validation.py -v
```

### Week 2: E2E 測試
```bash
# 完整工作流測試
cd tests/e2e
pytest test_complete_workflows.py -v --e2e
pytest test_error_recovery.py -v --e2e
```

### Week 3: 性能 & 安全測試
```bash
# 性能測試
pytest tests/performance/ -v --performance

# 安全測試
pytest tests/security/ -v
```

### Week 4: 混沌 & 回歸測試
```bash
# 混沌測試（需要特殊環境）
pytest tests/chaos/ -v --chaos

# 回歸測試（每次 release 前執行）
pytest tests/regression/ -v
```

---

## 🎯 覆蓋率目標

| 測試類型 | 測試數量目標 | 優先級 |
|---------|-------------|--------|
| 邊界測試 | 50+ tests | ⭐⭐⭐ 高 |
| E2E 工作流 | 20+ tests | ⭐⭐⭐ 高 |
| 性能測試 | 15+ tests | ⭐⭐ 中 |
| 安全測試 | 20+ tests | ⭐⭐⭐ 高 |
| 混沌測試 | 10+ tests | ⭐ 低 |
| 回歸測試 | 30+ tests | ⭐⭐ 中 |
| **總計** | **145+** | |

---

## 🚀 Quick Start

```bash
# 安裝測試依賴
pip install pytest pytest-asyncio pytest-cov pytest-benchmark

# 執行邊界測試
make test-edge

# 執行 E2E 測試
make test-e2e

# 執行所有測試
make test-all

# 生成覆蓋率報告
make test-coverage
```

---

## 📝 測試標記 (Markers)

```python
# pytest.ini
[pytest]
markers =
    unit: Unit tests (fast, no dependencies)
    integration: Integration tests (requires services)
    e2e: End-to-end tests (full system)
    performance: Performance benchmarks
    security: Security validation tests
    chaos: Chaos engineering tests
    regression: Regression test suite
    slow: Slow tests (>10s)
```

---

## 🎓 最佳實踐

1. **邊界測試優先**: 先測試邊界條件，再測試正常流程
2. **隔離測試**: 每個測試應獨立，不依賴其他測試
3. **快速反饋**: Unit tests < 1s, Integration < 10s
4. **清理資源**: 測試後清理臨時檔案和資料
5. **可重複性**: 測試應可重複執行，結果一致
6. **有意義的斷言**: 斷言應清楚表達預期行為
7. **錯誤訊息**: 測試失敗時應有清楚的錯誤訊息

---

**下一步**: 從邊界測試開始，逐步補充測試覆蓋！
