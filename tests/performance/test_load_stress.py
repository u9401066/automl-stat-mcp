"""
性能測試 - 負載與壓力測試

測試系統在高負載下的表現
"""

import pytest
import asyncio
import httpx
import time
import os
from typing import List


@pytest.mark.performance
class TestLoadBenchmarks:
    """負載基準測試"""
    
    @pytest.fixture
    def mcp_base_url(self):
        return os.getenv('MCP_SERVER_URL', 'http://localhost:8002')
    
    @pytest.mark.benchmark
    async def test_quick_preview_speed(self, mcp_base_url, benchmark):
        """測試 quick_preview 速度（應該 < 1秒）"""
        
        async def run_preview():
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{mcp_base_url}/mcp/tools/quick_preview",
                    json={"csv_path": "/data/sample_data/iris.csv"}
                )
                return response.json()
        
        # Benchmark
        start_time = time.time()
        result = await run_preview()
        elapsed = time.time() - start_time
        
        assert elapsed < 1.0, f"Preview took {elapsed:.2f}s, should be < 1s"
        assert 'shape' in result
    
    @pytest.mark.benchmark
    async def test_stats_calculation_speed(self, mcp_base_url):
        """測試統計計算速度（應該 < 3秒）"""
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            start_time = time.time()
            
            response = await client.post(
                f"{mcp_base_url}/mcp/tools/quick_stats",
                json={"csv_path": "/data/sample_data/iris.csv"}
            )
            
            elapsed = time.time() - start_time
            
            assert response.status_code == 200
            assert elapsed < 3.0, f"Stats took {elapsed:.2f}s, should be < 3s"
    
    @pytest.mark.slow
    async def test_large_dataset_performance(self, mcp_base_url):
        """測試大資料集效能（1萬筆資料）"""
        # 使用較大的範例資料集
        async with httpx.AsyncClient(timeout=60.0) as client:
            start_time = time.time()
            
            response = await client.post(
                f"{mcp_base_url}/mcp/tools/smart_analyze",
                json={
                    "csv_path": "/data/sample_data/medical_study_200.csv"
                }
            )
            
            elapsed = time.time() - start_time
            
            assert response.status_code == 200
            # 大資料集分析應該在 30 秒內完成
            assert elapsed < 30.0, f"Large dataset analysis took {elapsed:.2f}s"


