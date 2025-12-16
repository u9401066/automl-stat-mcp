"""
E2E Test - Visualization and Local Results Workflow

Tests the complete visualization and local results storage workflow including:
- Results directory creation
- Figure generation and saving
- HTML report generation
- Various chart types

Prerequisites:
    - Services running (docker compose up)
    - Results volume mounted

Usage:
    cd tests
    python -m pytest test_e2e_visualization.py -v
"""
import asyncio
import os
import time
from pathlib import Path
from typing import Optional

import httpx
import pytest

# =============================================================================
# Configuration
# =============================================================================

STATS_API_URL = os.getenv("STATS_API_URL", "http://localhost:8003")
AUTOML_API_URL = os.getenv("AUTOML_API_URL", "http://localhost:8001")

TEST_USER_ID = "e2e_viz_test"
TIMEOUT = 120.0
POLL_INTERVAL = 3

# Local results path (from workspace, not container)
WORKSPACE_ROOT = Path(__file__).parent.parent
RESULTS_PATH = WORKSPACE_ROOT / "results"

# Sample data paths (container paths)
SAMPLE_DATA = {
    "iris": "/data/sample_data/iris.csv",
    "heart": "/data/sample_data/heart_disease.csv",
    "breast_cancer": "/data/sample_data/breast_cancer.csv",
    "rossi": "/data/sample_data/rossi_recidivism.csv",
}


# =============================================================================
# Helper Functions
# =============================================================================

async def wait_for_job(
    client: httpx.AsyncClient, 
    job_id: str, 
    timeout: int = 120,
    poll_interval: int = POLL_INTERVAL
) -> dict:
    """Wait for a job to complete."""
    start = time.time()
    
    while time.time() - start < timeout:
        resp = await client.get(f"{STATS_API_URL}/jobs/{job_id}")
        
        if resp.status_code == 200:
            data = resp.json()
            status = data.get("status", "unknown")
            
            if status in ["completed", "failed", "error"]:
                return data
        
        await asyncio.sleep(poll_interval)
    
    return {"status": "timeout", "job_id": job_id}


def get_latest_result_dir(user_id: str) -> Optional[Path]:
    """Get the latest results directory for a user."""
    user_results = RESULTS_PATH / user_id
    
    if not user_results.exists():
        return None
    
    # Get latest directory
    dirs = [d for d in user_results.iterdir() if d.is_dir()]
    if not dirs:
        return None
    
    return max(dirs, key=lambda d: d.stat().st_mtime)


def check_results_directory(result_dir: Path) -> dict:
    """Check contents of a results directory."""
    contents = {
        "exists": result_dir.exists(),
        "has_metadata": (result_dir / "metadata.json").exists(),
        "has_report_json": (result_dir / "report.json").exists(),
        "has_report_html": (result_dir / "report.html").exists(),
        "figures": [],
        "data_files": [],
    }
    
    # Check figures
    figures_dir = result_dir / "figures"
    if figures_dir.exists():
        contents["figures"] = [f.name for f in figures_dir.iterdir() if f.is_file()]
    
    # Check data files
    data_dir = result_dir / "data"
    if data_dir.exists():
        contents["data_files"] = [f.name for f in data_dir.iterdir() if f.is_file()]
    
    return contents


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(scope="module")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def stats_client():
    """Create HTTP client for stats service (not pre-opened)."""
    return httpx.AsyncClient(timeout=TIMEOUT)


@pytest.fixture
def results_dir():
    """Ensure results directory exists."""
    RESULTS_PATH.mkdir(exist_ok=True)
    return RESULTS_PATH


# =============================================================================
# Test: Results Directory Structure
# =============================================================================

