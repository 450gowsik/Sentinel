"""
SENTINEL — Analytics Router
Live metrics, heatmaps, trajectories, and safe paths.
"""

from __future__ import annotations

import base64
from typing import Optional

import cv2
import numpy as np
from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_pipeline_runner
from app.schemas.analytics import (
    HeatmapResponse,
    LiveMetrics,
    SafePathResponse,
    TrajectoryPoint,
    TrajectoryResponse,
)

router = APIRouter(prefix="/api/v1", tags=["analytics"])


@router.get("/metrics/live", response_model=LiveMetrics)
async def live_metrics(
    camera_id: str = "cam_0",
    runner=Depends(get_pipeline_runner),
):
    """Real-time metrics snapshot from the latest processed frame."""
    output = runner.output_buffer

    # Try to get the latest frame without blocking
    packet = output.get_nowait()
    if packet is None:
        return LiveMetrics(camera_id=camera_id)

    from app.services.alert_service import alert_service
    active = await alert_service.active_count()

    return LiveMetrics(
        camera_id=camera_id,
        fps=packet.meta.fps,
        person_count=len(packet.detections),
        density=packet.density_count,
        avg_flow_magnitude=packet.flow_magnitude,
        risk_score=packet.risk_score,
        risk_level=packet.risk_level,
        congestion_score=packet.congestion_score,
        anomaly_score=packet.anomaly_score,
        pipeline_latency_ms=packet.total_latency_ms,
        active_alerts=active,
    )


@router.get("/heatmap/{camera_id}", response_model=HeatmapResponse)
async def heatmap(
    camera_id: str,
    runner=Depends(get_pipeline_runner),
):
    """Get the latest density heatmap as base64 JPEG."""
    packet = runner.output_buffer.get_nowait()
    if packet is None or packet.density_map is None:
        raise HTTPException(status_code=404, detail="No heatmap available yet")

    # Normalize and colorize
    dmap = packet.density_map
    dmap_norm = (dmap / (dmap.max() + 1e-8) * 255).astype(np.uint8)
    heatmap_color = cv2.applyColorMap(dmap_norm, cv2.COLORMAP_JET)
    heatmap_color = cv2.resize(heatmap_color, (packet.meta.width or 640, packet.meta.height or 480))

    _, jpeg = cv2.imencode(".jpg", heatmap_color, [cv2.IMWRITE_JPEG_QUALITY, 80])
    b64 = base64.b64encode(jpeg.tobytes()).decode("ascii")

    return HeatmapResponse(
        camera_id=camera_id,
        width=packet.meta.width or 640,
        height=packet.meta.height or 480,
        density_count=packet.density_count,
        heatmap_b64=b64,
    )


@router.get("/trajectories", response_model=list[TrajectoryResponse])
async def trajectories(
    camera_id: str = "cam_0",
    runner=Depends(get_pipeline_runner),
):
    """Get current track trajectories + predicted future positions."""
    packet = runner.output_buffer.get_nowait()
    if packet is None:
        return []

    results = []
    for track in packet.tracks:
        points = [
            TrajectoryPoint(x=p[0], y=p[1], t=0)
            for p in track.trajectory
        ]
        predicted_pts = []
        if track.track_id in packet.predicted_positions:
            predicted_pts = [
                TrajectoryPoint(x=p[0], y=p[1], t=0)
                for p in packet.predicted_positions[track.track_id]
            ]
        results.append(TrajectoryResponse(
            track_id=track.track_id,
            camera_id=camera_id,
            points=points,
            predicted=predicted_pts,
        ))

    return results


@router.get("/safepath/{zone_id}", response_model=SafePathResponse)
async def safepath(
    zone_id: str,
    runner=Depends(get_pipeline_runner),
):
    """Get computed evacuation path for a zone."""
    packet = runner.output_buffer.get_nowait()
    if packet is None or not packet.safe_paths:
        raise HTTPException(status_code=404, detail="No safe paths computed yet")

    # Map zone_id to index
    try:
        idx = int(zone_id)
    except ValueError:
        idx = 0

    if idx >= len(packet.safe_paths):
        idx = 0

    path = packet.safe_paths[idx]
    distance = sum(
        np.sqrt((path[i][0] - path[i - 1][0]) ** 2 + (path[i][1] - path[i - 1][1]) ** 2)
        for i in range(1, len(path))
    ) if len(path) > 1 else 0

    return SafePathResponse(
        zone_id=zone_id,
        path=path,
        distance=float(distance),
        estimated_time_s=float(distance / 50),  # assume 50 px/s walk speed
    )
