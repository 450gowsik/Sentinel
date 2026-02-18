"""
SENTINEL — Dependency Injection Providers
FastAPI Depends() callables for GPU manager, Redis, and model registry.
"""

from __future__ import annotations

import asyncio
from functools import lru_cache
from typing import AsyncGenerator

import redis.asyncio as aioredis
import structlog

from app.config import settings

logger = structlog.get_logger(__name__)

# ── Singleton containers (initialised at lifespan) ───────────

_redis_pool: aioredis.Redis | None = None
_gpu_manager = None  # type: ignore[assignment]
_pipeline_runner = None  # type: ignore[assignment]


# ── Redis ────────────────────────────────────────────────────

async def init_redis() -> aioredis.Redis:
    global _redis_pool
    _redis_pool = aioredis.from_url(
        settings.redis_url,
        decode_responses=False,
        max_connections=20,
    )
    await _redis_pool.ping()
    logger.info("redis.connected", url=settings.redis_url)
    return _redis_pool


async def close_redis() -> None:
    global _redis_pool
    if _redis_pool:
        await _redis_pool.close()
        _redis_pool = None
        logger.info("redis.disconnected")


async def get_redis() -> aioredis.Redis:
    """FastAPI dependency."""
    if _redis_pool is None:
        raise RuntimeError("Redis not initialised — check lifespan")
    return _redis_pool


# ── GPU Manager ──────────────────────────────────────────────

async def init_gpu_manager():
    """Lazy-import to avoid CUDA init at module load."""
    global _gpu_manager
    from app.engine.gpu_manager import GPUManager

    _gpu_manager = GPUManager(
        device_id=settings.cuda_device,
        vram_limit_mb=settings.vram_limit_mb,
    )
    await _gpu_manager.initialize()
    logger.info("gpu_manager.ready", device=settings.cuda_device)
    return _gpu_manager


async def shutdown_gpu_manager() -> None:
    global _gpu_manager
    if _gpu_manager:
        await _gpu_manager.shutdown()
        _gpu_manager = None


def get_gpu_manager():
    """FastAPI dependency."""
    if _gpu_manager is None:
        raise RuntimeError("GPUManager not initialised — check lifespan")
    return _gpu_manager


# ── Pipeline Runner ──────────────────────────────────────────

async def init_pipeline_runner():
    """Build and warm-up the 14-stage async pipeline."""
    global _pipeline_runner
    from app.engine.pipeline_runner import PipelineRunner

    _pipeline_runner = PipelineRunner(
        gpu_manager=_gpu_manager,
        redis=_redis_pool,
        settings=settings,
    )
    await _pipeline_runner.build()
    logger.info("pipeline.ready", stages=_pipeline_runner.stage_count)
    return _pipeline_runner


async def shutdown_pipeline_runner() -> None:
    global _pipeline_runner
    if _pipeline_runner:
        await _pipeline_runner.stop()
        _pipeline_runner = None


def get_pipeline_runner():
    """FastAPI dependency."""
    if _pipeline_runner is None:
        raise RuntimeError("PipelineRunner not initialised — check lifespan")
    return _pipeline_runner
