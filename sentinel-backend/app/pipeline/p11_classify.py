"""
SENTINEL — Phase 11: Alert Classification
Maps risk level + signals to alert tiers with reasoning.
"""

from __future__ import annotations

import asyncio

import structlog

from app.pipeline.base import PipelineStage
from app.schemas.frame import FramePacket

logger = structlog.get_logger(__name__)


class ClassifyStage(PipelineStage):
    """Rule-based alert tier classifier.

    Tiers
    ─────
        EMERGENCY  — immediate evacuation risk
        DANGER     — high risk, intervention needed
        WARNING    — elevated risk, monitor closely
        INFO       — normal reporting
        None       — no alert needed
    """

    name = "p11_classify"

    async def process(self, packet: FramePacket) -> FramePacket:
        tier, reason = self._classify(packet)
        packet.alert_tier = tier
        packet.alert_reason = reason
        return packet

    @staticmethod
    def _classify(packet: FramePacket) -> tuple[str | None, str | None]:
        risk = packet.risk_score
        level = packet.risk_level

        # EMERGENCY: critical risk + anomaly
        if level == "CRITICAL" and packet.is_anomaly:
            return "EMERGENCY", (
                f"CRITICAL risk ({risk:.2f}) with anomaly detected "
                f"(score={packet.anomaly_score:.2f}). "
                f"Density={packet.density_count:.0f}, "
                f"congestion={packet.congestion_score:.2f}."
            )

        # EMERGENCY: critical risk even without anomaly
        if level == "CRITICAL":
            return "EMERGENCY", (
                f"CRITICAL risk ({risk:.2f}). "
                f"Density={packet.density_count:.0f}, "
                f"congestion zones={len(packet.congestion_zones)}."
            )

        # DANGER: high risk
        if level == "HIGH":
            reason_parts = [f"HIGH risk ({risk:.2f})"]
            if packet.is_anomaly:
                reason_parts.append(f"anomaly score={packet.anomaly_score:.2f}")
            if packet.congestion_zones:
                reason_parts.append(
                    f"{len(packet.congestion_zones)} congestion zones"
                )
            return "DANGER", ". ".join(reason_parts) + "."

        # WARNING: medium risk
        if level == "MEDIUM":
            return "WARNING", (
                f"MEDIUM risk ({risk:.2f}). "
                f"Density={packet.density_count:.0f}."
            )

        # INFO: if density is noteworthy
        if packet.density_count > 50:
            return "INFO", (
                f"Crowd density notable ({packet.density_count:.0f} persons)."
            )

        # No alert
        return None, None
