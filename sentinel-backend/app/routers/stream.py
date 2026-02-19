"""
SENTINEL — WebSocket Stream Router
Streams annotated JPEG frames + JSON metadata to frontend clients.
Non-blocking: never stalls the inference pipeline.
"""

from __future__ import annotations

import asyncio
import time

import orjson
import structlog
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from app.dependencies import get_pipeline_runner
from app.services.metrics_service import ws_connections, ws_frames_sent
from pydantic import BaseModel

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["stream"])


class StreamConfig(BaseModel):
    source: str
    camera_id: str = "cam_0"


@router.post("/api/v1/stream/config")
async def config_stream(config: StreamConfig):
    """Configure the pipeline source (e.g., set IP camera URL)."""
    runner = get_pipeline_runner()
    if runner._running:
        await runner.stop()
        logger.info("stream.config_stop", reason="reconfiguring")

    # Start with new source
    await runner.start(camera_id=config.camera_id, source=config.source)
    logger.info("stream.config_start", source=config.source)
    return {"status": "ok", "source": config.source}


@router.websocket("/ws/stream/{camera_id}")
async def stream_ws(websocket: WebSocket, camera_id: str):
    """Stream annotated frames + metadata over WebSocket.

    Protocol
    ────────
    Each message is a JSON object:
    {
        "type": "frame",
        "camera_id": "cam_0",
        "frame_idx": 123,
        "frame_b64": "<base64 JPEG>",
        "metadata": {
            "person_count": 42,
            "risk_score": 0.73,
            "risk_level": "HIGH",
            "density": 120.5,
            "congestion": 0.65,
            "anomaly": 0.12,
            "latency_ms": 47.2,
            "alert_tier": "DANGER",
            "tracks": 38,
            "fps": 25.0
        }
    }
    """
    await websocket.accept()
    ws_connections.inc()
    logger.info("ws.connected", camera=camera_id, client=websocket.client.host)

    try:
        # Get the pipeline runner (injected at app level)
        runner = get_pipeline_runner()

        # Start pipeline if not running
        if not runner._running:
            source = None  # Will use configured camera URL
            await runner.start(camera_id=camera_id, source=source)

        output_buffer = runner.output_buffer
        frame_count = 0
        fps_time = time.time()

        while True:
            # Non-blocking: get latest frame or wait briefly
            try:
                packet = await output_buffer.get(timeout=0.5)
            except asyncio.TimeoutError:
                # Send keepalive ping
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    break
                continue

            frame_count += 1

            # Calculate real-time FPS
            now = time.time()
            elapsed = now - fps_time
            if elapsed > 0:
                current_fps = frame_count / elapsed
            else:
                current_fps = 0

            # Reset FPS counter every 5 seconds
            if elapsed > 5.0:
                frame_count = 0
                fps_time = now

            # Build message payload
            import base64
            frame_b64 = ""
            if packet.annotated_jpeg:
                frame_b64 = base64.b64encode(packet.annotated_jpeg).decode("ascii")

            message = {
                "type": "frame",
                "camera_id": camera_id,
                "frame_idx": packet.meta.frame_idx,
                "frame_b64": frame_b64,
                "metadata": {
                    "person_count": len(packet.detections),
                    "risk_score": packet.risk_score,
                    "risk_level": packet.risk_level,
                    "density": packet.density_count,
                    "congestion": packet.congestion_score,
                    "anomaly": packet.anomaly_score,
                    "latency_ms": round(packet.total_latency_ms, 1),
                    "alert_tier": packet.alert_tier,
                    "tracks": len(packet.tracks),
                    "fps": round(current_fps, 1),
                    "flow_magnitude": round(packet.flow_magnitude, 2),
                    "pressure": packet.pressure_score,
                    "collisions": packet.collision_points,
                },
            }

            try:
                await websocket.send_text(orjson.dumps(message).decode("utf-8"))
                ws_frames_sent.labels(camera_id=camera_id).inc()
            except Exception:
                break

    except WebSocketDisconnect:
        logger.info("ws.disconnected", camera=camera_id)
    except Exception as exc:
        logger.error("ws.error", camera=camera_id, error=str(exc))
    finally:
        ws_connections.dec()
        logger.info("ws.closed", camera=camera_id)
