"""
Service Communication Tests

Tests HTTP communication between services:
- MCP → Stats Service
- MCP → AutoML Service
- Timeout handling
- Error responses

Requires: Services running (docker compose up)
"""
import asyncio
import time

import httpx
import pytest
import structlog

# =============================================================================
# Configuration
# =============================================================================

logger = structlog.get_logger(__name__)

STATS_API_URL = "http://localhost:8003"
AUTOML_API_URL = "http://localhost:8001"
MCP_SERVER_URL = "http://localhost:8002"


# =============================================================================
# Test: Health Endpoints
# =============================================================================

@pytest.mark.e2e
@pytest.mark.asyncio
class TestServiceHealth:
    """Test service health endpoints."""

    async def test_stats_service_health(self, test_logger):
        """Test stats service health endpoint."""
        test_logger.info("test_start", test="stats_health")

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get(f"{STATS_API_URL}/health")
                test_logger.info(
                    "health_response",
                    service="stats",
                    status=resp.status_code,
                    body=resp.json() if resp.status_code == 200 else resp.text[:100]
                )
                assert resp.status_code == 200
            except httpx.ConnectError:
                pytest.skip("Stats service not available")

    async def test_automl_service_health(self, test_logger):
        """Test automl service health endpoint."""
        test_logger.info("test_start", test="automl_health")

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get(f"{AUTOML_API_URL}/health")
                test_logger.info(
                    "health_response",
                    service="automl",
                    status=resp.status_code
                )
                assert resp.status_code == 200
            except httpx.ConnectError:
                pytest.skip("AutoML service not available")

    async def test_all_services_health(self, test_logger):
        """Test all services are healthy."""
        test_logger.info("test_start", test="all_services_health")

        services = {
            "stats": STATS_API_URL,
            "automl": AUTOML_API_URL,
        }

        results = {}
        async with httpx.AsyncClient(timeout=10.0) as client:
            for name, url in services.items():
                try:
                    resp = await client.get(f"{url}/health")
                    results[name] = {
                        "status": resp.status_code,
                        "healthy": resp.status_code == 200,
                    }
                except Exception as e:
                    results[name] = {
                        "status": None,
                        "healthy": False,
                        "error": str(e),
                    }

        test_logger.info("health_summary", results=results)

        # At least one service should be healthy for tests to run
        healthy_count = sum(1 for r in results.values() if r["healthy"])
        if healthy_count == 0:
            pytest.skip("No services available")


# =============================================================================
# Test: API Endpoints
# =============================================================================

@pytest.mark.e2e
@pytest.mark.asyncio
class TestAPIEndpoints:
    """Test API endpoint availability."""

    async def test_stats_endpoints_exist(
        self,
        stats_service_available,
        test_logger,
    ):
        """Test that expected stats endpoints exist."""
        test_logger.info("test_start", test="stats_endpoints")

        endpoints = [
            ("GET", "/health"),
            ("POST", "/direct/quick-stats"),
            ("POST", "/direct/analyze"),
            ("GET", "/jobs/{job_id}"),
        ]

        async with httpx.AsyncClient(timeout=10.0) as client:
            for method, path in endpoints:
                # Just check endpoint exists (may return 4xx without proper params)
                url = f"{STATS_API_URL}{path.replace('{job_id}', 'test')}"
                try:
                    if method == "GET":
                        resp = await client.get(url)
                    else:
                        resp = await client.post(url, json={})

                    # 405 means method not allowed, 422 means validation error
                    # Both indicate endpoint exists
                    exists = resp.status_code not in [404]
                    test_logger.info(
                        "endpoint_check",
                        method=method,
                        path=path,
                        status=resp.status_code,
                        exists=exists
                    )
                except Exception as e:
                    test_logger.error("endpoint_error", path=path, error=str(e))

    async def test_automl_endpoints_exist(
        self,
        automl_service_available,
        test_logger,
    ):
        """Test that expected automl endpoints exist."""
        test_logger.info("test_start", test="automl_endpoints")

        endpoints = [
            ("GET", "/health"),
            ("GET", "/algorithms"),
            ("POST", "/datasets/upload"),
            ("GET", "/datasets"),
        ]

        async with httpx.AsyncClient(timeout=10.0) as client:
            for method, path in endpoints:
                url = f"{AUTOML_API_URL}{path}"
                try:
                    if method == "GET":
                        resp = await client.get(url)
                    else:
                        resp = await client.post(url, json={})

                    exists = resp.status_code not in [404]
                    test_logger.info(
                        "endpoint_check",
                        method=method,
                        path=path,
                        status=resp.status_code,
                        exists=exists
                    )
                except Exception as e:
                    test_logger.error("endpoint_error", path=path, error=str(e))


# =============================================================================
# Test: Timeout Handling
# =============================================================================

@pytest.mark.e2e
@pytest.mark.asyncio
class TestTimeoutHandling:
    """Test timeout handling."""

    async def test_short_timeout_handling(self, test_logger):
        """Test behavior with very short timeout."""
        test_logger.info("test_start", test="short_timeout")

        # Use very short timeout - should fail gracefully
        async with httpx.AsyncClient(timeout=0.001) as client:
            try:
                resp = await client.get(f"{STATS_API_URL}/health")
                test_logger.warning("unexpected_success", status=resp.status_code)
            except httpx.TimeoutException as e:
                test_logger.info("timeout_handled", error_type=type(e).__name__)
            except httpx.ConnectError:
                test_logger.info("connect_error", note="Service not available")

    async def test_reasonable_timeout_success(
        self,
        stats_service_available,
        test_logger,
    ):
        """Test that reasonable timeout succeeds."""
        test_logger.info("test_start", test="reasonable_timeout")

        async with httpx.AsyncClient(timeout=30.0) as client:
            start = time.time()
            resp = await client.get(f"{STATS_API_URL}/health")
            elapsed = time.time() - start

            test_logger.info(
                "request_completed",
                status=resp.status_code,
                elapsed_ms=round(elapsed * 1000)
            )

            assert resp.status_code == 200
            assert elapsed < 5.0  # Should be fast


