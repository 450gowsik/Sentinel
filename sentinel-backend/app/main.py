"""
SENTINEL (PRAVAHA) — FastAPI Application Entry Point
Lifespan-managed startup / shutdown for GPU, Redis, Pipeline, and Camera Manager.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

import structlog
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.config import settings
from app.dependencies import (
    close_redis,
    init_gpu_manager,
    init_pipeline_runner,
    init_redis,
    shutdown_gpu_manager,
    shutdown_pipeline_runner,
)
from app.services.camera_manager import camera_manager

logger = structlog.get_logger(__name__)


# ── Lifespan ─────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: Redis → GPU → Pipeline → Camera.  Shutdown: reverse.
    
    Each init step is wrapped in try/except so the server boots
    even when Redis, GPU, or models are unavailable (dev mode).
    """
    logger.info("sentinel.starting", env=settings.app_env)

    # --- Startup (graceful — each step optional) ---
    
    # Initialize MongoDB
    try:
        from app.database.mongodb import mongodb
        await mongodb.connect()
    except Exception as exc:
        logger.warning("sentinel.mongodb_unavailable", error=str(exc))
    
    try:
        await init_redis()
    except Exception as exc:
        logger.warning("sentinel.redis_unavailable", error=str(exc))

    try:
        await init_gpu_manager()
    except Exception as exc:
        logger.warning("sentinel.gpu_unavailable", error=str(exc))

    try:
        await init_pipeline_runner()
    except Exception as exc:
        logger.warning("sentinel.pipeline_init_failed", error=str(exc))


    # Camera Manager: initialized but NOT started on boot.
    # Camera capture starts lazily on first WebSocket connection
    # or via POST /live/config. This prevents blocking if no camera exists.
    logger.info("sentinel.camera_manager_ready", note="starts on first ws connect")

    logger.info("sentinel.ready", port=settings.port)
    yield

    # --- Shutdown ---
    logger.info("sentinel.stopping")
    
    # Stop Camera Manager
    try:
        await camera_manager.stop()
    except Exception:
        pass

    try:
        await shutdown_pipeline_runner()
    except Exception:
        pass
    try:
        await shutdown_gpu_manager()
    except Exception:
        pass
    try:
        await close_redis()
    except Exception:
        pass
    try:
        from app.database.mongodb import mongodb
        await mongodb.close()
    except Exception:
        pass
    logger.info("sentinel.stopped")


# ── App Factory ──────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title="SENTINEL (PRAVAHA)",
        description="Real-Time Crowd Surge Intelligence Platform",
        version="2.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    # ── CORS ─────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # lock down in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Prometheus ───────────────────────────────────────
    if settings.metrics_enabled:
        Instrumentator(
            should_group_status_codes=True,
            should_ignore_untemplated=True,
            excluded_handlers=["/health", "/metrics"],
        ).instrument(app).expose(app, endpoint="/metrics")

    # ── Routers ──────────────────────────────────────────
    from app.routers import alerts, analytics, detect, health, stream, live_cam

    app.include_router(health.router)
    app.include_router(stream.router)
    app.include_router(live_cam.router)
    app.include_router(alerts.router)
    app.include_router(analytics.router)
    app.include_router(detect.router)

    return app


app = create_app()


# ── CLI entry point ──────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        workers=settings.workers,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
