"""
RDBMS Builder API Server
FastAPI application entry point

Run with:
    uvicorn api-main:app --host 0.0.0.0 --port 8000 --reload

Or for production:
    uvicorn api-main:app --host 0.0.0.0 --port 8000 --workers 4
"""
import os
import sys
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.routes import router as api_router
from api.job_manager import JobManager
from api.graph_service import get_graph_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    print("🚀 Starting RDBMS Builder API...")
    
    # Initialize services
    _ = get_graph_service()
    _ = JobManager.get_instance()
    
    # Ensure data directory exists
    os.makedirs("./data", exist_ok=True)
    os.makedirs("./output", exist_ok=True)
    
    print("✅ API Ready!")
    print("📚 API Docs: http://localhost:8000/docs")
    print("📋 ReDoc: http://localhost:8000/redoc")
    
    yield
    
    # Shutdown
    print("\n🛑 Shutting down RDBMS Builder API...")
    
    # Cleanup job manager
    job_manager = JobManager.get_instance()
    job_manager.shutdown()
    
    # Cleanup graph service
    service = get_graph_service()
    service.cleanup()
    
    print("👋 Goodbye!")


# Create FastAPI app
app = FastAPI(
    title="RDBMS Builder API",
    description="""
## AI-Powered Backend Builder

Generate complete database schemas and NestJS backend architectures from natural language requirements.

### Features

- **Database Schema Generation**: PostgreSQL, MySQL, SQLite support
- **ERD Diagram Generation**: Mermaid diagrams
- **NestJS Architecture**: Complete backend structure with modules, controllers, services
- **Critic Review**: AI-powered schema review and optimization
- **Conversation Memory**: Resume and continue previous sessions
- **Async Processing**: Long-running jobs with status polling

### Workflow

1. **Sync Mode**: Call `/api/v1/generate` for quick jobs (may timeout)
2. **Async Mode**: 
   - POST `/api/v1/generate-async` → Get `job_id`
   - GET `/api/v1/job/{job_id}` → Poll status
   - If `awaiting_input`, POST `/api/v1/answer` with answers
   - Continue polling until `completed`

### Status Values

- `pending`: Job created but not started
- `processing`: Job is running
- `awaiting_input`: Clarification questions need answers
- `completed`: Job finished successfully
- `failed`: Job failed with error
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)


# CORS middleware - allow all origins for development
# TODO: Restrict origins in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions"""
    import traceback
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": str(exc),
            "traceback": traceback.format_exc() if os.getenv("DEBUG") else None
        }
    )


# Include API routes
app.include_router(api_router)


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information"""
    return {
        "name": "RDBMS Builder API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health"
    }


if __name__ == "__main__":
    import uvicorn
    
    # Get configuration from environment
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    reload = os.getenv("API_RELOAD", "true").lower() == "true"
    workers = int(os.getenv("API_WORKERS", "1"))
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                    RDBMS Builder API                         ║
╠══════════════════════════════════════════════════════════════╣
║  Host: {host:<53} ║
║  Port: {port:<53} ║
║  Reload: {str(reload):<51} ║
║  Workers: {workers:<50} ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    uvicorn.run(
        "api-main:app",
        host=host,
        port=port,
        reload=reload,
        workers=workers if not reload else 1  # Can't use workers with reload
    )

