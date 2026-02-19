"""
SENTINEL — Analytics response schemas.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class LiveMetrics(BaseModel):
    """Real-time metrics snapshot."""
    camera_id: str
    fps: float = 0.0
    person_count: int = 0
    density: float = 0.0
    avg_flow_magnitude: float = 0.0
    risk_score: float = 0.0
    risk_level: str = "LOW"
    congestion_score: float = 0.0
    anomaly_score: float = 0.0
    pipeline_latency_ms: float = 0.0
    active_alerts: int = 0


class HeatmapResponse(BaseModel):
    """Base64-encoded density heatmap for a camera."""
    camera_id: str
    width: int
    height: int
    density_count: float
    heatmap_b64: str = ""  # base64 JPEG


class TrajectoryPoint(BaseModel):
    x: float
    y: float
    t: float  # timestamp


class TrajectoryResponse(BaseModel):
    """Track history for one person."""
    track_id: int
    camera_id: str
    points: list[TrajectoryPoint] = Field(default_factory=list)
    predicted: list[TrajectoryPoint] = Field(default_factory=list)


class SafePathResponse(BaseModel):
    """Computed evacuation path for a zone."""
    zone_id: str
    path: list[tuple[int, int]] = Field(default_factory=list)
    distance: float = 0.0
    estimated_time_s: float = 0.0


class GPUStatus(BaseModel):
    """GPU health snapshot."""
    device_id: int
    name: str = ""
    vram_total_mb: int = 0
    vram_used_mb: int = 0
    vram_free_mb: int = 0
    utilization_pct: float = 0.0
    temperature_c: float = 0.0
    models_loaded: list[str] = Field(default_factory=list)
