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
    (0.85, "CRITICAL"),
    (0.65, "HIGH"),
    (0.40, "MEDIUM"),
    (0.00, "LOW"),
]


class RiskStage(PipelineStage):
    """Computes a composite risk score from upstream signals including behavior."""

    name = "p10_risk"

    async def process(self, packet: FramePacket) -> FramePacket:
        # Normalize each signal to [0, 1]
        density_norm = min(1.0, packet.density_count / 150) if packet.density_count > 0 else 0.0
        congestion_norm = min(1.0, packet.congestion_score)
        flow_norm = min(1.0, packet.flow_magnitude / 15.0) if packet.flow_magnitude > 0 else 0.0
        anomaly_norm = min(1.0, packet.anomaly_score / 2.0) if packet.anomaly_score > 0 else 0.0
        pressure_norm = min(1.0, packet.pressure_score / 2.0) if packet.pressure_score > 0 else 0.0

        # Behavioral Signals
        avg_vel = 0.0
        dir_consistency = 1.0  # 1.0 = all same direction, 0.0 = total chaos
        speed_variance = 0.0
        
        if packet.tracks:
            import numpy as np
            # Velocity vectors
            vels = np.array([t.velocity for t in packet.tracks]) # [N, 2]
            speeds = np.linalg.norm(vels, axis=1)
            avg_vel = float(np.mean(speeds))
            speed_variance = float(np.var(speeds))
            
            # Direction Consistency (Cosine similarity of headings)
            headings = vels / (speeds[:, None] + 1e-6)
            avg_heading = np.mean(headings, axis=0)
            dir_consistency = float(np.linalg.norm(avg_heading)) # ||mean(unit_vectors)||
            
        vel_norm = min(1.0, avg_vel / 25.0)
        var_norm = min(1.0, speed_variance / 50.0)
        
        # Weighted composite
        score = (
            _WEIGHTS["density"] * density_norm
            + _WEIGHTS["congestion"] * congestion_norm
            + _WEIGHTS["flow"] * flow_norm
            + _WEIGHTS["anomaly"] * anomaly_norm
            + _WEIGHTS["velocity"] * vel_norm
        )
        
        # Adjust score based on behavioral factors
        # Panic boost: High speed variance + chaotic directions
        panic_factor = var_norm * (1.0 - dir_consistency)
        score += panic_factor * 0.15
        
        # Stampede boost: High speed + high consistency
        stampede_factor = vel_norm * dir_consistency
        if vel_norm > 0.4 and dir_consistency > 0.7:
             score += stampede_factor * 0.20

        # Boost if pressure is high (Physical Crush)
        score += pressure_norm * 0.10

        # Enforce bounds
        score = min(1.0, max(0.0, score))

        # Determine level
        level = "LOW"
        for threshold, label in _LEVELS:
            if score >= threshold:
                level = label
                break

        packet.risk_score = round(score, 4)
        packet.risk_level = level
        
        # Store behavioral metadata for p11_classify
        packet.stage_latencies["behavior_dir_consistency"] = dir_consistency
        packet.stage_latencies["behavior_vel_variance"] = speed_variance

        return packet
