import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.analytics import router as analytics_router
from app.api.changes import router as changes_router
from app.api.demo import router as demo_router
from app.api.health import router as health_router
from app.api.historical_changes import router as historical_changes_router
from app.core.config import get_settings
from app.db.session import check_database_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()

    if settings.check_db_on_startup:
        if check_database_connection():
            logger.info("Database connection check succeeded")
        else:
            logger.error("Database connection check failed; application will keep running")

    yield


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.service_name,
        version="0.1.0",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(analytics_router)
    application.include_router(changes_router)
    application.include_router(demo_router)
    application.include_router(historical_changes_router)
    application.include_router(health_router)
    return application


app = create_app()
