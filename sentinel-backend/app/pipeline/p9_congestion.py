"""
SENTINEL — Phase 9: Congestion Analysis
Grid-based flow detection and jam identification.
"""

from __future__ import annotations

import asyncio
from typing import List

import numpy as np
import structlog

from app.pipeline.base import PipelineStage
from app.schemas.frame import FramePacket

logger = structlog.get_logger(__name__)

_GRID_ROWS = 4
_GRID_COLS = 4
_CONGESTION_THRESH = 0.6


class CongestionStage(PipelineStage):
    """Divides the frame into a grid and scores congestion per cell.

    Congestion signals:
    ──────────────────
    • High person density per cell
    • Low average velocity (people stuck)
    • High flow magnitude (turbulent movement)
    """

    name = "p9_congestion"

    async def process(self, packet: FramePacket) -> FramePacket:
        loop = asyncio.get_running_loop()
        score, zones = await loop.run_in_executor(None, self._analyze, packet)
        packet.congestion_score = score
        packet.congestion_zones = zones
        return packet

    def _analyze(self, packet: FramePacket) -> tuple[float, list[dict]]:
        w = packet.meta.width or 640
        h = packet.meta.height or 480
        cell_w = w / _GRID_COLS
        cell_h = h / _GRID_ROWS

        # Count persons per cell
        grid_count = np.zeros((_GRID_ROWS, _GRID_COLS), dtype=np.float32)
        grid_vel = np.zeros((_GRID_ROWS, _GRID_COLS), dtype=np.float32)
        grid_vel_n = np.zeros((_GRID_ROWS, _GRID_COLS), dtype=np.float32)

        for t in packet.tracks:
            cx, cy = t.bbox.center
            col = min(int(cx / cell_w), _GRID_COLS - 1)
            row = min(int(cy / cell_h), _GRID_ROWS - 1)
            grid_count[row, col] += 1
            speed = np.sqrt(t.velocity[0] ** 2 + t.velocity[1] ** 2)
            grid_vel[row, col] += speed
            grid_vel_n[row, col] += 1

        # Average velocity per cell
        mask = grid_vel_n > 0
        avg_vel = np.zeros_like(grid_vel)
        avg_vel[mask] = grid_vel[mask] / grid_vel_n[mask]

        # Normalise count (0-1)
        max_count = grid_count.max() if grid_count.max() > 0 else 1
        norm_count = grid_count / max_count

        # Congestion score: high density + low velocity
        max_vel = avg_vel.max() if avg_vel.max() > 0 else 1
        norm_vel = avg_vel / max_vel
        congestion_grid = norm_count * (1 - norm_vel * 0.5)

        overall = float(congestion_grid.mean())

        # Identify congested zones
        zones = []
        for r in range(_GRID_ROWS):
            for c in range(_GRID_COLS):
                if congestion_grid[r, c] > _CONGESTION_THRESH:
                    zones.append({
                        "row": r,
                        "col": c,
                        "score": float(congestion_grid[r, c]),
                        "person_count": int(grid_count[r, c]),
                        "avg_velocity": float(avg_vel[r, c]),
                        "x1": int(c * cell_w),
                        "y1": int(r * cell_h),
                        "x2": int((c + 1) * cell_w),
                        "y2": int((r + 1) * cell_h),
                    })

        return overall, zones
