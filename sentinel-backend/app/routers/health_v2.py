"""
SENTINEL — Comprehensive Health Check Router
Production-grade health endpoints following Kubernetes patterns.

Production patterns:
  • Kubernetes-compatible liveness/readiness probes
  • Component-level health checks
  • Dependency health aggregation
  • Metrics export for monitoring
  • Graceful degradation status
"""

from __future__ import annotations

import asyncio
import platform
import time
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import structlog
from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field

from app.config import settings
from app.dependencies import get_gpu_manager, get_pipeline_runner

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["health"])


# ── Health Models ────────────────────────────────────────────


class HealthStatus(str, Enum):
    """Component health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ComponentHealth(BaseModel):
    """Health status of a single component."""
    name: str
    status: HealthStatus
    latency_ms: Optional[float] = None
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    last_check: datetime = Field(default_factory=datetime.utcnow)


class SystemHealth(BaseModel):
    """Overall system health response."""
    status: HealthStatus
    version: str
    environment: str
    uptime_seconds: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    components: List[ComponentHealth]
    
    @property
    def is_healthy(self) -> bool:
        return self.status == HealthStatus.HEALTHY


class ReadinessResponse(BaseModel):
    """Kubernetes readiness probe response."""
    ready: bool
    checks: Dict[str, bool]


class LivenessResponse(BaseModel):
    """Kubernetes liveness probe response."""
    alive: bool
    uptime_seconds: float


# ── Health Check Functions ───────────────────────────────────


_start_time = time.monotonic()


def get_uptime() -> float:
    """Get server uptime in seconds."""
    return time.monotonic() - _start_time


async def check_mongodb() -> ComponentHealth:
    """Check MongoDB connectivity."""
    start = time.perf_counter()
    try:
        from app.database.mongodb import mongodb
        healthy = await mongodb.health_check()
        latency = (time.perf_counter() - start) * 1000
        
        if healthy:
            return ComponentHealth(
                name="mongodb",
                status=HealthStatus.HEALTHY,
                latency_ms=round(latency, 2),
                message="Connected to MongoDB Atlas",
                details={"database": settings.mongodb_db},
            )
        else:
            return ComponentHealth(
                name="mongodb",
                status=HealthStatus.UNHEALTHY,
                latency_ms=round(latency, 2),
                message="MongoDB connection failed",
            )
    except Exception as e:
        latency = (time.perf_counter() - start) * 1000
        return ComponentHealth(
            name="mongodb",
            status=HealthStatus.UNHEALTHY,
            latency_ms=round(latency, 2),
            message=f"MongoDB error: {str(e)[:100]}",
        )


async def check_redis() -> ComponentHealth:
    """Check Redis connectivity."""
    start = time.perf_counter()
    try:
        from app.dependencies import _redis_pool
        if _redis_pool is None:
            return ComponentHealth(
                name="redis",
                status=HealthStatus.DEGRADED,
                message="Redis not initialized (optional)",
            )
        
        await _redis_pool.ping()
        latency = (time.perf_counter() - start) * 1000
        
        return ComponentHealth(
            name="redis",
            status=HealthStatus.HEALTHY,
            latency_ms=round(latency, 2),
            message="Redis connected",
        )
    except Exception as e:
        latency = (time.perf_counter() - start) * 1000
        return ComponentHealth(
            name="redis",
            status=HealthStatus.DEGRADED,
            latency_ms=round(latency, 2),
            message=f"Redis unavailable (optional): {str(e)[:50]}",
        )


async def check_gpu() -> ComponentHealth:
    """Check GPU availability."""
    start = time.perf_counter()
    try:
        import torch
        if not torch.cuda.is_available():
            return ComponentHealth(
                name="gpu",
                status=HealthStatus.DEGRADED,
                message="CUDA not available, using CPU",
            )
        
        device_name = torch.cuda.get_device_name(0)
        memory_allocated = torch.cuda.memory_allocated(0) / 1024**2
        memory_reserved = torch.cuda.memory_reserved(0) / 1024**2
        
        latency = (time.perf_counter() - start) * 1000
        
        return ComponentHealth(
            name="gpu",
            status=HealthStatus.HEALTHY,
            latency_ms=round(latency, 2),
            message=f"GPU: {device_name}",
            details={
                "device": device_name,
                "memory_allocated_mb": round(memory_allocated, 1),
                "memory_reserved_mb": round(memory_reserved, 1),
            },
        )
    except ImportError:
        return ComponentHealth(
            name="gpu",
            status=HealthStatus.DEGRADED,
            message="PyTorch not installed",
        )
    except Exception as e:
        return ComponentHealth(
            name="gpu",
            status=HealthStatus.UNHEALTHY,
            message=f"GPU error: {str(e)[:100]}",
        )


async def check_pipeline() -> ComponentHealth:
    """Check ML pipeline status."""
    start = time.perf_counter()
    try:
        from app.dependencies import _pipeline_runner
        if _pipeline_runner is None:
            return ComponentHealth(
                name="pipeline",
                status=HealthStatus.UNHEALTHY,
                message="Pipeline not initialized",
            )
        
        diag = _pipeline_runner.diagnostics()
        latency = (time.perf_counter() - start) * 1000
        
        return ComponentHealth(
            name="pipeline",
            status=HealthStatus.HEALTHY,
            latency_ms=round(latency, 2),
            message=f"Pipeline ready with {diag.get('stage_count', 0)} stages",
            details=diag,
        )
    except Exception as e:
        return ComponentHealth(
            name="pipeline",
            status=HealthStatus.UNHEALTHY,
            message=f"Pipeline error: {str(e)[:100]}",
        )


async def check_camera() -> ComponentHealth:
    """Check camera manager status."""
    try:
        from app.services.camera_manager import camera_manager
        
        return ComponentHealth(
            name="camera",
            status=HealthStatus.HEALTHY if camera_manager.state == "connected" else HealthStatus.DEGRADED,
            message=f"Camera state: {camera_manager.state}",
            details={
                "state": camera_manager.state,
                "source": camera_manager.source,
                "frame_id": camera_manager.frame_id,
            },
        )
    except Exception as e:
        return ComponentHealth(
            name="camera",
            status=HealthStatus.UNKNOWN,
            message=f"Camera check error: {str(e)[:100]}",
        )


def aggregate_status(components: List[ComponentHealth]) -> HealthStatus:
    """Determine overall status from component statuses."""
    statuses = [c.status for c in components]
    
    # Any unhealthy critical component = unhealthy
    critical_components = {"mongodb", "pipeline"}
    for comp in components:
        if comp.name in critical_components and comp.status == HealthStatus.UNHEALTHY:
            return HealthStatus.UNHEALTHY
    
    # Any unhealthy = degraded
    if HealthStatus.UNHEALTHY in statuses:
        return HealthStatus.DEGRADED
    
    # Any degraded = degraded
    if HealthStatus.DEGRADED in statuses:
        return HealthStatus.DEGRADED
    
    return HealthStatus.HEALTHY


# ── Health Endpoints ─────────────────────────────────────────


@router.get("/health", response_model=SystemHealth)
async def health_check() -> SystemHealth:
    """
    Comprehensive health check.
    
    Returns detailed status of all system components.
    Use for monitoring dashboards and alerting.
    """
    # Run all health checks concurrently
    checks = await asyncio.gather(
        check_mongodb(),
        check_redis(),
        check_gpu(),
        check_pipeline(),
        check_camera(),
        return_exceptions=True,
    )
    
    # Handle any exceptions from health checks
    components = []
    for check in checks:
        if isinstance(check, Exception):
            components.append(ComponentHealth(
                name="unknown",
                status=HealthStatus.UNKNOWN,
                message=f"Check failed: {str(check)[:100]}",
            ))
        else:
            components.append(check)
    
    return SystemHealth(
        status=aggregate_status(components),
        version="2.0.0",
        environment=settings.app_env,
        uptime_seconds=round(get_uptime(), 2),
        components=components,
    )


@router.get("/health/live", response_model=LivenessResponse)
async def liveness_probe() -> LivenessResponse:
    """
    Kubernetes liveness probe.
    
    Returns quickly to indicate the process is running.
    Does NOT check dependencies.
    """
    return LivenessResponse(
        alive=True,
        uptime_seconds=round(get_uptime(), 2),
    )


@router.get("/health/ready", response_model=ReadinessResponse)
async def readiness_probe(response: Response) -> ReadinessResponse:
    """
    Kubernetes readiness probe.
    
    Checks if the service is ready to receive traffic.
    Returns 503 if not ready.
    """
    # Check critical components only
    mongo_check = await check_mongodb()
    pipeline_check = await check_pipeline()
    
    checks = {
        "mongodb": mongo_check.status == HealthStatus.HEALTHY,
        "pipeline": pipeline_check.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED],
    }
    
    ready = all(checks.values())
    
    if not ready:
        response.status_code = 503
    
    return ReadinessResponse(
        ready=ready,
        checks=checks,
    )


@router.get("/health/startup")
async def startup_probe():
    """
    Kubernetes startup probe.
    
    Used during container startup to allow slow initialization.
    """
    from app.dependencies import _pipeline_runner
    
    if _pipeline_runner is None:
        return Response(status_code=503, content="Pipeline initializing...")
    
    return {"status": "started"}


@router.get("/health/metrics")
async def health_metrics():
    """
    Prometheus-compatible metrics endpoint.
    
    Returns metrics in text format for scraping.
    """
    uptime = get_uptime()
    
    # Build Prometheus format
    lines = [
        "# HELP sentinel_uptime_seconds Server uptime in seconds",
        "# TYPE sentinel_uptime_seconds gauge",
        f"sentinel_uptime_seconds {uptime:.2f}",
        "",
        "# HELP sentinel_info Server information",
        "# TYPE sentinel_info gauge",
        f'sentinel_info{{version="2.0.0",env="{settings.app_env}"}} 1',
    ]
    
    # Add component statuses
    health = await health_check()
    for comp in health.components:
        status_value = 1 if comp.status == HealthStatus.HEALTHY else 0
        lines.append(f'sentinel_component_healthy{{component="{comp.name}"}} {status_value}')
        if comp.latency_ms:
            lines.append(f'sentinel_component_latency_ms{{component="{comp.name}"}} {comp.latency_ms}')
    
    return Response(
        content="\n".join(lines),
        media_type="text/plain",
    )


@router.get("/api/v1/system/info")
async def system_info():
    """
    Detailed system information for debugging.
    """
    import sys
    
    return {
        "python_version": sys.version,
        "platform": platform.platform(),
        "architecture": platform.architecture(),
        "processor": platform.processor(),
        "environment": settings.app_env,
        "debug": settings.debug,
        "uptime_seconds": round(get_uptime(), 2),
    }


# Keep existing endpoints for backward compatibility

@router.get("/api/v1/gpu-status")
async def gpu_status():
    """GPU health snapshot."""
    try:
        gpu_manager = get_gpu_manager()
        data = gpu_manager.status()
        return {
            "device_id": data.get("device_id", 0),
            "name": data.get("name", "unknown"),
            "vram_total_mb": data.get("vram_total_mb", 0),
            "vram_used_mb": data.get("vram_used_mb", 0),
            "vram_free_mb": data.get("vram_free_mb", 0),
            "utilization_pct": data.get("utilization_pct", 0),
            "temperature_c": data.get("temperature_c", 0),
            "models_loaded": [m["name"] for m in data.get("models_loaded", [])],
        }
    except Exception as e:
        return {
            "status": "unavailable",
            "error": str(e),
        }


@router.get("/api/v1/pipeline/diagnostics")
async def pipeline_diagnostics():
    """Pipeline buffer depths and drop stats."""
    try:
        runner = get_pipeline_runner()
        return runner.diagnostics()
    except Exception as e:
        return {
            "status": "unavailable",
            "error": str(e),
        }
