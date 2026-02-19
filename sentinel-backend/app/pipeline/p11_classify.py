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
        
        # Behavioral metadata extracted in p10_risk
        dir_consistency = packet.stage_latencies.get("behavior_dir_consistency", 1.0)
        vel_variance = packet.stage_latencies.get("behavior_vel_variance", 0.0)
        
        # 1. EMERGENCY: Stampede Risk (Uniform direction, high speed/risk)
        if level in ["CRITICAL", "HIGH"] and dir_consistency > 0.75 and packet.flow_magnitude > 8.0:
            return "EMERGENCY", (
                f"STAMPEDE RISK DETECTED. Uniform movement flow ({dir_consistency:.0%}) "
                f"at high speed. Risk Score: {risk:.2f}."
            )

        # 2. EMERGENCY: Panic Risk (Chaotic direction, high variance, high risk)
        if level in ["CRITICAL", "HIGH"] and dir_consistency < 0.3 and vel_variance > 15.0:
            return "EMERGENCY", (
                f"PANIC / CHAOS DETECTED. Erratic movement patterns "
                f"(variance={vel_variance:.1f}) in random directions. "
                f"Risk Score: {risk:.2f}."
            )

        # 3. EMERGENCY: Critical risk with anomaly
        if level == "CRITICAL" and packet.is_anomaly:
            return "EMERGENCY", (
                f"ANOMALY DETECTED. Critical risk level ({risk:.2f}). "
                f"Potential security or safety incident."
            )

        # 4. EMERGENCY: General Critical
        if level == "CRITICAL":
            return "EMERGENCY", f"CRITICAL safety risk ({risk:.2f}). Density: {packet.density_count:.0f}."

        # 5. DANGER: High risk or physical pressure
        if level == "HIGH" or packet.pressure_score > 0.7:
            reason = f"DANGER: High crowd pressure/risk ({risk:.2f})."
            if packet.pressure_score > 0.7:
                reason = f"PHYSICAL CRUSH RISK. High social force intensity detected."
            return "DANGER", reason

        # 6. WARNING: Medium risk
        if level == "MEDIUM":
            return "WARNING", f"Elevated crowd risk ({risk:.2f}). Monitor flow levels."

        # 7. INFO: Notable density
        if packet.density_count > 40:
            return "INFO", f"High density area ({packet.density_count:.0f} persons)."

        # No alert
        return None, None
