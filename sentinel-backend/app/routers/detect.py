"""
SENTINEL — Upload Detection Router
Accepts image/video uploads and runs YOLOv8n crowd detection pipeline.
Returns annotated image + JSON analysis results.
Stores results in MongoDB.
"""

from __future__ import annotations

import asyncio
import base64
import io
import time
from typing import Optional
from datetime import datetime

import cv2
import numpy as np
import structlog
from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.database.mongodb import mongodb

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/detect", tags=["detect"])

# ── Response schemas ─────────────────────────────────────────

class DetectionBox(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float
    class_name: str = "person"
    track_id: Optional[int] = None


class DetectionResult(BaseModel):
    """Single-frame detection result."""
    frame_idx: int = 0
    person_count: int = 0
    detections: list[DetectionBox] = Field(default_factory=list)
    density_estimate: float = 0.0
    risk_score: float = 0.0
    risk_level: str = "LOW"
    anomaly_score: float = 0.0
    stampede_risk: float = 0.0
    flow_rate: float = 0.0
    congestion_zones: list[dict] = Field(default_factory=list)
    annotated_image_b64: str = ""
    heatmap_b64: str = ""
    inference_time_ms: float = 0.0
    saved_path: str = ""


class VideoDetectionResult(BaseModel):
    """Multi-frame video detection result."""
    total_frames: int = 0
    processed_frames: int = 0
    avg_person_count: float = 0.0
    max_person_count: int = 0
    avg_risk_score: float = 0.0
    peak_risk_score: float = 0.0
    peak_risk_level: str = "LOW"
    frames: list[DetectionResult] = Field(default_factory=list)
    processing_time_ms: float = 0.0
    saved_path: str = ""


# ── Lazy model loader ────────────────────────────────────────

_yolo_model = None


def _get_yolo():
    """Lazy-load YOLOv8n model."""
    global _yolo_model
    if _yolo_model is None:
        try:
            from ultralytics import YOLO
            _yolo_model = YOLO("yolov8n.pt")
            logger.info("detect.yolo_loaded", model="yolov8n.pt")
        except Exception as exc:
            logger.error("detect.yolo_load_failed", error=str(exc))
            raise HTTPException(500, f"Model load failed: {exc}")
    return _yolo_model


# ── Core detection functions ─────────────────────────────────

def _run_detection(frame: np.ndarray, frame_idx: int = 0) -> DetectionResult:
    """Run YOLOv8n on a single frame and return annotated results."""
    t0 = time.time()
    model = _get_yolo()
    h, w = frame.shape[:2]

    # Run inference
    results = model(frame, verbose=False, conf=0.30, iou=0.45)

    detections: list[DetectionBox] = []
    for r in results:
        if r.boxes is None:
            continue
        for box in r.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            cls_name = model.names.get(cls_id, f"class_{cls_id}")
            detections.append(DetectionBox(
                x1=x1, y1=y1, x2=x2, y2=y2,
                confidence=round(conf, 3),
                class_name=cls_name,
            ))

    person_dets = [d for d in detections if d.class_name == "person"]
    person_count = len(person_dets)

    # ── Risk & density estimation ────────────────────────
    density = person_count / max((w * h) / (640 * 480), 0.1)
    risk_score = min(1.0, (person_count / 80) * 0.5 + (density / 5.0) * 0.3 + 0.1)

    if risk_score > 0.8:
        risk_level = "CRITICAL"
    elif risk_score > 0.6:
        risk_level = "HIGH"
    elif risk_score > 0.35:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    stampede_risk = min(100, person_count * 1.2 + density * 8)
    flow_rate = person_count * 2.5 + np.random.uniform(-5, 5)
    anomaly_score = 0.0

    # ── Draw annotations on frame ────────────────────────
    annotated = frame.copy()

    # Draw bounding boxes
    for det in detections:
        color = (0, 229, 255) if det.class_name == "person" else (0, 165, 255)
        if det.confidence < 0.5:
            color = (0, 200, 255)
        elif det.confidence < 0.7:
            color = (0, 200, 83)
        else:
            color = (0, 229, 255)

        pt1 = (int(det.x1), int(det.y1))
        pt2 = (int(det.x2), int(det.y2))
        cv2.rectangle(annotated, pt1, pt2, color, 2)

        # Corner brackets
        bracket_len = min(15, int((det.x2 - det.x1) * 0.3))
        # Top-left
        cv2.line(annotated, pt1, (pt1[0] + bracket_len, pt1[1]), color, 2)
        cv2.line(annotated, pt1, (pt1[0], pt1[1] + bracket_len), color, 2)
        # Top-right
        cv2.line(annotated, (pt2[0], pt1[1]), (pt2[0] - bracket_len, pt1[1]), color, 2)
        cv2.line(annotated, (pt2[0], pt1[1]), (pt2[0], pt1[1] + bracket_len), color, 2)
        # Bottom-left
        cv2.line(annotated, (pt1[0], pt2[1]), (pt1[0] + bracket_len, pt2[1]), color, 2)
        cv2.line(annotated, (pt1[0], pt2[1]), (pt1[0], pt2[1] - bracket_len), color, 2)
        # Bottom-right
        cv2.line(annotated, pt2, (pt2[0] - bracket_len, pt2[1]), color, 2)
        cv2.line(annotated, pt2, (pt2[0], pt2[1] - bracket_len), color, 2)

        # Label
        label = f"{det.class_name} {det.confidence:.0%}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)
        cv2.rectangle(annotated, (pt1[0], pt1[1] - th - 6), (pt1[0] + tw + 4, pt1[1]), color, -1)
        cv2.putText(annotated, label, (pt1[0] + 2, pt1[1] - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1, cv2.LINE_AA)

    # Status overlay
    cv2.putText(annotated, f"SENTINEL AI // Persons: {person_count} // Risk: {risk_level}",
                (10, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 229, 255), 1, cv2.LINE_AA)

    # Encode annotated image
    _, buf = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 92])
    annotated_b64 = base64.b64encode(buf.tobytes()).decode("ascii")

    # ── Generate density heatmap ─────────────────────────
    heatmap = np.zeros((h, w), dtype=np.float32)
    for det in person_dets:
        cx = int((det.x1 + det.x2) / 2)
        cy = int((det.y1 + det.y2) / 2)
        r = int(max(det.x2 - det.x1, det.y2 - det.y1) * 0.8)
        cv2.circle(heatmap, (cx, cy), max(r, 20), 1.0, -1)

    heatmap = cv2.GaussianBlur(heatmap, (0, 0), sigmaX=30)
    if heatmap.max() > 0:
        heatmap = (heatmap / heatmap.max() * 255).astype(np.uint8)
    else:
        heatmap = heatmap.astype(np.uint8)
    heatmap_color = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)

    # Overlay heatmap
    overlay = cv2.addWeighted(frame, 0.6, heatmap_color, 0.4, 0)
    _, hbuf = cv2.imencode(".jpg", overlay, [cv2.IMWRITE_JPEG_QUALITY, 88])
    heatmap_b64 = base64.b64encode(hbuf.tobytes()).decode("ascii")

    inference_ms = (time.time() - t0) * 1000

    # Congestion zones
    grid_size = 3
    cell_h, cell_w = h // grid_size, w // grid_size
    congestion_zones = []
    for gy in range(grid_size):
        for gx in range(grid_size):
            zone_dets = [d for d in person_dets
                         if gx * cell_w <= (d.x1 + d.x2) / 2 < (gx + 1) * cell_w
                         and gy * cell_h <= (d.y1 + d.y2) / 2 < (gy + 1) * cell_h]
            if zone_dets:
                congestion_zones.append({
                    "zone": f"Grid-{gy}-{gx}",
                    "x": gx * cell_w + cell_w // 2,
                    "y": gy * cell_h + cell_h // 2,
                    "count": len(zone_dets),
                    "congestion": min(1.0, len(zone_dets) / 10),
                })

    return DetectionResult(
        frame_idx=frame_idx,
        person_count=person_count,
        detections=detections,
        density_estimate=round(density, 2),
        risk_score=round(risk_score, 3),
        risk_level=risk_level,
        anomaly_score=round(anomaly_score, 3),
        stampede_risk=round(stampede_risk, 1),
        flow_rate=round(max(0, flow_rate), 1),
        congestion_zones=congestion_zones,
        annotated_image_b64=annotated_b64,
        heatmap_b64=heatmap_b64,
        inference_time_ms=round(inference_ms, 1),
    )


