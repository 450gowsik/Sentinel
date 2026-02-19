"""
SENTINEL — Phase 12: Safe Path Planning
BFS/A* evacuation route planner on grid overlaid on frame.
"""

from __future__ import annotations

import asyncio
import heapq
from typing import List, Tuple

import numpy as np
import structlog

from app.pipeline.base import PipelineStage
from app.schemas.frame import FramePacket

logger = structlog.get_logger(__name__)

_GRID_SIZE = 20  # planning grid cells per axis
_EXIT_POINTS = [
    (0, _GRID_SIZE // 2),          # left exit
    (_GRID_SIZE - 1, _GRID_SIZE // 2),  # right exit
    (_GRID_SIZE // 2, 0),          # top exit
    (_GRID_SIZE // 2, _GRID_SIZE - 1),  # bottom exit
]


class SafePathStage(PipelineStage):
    """Computes evacuation paths from congested zones to exits using A*."""

    name = "p12_safepath"

    async def process(self, packet: FramePacket) -> FramePacket:
        if not packet.congestion_zones:
            return packet

        loop = asyncio.get_running_loop()
        paths = await loop.run_in_executor(None, self._plan, packet)
        packet.safe_paths = paths
        return packet

    def _plan(self, packet: FramePacket) -> list[list[tuple[int, int]]]:
        """Build occupancy grid and run A* from each congested zone to nearest exit."""
        w = packet.meta.width or 640
        h = packet.meta.height or 480
        cell_w = w / _GRID_SIZE
        cell_h = h / _GRID_SIZE

        # Build occupancy grid from tracks
        grid = np.zeros((_GRID_SIZE, _GRID_SIZE), dtype=np.float32)
        for t in packet.tracks:
            cx, cy = t.bbox.center
            col = min(int(cx / cell_w), _GRID_SIZE - 1)
            row = min(int(cy / cell_h), _GRID_SIZE - 1)
            grid[row, col] += 1.0

        # Normalize for cost (high density = high cost)
        max_count = grid.max() if grid.max() > 0 else 1
        cost_grid = grid / max_count

        paths = []
        for zone in packet.congestion_zones:
            start = (zone["row"], zone["col"])
            # Scale to planning grid
            gr = min(int(start[0] * _GRID_SIZE / 4), _GRID_SIZE - 1)
            gc = min(int(start[1] * _GRID_SIZE / 4), _GRID_SIZE - 1)
            start_cell = (gr, gc)

            # Find path to nearest exit
            best_path = None
            best_dist = float("inf")
            for exit_pt in _EXIT_POINTS:
                path = self._astar(cost_grid, start_cell, exit_pt)
                if path and len(path) < best_dist:
                    best_dist = len(path)
                    best_path = path

            if best_path:
                # Convert grid coords to pixel coords
                pixel_path = [
                    (int((c + 0.5) * cell_w), int((r + 0.5) * cell_h))
                    for r, c in best_path
                ]
                paths.append(pixel_path)

        return paths

    @staticmethod
    def _astar(
        cost_grid: np.ndarray,
        start: Tuple[int, int],
        goal: Tuple[int, int],
    ) -> list[tuple[int, int]] | None:
        """A* pathfinding on 2D grid with density-based cost."""
        rows, cols = cost_grid.shape

        def heuristic(a, b):
            return abs(a[0] - b[0]) + abs(a[1] - b[1])

        open_set = [(0, start)]
        came_from = {}
        g_score = {start: 0}

        while open_set:
            _, current = heapq.heappop(open_set)

            if current == goal:
                # Reconstruct path
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.append(start)
                return list(reversed(path))

            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = current[0] + dr, current[1] + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    neighbor = (nr, nc)
                    # Movement cost = 1 + density penalty
                    cost = 1.0 + cost_grid[nr, nc] * 5.0
                    tentative = g_score[current] + cost
                    if tentative < g_score.get(neighbor, float("inf")):
                        came_from[neighbor] = current
                        g_score[neighbor] = tentative
                        f = tentative + heuristic(neighbor, goal)
                        heapq.heappush(open_set, (f, neighbor))

        return None  # no path found
