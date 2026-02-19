"""
SENTINEL — Phase 14: Visualization & Frame Annotation
Renders bounding boxes, tracks, density overlay, risk, and safe paths onto frame.
Encodes final annotated frame as JPEG for WebSocket streaming.
"""

from __future__ import annotations

import asyncio
from typing import Optional

import cv2
import numpy as np
import structlog

from app.pipeline.base import PipelineStage
from app.schemas.frame import FramePacket

logger = structlog.get_logger(__name__)

# Color palette (BGR)
_COLORS = {
    "LOW": (0, 200, 0),        # green
    "MEDIUM": (0, 200, 255),   # orange
    "HIGH": (0, 80, 255),      # red-orange
    "CRITICAL": (0, 0, 255),   # red
    "track": (255, 200, 0),    # cyan
    "path": (0, 255, 128),     # green
    "zone": (0, 0, 200),       # red overlay
}


class VisualizeStage(PipelineStage):
    """Renders annotations and encodes JPEG."""

    name = "p14_visualize"

    async def process(self, packet: FramePacket) -> FramePacket:
        if packet.frame is None:
            return packet

        if not (self.settings and self.settings.enable_visualization):
            # Skip visualization but still encode frame
            _, jpeg = cv2.imencode(".jpg", packet.frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            packet.annotated_jpeg = jpeg.tobytes()
            return packet

        loop = asyncio.get_running_loop()
        jpeg_bytes = await loop.run_in_executor(None, self._render, packet)
        packet.annotated_jpeg = jpeg_bytes

        # Publish metrics to Redis
        if self.redis:
            try:
                import orjson
                metrics = {
                    "camera_id": packet.meta.camera_id,
                    "frame_idx": packet.meta.frame_idx,
                    "person_count": len(packet.detections),
                    "density": packet.density_count,
                    "risk_score": packet.risk_score,
                    "risk_level": packet.risk_level,
                    "congestion": packet.congestion_score,
                    "anomaly": packet.anomaly_score,
                    "latency_ms": packet.total_latency_ms,
                    "stage_latencies": packet.stage_latencies,
                }
                await self.redis.publish("metrics.updated", orjson.dumps(metrics))
            except Exception:
                pass

        return packet

    def _render(self, packet: FramePacket) -> bytes:
        """Draw all overlays onto frame and encode as JPEG."""
        canvas = packet.frame.copy()

        # 1. Draw tracks + bounding boxes
        for track in packet.tracks:
            bb = track.bbox
            color = _COLORS["track"]
            cv2.rectangle(
                canvas,
                (int(bb.x1), int(bb.y1)),
                (int(bb.x2), int(bb.y2)),
                color, 2,
            )
            label = f"ID:{track.track_id}"
            cv2.putText(
                canvas, label,
                (int(bb.x1), int(bb.y1) - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1,
            )
            # Trajectory trail
            if len(track.trajectory) > 1:
                pts = np.array(track.trajectory[-30:], dtype=np.int32)
                cv2.polylines(canvas, [pts], False, color, 1, cv2.LINE_AA)

        # 2. Congestion zones overlay
        overlay = canvas.copy()
        for zone in packet.congestion_zones:
            cv2.rectangle(
                overlay,
                (zone["x1"], zone["y1"]),
                (zone["x2"], zone["y2"]),
                _COLORS["zone"], -1,
            )
        cv2.addWeighted(overlay, 0.25, canvas, 0.75, 0, canvas)

        # 3. Safe paths
        for path in packet.safe_paths:
            if len(path) > 1:
                pts = np.array(path, dtype=np.int32)
                cv2.polylines(canvas, [pts], False, _COLORS["path"], 3, cv2.LINE_AA)
                # Arrow at end
                if len(path) >= 2:
                    cv2.arrowedLine(
                        canvas, path[-2], path[-1],
                        _COLORS["path"], 3, tipLength=0.3,
                    )

        # 4. Status bar
        h, w = canvas.shape[:2]
        bar_h = 40
        cv2.rectangle(canvas, (0, 0), (w, bar_h), (30, 30, 30), -1)

        risk_color = _COLORS.get(packet.risk_level, (255, 255, 255))
        status_text = (
            f"RISK: {packet.risk_level} ({packet.risk_score:.2f}) | "
            f"Persons: {len(packet.detections)} | "
            f"Density: {packet.density_count:.0f} | "
            f"Flow: {packet.flow_magnitude:.1f} | "
            f"Latency: {packet.total_latency_ms:.0f}ms"
        )
        cv2.putText(
            canvas, status_text,
            (10, 28), cv2.FONT_HERSHEY_SIMPLEX,
            0.55, risk_color, 1, cv2.LINE_AA,
        )

        # 5. Social Force Collision Points
        for cp in packet.collision_points:
            cx, cy = int(cp["x"]), int(cp["y"])
            force = cp["force"]
            label = cp["label"]
            
            # Pulsing color based on force
            pulse_color = (0, 0, 255) if force > 150 else (0, 165, 255) # Red for high force, Orange for medium
            
            # Draw cross/target
            size = 8
            cv2.line(canvas, (cx - size, cy), (cx + size, cy), pulse_color, 2)
            cv2.line(canvas, (cx, cy - size), (cx, cy + size), pulse_color, 2)
            cv2.circle(canvas, (cx, cy), size + 2, pulse_color, 1)
            
            # Label
            cv2.putText(
                canvas, f"{label}: {force}N",
                (cx + 10, cy + 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, pulse_color, 1, cv2.LINE_AA
            )

        # 6. Alert badge
        if packet.alert_tier:
            badge_text = f"⚠ {packet.alert_tier}"
            cv2.putText(
                canvas, badge_text,
                (w - 200, 28), cv2.FONT_HERSHEY_SIMPLEX,
                0.7, (0, 0, 255), 2, cv2.LINE_AA,
            )

        # Encode JPEG
        _, jpeg = cv2.imencode(".jpg", canvas, [cv2.IMWRITE_JPEG_QUALITY, 75])
        return jpeg.tobytes()