# ── Endpoints ────────────────────────────────────────────────

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/bmp"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/avi", "video/x-msvideo", "video/quicktime", "video/webm"}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB


@router.post("/upload", response_model=DetectionResult | VideoDetectionResult)
async def upload_detect(file: UploadFile = File(...)):
    """Upload an image or video for AI crowd detection analysis.

    Supported formats:
    - Images: JPEG, PNG, WebP, BMP
    - Videos: MP4, AVI, MOV, WebM (processed frame-by-frame)
    """
    content_type = file.content_type or ""

    # Read file
    data = await file.read()
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(413, "File too large (max 100 MB)")

    loop = asyncio.get_running_loop()

    # Process and save
    filename = file.filename or "upload"
    result: DetectionResult | VideoDetectionResult
    
    if content_type in ALLOWED_IMAGE_TYPES or filename.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".bmp")):
        result = await _detect_image(data, loop)
    elif content_type in ALLOWED_VIDEO_TYPES or filename.lower().endswith((".mp4", ".avi", ".mov", ".webm")):
        result = await _detect_video(data, loop)
    else:
        raise HTTPException(
            415,
            f"Unsupported type: {content_type}. Use JPEG/PNG images or MP4/AVI videos."
        )

    # Save to disk and MongoDB
    try:
        saved_path = await loop.run_in_executor(None, _save_result, data, result, filename)
        result.saved_path = saved_path
        
        # Save to MongoDB
        await _save_to_mongodb(result, filename, saved_path)
        
    except Exception as exc:
        logger.error("detect.save_failed", error=str(exc))
        # Don't fail the request if save fails, just log it
    
    return result


