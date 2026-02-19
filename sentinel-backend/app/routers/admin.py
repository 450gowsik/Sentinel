"""
SENTINEL — Admin Router
Production-grade admin endpoints for system management.

Endpoints:
  • /admin/scheduler - Scheduler status and control
  • /admin/config - Runtime configuration
  • /admin/tasks - Background task management
"""

from __future__ import annotations

from typing import Any, Dict

import structlog
from fastapi import APIRouter, HTTPException, status

from app.config import settings
from app.services.scheduler import scheduler

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/scheduler")
async def scheduler_status() -> Dict[str, Any]:
    """Get background scheduler status and task statistics."""
    return scheduler.status()


@router.post("/scheduler/task/{task_name}/run")
async def run_task_now(task_name: str):
    """Manually trigger a background task."""
    success = await scheduler.run_now(task_name)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task '{task_name}' not found",
        )
    return {"status": "triggered", "task": task_name}


@router.post("/scheduler/task/{task_name}/enable")
async def enable_task(task_name: str):
    """Enable a background task."""
    success = scheduler.enable_task(task_name)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task '{task_name}' not found",
        )
    return {"status": "enabled", "task": task_name}


@router.post("/scheduler/task/{task_name}/disable")
async def disable_task(task_name: str):
    """Disable a background task."""
    success = scheduler.disable_task(task_name)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task '{task_name}' not found",
        )
    return {"status": "disabled", "task": task_name}


@router.get("/config")
async def get_config():
    """Get current runtime configuration (non-sensitive)."""
    return {
        "app_env": settings.app_env,
        "debug": settings.debug,
        "host": settings.host,
        "port": settings.port,
        "metrics_enabled": settings.metrics_enabled,
        "mongodb_db": settings.mongodb_db,
    }


@router.get("/middleware/timing")
async def timing_stats():
    """Get request timing statistics."""
    from app.middleware.timing import TimingMiddleware
    return TimingMiddleware.get_latency_stats()


@router.get("/middleware/rate-limiter")
async def rate_limiter_stats():
    """Get rate limiter statistics."""
    from app.middleware.rate_limiter import RateLimiterMiddleware
    return {
        "active_clients": len(RateLimiterMiddleware._buckets) if hasattr(RateLimiterMiddleware, '_buckets') else 0,
    }
