"""
E2E 完整工作流測試

測試從資料上傳到分析完成的完整流程
"""

import pytest
import asyncio
import httpx
import os


@pytest.mark.e2e
class TestCompleteMedicalWorkflow:
    """測試完整醫學研究工作流"""
    
    @pytest.fixture
    def mcp_base_url(self):
        return os.getenv(

'MCP_SERVER_URL', 'http://localhost:8002')
    
    @pytest.fixture
    def stats_base_url(self):
        return os.getenv('STATS_SERVICE_URL', 'http://localhost:8003')
    
    async def test_rct_full_pipeline(self, mcp_base_url, stats_base_url):
        """
        完整 RCT 研究流程:
        1. 上傳資料
        2. 資料品質檢查
        3. 生成 Table One
        4. 統計檢定
        5. 結果儲存
        """
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Step 1: 上傳資料 (使用 temporary mode)
            upload_response = await client.post(
                f"{mcp_base_url}/mcp/tools/upload_dataset",
                json={
                    "name": "rct_test",
                    "source_type": "local",
                    "source_path": "/data/sample_data/medical_study_200.csv",
                    "storage_mode": "temporary",
                    "user_id": "e2e_test_user"
                }
            )
            
            assert upload_response.status_code == 200
            upload_result = upload_response.json()
            assert 'job_id' in upload_result
            job_id = upload_result['job_id']
            
            # Step 2: 品質檢查
            quality_response = await client.post(
                f"{mcp_base_url}/mcp/tools/quality_check",
                json={
                    "csv_path": "/data/sample_data/medical_study_200.csv"
                }
            )
            
            assert quality_response.status_code == 200
            quality_result = quality_response.json()
            assert quality_result['analysis_readiness'] in ['ready', 'needs_review']
            
            # Step 3: 生成 Table One
            tableone_response = await client.post(
                f"{mcp_base_url}/mcp/tools/generate_tableone_directly",
                json={
                    "csv_path": "/data/sample_data/medical_study_200.csv",
                    "group_column": "treatment_group"
                }
            )
            
            assert tableone_response.status_code == 200
            tableone_result = tableone_response.json()
            assert 'html_report' in tableone_result
            assert 'Total' in tableone_result['html_report']
            
            # Step 4: 統計檢定
            stats_response = await client.post(
                f"{mcp_base_url}/mcp/tools/compare_groups",
                json={
                    "csv_path": "/data/sample_data/medical_study_200.csv",
                    "numeric_column": "outcome",
                    "group_column": "treatment_group"
                }
            )
            
            assert stats_response.status_code == 200
            stats_result = stats_response.json()
            assert 'main_test' in stats_result
            assert 'p_value' in stats_result['main_test']
    
    async def test_survival_analysis_workflow(self, mcp_base_url):
        """
        完整存活分析流程:
        1. 上傳存活資料
        2. Kaplan-Meier 曲線
        3. Log-rank 檢定
        4. Cox 迴歸
        """
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Step 1: 上傳存活資料
            upload_response = await client.post(
                f"{mcp_base_url}/mcp/tools/upload_dataset",
                json={
                    "name": "survival_test",
                    "source_type": "local",
                    "source_path": "/data/sample_data/rossi_recidivism.csv",
                    "storage_mode": "temporary",
                    "user_id": "e2e_test_user"
                }
            )
            
            assert upload_response.status_code == 200
            
            # Step 2: Kaplan-Meier
            km_response = await client.post(
                f"{mcp_base_url}/mcp/tools/kaplan_meier_survival",
                json={
                    "csv_path": "/data/sample_data/rossi_recidivism.csv",
                    "time_col": "week",
                    "event_col": "arrest"
                }
            )
            
            assert km_response.status_code == 200
            km_result = km_response.json()
            assert 'median_survival_time' in km_result
            
            # Step 3: Cox 迴歸
            cox_response = await client.post(
                f"{mcp_base_url}/mcp/tools/cox_proportional_hazards",
                json={
                    "csv_path": "/data/sample_data/rossi_recidivism.csv",
                    "time_col": "week",
                    "event_col": "arrest",
                    "covariates": ["age", "prio"]
                }
            )
            
            assert cox_response.status_code == 200
            cox_result = cox_response.json()
            assert 'coefficients' in cox_result


