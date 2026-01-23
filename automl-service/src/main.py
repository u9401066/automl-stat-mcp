"""
AutoML Service - FastAPI Main Application

Lightweight API service. AutoGluon runs in separate worker container.
"""
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import API_HOST, API_PORT, AVAILABLE_ALGORITHMS
from .infrastructure.storage_factory import get_storage
from .interface.api.routes import datasets, direct, jobs, models, post_only, training
from .interface.api.schemas import HealthResponse

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
    logger.info("Starting AutoML API Service...")
    
    # Initialize storage backend
    storage = get_storage()
    storage_type = storage.__class__.__name__
    logger.info(f"Storage backend initialized: {storage_type}")
    
    logger.info("Note: Training jobs are processed by the worker container")

    yield

    # Shutdown
    logger.info("Shutting down AutoML API Service...")
    logger.info("Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="AutoML Service",
    description="""
AutoML Service using AutoGluon.

## Features

- **AutoML**: Automatic model selection and hyperparameter tuning
- **Specific Training**: Train with specific algorithms
- **Model Comparison**: Compare multiple algorithms
- **Async Training**: Non-blocking training with WebSocket progress updates
- **Multi-user Support**: User/session resource isolation

## Available Algorithms

""" + "\n".join([f"- **{k}**: {v}" for k, v in AVAILABLE_ALGORITHMS.items()]),
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(datasets.router)
app.include_router(training.router)
app.include_router(jobs.router)
app.include_router(models.router)
app.include_router(direct.router)

# POST-only API for enterprise environments (external access)
app.include_router(post_only.router)


@app.get("/", response_model=HealthResponse, tags=["Health"])
async def root():
    """Root endpoint"""
    return HealthResponse(status="healthy", version="1.0.0")


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint for Docker healthcheck"""
    return HealthResponse(status="healthy", version="1.0.0")


@app.get("/algorithms", tags=["Info"])
async def list_algorithms():
    """List available algorithms"""
    return {
        "algorithms": AVAILABLE_ALGORITHMS,
        "description": "Use the algorithm codes (e.g., 'XGB', 'GBM') in training requests",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=API_HOST, port=API_PORT)
