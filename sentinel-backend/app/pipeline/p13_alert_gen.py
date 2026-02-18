"""
SENTINEL — Phase 13: Alert Generation
Builds alert objects, deduplicates, and publishes to Redis.
"""

from __future__ import annotations

import asyncio
import hashlib
import time
from collections import defaultdict
from typing import Optional

import structlog

from app.pipeline.base import PipelineStage
from app.schemas.alert import AlertCreate
from app.schemas.frame import FramePacket

logger = structlog.get_logger(__name__)

# Cooldown per camera+tier (seconds) to prevent alert spam
_COOLDOWN = {
    "INFO": 60,
    "WARNING": 30,
    "DANGER": 15,
    "EMERGENCY": 5,
}


class AlertGenStage(PipelineStage):
    """Generates de-duplicated alert objects and publishes to Redis."""

    name = "p13_alert_gen"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._last_alert_time: dict[str, float] = defaultdict(float)

    async def process(self, packet: FramePacket) -> FramePacket:
        if packet.alert_tier is None:
            return packet

        # Cooldown check
        key = f"{packet.meta.camera_id}:{packet.alert_tier}"
        now = time.time()
        cooldown = _COOLDOWN.get(packet.alert_tier, 30)

        if now - self._last_alert_time[key] < cooldown:
            return packet

        self._last_alert_time[key] = now

        # Build alert
        alert = AlertCreate(
            camera_id=packet.meta.camera_id,
            tier=packet.alert_tier,
            reason=packet.alert_reason or "Risk threshold exceeded",
            risk_score=packet.risk_score,
            density_count=packet.density_count,
            anomaly_score=packet.anomaly_score,
            frame_idx=packet.meta.frame_idx,
        )

        # Publish to Redis
        if self.redis:
            try:
                import orjson
                payload = orjson.dumps(alert.model_dump())
                await self.redis.publish("alert.created", payload)
                logger.info(
                    "alert.published",
                    tier=alert.tier,
                    camera=alert.camera_id,
                    risk=alert.risk_score,
                )
            except Exception as exc:
                logger.error("alert.publish_failed", error=str(exc))

        packet.alert_emitted = True
        return packet
