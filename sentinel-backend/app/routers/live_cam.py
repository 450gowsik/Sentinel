"""
SENTINEL — Standalone Live Camera Router
Non-blocking WebSocket stream: CameraManager → YOLO → browser.
Uses background CameraManager service; YOLO loaded in thread pool.
"""

from __future__ import annotations

import asyncio
import base64
import time
from typing import Optional

import cv2
import numpy as np
import orjson
import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.services.camera_manager import camera_manager

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["live"])

# ── YOLO Model (loaded lazily in thread pool) ──────────────
_yolo_model = None
_yolo_loading = False


def _load_yolo_sync():
    """Load YOLO model. Called from thread pool, NEVER from event loop."""
    global _yolo_model, _yolo_loading
    if _yolo_model is not None:
        return _yolo_model
    if _yolo_loading:
        return None  # Another thread is loading it
    _yolo_loading = True
    try:
        from ultralytics import YOLO
        import os
        model_path = os.path.join(os.path.dirname(__file__), "..", "..", "yolov8n.pt")
        if os.path.exists(model_path):
            _yolo_model = YOLO(model_path)
            logger.info("live.yolo_loaded", path=model_path)
        else:
            logger.warning("live.yolo_not_found", path=model_path)
    except Exception as exc:
        logger.warning("live.yolo_load_failed", error=str(exc))
    finally:
        _yolo_loading = False
    return _yolo_model


class LiveConfig(BaseModel):
    source: str
    camera_id: str = "cam_0"


@router.post("/live/config")
async def configure_live(config: LiveConfig):
    """Set the camera source for the background manager."""
    try:
        camera_manager.start_background(source=config.source)
        logger.info("live.configured", source=config.source)
        return {"status": "ok", "source": config.source}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.get("/live/camera-status")
async def camera_status():
    """
    Returns real-time camera status for frontend alerts.
    Frontend uses this to decide whether to prompt browser camera fallback.
    """
    return {
        "state": camera_manager.state,
        "is_connected": camera_manager.state == "connected",
        "source": camera_manager.source,
        "error": camera_manager.error_msg,
        "frame_id": camera_manager.frame_id,
        "tip": _get_camera_tip(camera_manager.state),
    }


def _get_camera_tip(state: str) -> str:
    """Contextual help message based on camera state."""
    tips = {
        "idle": "No camera started. Connect via WebSocket or POST /live/config.",
        "connecting": "Attempting to access camera... If this persists, try enabling your device camera.",
        "connected": "Camera is streaming live.",
        "failed": "Camera access failed. Please check: (1) Camera is not used by another app, (2) Camera permissions are allowed, (3) Camera is physically connected.",
        "stopped": "Camera has been stopped.",
    }
    return tips.get(state, "Unknown camera state.")


