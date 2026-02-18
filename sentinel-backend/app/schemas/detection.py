"""
SENTINEL — Detection response schemas.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class DetectionResult(BaseModel):
    """Single person detection result."""
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float
    track_id: int | None = None


class DetectionFrame(BaseModel):
    """All detections for one frame."""
    camera_id: str
    frame_idx: int
    timestamp: float
    person_count: int
    detections: list[DetectionResult] = Field(default_factory=list)
