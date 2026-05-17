import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from app.api.employee_routes import router
import uvicorn

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.getLogger(__name__).info("emp-genai API starting up …")
    yield
    logging.getLogger(__name__).info("emp-genai API shut down.")


app = FastAPI(
    title="emp-genai",
    version="1.0.0",
    description="RAG pipeline for automated employee performance review.",
    lifespan=lifespan,
)

app.include_router(router)

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        workers=1,
        log_level="info",
    )
