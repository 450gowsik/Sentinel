"""
SENTINEL — Phase 3: YOLOv8n Person Detection
TensorRT FP16 primary · Ultralytics PyTorch fallback.
"""

from __future__ import annotations

import asyncio
from typing import Optional

import numpy as np
import structlog
import torch

from app.pipeline.base import PipelineStage
from app.schemas.frame import BoundingBox, FramePacket

logger = structlog.get_logger(__name__)

# Person class id in COCO
_PERSON_CLS = 0
_CONF_THRESH = 0.35
_NMS_THRESH = 0.45


class DetectionStage(PipelineStage):
    """YOLOv8n person detection.

    Loading priority:
        1. TensorRT FP16 engine  (~200 MB VRAM, 50+ FPS on 3050)
        2. Ultralytics PyTorch   (~200 MB VRAM, 12-16 FPS)
    """

    name = "p3_detection"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._model = None
        self._is_trt = False

    async def setup(self) -> None:
        await super().setup()

        trt_path = self.settings.yolo_model_path if self.settings else "models/yolov8n.engine"

        # Try TensorRT relative to setting
        if self.settings and not self.settings.enable_tensorrt:
            logger.info("detection.trt_skipped_by_config")
        else:
            try:
                from app.engine.trt_loader import TRTEngine
                engine = TRTEngine.load(trt_path, device=self.gpu.device_id if self.gpu else 0)
                if engine.ready:
                    self._model = engine
                    self._is_trt = True
                    if self.gpu:
                        await self.gpu.register_model("yolov8n_trt", engine)
                    logger.info("detection.trt_loaded", path=trt_path)
                    return
            except Exception as exc:
                logger.warning("detection.trt_failed", error=str(exc))

        # Fallback: Ultralytics
        try:
            from ultralytics import YOLO
            model = YOLO("yolov8n.pt")
            device = self.gpu.device if self.gpu else "cpu"
            model.to(device)
            self._model = model
            self._is_trt = False
            if self.gpu:
                await self.gpu.register_model("yolov8n_pt", model)
            logger.info("detection.ultralytics_loaded")
        except Exception as exc:
            logger.error("detection.no_model", error=str(exc))

    async def process(self, packet: FramePacket) -> FramePacket:
        """Run detection and populate packet.detections."""
        if self._model is None:
            return packet

        loop = asyncio.get_running_loop()

        if self._is_trt:
            detections = await self._infer_trt(packet)
        else:
            detections = await loop.run_in_executor(None, self._infer_ultralytics, packet)

        packet.detections = detections
        return packet

    # ── TensorRT inference ───────────────────────────────

    async def _infer_trt(self, packet: FramePacket) -> list[BoundingBox]:
        """TensorRT async inference."""
        tensor = packet.preprocessed  # NCHW float32 GPU
        if tensor is None:
            return []

        output = await self._model.infer_async(tensor.half())  # FP16
        return self._parse_yolo_output(output, packet.meta.width, packet.meta.height)

    # ── Ultralytics inference ────────────────────────────

    def _infer_ultralytics(self, packet: FramePacket) -> list[BoundingBox]:
        """Ultralytics PyTorch inference (thread-safe)."""
        frame = packet.frame
        if frame is None:
            return []

        results = self._model(frame, verbose=False, conf=_CONF_THRESH, iou=_NMS_THRESH)

        detections = []
        for r in results:
            if r.boxes is None:
                continue
            for box in r.boxes:
                cls_id = int(box.cls[0])
                if cls_id != _PERSON_CLS:
                    continue
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                conf = float(box.conf[0])
                detections.append(BoundingBox(
                    x1=x1, y1=y1, x2=x2, y2=y2,
                    confidence=conf, class_id=cls_id,
                ))
        return detections

    # ── Output parsing ───────────────────────────────────

    @staticmethod
    def _parse_yolo_output(
        output: torch.Tensor,
        orig_w: int,
        orig_h: int,
    ) -> list[BoundingBox]:
        """Parse raw TRT YOLO output tensor into BoundingBox list."""
        detections = []
        if output is None or output.numel() == 0:
            return detections

        data = output.cpu().float().numpy()

        # YOLOv8 raw output: [batch, 84, num_preds]  (4 box + 80 classes)
        if data.ndim == 3:
            data = data[0].T  # [num_preds, 84]

        for row in data:
            cx, cy, w, h = row[:4]
            class_scores = row[4:]
            cls_id = int(np.argmax(class_scores))
            conf = float(class_scores[cls_id])

            if cls_id != _PERSON_CLS or conf < _CONF_THRESH:
                continue

            # Convert center-wh to xyxy, scale to original
            scale_x = orig_w / 640
            scale_y = orig_h / 640
            x1 = (cx - w / 2) * scale_x
            y1 = (cy - h / 2) * scale_y
            x2 = (cx + w / 2) * scale_x
            y2 = (cy + h / 2) * scale_y

            detections.append(BoundingBox(
                x1=x1, y1=y1, x2=x2, y2=y2,
                confidence=conf, class_id=0,
            ))

        return detections
