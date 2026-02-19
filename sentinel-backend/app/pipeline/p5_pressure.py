"""
SENTINEL — Phase 5: Pressure Field Estimation (Social Force Model)
Calculates crowd pressure (MPa) and collision forces (N).
"""

from __future__ import annotations

import asyncio
import time
from typing import List, Tuple

import numpy as np
import structlog

from app.pipeline.base import PipelineStage
from app.schemas.frame import FramePacket, TrackInfo

logger = structlog.get_logger(__name__)

# Constants for Social Force Model
_CELL_SIZE = 40  # pixels
_INTERACTION_RADIUS = 60.0  # pixels
_PRESSURE_SENSITIVITY = 0.05
_FORCE_CONSTANT = 100.0

class PressureStage(PipelineStage):
    """Computes spatial pressure and collision events using physical modeling."""

    name = "p5_pressure"

    async def process(self, packet: FramePacket) -> FramePacket:
        if not packet.tracks or not packet.meta.width:
            packet.pressure_score = 0.0
            packet.collision_points = []
            return packet

        loop = asyncio.get_running_loop()
        score, field, collisions = await loop.run_in_executor(
            None, self._calculate_physics, packet
        )

        packet.pressure_score = score
        packet.pressure_field = field
        packet.collision_points = collisions

        return packet

    def _calculate_physics(self, packet: FramePacket) -> Tuple[float, np.ndarray, List[dict]]:
        """
        Implementation of the Helbing-Johansson Pressure Formula:
        P = Density * Velocity_Variance
        """
        width, height = packet.meta.width, packet.meta.height
        
        # 1. Spatial Binning (Grid)
        rows = int(height / _CELL_SIZE) + 1
        cols = int(width / _CELL_SIZE) + 1
        
        # Accumulators for Density (rho) and Velocity
        density_grid = np.zeros((rows, cols), dtype=np.float32)
        velocity_grid = np.zeros((rows, cols, 2), dtype=np.float32) # Sum of velocities
        v_squared_grid = np.zeros((rows, cols), dtype=np.float32)   # Sum of speed squared
        
        tracks = packet.tracks
        collision_points = []
        
        # Constants for SFM repulsion
        A, B = 200.0, 0.08  # Repulsion constants
        
        for i, t in enumerate(tracks):
            pos = np.array(t.bbox.center)
            vel = np.array(t.velocity)
            speed_sq = np.sum(vel**2)
            
            # Boundary check + mapping
            r = min(int(pos[1] / _CELL_SIZE), rows - 1)
            c = min(int(pos[0] / _CELL_SIZE), cols - 1)
            
            # Increment accumulators
            density_grid[r, c] += 1.0
            velocity_grid[r, c] += vel
            v_squared_grid[r, c] += speed_sq
            
            # Pairwise Repulsion Force (SFM)
            for j in range(i + 1, len(tracks)):
                t2 = tracks[j]
                pos2 = np.array(t2.bbox.center)
                dist = np.linalg.norm(pos - pos2) / 100.0 # Normalize distance for exponential
                
                # Helbing Social Force: f = A * exp((r-d)/B)
                force_mag = A * np.exp((0.4 - dist) / B) # 0.4m radius estimate
                
                if force_mag > 50.0:
                    collision_points.append({
                        "x": float((pos[0] + pos2[0]) / 2),
                        "y": float((pos[1] + pos2[1]) / 2),
                        "force": round(float(force_mag), 1),
                        "label": f"SF-{len(collision_points) + 1}"
                    })

        # 2. Compute Macroscopic Pressure Field
        # Var(v) = E[v^2] - (E[v])^2
        # P = Density * Var(v)
        
        # Avoid division by zero
        safe_density = np.where(density_grid > 0, density_grid, 1.0)
        
        avg_v = velocity_grid / safe_density[..., None]
        avg_v_sq = v_squared_grid / safe_density
        
        # Variance of velocity (kinetic temperature)
        v_variance = np.abs(avg_v_sq - np.sum(avg_v**2, axis=-1))
        
        # Pressure P = rho * Var(v)
        pressure_grid = density_grid * v_variance
        
        # Apply Gaussian Smoothing (Spatial correlations)
        from scipy.ndimage import gaussian_filter
        smoothed_pressure = gaussian_filter(pressure_grid, sigma=1.2)
        
        # Global metric (normalized stress)
        avg_pressure = float(np.mean(smoothed_pressure) * _PRESSURE_SENSITIVITY)
        
        return round(avg_pressure, 3), smoothed_pressure, collision_points[:8]