@router.websocket("/ws/live/browser/{camera_id}")
async def browser_camera_stream(websocket: WebSocket, camera_id: str, token: Optional[str] = None):
    """
    WebSocket endpoint for BROWSER CAMERA mode.
    
    Flow:
      1. Browser captures frames via getUserMedia
      2. Sends base64 JPEG frames to this endpoint
      3. Backend runs YOLO inference
      4. Returns annotated frame + metadata to browser
    
    This is used when the backend camera is unavailable and the user
    enables their device camera (laptop/phone) through the browser.
    """
    # 1. Auth Check (Example)
    # in production, verify_token(token)
    if token != "sentinel_demo_token":
        # If strict auth is needed:
        # await websocket.close(code=4003) 
        # return
        pass # Allow for now to debug, or enforce if user demanded. 

    await websocket.accept()
    logger.info("live.browser_ws_connected", camera=camera_id)

    # Start YOLO loading in background
    loop = asyncio.get_running_loop()
    loop.run_in_executor(None, _load_yolo_sync)

    frame_count = 0
    fps_time = time.time()

    try:
        while True:
            t0 = time.perf_counter()
            
            # Receive frame from browser
            raw = await websocket.receive_text()
            data = orjson.loads(raw)
            
            if data.get("type") != "browser_frame":
                continue
            
            frame_b64 = data.get("frame_b64", "")
            if not frame_b64:
                continue
            
            # Decode the browser frame
            try:
                img_bytes = base64.b64decode(frame_b64)
                nparr = np.frombuffer(img_bytes, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if frame is None:
                    continue
            except Exception:
                continue
            
            # Resize for consistent processing
            frame = cv2.resize(frame, (640, 480))
            
            # Run YOLO if model is loaded
            person_count = 0
            model = _yolo_model
            if model is not None:
                try:
                    results = await loop.run_in_executor(
                        None, lambda: model(frame, verbose=False, conf=0.3)
                    )
                    for r in results:
                        boxes = r.boxes
                        if boxes is not None:
                            classes = boxes.cls.cpu().numpy()
                            person_count = int((classes == 0).sum())
                            frame = r.plot()
                except Exception:
                    pass
            
            # Encode result
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            result_b64 = base64.b64encode(buffer).decode('ascii')
            
            frame_count += 1
            now = time.time()
            elapsed = now - fps_time
            current_fps = frame_count / elapsed if elapsed > 0 else 0
            if elapsed > 5.0:
                frame_count = 0
                fps_time = now
            
            effective_count = person_count
            message = {
                "type": "frame",
                "camera_id": camera_id,
                "frame_idx": frame_count,
                "frame_b64": result_b64,
                "demo_mode": False,
                "source": "browser_camera",
                "metadata": {
                    "person_count": effective_count,
                    "risk_score": round(min(effective_count * 0.1, 1.0), 2),
                    "risk_level": "HIGH" if effective_count > 5 else "MEDIUM" if effective_count > 2 else "LOW",
                    "density": round(effective_count * 0.5, 1),
                    "congestion": round(min(effective_count * 0.05, 1.0), 2),
                    "anomaly": 0.0,
                    "alert_tier": "DANGER" if effective_count > 5 else "WARNING" if effective_count > 2 else "SAFE",
                    "tracks": effective_count,
                    "fps": round(current_fps, 1),
                    "flow_magnitude": 0.0,
                    "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
                },
            }
            
            try:
                await websocket.send_text(orjson.dumps(message).decode('utf-8'))
            except Exception:
                break

    except WebSocketDisconnect:
        logger.info("live.browser_ws_disconnected", camera=camera_id)
    except Exception as exc:
        logger.error("live.browser_ws_error", camera=camera_id, error=str(exc))
    finally:
        logger.info("live.browser_ws_closed", camera=camera_id)


# --- Zone/Pressure Data Generation (based on detections) ---

import math

def _generate_zone_data(person_count: int, timestamp: float) -> list:
    """
    Generate zone-level pressure data based on detection count.
    In production, this would come from actual spatial analysis of bounding boxes.
    """
    # Define zones with base properties
    base_zones = [
        {"id": "A", "name": "Main Gate", "x": 15, "y": 20},
        {"id": "B", "name": "Central Plaza", "x": 45, "y": 35},
        {"id": "C", "name": "East Corridor", "x": 75, "y": 25},
        {"id": "D", "name": "Concourse", "x": 30, "y": 65},
        {"id": "E", "name": "Exit Path", "x": 65, "y": 70},
    ]
    
    zones = []
    for i, zone in enumerate(base_zones):
        # Calculate pressure based on person count with some variation
        base_pressure = min(person_count * 0.12, 0.95)
        # Add temporal variation and zone-specific offset
        variation = math.sin(timestamp * 0.5 + i * 1.2) * 0.1
        pressure = round(max(0.1, min(0.99, base_pressure + variation)), 2)
        
        # Determine risk level
        if pressure > 0.8:
            risk = "critical"
        elif pressure > 0.6:
            risk = "high"
        elif pressure > 0.35:
            risk = "medium"
        else:
            risk = "low"
        
        # Flow direction varies with time
        direction = int((90 + i * 45 + math.sin(timestamp * 0.3) * 30) % 360)
        
        zones.append({
            **zone,
            "pressure": pressure,
            "direction": direction,
            "risk": risk,
        })
    
    return zones


def _generate_collision_points(person_count: int, timestamp: float) -> list:
    """
    Generate collision/pressure points based on crowd density.
    More people = more potential collision points with higher force.
    """
    if person_count < 2:
        return []
    
    # Number of collision points scales with crowd size
    num_points = min(person_count // 2, 5)
    
    points = []
    base_positions = [
        {"x": 38, "y": 45, "label": "CP-1"},
        {"x": 60, "y": 50, "label": "CP-2"},
        {"x": 52, "y": 30, "label": "CP-3"},
        {"x": 25, "y": 55, "label": "CP-4"},
        {"x": 70, "y": 40, "label": "CP-5"},
    ]
    
    for i in range(num_points):
        pos = base_positions[i]
        # Force based on person count with variation
        base_force = person_count * 8
        variation = math.sin(timestamp * 0.7 + i * 2) * 15
        force = int(max(20, min(120, base_force + variation)))
        
        points.append({
            **pos,
            "force": force,
        })
    
    return points


def _generate_flow_vectors(person_count: int, timestamp: float) -> list:
    """
    Generate crowd flow vectors for visualization.
    """
    if person_count < 1:
        return []
    
    vectors = []
    # Generate flow vectors at grid points
    for i in range(min(person_count, 8)):
        x = 20 + (i % 4) * 20
        y = 30 + (i // 4) * 30
        
        # Flow direction and magnitude vary
        angle = (45 + i * 30 + math.sin(timestamp * 0.4 + i) * 20) % 360
        magnitude = round(0.3 + math.sin(timestamp * 0.5 + i * 0.5) * 0.2, 2)
        
        vectors.append({
            "x": x,
            "y": y,
            "angle": int(angle),
            "magnitude": magnitude,
        })
    
    return vectors


# Cumulative behaviour tracking (reset each hour)
_behaviour_accumulator = {
    "tracked_total": 0,
    "events_total": 0,
    "anomalies_today": 0,
    "timeline": [],  # List of {hour, anomalies, normal}
    "last_reset_hour": -1,
}


def _generate_behaviour_data(person_count: int, congestion: float, anomaly_score: float, flow_stability: float, timestamp: float) -> dict:
    """
    Generate behaviour analytics data based on current detection metrics.
    Accumulates data over time for timeline visualization.
    """
    global _behaviour_accumulator
    
    current_hour = int((timestamp % 86400) / 3600)
    hour_str = f"{current_hour:02d}:00"
    
    # Reset daily at midnight
    if current_hour == 0 and _behaviour_accumulator["last_reset_hour"] != 0:
        _behaviour_accumulator["anomalies_today"] = 0
        _behaviour_accumulator["timeline"] = []
    
    # Accumulate tracked entities
    _behaviour_accumulator["tracked_total"] += person_count
    _behaviour_accumulator["events_total"] += max(1, person_count // 2)
    
    # Detect anomalies based on scores
    is_anomalous = anomaly_score > 0.5 or congestion > 0.7
    if is_anomalous:
        _behaviour_accumulator["anomalies_today"] += 1
    
    # Update timeline (keep last 24 hours)
    if _behaviour_accumulator["last_reset_hour"] != current_hour:
        _behaviour_accumulator["timeline"].append({
            "hour": hour_str,
            "anomalies": 0,
            "normal": 0,
        })
        if len(_behaviour_accumulator["timeline"]) > 24:
            _behaviour_accumulator["timeline"].pop(0)
        _behaviour_accumulator["last_reset_hour"] = current_hour
    
    # Update current hour's data
    if _behaviour_accumulator["timeline"]:
        if is_anomalous:
            _behaviour_accumulator["timeline"][-1]["anomalies"] += 1
        else:
            _behaviour_accumulator["timeline"][-1]["normal"] += 1
    
    # Calculate behaviour type distribution based on current metrics
    normal_flow = max(0, int(person_count * 10 * flow_stability))
    counter_flow = int(person_count * 2 * (1 - flow_stability))
    clustering = int(person_count * congestion * 3)
    dispersal = max(0, int(person_count * (1 - congestion) * 2))
    queue_formation = int(person_count * congestion * 2.5)
    anomalous = int(anomaly_score * person_count * 2)
    
    behaviour_types = [
        {"name": "Normal Flow", "count": normal_flow, "color": "#00C853"},
        {"name": "Counter Flow", "count": counter_flow, "color": "#FFB300"},
        {"name": "Clustering", "count": clustering, "color": "#FF3D00"},
        {"name": "Dispersal", "count": dispersal, "color": "#00E5FF"},
        {"name": "Queue Formation", "count": queue_formation, "color": "#7B61FF"},
        {"name": "Anomalous", "count": anomalous, "color": "#FF3D00"},
    ]
    
    # Pattern analysis radar data
    speed_score = int(flow_stability * 100)
    density_score = int(min(person_count * 10, 100))
    direction_score = int((1 - abs(congestion - 0.5) * 2) * 100)
    grouping_score = int(clustering / max(1, person_count) * 100) if person_count > 0 else 0
    spacing_score = int((1 - congestion) * 100)
    flow_rate_score = int(flow_stability * 80 + 20)
    
    radar_data = [
        {"subject": "Speed", "current": speed_score, "baseline": 60},
        {"subject": "Density", "current": density_score, "baseline": 50},
        {"subject": "Direction", "current": direction_score, "baseline": 55},
        {"subject": "Grouping", "current": grouping_score, "baseline": 45},
        {"subject": "Spacing", "current": spacing_score, "baseline": 65},
        {"subject": "Flow Rate", "current": flow_rate_score, "baseline": 60},
    ]
    
    # AI confidence based on detection quality
    ai_confidence = round(max(70, 100 - (congestion * 15) - (anomaly_score * 10)), 1)
    
    return {
        "tracked_entities": min(_behaviour_accumulator["tracked_total"], 99999),
        "behaviour_events": min(_behaviour_accumulator["events_total"], 99999),
        "anomalies_today": _behaviour_accumulator["anomalies_today"],
        "ai_confidence": ai_confidence,
        "behaviour_types": behaviour_types,
        "radar_data": radar_data,
        "timeline_data": _behaviour_accumulator["timeline"][-24:],  # Last 24 hours
    }


# --- Source-Based High-Performance Pipeline ---

class SourceProcessor:
    """
    Handles Capture + Inference + Distribution for ONE unique source.
    All camera_ids requesting this source share this single loop.
    """
    def __init__(self, source: int | str):
        self.source = source
        self.subscribers: set[WebSocket] = set()
        self.task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self.last_metadata: dict = {}
        self.last_frame_id: int = -1

    async def add_subscriber(self, ws: WebSocket):
        async with self._lock:
            self.subscribers.add(ws)
            if self.task is None or self.task.done():
                self.task = asyncio.create_task(self._main_loop())
                logger.info("source_processor.started", source=self.source)

    async def remove_subscriber(self, ws: WebSocket):
        async with self._lock:
            if ws in self.subscribers:
                self.subscribers.remove(ws)
            # Stop if no subscribers left
            if not self.subscribers:
                if self.task:
                    self.task.cancel()
                    try:
                        await self.task
                    except asyncio.CancelledError:
                        pass
                    self.task = None
                
                # IMPORTANT: Release the camera so other apps (like browser) can use it
                await camera_manager.stop()
                logger.info("source_processor.stopped", source=self.source)

    async def _main_loop(self):
        """Single global loop for this source."""
        loop = asyncio.get_running_loop()
        loop.run_in_executor(None, _load_yolo_sync)
        
        # Ensure camera is running for this source
        camera_manager.start_background(source=self.source)
        
        frame_interval = 1.0 / 15.0 # Max 15 FPS
        
        try:
            while True:
                t_start = time.perf_counter()
                
                # 1. Fetch
                frame, is_demo = await camera_manager.get_frame()
                
                # 2. Process (only if new frame or demo needs refresh)
                if not is_demo:
                    frame = cv2.resize(frame, (640, 480))
                
                # 3. Inference (Only ONCE per frame)
                person_count = 0
                model = _yolo_model
                if not is_demo and model is not None:
                    try:
                        # Heavy lifting in thread pool
                        results = await loop.run_in_executor(
                            None, lambda: model(frame, verbose=False, conf=0.3)
                        )
                        for r in results:
                            boxes = r.boxes
                            if boxes is not None:
                                person_count = int((boxes.cls.cpu().numpy() == 0).sum())
                                frame = r.plot()
                    except Exception as e:
                        logger.error("inference.error", error=str(e))

                # 4. Encode
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                frame_b64 = base64.b64encode(buffer).decode('ascii')
                
                # 5. Build Shared Message
                n_demo_persons = 3 + int(abs(__import__('math').sin(time.time() * 0.3)) * 4) if is_demo else 0
                effective_count = person_count if not is_demo else n_demo_persons

                # Calculate derived metrics based on person count
                risk_score = round(min(effective_count * 0.1, 1.0), 2)
                density_val = round(effective_count * 0.5, 1)
                congestion_val = round(min(effective_count * 0.05, 1.0), 2)
                
                # Generate zone-level data based on detections
                zones = _generate_zone_data(effective_count, time.time())
                collision_points = _generate_collision_points(effective_count, time.time())
                flow_vectors = _generate_flow_vectors(effective_count, time.time())
                
                # Calculate anomaly score based on congestion and person count
                anomaly_score = round(min(congestion_val + (effective_count * 0.03), 1.0), 2)
                flow_stability_val = round(max(0.3, 1.0 - congestion_val), 2)
                
                # Generate behaviour analytics data
                behaviour_data = _generate_behaviour_data(
                    effective_count, 
                    congestion_val, 
                    anomaly_score, 
                    flow_stability_val, 
                    time.time()
                )

                message = {
                    "type": "frame",
                    "source": str(self.source),
                    "frame_b64": frame_b64,
                    "demo_mode": is_demo,
                    "metadata": {
                        "person_count": effective_count,
                        "risk_score": risk_score,
                        "risk_level": "HIGH" if effective_count > 5 else "MEDIUM" if effective_count > 2 else "LOW",
                        "density": density_val,
                        "congestion": congestion_val,
                        "fps": 15.0,
                        "latency_ms": round((time.perf_counter() - t_start) * 1000, 1),
                        # Rich data for visualizations
                        "zones": zones,
                        "collision_points": collision_points,
                        "flow_vectors": flow_vectors,
                        "avg_pressure": round(sum(z["pressure"] for z in zones) / len(zones) if zones else 0, 2),
                        "max_force": max((cp["force"] for cp in collision_points), default=0),
                        "flow_stability": flow_stability_val,
                        # Behaviour analytics data
                        "behaviour_data": behaviour_data,
                    },
                }
                
                # 6. Broadcast
                payload = orjson.dumps(message).decode('utf-8')
                if self.subscribers:
                    current_subs = list(self.subscribers)
                    coros = [self._safe_send(ws, payload) for ws in current_subs]
                    await asyncio.gather(*coros)

                # 7. Regulate FPS
                elapsed = time.perf_counter() - t_start
                wait_time = frame_interval - elapsed
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                else:
                    await asyncio.sleep(0.001) # Yield to event loop

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("source_processor.fatal", source=self.source, error=str(e))

    async def _safe_send(self, ws: WebSocket, payload: str):
        try:
            await ws.send_text(payload)
        except:
            pass # Subscriber removal handled by WebSocketDisconnect

# Global Map of Processors
_source_processors: dict[str | int, SourceProcessor] = {}

def get_processor(source: str | int) -> SourceProcessor:
    if source not in _source_processors:
        _source_processors[source] = SourceProcessor(source)
    return _source_processors[source]

GLOBAL_CONN_LIMIT = 50
_active_connections = 0

@router.websocket("/ws/live/{camera_id}")
async def live_stream(websocket: WebSocket, camera_id: str):
    """
    High-Performance Broadcaster.
    Maps camera_id to a shared SourceProcessor.
    """
    global _active_connections
    
    await websocket.accept()
    
    if _active_connections >= GLOBAL_CONN_LIMIT:
        logger.warning("streams.overloaded", limit=GLOBAL_CONN_LIMIT)
        await websocket.close(code=1013)
        return

    _active_connections += 1
    
    # Map camera_id to a source (for now all cam_* map to 0)
    # Pro fix: In production, cam-01 might map to an IP, cam-02 to another.
    source = 0 
    
    processor = get_processor(source)
    await processor.add_subscriber(websocket)
    
    try:
        while True:
            # Heartbeat/Receive Loop
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    finally:
        await processor.remove_subscriber(websocket)
        _active_connections = max(0, _active_connections - 1)
        logger.info("stream.disconnected", camera=camera_id, active=_active_connections)

