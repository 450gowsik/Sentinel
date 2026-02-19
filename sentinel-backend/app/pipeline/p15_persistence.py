"""
SENTINEL — Phase 15: Live Persistence
Archives detection metadata to MongoDB for auditing and reporting.
Matches the schema of the image/video upload service for consistency.
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Optional

import structlog

from app.database.mongodb import mongodb
from app.pipeline.base import PipelineStage
from app.schemas.frame import FramePacket

logger = structlog.get_logger(__name__)


class PersistenceStage(PipelineStage):
    """Saves detection metadata to MongoDB at periodic intervals."""

    name = "p15_persistence"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._last_save_time: float = 0.0
        self._interval: float = 5.0  # Default to 5s if not in settings

    async def setup(self) -> None:
        """Fetch interval from settings if available."""
        if hasattr(self.settings, "persistence_interval_seconds"):
            self._interval = float(self.settings.persistence_interval_seconds)
        logger.info("persistence.setup", interval=self._interval)

    async def process(self, packet: FramePacket) -> FramePacket:
        now = time.time()
        
        # Check if it's time to save (Frequency Control)
        if now - self._last_save_time < self._interval:
            return packet

        if not mongodb.is_connected():
            return packet

        self._last_save_time = now

        try:
            collection = mongodb.get_collection("detections")
            
            # Map FramePacket to MongoDB Schema (Detect Protocol)
            doc = {
                "detection_type": "live_stream",
                "camera_id": packet.meta.camera_id,
                "frame_idx": packet.meta.frame_idx,
                "person_count": len([d for d in packet.detections if d.class_id == 0]),
                "density_estimate": round(packet.density_count, 2),
                "risk_score": round(packet.risk_score, 3),
                "risk_level": packet.risk_level,
                "anomaly_score": round(packet.anomaly_score, 3),
                "flow_rate": round(packet.flow_magnitude, 1),
                "timestamp": datetime.fromtimestamp(packet.meta.timestamp),
                "upload_source": "live_monitoring",
                "congestion_zones": packet.congestion_zones[:5],  # Limit zones
                "is_anomaly": packet.is_anomaly,
                "alert_tier": packet.alert_tier,
                "alert_reason": packet.alert_reason,
            }

            # Insert metadata (No images to keep DB small)
            # Use background execution for DB insert to not block pipeline
            # Note: motor's insert_one is already async, but we don't await it 
            # if we don't want to block the frame throughput.
            # However, for 1 save every 5s, awaiting is fine and safer.
            await collection.insert_one(doc)
            
            logger.debug("persistence.saved", 
                        camera=packet.meta.camera_id, 
                        frame=packet.meta.frame_idx)
            
        except Exception as exc:
            logger.error("persistence.failed", error=str(exc))

        return packet