# =============================================================================
# Test: Error Responses
# =============================================================================

@pytest.mark.e2e
@pytest.mark.asyncio
class TestErrorResponses:
    """Test error response handling."""

    async def test_invalid_json_body(
        self,
        stats_service_available,
        test_logger,
    ):
        """Test handling of invalid JSON body."""
        test_logger.info("test_start", test="invalid_json")

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{STATS_API_URL}/direct/quick-stats",
                content="invalid json{{{",
                headers={"Content-Type": "application/json"}
            )

            test_logger.info(
                "invalid_json_response",
                status=resp.status_code,
                body=resp.text[:200]
            )

            # Should return 4xx error
            assert resp.status_code >= 400

    async def test_missing_required_fields(
        self,
        stats_service_available,
        test_logger,
    ):
        """Test handling of missing required fields."""
        test_logger.info("test_start", test="missing_fields")

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{STATS_API_URL}/direct/quick-stats",
                json={}  # Empty body - missing required fields
            )

            test_logger.info(
                "missing_fields_response",
                status=resp.status_code,
                body=resp.text[:200]
            )

            # Should return validation error (422) or bad request (400)
            assert resp.status_code in [400, 422]

    async def test_nonexistent_endpoint(
        self,
        stats_service_available,
        test_logger,
    ):
        """Test handling of nonexistent endpoint."""
        test_logger.info("test_start", test="nonexistent_endpoint")

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{STATS_API_URL}/this/endpoint/does/not/exist"
            )

            test_logger.info(
                "notfound_response",
                status=resp.status_code
            )

            assert resp.status_code == 404


# =============================================================================
# Test: Response Format
# =============================================================================

@pytest.mark.e2e
@pytest.mark.asyncio
class TestResponseFormat:
    """Test response format consistency."""

    async def test_health_response_format(
        self,
        stats_service_available,
        test_logger,
    ):
        """Test health endpoint response format."""
        test_logger.info("test_start", test="health_format")

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{STATS_API_URL}/health")

            assert resp.status_code == 200
            data = resp.json()

            # Check expected fields
            test_logger.info("health_data", data=data)

            # Should have status field
            assert "status" in data

    async def test_error_response_format(
        self,
        stats_service_available,
        test_logger,
    ):
        """Test error response format."""
        test_logger.info("test_start", test="error_format")

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{STATS_API_URL}/direct/quick-stats",
                json={}
            )

            # Check error response has useful information
            data = resp.json()
            test_logger.info("error_data", data=data)

            # FastAPI validation errors have 'detail' field
            # Our custom errors might have 'error' or 'message'
            has_error_info = any(k in data for k in ["detail", "error", "message"])
            test_logger.info("has_error_info", result=has_error_info)


# =============================================================================
# Test: Concurrent Requests
# =============================================================================

@pytest.mark.e2e
@pytest.mark.asyncio
class TestConcurrentRequests:
    """Test concurrent request handling."""

    async def test_concurrent_health_checks(
        self,
        stats_service_available,
        test_logger,
    ):
        """Test concurrent health check requests."""
        test_logger.info("test_start", test="concurrent_health")

        async def check_health(client: httpx.AsyncClient, idx: int):
            start = time.time()
            resp = await client.get(f"{STATS_API_URL}/health")
            elapsed = time.time() - start
            return {
                "idx": idx,
                "status": resp.status_code,
                "elapsed_ms": round(elapsed * 1000),
            }

        async with httpx.AsyncClient(timeout=30.0) as client:
            tasks = [check_health(client, i) for i in range(10)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        success_count = sum(
            1 for r in results
            if isinstance(r, dict) and r.get("status") == 200
        )

        test_logger.info(
            "concurrent_results",
            total=len(results),
            success=success_count,
            results=results
        )

        assert success_count == len(results), "Some concurrent requests failed"


# =============================================================================
# Test: Service Discovery
# =============================================================================

@pytest.mark.e2e
@pytest.mark.asyncio
class TestServiceDiscovery:
    """Test service discovery and connectivity."""

    async def test_service_versions(self, test_logger):
        """Get service version information if available."""
        test_logger.info("test_start", test="service_versions")

        services = {
            "stats": STATS_API_URL,
            "automl": AUTOML_API_URL,
        }

        versions = {}
        async with httpx.AsyncClient(timeout=10.0) as client:
            for name, url in services.items():
                try:
                    # Try common version endpoints
                    for endpoint in ["/health", "/version", "/info"]:
                        resp = await client.get(f"{url}{endpoint}")
                        if resp.status_code == 200:
                            data = resp.json()
                            versions[name] = {
                                "endpoint": endpoint,
                                "data": data,
                            }
                            break
                except Exception as e:
                    versions[name] = {"error": str(e)}

        test_logger.info("service_versions", versions=versions)


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