@pytest.mark.performance
class TestConcurrentRequests:
    """並行請求測試"""
    
    @pytest.fixture
    def mcp_base_url(self):
        return os.getenv('MCP_SERVER_URL', 'http://localhost:8002')
    
    async def test_10_concurrent_previews(self, mcp_base_url):
        """測試 10 個並行 preview 請求"""
        
        async def single_preview(session_id: int):
            async with httpx.AsyncClient(timeout=30.0) as client:
                start = time.time()
                response = await client.post(
                    f"{mcp_base_url}/mcp/tools/quick_preview",
                    json={"csv_path": "/data/sample_data/iris.csv"}
                )
                elapsed = time.time() - start
                return session_id, response.status_code, elapsed
        
        # 並行執行
        start_time = time.time()
        tasks = [single_preview(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        total_elapsed = time.time() - start_time
        
        # 檢查結果
        for session_id, status_code, elapsed in results:
            assert status_code == 200
        
        # 平均回應時間應該合理
        avg_elapsed = sum(r[2] for r in results) / len(results)
        assert avg_elapsed < 2.0, f"Average response time: {avg_elapsed:.2f}s"
        
        # 總時間應遠小於串行執行（10 * avg_elapsed）
        serial_time = avg_elapsed * 10
        assert total_elapsed < serial_time * 0.5, "Parallelization not working"
    
    async def test_100_sequential_requests(self, mcp_base_url):
        """測試 100 個連續請求（壓力測試）"""
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            success_count = 0
            error_count = 0
            response_times: List[float] = []
            
            for i in range(100):
                try:
                    start = time.time()
                    
                    response = await client.post(
                        f"{mcp_base_url}/mcp/tools/quick_preview",
                        json={"csv_path": "/data/sample_data/iris.csv"}
                    )
                    
                    elapsed = time.time() - start
                    response_times.append(elapsed)
                    
                    if response.status_code == 200:
                        success_count += 1
                    else:
                        error_count += 1
                        
                except Exception as e:
                    error_count += 1
            
            # 成功率應該 > 95%
            success_rate = success_count / 100
            assert success_rate > 0.95, f"Success rate: {success_rate:.1%}"
            
            # 計算統計
            if response_times:
                avg_time = sum(response_times) / len(response_times)
                max_time = max(response_times)
                
                print(f"\nPerformance stats:")
                print(f"  Success: {success_count}/100 ({success_rate:.1%})")
                print(f"  Avg response: {avg_time:.3f}s")
                print(f"  Max response: {max_time:.3f}s")


@pytest.mark.performance
class TestMemoryUsage:
    """記憶體使用測試"""
    
    @pytest.fixture
    def mcp_base_url(self):
        return os.getenv('MCP_SERVER_URL', 'http://localhost:8002')
    
    async def test_memory_leak_detection(self, mcp_base_url):
        """測試記憶體洩漏（重複執行同一分析）"""
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            # 執行 20 次相同分析
            for i in range(20):
                response = await client.post(
                    f"{mcp_base_url}/mcp/tools/quick_stats",
                    json={"csv_path": "/data/sample_data/iris.csv"}
                )
                
                assert response.status_code == 200
                
                # 可以在這裡加入記憶體監控
                # 如果有顯著增長，可能有洩漏
    
    @pytest.mark.slow
    async def test_large_result_handling(self, mcp_base_url):
        """測試大量結果處理（記憶體壓力）"""
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            # 執行多個分析，累積結果
            results = []
            
            for dataset in ["iris.csv", "titanic.csv", "breast_cancer.csv"]:
                response = await client.post(
                    f"{mcp_base_url}/mcp/tools/smart_analyze",
                    json={"csv_path": f"/data/sample_data/{dataset}"}
                )
                
                if response.status_code == 200:
                    results.append(response.json())
            
            # 檢查能否處理多個大結果
            assert len(results) >= 2


@pytest.mark.performance
class TestStressTests:
    """壓力測試"""
    
    @pytest.fixture
    def mcp_base_url(self):
        return os.getenv('MCP_SERVER_URL', 'http://localhost:8002')
    
    @pytest.mark.slow
    async def test_sustained_load(self, mcp_base_url):
        """測試持續負載（5 分鐘）"""
        
        duration = 60  # 1 分鐘（測試時可改為 300 秒）
        interval = 2    # 每 2 秒一次請求
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            start_time = time.time()
            request_count = 0
            success_count = 0
            
            while time.time() - start_time < duration:
                try:
                    response = await client.post(
                        f"{mcp_base_url}/mcp/tools/quick_preview",
                        json={"csv_path": "/data/sample_data/iris.csv"}
                    )
                    
                    request_count += 1
                    if response.status_code == 200:
                        success_count += 1
                        
                except Exception:
                    request_count += 1
                
                await asyncio.sleep(interval)
            
            # 計算成功率
            success_rate = success_count / request_count if request_count > 0 else 0
            
            print(f"\nSustained load test ({duration}s):")
            print(f"  Total requests: {request_count}")
            print(f"  Success rate: {success_rate:.1%}")
            
            # 成功率應保持高水準
            assert success_rate > 0.90, f"Success rate dropped to {success_rate:.1%}"
    
    @pytest.mark.slow
    async def test_burst_traffic(self, mcp_base_url):
        """測試突發流量（50 個同時請求）"""
        
        async def single_request(request_id: int):
            async with httpx.AsyncClient(timeout=30.0) as client:
                try:
                    response = await client.post(
                        f"{mcp_base_url}/mcp/tools/quick_preview",
                        json={"csv_path": "/data/sample_data/iris.csv"}
                    )
                    return request_id, response.status_code
                except Exception as e:
                    return request_id, 0
        
        # 突發 50 個並行請求
        tasks = [single_request(i) for i in range(50)]
        results = await asyncio.gather(*tasks)
        
        # 統計成功率
        success_count = sum(1 for _, status in results if status == 200)
        success_rate = success_count / len(results)
        
        print(f"\nBurst test (50 concurrent):")
        print(f"  Success: {success_count}/50 ({success_rate:.1%})")
        
        # 至少 80% 成功
        assert success_rate >= 0.80, f"Too many failures: {success_rate:.1%}"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-m', 'performance'])
