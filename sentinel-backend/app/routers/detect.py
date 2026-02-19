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
from fastapi import APIRouter, File, HTTPException, UploadFile, Depends
from pydantic import BaseModel, Field

from app.database.mongodb import mongodb
from app.dependencies import get_pipeline_runner
from app.schemas.frame import FramePacket

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


# Removed local _get_yolo and _run_detection. Using PipelineRunner.

def _map_packet_to_result(packet: FramePacket) -> DetectionResult:
    """Map internal FramePacket to public DetectionResult."""
    # Bounding Boxes
    detections: list[DetectionBox] = []
    for det in packet.detections:
        detections.append(DetectionBox(
            x1=det.x1, y1=det.y1, x2=det.x2, y2=det.y2,
            confidence=round(det.confidence, 3),
            class_name="person" if det.class_id == 0 else f"class_{det.class_id}"
        ))

    # Base64 annotated image
    annotated_b64 = ""
    if packet.annotated_jpeg:
        annotated_b64 = base64.b64encode(packet.annotated_jpeg).decode("ascii")

    # Heatmap Base64 (Using Density Map if available)
    heatmap_b64 = ""
    if packet.density_map is not None:
        try:
            h, w = packet.meta.height, packet.meta.width
            dmap = packet.density_map
            # Normalize and colormap
            if dmap.max() > 0:
                dmap = (dmap / dmap.max() * 255).astype(np.uint8)
            else:
                dmap = dmap.astype(np.uint8)
            dmap_resized = cv2.resize(dmap, (w, h))
            heatmap_color = cv2.applyColorMap(dmap_resized, cv2.COLORMAP_JET)
            
            # Blend with original frame
            overlay = cv2.addWeighted(packet.frame, 0.6, heatmap_color, 0.4, 0)
            _, hbuf = cv2.imencode(".jpg", overlay, [cv2.IMWRITE_JPEG_QUALITY, 85])
            heatmap_b64 = base64.b64encode(hbuf).decode("ascii")
        except Exception as exc:
            logger.warning("detect.heatmap_failed", error=str(exc))

    return DetectionResult(
        frame_idx=packet.meta.frame_idx,
        person_count=len(packet.detections),
        detections=detections,
        density_estimate=round(packet.density_count, 2),
        risk_score=round(packet.risk_score, 3),
        risk_level=packet.risk_level,
        anomaly_score=round(packet.anomaly_score, 3),
        stampede_risk=round(packet.flow_magnitude * 8.0, 1), # Approx from flow
        flow_rate=round(packet.flow_magnitude, 1),
        congestion_zones=packet.congestion_zones,
        annotated_image_b64=annotated_b64,
        heatmap_b64=heatmap_b64,
        inference_time_ms=packet.total_latency_ms,
    )


# ── Endpoints ────────────────────────────────────────────────

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/bmp"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/avi", "video/x-msvideo", "video/quicktime", "video/webm"}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB


@router.post("/upload", response_model=DetectionResult | VideoDetectionResult)
async def upload_detect(
    file: UploadFile = File(...),
    runner=Depends(get_pipeline_runner)
):
    """Upload an image or video for unified 15-stage AI analysis."""
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
        result = await _detect_image(data, runner, loop)
    elif content_type in ALLOWED_VIDEO_TYPES or filename.lower().endswith((".mp4", ".avi", ".mov", ".webm")):
        result = await _detect_video(data, runner, loop)
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



async def _detect_image(data: bytes, runner, loop) -> DetectionResult:
    """Process a single image through full pipeline."""
    arr = np.frombuffer(data, dtype=np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if frame is None:
        raise HTTPException(400, "Could not decode image")

    packet = await runner.process_single_frame(frame)
    return _map_packet_to_result(packet)


async def _detect_video(data: bytes, runner, loop) -> VideoDetectionResult:
    """Process a video file through full pipeline sequence."""
    import tempfile
    import os

    t0 = time.time()
    tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
    tmp.write(data)
    tmp.close()

    try:
        cap = cv2.VideoCapture(tmp.name)
        if not cap.isOpened():
            raise HTTPException(400, "Could not open video")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # Sample frames for processing
        max_sample_frames = 20
        step = max(1, total_frames // max_sample_frames)

        batch_frames = []
        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret: break
            if frame_idx % step == 0:
                batch_frames.append(frame)
            frame_idx += 1
        cap.release()
        
        # Run unified sequence (maintains isolated tracking state)
        packets = await runner.process_video_sequence(batch_frames)
        frames_results = [_map_packet_to_result(p) for p in packets]

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
        avg_person_count=round(sum(person_counts) / len(person_counts), 1) if person_counts else 0,
        max_person_count=max(person_counts) if person_counts else 0,
        avg_risk_score=round(sum(risk_scores) / len(risk_scores), 3) if risk_scores else 0,
        peak_risk_score=round(peak_risk, 3),
        peak_risk_level=frames_results[np.argmax(risk_scores)].risk_level if risk_scores else "LOW",
        frames=frames_results,
        processing_time_ms=round((time.time() - t0) * 1000, 1),
    )
