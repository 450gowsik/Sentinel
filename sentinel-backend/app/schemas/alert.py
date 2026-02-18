"""
SENTINEL — Alert schemas for API and storage.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class AlertTier(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    DANGER = "DANGER"
    EMERGENCY = "EMERGENCY"


class AlertStatus(str, Enum):
    ACTIVE = "ACTIVE"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"
    EXPIRED = "EXPIRED"


class AlertCreate(BaseModel):
    """Internal: emitted by Phase 13."""
    camera_id: str
    tier: AlertTier
    reason: str
    risk_score: float
    density_count: float = 0.0
    anomaly_score: float = 0.0
    zone_id: str | None = None
    frame_idx: int = 0


class AlertResponse(BaseModel):
    """API response for a single alert."""
    id: str
    camera_id: str
    tier: AlertTier
    status: AlertStatus = AlertStatus.ACTIVE
    reason: str
    risk_score: float
    density_count: float = 0.0
    anomaly_score: float = 0.0
    zone_id: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    acknowledged_at: datetime | None = None
    acknowledged_by: str | None = None


class AlertAck(BaseModel):
    """Payload to acknowledge an alert."""
    operator_id: str
    notes: str = ""