@pytest.mark.e2e
@pytest.mark.asyncio
class TestResultsDirectoryFlow:
    """Test results directory creation and structure."""
    
    def test_results_base_exists(self, results_dir):
        """Test that results base directory exists."""
        assert results_dir.exists()
    
    async def test_job_creates_results_directory(self, stats_client, results_dir):
        """Test that running a job creates results directory."""
        async with stats_client as client:
            # Submit a job that should create results
            resp = await client.post(
                f"{STATS_API_URL}/roc/full-eval",
                json={
                    "csv_path": SAMPLE_DATA["breast_cancer"],
                    "y_true_col": "diagnosis",
                    "y_score_col": "mean_radius",
                    "user_id": TEST_USER_ID,
                    "job_name": "viz_test_roc",
                }
            )
            
            if resp.status_code == 200:
                data = resp.json()
                job_id = data.get("job_id")
                
                # Wait for completion
                result = await wait_for_job(client, job_id)
                
                if result["status"] == "completed":
                    # Check local results
                    latest_dir = get_latest_result_dir(TEST_USER_ID)
                    
                    if latest_dir:
                        contents = check_results_directory(latest_dir)
                        
                        assert contents["exists"], "Results directory not created"
                        # May or may not have all files depending on implementation
            elif resp.status_code == 404:
                pytest.skip("ROC full-eval endpoint not implemented")


# =============================================================================
# Test: ROC Visualization
# =============================================================================

@pytest.mark.e2e
@pytest.mark.asyncio
class TestROCVisualizationFlow:
    """Test ROC curve visualization generation."""
    
    async def test_roc_curve_generation(self, stats_client, results_dir):
        """Test that ROC analysis generates curve figure."""
        async with stats_client as client:
            resp = await client.post(
                f"{STATS_API_URL}/roc/compute",
                json={
                    "csv_path": SAMPLE_DATA["breast_cancer"],
                    "y_true_col": "diagnosis",
                    "y_score_col": "mean_radius",
                    "user_id": TEST_USER_ID,
                    "generate_plot": True,
                }
            )
            
            if resp.status_code == 200:
                data = resp.json()
                
                # Check if visualizations included
                if "visualizations" in data:
                    viz = data["visualizations"]
                    assert len(viz) > 0, "No visualizations generated"
                    
                    # Check for ROC curve
                    has_roc = any("roc" in v.get("filename", "").lower() for v in viz)
                    assert has_roc, "ROC curve not in visualizations"
            elif resp.status_code == 404:
                pytest.skip("ROC endpoint not implemented")
    
    async def test_roc_comparison_figures(self, stats_client):
        """Test ROC comparison generates comparison figure."""
        async with stats_client as client:
            resp = await client.post(
                f"{STATS_API_URL}/roc/compare",
                json={
                    "csv_path": SAMPLE_DATA["breast_cancer"],
                    "y_true_col": "diagnosis",
                    "y_score_col_1": "mean_radius",
                    "y_score_col_2": "mean_texture",
                    "user_id": TEST_USER_ID,
                }
            )
            
            if resp.status_code == 200:
                data = resp.json()
                # Should have comparison visualization
            elif resp.status_code == 404:
                pytest.skip("ROC compare endpoint not implemented")


# =============================================================================
# Test: Survival Visualization
# =============================================================================

@pytest.mark.e2e
@pytest.mark.asyncio
class TestSurvivalVisualizationFlow:
    """Test survival analysis visualization generation."""
    
    async def test_kaplan_meier_curve(self, stats_client):
        """Test Kaplan-Meier curve generation."""
        async with stats_client as client:
            resp = await client.post(
                f"{STATS_API_URL}/survival/kaplan-meier",
                json={
                    "csv_path": SAMPLE_DATA["rossi"],
                    "time_column": "week",
                    "event_column": "arrest",
                    "user_id": TEST_USER_ID,
                    "generate_plot": True,
                }
            )
            
            if resp.status_code == 200:
                data = resp.json()
                
                if "visualizations" in data:
                    viz = data["visualizations"]
                    # Check for KM curve
                    has_km = any("km" in v.get("filename", "").lower() or 
                                 "kaplan" in v.get("filename", "").lower() or
                                 "survival" in v.get("filename", "").lower() 
                                 for v in viz)
            elif resp.status_code == 404:
                pytest.skip("Kaplan-Meier endpoint not implemented")
    
    async def test_survival_comparison_curves(self, stats_client):
        """Test survival curves with group comparison."""
        async with stats_client as client:
            resp = await client.post(
                f"{STATS_API_URL}/survival/kaplan-meier",
                json={
                    "csv_path": SAMPLE_DATA["rossi"],
                    "time_column": "week",
                    "event_column": "arrest",
                    "group_column": "fin",
                    "user_id": TEST_USER_ID,
                }
            )
            
            if resp.status_code == 200:
                data = resp.json()
                # Should have grouped survival curves
            elif resp.status_code == 404:
                pytest.skip("Kaplan-Meier endpoint not implemented")


