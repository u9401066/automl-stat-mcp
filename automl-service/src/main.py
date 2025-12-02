"""
AutoML Service - FastAPI Main Application
"""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .interface.api.routes import datasets, training, jobs, models
from .interface.api.dependencies import get_container
from .interface.api.schemas import HealthResponse
from .config import API_HOST, API_PORT, AVAILABLE_ALGORITHMS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown"""
    # Startup
    logger.info("Starting AutoML Service...")
    
    container = get_container()
    
    # Start job worker
    worker_task = asyncio.create_task(container.job_worker.run())
    logger.info("Job worker started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down AutoML Service...")
    container.job_worker.stop()
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass
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


@app.get("/", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint"""
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