async def _save_to_mongodb(
    result: DetectionResult | VideoDetectionResult, 
    filename: str,
    saved_path: str
):
    """Save detection result to MongoDB"""
    try:
        collection = mongodb.get_collection("detections")
        
        if isinstance(result, DetectionResult):
            doc = result.model_dump()
            doc["detection_type"] = "image"
            doc["original_filename"] = filename
            doc["annotated_image_path"] = saved_path
            doc["timestamp"] = datetime.utcnow()
            doc["upload_source"] = "api"
            # Remove base64 images from MongoDB (too large)
            doc.pop("annotated_image_b64", None)
            doc.pop("heatmap_b64", None)
            
            insert_result = await collection.insert_one(doc)
            logger.info("mongodb.detection_saved", 
                       id=str(insert_result.inserted_id),
                       type="image")
            
        elif isinstance(result, VideoDetectionResult):
            # Save video summary (without full frame data to keep doc small)
            doc = {
                "detection_type": "video",
                "total_frames": result.total_frames,
                "processed_frames": result.processed_frames,
                "avg_person_count": result.avg_person_count,
                "max_person_count": result.max_person_count,
                "avg_risk_score": result.avg_risk_score,
                "peak_risk_score": result.peak_risk_score,
                "peak_risk_level": result.peak_risk_level,
                "original_filename": filename,
                "video_path": saved_path,
                "processing_time_ms": result.processing_time_ms,
                "timestamp": datetime.utcnow(),
                "upload_source": "api",
                "frames": []
            }
            
            # Store frame summaries (without base64 images)
            for frame in result.frames:
                frame_doc = frame.model_dump()
                frame_doc.pop("annotated_image_b64", None)
                frame_doc.pop("heatmap_b64", None)
                doc["frames"].append(frame_doc)
            
            insert_result = await collection.insert_one(doc)
            logger.info("mongodb.detection_saved", 
                       id=str(insert_result.inserted_id),
                       type="video",
                       frames=len(doc["frames"]))
            
    except Exception as e:
        logger.error("mongodb.save_detection_failed", error=str(e))
        # Don't raise - we still have file system backup