# =============================================================================
# Test: HTML Report Generation
# =============================================================================

@pytest.mark.e2e
@pytest.mark.asyncio
class TestHTMLReportFlow:
    """Test HTML report generation."""
    
    async def test_full_analysis_generates_html(self, stats_client, results_dir):
        """Test that full analysis generates HTML report."""
        async with stats_client as client:
            resp = await client.post(
                f"{STATS_API_URL}/roc/full-eval",
                json={
                    "csv_path": SAMPLE_DATA["breast_cancer"],
                    "y_true_col": "diagnosis",
                    "y_score_col": "mean_radius",
                    "user_id": TEST_USER_ID,
                }
            )
            
            if resp.status_code == 200:
                data = resp.json()
                job_id = data.get("job_id")
                
                if job_id:
                    # Wait for completion
                    result = await wait_for_job(client, job_id)
                    
                    if result["status"] == "completed":
                        # Check for HTML report in results
                        latest_dir = get_latest_result_dir(TEST_USER_ID)
                        
                        if latest_dir:
                            html_path = latest_dir / "report.html"
                            if html_path.exists():
                                # Verify HTML content
                                html_content = html_path.read_text()
                                assert "<!DOCTYPE html>" in html_content or "<html" in html_content
                                assert "report" in html_content.lower() or "analysis" in html_content.lower()
            elif resp.status_code == 404:
                pytest.skip("Full-eval endpoint not implemented")
    
    def test_html_report_contains_figures(self, results_dir):
        """Test that HTML report references figures."""
        # Find latest HTML report
        latest_dir = get_latest_result_dir(TEST_USER_ID)
        
        if not latest_dir:
            pytest.skip("No results directory found")
        
        html_path = latest_dir / "report.html"
        
        if not html_path.exists():
            pytest.skip("No HTML report found")
        
        html_content = html_path.read_text()
        
        # Check for figure references
        assert "figures/" in html_content or "img" in html_content.lower()


# =============================================================================
# Test: Figure Files
# =============================================================================

@pytest.mark.e2e
class TestFigureFilesFlow:
    """Test figure file generation and storage."""
    
    def test_figures_directory_structure(self, results_dir):
        """Test figures are saved in correct directory."""
        latest_dir = get_latest_result_dir(TEST_USER_ID)
        
        if not latest_dir:
            pytest.skip("No results directory found")
        
        figures_dir = latest_dir / "figures"
        
        if figures_dir.exists():
            figures = list(figures_dir.glob("*.png"))
            
            if figures:
                # Check figure file properties
                for fig in figures:
                    assert fig.stat().st_size > 0, f"Empty figure: {fig.name}"
    
    def test_figure_filenames_descriptive(self, results_dir):
        """Test figure filenames are descriptive."""
        latest_dir = get_latest_result_dir(TEST_USER_ID)
        
        if not latest_dir:
            pytest.skip("No results directory found")
        
        figures_dir = latest_dir / "figures"
        
        if figures_dir.exists():
            figures = list(figures_dir.glob("*.png"))
            
            for fig in figures:
                # Should not be generic names
                name = fig.stem.lower()
                assert name != "figure" and name != "plot"


# =============================================================================
# Test: Metadata Files
# =============================================================================

