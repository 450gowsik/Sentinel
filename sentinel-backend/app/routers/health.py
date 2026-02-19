"""
SENTINEL — Health & GPU Status Router
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.dependencies import get_gpu_manager, get_pipeline_runner
from app.schemas.analytics import GPUStatus

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    """Liveness check."""
    from app.database.mongodb import mongodb
    mongo_status = await mongodb.health_check()
    return {
        "status": "ok", 
        "service": "sentinel-backend", 
        "version": "2.0.0",
        "mongodb": "connected" if mongo_status else "disconnected"
    }


@router.get("/api/v1/gpu-status", response_model=GPUStatus)
async def gpu_status(gpu=Depends(get_gpu_manager)):
    """GPU health snapshot."""
    data = gpu.status()
    return GPUStatus(
        device_id=data.get("device_id", 0),
        name=data.get("name", "unknown"),
        vram_total_mb=data.get("vram_total_mb", 0),
        vram_used_mb=data.get("vram_used_mb", 0),
        vram_free_mb=data.get("vram_free_mb", 0),
        utilization_pct=data.get("utilization_pct", 0),
        temperature_c=data.get("temperature_c", 0),
        models_loaded=[m["name"] for m in data.get("models_loaded", [])],
    )


@router.get("/api/v1/pipeline/diagnostics")
async def pipeline_diagnostics(runner=Depends(get_pipeline_runner)):
    """Pipeline buffer depths and drop stats."""
    return runner.diagnostics()
