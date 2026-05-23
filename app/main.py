import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from app.config.database import init_db
from app.api.employee_routes import router
import uvicorn

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("emp-genai API starting up …")
    try:
        logger.info("Initializing database schema...")
        init_db()
        logger.info("✓ Database initialized successfully")
    except Exception as e:
        logger.error(f"✗ Database initialization failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("emp-genai API shut down.")


app = FastAPI(
    title="emp-genai",
    version="1.0.0",
    description="RAG pipeline for automated employee performance review with pgvector embeddings.",
    lifespan=lifespan,
)

app.include_router(router)

# Health check endpoint
@app.get("/health")
def health_check():
    return {"status": "ok", "service": "emp-genai"}

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        workers=1,
        log_level="info",
    )