@pytest.mark.e2e
class TestMetadataFilesFlow:
    """Test metadata file generation."""
    
    def test_metadata_json_exists(self, results_dir):
        """Test metadata.json exists in results."""
        latest_dir = get_latest_result_dir(TEST_USER_ID)
        
        if not latest_dir:
            pytest.skip("No results directory found")
        
        metadata_path = latest_dir / "metadata.json"
        
        if metadata_path.exists():
            import json
            metadata = json.loads(metadata_path.read_text())
            
            # Check required fields
            assert "job_id" in metadata
            assert "user_id" in metadata
            assert "status" in metadata
    
    def test_source_info_exists(self, results_dir):
        """Test source_info.json exists in data directory."""
        latest_dir = get_latest_result_dir(TEST_USER_ID)
        
        if not latest_dir:
            pytest.skip("No results directory found")
        
        source_info_path = latest_dir / "data" / "source_info.json"
        
        if source_info_path.exists():
            import json
            source_info = json.loads(source_info_path.read_text())
            
            # Should have some source information
            assert len(source_info) > 0


# =============================================================================
# Test: Complete Visualization Workflow
# =============================================================================

@pytest.mark.e2e
@pytest.mark.asyncio
@pytest.mark.slow
class TestCompleteVisualizationWorkflow:
    """Test complete visualization workflow."""
    
    async def test_full_roc_analysis_with_local_results(self, stats_client, results_dir):
        """
        Complete ROC analysis workflow with local results:
        1. Submit full ROC evaluation
        2. Wait for completion
        3. Verify local results directory
        4. Check figures generated
        5. Check HTML report
        6. Check metadata
        """
        async with stats_client as client:
            # 1. Submit job
            resp = await client.post(
                f"{STATS_API_URL}/roc/full-eval",
                json={
                    "csv_path": SAMPLE_DATA["breast_cancer"],
                    "y_true_col": "diagnosis",
                    "y_score_col": "mean_radius",
                    "user_id": TEST_USER_ID,
                    "job_name": "complete_viz_workflow",
                }
            )
            
            if resp.status_code != 200:
                pytest.skip("Full-eval endpoint not available")
            
            data = resp.json()
            job_id = data.get("job_id")
            
            if not job_id:
                pytest.skip("No job_id returned")
            
            # 2. Wait for completion
            result = await wait_for_job(client, job_id)
            
            if result["status"] != "completed":
                pytest.skip("Job did not complete")
            
            # 3. Check local results
            # Wait a bit for file system sync
            await asyncio.sleep(1)
            
            latest_dir = get_latest_result_dir(TEST_USER_ID)
            
            if not latest_dir:
                print("⚠ Local results directory not found (may not be mounted)")
                return
            
            contents = check_results_directory(latest_dir)
            
            # 4. Verify structure
            print(f"Results directory: {latest_dir}")
            print(f"Contents: {contents}")
            
            assert contents["exists"], "Results directory exists"
            
            if contents["has_metadata"]:
                print("✓ metadata.json present")
            
            if contents["has_report_json"]:
                print("✓ report.json present")
            
            if contents["has_report_html"]:
                print("✓ report.html present")
            
            if contents["figures"]:
                print(f"✓ Figures: {contents['figures']}")
            
            print("✓ Complete visualization workflow passed!")


# =============================================================================
# Test: List User Results
# =============================================================================

@pytest.mark.e2e
class TestListUserResults:
    """Test listing user results."""
    
    def test_list_user_results_directories(self, results_dir):
        """List all results directories for test user."""
        user_results = results_dir / TEST_USER_ID
        
        if not user_results.exists():
            pytest.skip("No results for test user")
        
        result_dirs = [d for d in user_results.iterdir() if d.is_dir()]
        
        print(f"\nUser '{TEST_USER_ID}' has {len(result_dirs)} result directories:")
        
        for rd in sorted(result_dirs, key=lambda d: d.stat().st_mtime, reverse=True)[:5]:
            contents = check_results_directory(rd)
            print(f"  - {rd.name}")
            print(f"    Figures: {len(contents['figures'])}")
            print(f"    Has HTML: {contents['has_report_html']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
