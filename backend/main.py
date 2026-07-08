"""
Quest2Travel — Enterprise AI Travel Planner
FastAPI Application Entry Point
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config.settings import settings
from database.connection import connect_db, disconnect_db
from routers.all_routers import (
    auth_router,
    chat_router,
    sessions_router,
    travel_router,
    company_router,
)

# =====================================================================
# Logging
# =====================================================================

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


# =====================================================================
# Application Lifespan
# =====================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup and shutdown events.
    """

    logger.info("=" * 60)
    logger.info("Starting Quest2Travel API")
    logger.info("Environment : %s", settings.ENVIRONMENT)
    logger.info("Version     : %s", settings.APP_VERSION)
    logger.info("=" * 60)

    try:
        await connect_db()
        logger.info("MongoDB connected successfully.")
    except Exception:
        logger.exception("Failed to connect MongoDB.")
        raise

    yield

    logger.info("Shutting down Quest2Travel API...")

    try:
        await disconnect_db()
        logger.info("MongoDB disconnected.")
    except Exception:
        logger.exception("Error while disconnecting MongoDB.")

    logger.info("Shutdown complete.")


# =====================================================================
# FastAPI
# =====================================================================

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Enterprise AI Travel Planner with Meetings, Flights, Hotels, Trains, Bus and Car Planning",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_tags=[
        {"name": "Chat"},
        {"name": "Travel"},
        {"name": "Sessions"},
        {"name": "Companies"},
    ],
)

# =====================================================================
# CORS
# =====================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"http://localhost:\d+",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)

# =====================================================================
# Global Exception Handler
# =====================================================================

@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request,
    exc: Exception,
):
    logger.exception(
        "Unhandled exception on %s %s",
        request.method,
        request.url,
    )

    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error. Please try again later."
        },
    )

# =====================================================================
# Routers
# =====================================================================

app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(sessions_router)
app.include_router(travel_router)
app.include_router(company_router)

# =====================================================================
# Health
# =====================================================================

@app.get(
    "/api/health",
    tags=["System"],
)
async def health():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }

# =====================================================================
# Readiness
# =====================================================================

@app.get(
    "/api/ready",
    tags=["System"],
)
async def ready():
    """
    Used by deployment platforms.
    """
    return {
        "ready": True,
    }

# =====================================================================
# Version
# =====================================================================

@app.get(
    "/api/version",
    tags=["System"],
)
async def version():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }

# =====================================================================
# Root
# =====================================================================

@app.get(
    "/",
    tags=["System"],
)
async def root():
    return {
        "message": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/api/docs",
        "redoc": "/api/redoc",
        "health": "/api/health",
        "ready": "/api/ready",
    }