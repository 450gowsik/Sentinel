"""
SENTINEL — Pydantic schemas for frame data flowing through the pipeline.
"""

from __future__ import annotations

import time
from typing import Any, Optional

import numpy as np
from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    """Pixel-space detection box."""
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float = 0.0
    class_id: int = 0  # 0 = person

    @property
    def center(self) -> tuple[float, float]:
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)

    @property
    def area(self) -> float:
        return max(0, self.x2 - self.x1) * max(0, self.y2 - self.y1)


class TrackInfo(BaseModel):
    """Per-person tracking state."""
    track_id: int
    bbox: BoundingBox
    velocity: tuple[float, float] = (0.0, 0.0)
    trajectory: list[tuple[float, float]] = Field(default_factory=list)
    age: int = 0  # frames alive


class FrameMetadata(BaseModel):
    """Immutable metadata attached to every frame."""
    camera_id: str = "cam_0"
    frame_idx: int = 0
    timestamp: float = Field(default_factory=time.time)
    width: int = 0
    height: int = 0
    fps: float = 0.0


class FramePacket(BaseModel):
    """Central data object flowing through all 14 pipeline stages.

    The raw numpy frame is stored outside Pydantic (via model_config)
    because ndarray is not JSON-serializable.  Stages mutate this
    in-place to avoid copies.
    """

    model_config = {"arbitrary_types_allowed": True}

    meta: FrameMetadata = Field(default_factory=FrameMetadata)

    # Raw pixel data (set externally, not serialized)
    frame: Optional[Any] = Field(default=None, exclude=True)           # np.ndarray HWC BGR
    preprocessed: Optional[Any] = Field(default=None, exclude=True)    # np.ndarray or tensor

    # Phase 3 — detections
    detections: list[BoundingBox] = Field(default_factory=list)

    # Phase 4 — tracks
    tracks: list[TrackInfo] = Field(default_factory=list)

    # Phase 5 — optical flow magnitude
    flow_magnitude: float = 0.0
    flow_field: Optional[Any] = Field(default=None, exclude=True)      # np.ndarray
    
    # Phase 5 — pressure
    pressure_score: float = 0.0
    pressure_field: Optional[Any] = Field(default=None, exclude=True)  # np.ndarray
    collision_points: list[dict] = Field(default_factory=list)         # List of {x, y, force, label}

    # Phase 6 — density
    density_count: float = 0.0
    density_map: Optional[Any] = Field(default=None, exclude=True)     # np.ndarray

    # Phase 7 — predicted trajectories
    predicted_positions: dict[int, list[tuple[float, float]]] = Field(default_factory=dict)

    # Phase 8 — anomaly
    anomaly_score: float = 0.0
    is_anomaly: bool = False

    # Phase 9 — congestion
    congestion_score: float = 0.0
    congestion_zones: list[dict] = Field(default_factory=list)

    # Phase 10 — risk
    risk_score: float = 0.0
    risk_level: str = "LOW"  # LOW | MEDIUM | HIGH | CRITICAL

    # Phase 11 — classified alert
    alert_tier: Optional[str] = None  # INFO | WARNING | DANGER | EMERGENCY
    alert_reason: Optional[str] = None

    # Phase 12 — safe paths
    safe_paths: list[list[tuple[int, int]]] = Field(default_factory=list)

    # Phase 13 — generated alert object
    alert_emitted: bool = False

    # Phase 14 — visualization
    annotated_jpeg: Optional[bytes] = Field(default=None, exclude=True)

    # ── Latency bookkeeping ──────────────────────────────
    stage_latencies: dict[str, float] = Field(default_factory=dict)
    pipeline_start: float = Field(default_factory=time.time)

    @property
    def total_latency_ms(self) -> float:
        return (time.time() - self.pipeline_start) * 1000
