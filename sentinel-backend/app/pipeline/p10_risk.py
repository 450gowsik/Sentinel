"""
SENTINEL — Phase 10: Risk Scoring
Weighted multi-signal risk scorer.
"""

from __future__ import annotations

import asyncio

import structlog

from app.pipeline.base import PipelineStage
from app.schemas.frame import FramePacket

logger = structlog.get_logger(__name__)

# Scoring weights (must sum to 1.0)
_WEIGHTS = {
    "density": 0.25,
    "congestion": 0.20,
    "flow": 0.15,
    "anomaly": 0.25,
    "velocity": 0.15,
}

# Risk level thresholds
_LEVELS = [
    (0.8, "CRITICAL"),
    (0.6, "HIGH"),
    (0.4, "MEDIUM"),
    (0.0, "LOW"),
]


class RiskStage(PipelineStage):
    """Computes a composite risk score from upstream signals."""

    name = "p10_risk"

    async def process(self, packet: FramePacket) -> FramePacket:
        # Normalize each signal to [0, 1]
        density_norm = min(1.0, packet.density_count / 200) if packet.density_count > 0 else 0.0
        congestion_norm = min(1.0, packet.congestion_score)
        flow_norm = min(1.0, packet.flow_magnitude / 10.0) if packet.flow_magnitude > 0 else 0.0
        anomaly_norm = min(1.0, packet.anomaly_score / 2.0) if packet.anomaly_score > 0 else 0.0

        # Average track velocity magnitude
        avg_vel = 0.0
        if packet.tracks:
            import numpy as np
            vels = [np.sqrt(t.velocity[0] ** 2 + t.velocity[1] ** 2) for t in packet.tracks]
            avg_vel = float(np.mean(vels)) if vels else 0.0
        vel_norm = min(1.0, avg_vel / 20.0)

        # Weighted composite
        score = (
            _WEIGHTS["density"] * density_norm
            + _WEIGHTS["congestion"] * congestion_norm
            + _WEIGHTS["flow"] * flow_norm
            + _WEIGHTS["anomaly"] * anomaly_norm
            + _WEIGHTS["velocity"] * vel_norm
        )

        # Boost if anomaly detected
        if packet.is_anomaly:
            score = min(1.0, score * 1.3)

        # Determine level
        level = "LOW"
        for threshold, label in _LEVELS:
            if score >= threshold:
                level = label
                break

        packet.risk_score = round(score, 4)
        packet.risk_level = level

        return packet