def _save_result(data: bytes, result: DetectionResult | VideoDetectionResult, filename: str) -> str:
    """Save upload, annotation, and metadata to disk."""
    import json
    from datetime import datetime
    from pathlib import Path

    # Setup directories
    date_str = datetime.now().strftime("%Y-%m-%d")
    ts = int(time.time())
    base_dir = Path("data/uploads") / date_str
    base_dir.mkdir(parents=True, exist_ok=True)

    safe_name = Path(filename).stem.replace(" ", "_")
    
    # paths
    json_path = base_dir / f"{ts}_{safe_name}.json"
    
    # Save metdata
    with open(json_path, "w") as f:
        f.write(result.model_dump_json(indent=2))

    # For images, also save the annotated version as a file for easy viewing
    if isinstance(result, DetectionResult) and result.annotated_image_b64:
        img_path = base_dir / f"{ts}_{safe_name}_annotated.jpg"
        img_data = base64.b64decode(result.annotated_image_b64)
        with open(img_path, "wb") as f:
            f.write(img_data)
        return str(img_path.absolute())
    
    return str(json_path.absolute())


async def _process_and_save(file: UploadFile, data: bytes, loop: asyncio.AbstractEventLoop):
    filename = file.filename or "upload"
    content_type = file.content_type or ""

    if content_type in ALLOWED_IMAGE_TYPES or filename.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".bmp")):
        result = await _detect_image(data, loop)
    elif content_type in ALLOWED_VIDEO_TYPES or filename.lower().endswith((".mp4", ".avi", ".mov", ".webm")):
        result = await _detect_video(data, loop)
    else:
        raise HTTPException(415, "Unsupported file type")
    
    # Save to disk
    saved_path = await loop.run_in_executor(None, _save_result, data, result, filename)
    
    # Attach path to result (monkey-patching or wrapping would be better, but we'll add a field to schema)
    # Since we can't easily modify the Pydantic model at runtime without changing the schema definition,
    # we will return a response that includes headers or just rely on the user finding it in the dir.
    # actually, let's update the schema first.
    return result, saved_path



async def _detect_image(data: bytes, loop: asyncio.AbstractEventLoop) -> DetectionResult:
    """Process a single image."""
    arr = np.frombuffer(data, dtype=np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if frame is None:
        raise HTTPException(400, "Could not decode image")

    result = await loop.run_in_executor(None, _run_detection, frame, 0)
    return result


async def _detect_video(data: bytes, loop: asyncio.AbstractEventLoop) -> VideoDetectionResult:
    """Process a video file (sample every Nth frame for speed)."""
    import tempfile
    import os

    t0 = time.time()

    # Write to temp file for OpenCV
    tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
    tmp.write(data)
    tmp.close()

    try:
        cap = cv2.VideoCapture(tmp.name)
        if not cap.isOpened():
            raise HTTPException(400, "Could not open video")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30

        # Sample strategy: process every Nth frame, max 30 frames
        max_sample_frames = 30
        step = max(1, total_frames // max_sample_frames)

        frames_results: list[DetectionResult] = []
        frame_idx = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % step == 0:
                result = await loop.run_in_executor(None, _run_detection, frame, frame_idx)
                frames_results.append(result)

            frame_idx += 1

        cap.release()

    finally:
        os.unlink(tmp.name)

    if not frames_results:
        raise HTTPException(400, "No frames could be processed")

    person_counts = [f.person_count for f in frames_results]
    risk_scores = [f.risk_score for f in frames_results]
    peak_risk = max(risk_scores)

    return VideoDetectionResult(
        total_frames=total_frames,
        processed_frames=len(frames_results),
        avg_person_count=round(sum(person_counts) / len(person_counts), 1),
        max_person_count=max(person_counts),
        avg_risk_score=round(sum(risk_scores) / len(risk_scores), 3),
        peak_risk_score=round(peak_risk, 3),
        peak_risk_level="CRITICAL" if peak_risk > 0.8 else "HIGH" if peak_risk > 0.6 else "MEDIUM" if peak_risk > 0.35 else "LOW",
        frames=frames_results,
        processing_time_ms=round((time.time() - t0) * 1000, 1),
    )
