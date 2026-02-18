"""
SENTINEL — Alerts Router
CRUD endpoints for alert management.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.schemas.alert import AlertAck, AlertResponse, AlertStatus
from app.services.alert_service import alert_service

router = APIRouter(prefix="/api/v1", tags=["alerts"])


@router.get("/alerts", response_model=list[AlertResponse])
async def list_alerts(
    limit: int = Query(50, ge=1, le=200),
    status: Optional[AlertStatus] = None,
    camera_id: Optional[str] = None,
):
    """List alerts with optional filters."""
    return await alert_service.list_alerts(
        limit=limit, status=status, camera_id=camera_id
    )


@router.get("/alerts/{alert_id}", response_model=AlertResponse)
async def get_alert(alert_id: str):
    """Get a single alert by ID."""
    alert = await alert_service.get(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.post("/alerts/{alert_id}/ack", response_model=AlertResponse)
async def acknowledge_alert(alert_id: str, ack: AlertAck):
    """Acknowledge an alert."""
    alert = await alert_service.acknowledge(alert_id, ack)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.get("/alerts/active/count")
async def active_alert_count():
    """Get count of active (unacknowledged) alerts."""
    count = await alert_service.active_count()
    return {"active_alerts": count}