@pytest.mark.e2e
class TestCompleteMLWorkflow:
    """測試完整機器學習工作流"""
    
    @pytest.fixture
    def mcp_base_url(self):
        return os.getenv('MCP_SERVER_URL', 'http://localhost:8002')
    
    @pytest.mark.slow
    async def test_ml_training_pipeline(self, mcp_base_url):
        """
        完整 ML 訓練流程:
        1. 上傳資料 (permanent)
        2. 訓練模型
        3. 查看排行榜
        4. 預測
        """
        async with httpx.AsyncClient(timeout=300.0) as client:
            # Step 1: 上傳資料 (permanent 模式用於 ML)
            upload_response = await client.post(
                f"{mcp_base_url}/mcp/tools/upload_dataset",
                json={
                    "name": "iris_ml_test",
                    "source_type": "local",
                    "source_path": "/data/sample_data/iris.csv",
                    "storage_mode": "permanent",
                    "user_id": "e2e_test_user"
                }
            )
            
            assert upload_response.status_code == 200
            upload_result = upload_response.json()
            assert 'dataset_id' in upload_result
            dataset_id = upload_result['dataset_id']
            
            # Step 2: 訓練模型 (快速測試，時間限制短)
            train_response = await client.post(
                f"{mcp_base_url}/mcp/tools/train_and_wait",
                json={
                    "dataset_id": dataset_id,
                    "target_column": "target",
                    "problem_type": "multiclass",
                    "time_limit": 60,  # 1 分鐘快速訓練
                    "user_id": "e2e_test_user"
                }
            )
            
            assert train_response.status_code == 200
            train_result = train_response.json()
            assert 'model_id' in train_result
            assert 'score' in train_result
            model_id = train_result['model_id']
            
            # Step 3: 查看排行榜
            leaderboard_response = await client.get(
                f"{mcp_base_url}/mcp/tools/get_model_leaderboard",
                params={
                    "model_id": model_id,
                    "user_id": "e2e_test_user"
                }
            )
            
            assert leaderboard_response.status_code == 200
            leaderboard = leaderboard_response.json()
            assert 'leaderboard' in leaderboard
            assert len(leaderboard['leaderboard']) > 0


@pytest.mark.e2e
class TestMultiUserConcurrency:
    """測試多使用者並行操作"""
    
    @pytest.fixture
    def mcp_base_url(self):
        return os.getenv('MCP_SERVER_URL', 'http://localhost:8002')
    
    async def test_concurrent_uploads(self, mcp_base_url):
        """測試多個使用者同時上傳資料"""
        
        async def upload_for_user(user_id: str, dataset_name: str):
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{mcp_base_url}/mcp/tools/upload_dataset",
                    json={
                        "name": f"{dataset_name}_{user_id}",
                        "source_type": "local",
                        "source_path": "/data/sample_data/iris.csv",
                        "storage_mode": "temporary",
                        "user_id": user_id
                    }
                )
                return response.status_code, response.json()
        
        # 並行上傳
        tasks = [
            upload_for_user("user_a", "test_dataset"),
            upload_for_user("user_b", "test_dataset"),
            upload_for_user("user_c", "test_dataset")
        ]
        
        results = await asyncio.gather(*tasks)
        
        # 所有請求都應成功
        for status_code, result in results:
            assert status_code == 200
            assert 'job_id' in result
    
    async def test_concurrent_analysis(self, mcp_base_url):
        """測試多個使用者同時執行分析"""
        
        async def analyze_for_user(user_id: str):
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{mcp_base_url}/mcp/tools/quick_stats",
                    json={
                        "csv_path": "/data/sample_data/iris.csv"
                    }
                )
                return response.status_code, response.json()
        
        # 並行分析
        tasks = [analyze_for_user(f"user_{i}") for i in range(5)]
        results = await asyncio.gather(*tasks)
        
        # 所有分析都應成功
        for status_code, result in results:
            assert status_code == 200
            assert 'summary_statistics' in result


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-m', 'e2e'])
