"""
Stats Service - FastAPI Main Application

Provides statistical analysis endpoints:
- EDA reports (ydata-profiling)
- Table 1 generation (tableone)
- Auto-analyze: intelligent statistical analysis
"""
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .config import SERVICE_HOST, SERVICE_PORT
from .infrastructure.redis_client import redis_client
from .infrastructure.minio_client import minio_client
from .routes import eda, tableone, jobs, auto_analyze, direct

# Configure logging
log_level = os.environ.get("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown"""
    # Startup
    logger.info("Starting Stats Service...")
    
    # Ensure MinIO buckets exist
    minio_client.ensure_buckets()
    logger.info("MinIO buckets verified")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Stats Service...")
    await redis_client.close()


# Create FastAPI app
app = FastAPI(
    title="Stats Service",
    description="""
Statistical Analysis Service for automated EDA and Table 1 generation.

## Features

- **EDA Reports**: Automated exploratory data analysis using ydata-profiling
- **Table 1**: Generate summary statistics tables for research papers using tableone
- **Async Processing**: Long-running tasks processed by background workers

## Job Flow

1. Submit job via POST endpoint
2. Poll status via GET endpoint
3. Retrieve results from MinIO when complete

## Endpoints

### EDA
- `POST /eda/submit` - Submit EDA analysis job
- `POST /eda/preview` - Preview dataset before analysis

### TableOne
- `POST /tableone/submit` - Submit Table 1 generation job
- `POST /tableone/columns` - Get column type suggestions

### Jobs
- `GET /jobs/` - List all jobs for a user
- `GET /jobs/{job_id}` - Get job status
- `GET /jobs/{job_id}/result` - Get job result (JSON)
- `GET /jobs/{job_id}/html` - Get EDA HTML report
- `DELETE /jobs/{job_id}` - Delete job record
""",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Health Endpoints
# =============================================================================

class HealthResponse(BaseModel):
    status: str
    version: str


@app.get("/", response_model=HealthResponse, tags=["Health"])
async def root():
    """Root endpoint"""
    return HealthResponse(status="healthy", version="1.0.0")


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health():
    """Health check endpoint"""
    return HealthResponse(status="healthy", version="1.0.0")


# =============================================================================
# Include Routers
# =============================================================================

app.include_router(auto_analyze.router)  # Smart analysis first
app.include_router(direct.router)  # Direct analysis (no MinIO)
app.include_router(eda.router)
app.include_router(tableone.router)
app.include_router(jobs.router)


# =============================================================================
# Run
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=SERVICE_HOST, port=SERVICE_PORT)
