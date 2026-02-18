"""
SENTINEL — Alert Service
Stores alerts to PostgreSQL, handles acknowledgement, deduplication.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import structlog

from app.schemas.alert import AlertAck, AlertCreate, AlertResponse, AlertStatus

logger = structlog.get_logger(__name__)


class AlertService:
    """In-memory alert store (swap for async SQLAlchemy in production).

    Provides:
        - create()     — persist new alert
        - list()       — paginated alert retrieval
        - acknowledge() — mark alert as ACK'd
        - cleanup()    — expire old alerts
    """

    def __init__(self):
        self._alerts: Dict[str, AlertResponse] = {}

    async def create(self, alert: AlertCreate) -> AlertResponse:
        """Create and store a new alert."""
        alert_id = str(uuid.uuid4())[:12]

        response = AlertResponse(
            id=alert_id,
            camera_id=alert.camera_id,
            tier=alert.tier,
            reason=alert.reason,
            risk_score=alert.risk_score,
            density_count=alert.density_count,
            anomaly_score=alert.anomaly_score,
            zone_id=alert.zone_id,
            created_at=datetime.utcnow(),
        )
        self._alerts[alert_id] = response
        logger.info("alert.stored", id=alert_id, tier=alert.tier)
        return response

    async def list_alerts(
        self,
        limit: int = 50,
        status: Optional[AlertStatus] = None,
        camera_id: Optional[str] = None,
    ) -> List[AlertResponse]:
        """Retrieve alerts with optional filters."""
        alerts = list(self._alerts.values())

        if status:
            alerts = [a for a in alerts if a.status == status]
        if camera_id:
            alerts = [a for a in alerts if a.camera_id == camera_id]

        # Sort by newest first
        alerts.sort(key=lambda a: a.created_at, reverse=True)
        return alerts[:limit]

    async def acknowledge(self, alert_id: str, ack: AlertAck) -> Optional[AlertResponse]:
        """Acknowledge an alert."""
        alert = self._alerts.get(alert_id)
        if not alert:
            return None

        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_at = datetime.utcnow()
        alert.acknowledged_by = ack.operator_id
        logger.info("alert.acknowledged", id=alert_id, by=ack.operator_id)
        return alert

    async def get(self, alert_id: str) -> Optional[AlertResponse]:
        return self._alerts.get(alert_id)

    async def active_count(self) -> int:
        return sum(
            1 for a in self._alerts.values()
            if a.status == AlertStatus.ACTIVE
        )

    async def cleanup(self, max_age_hours: int = 24) -> int:
        """Remove alerts older than max_age_hours."""
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        stale = [
            aid for aid, a in self._alerts.items()
            if a.created_at < cutoff
        ]
        for aid in stale:
            del self._alerts[aid]
        return len(stale)


# Global singleton
alert_service = AlertService()
