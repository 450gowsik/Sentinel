"""
SENTINEL — Phase 4: Multi-Object Tracking (BoTrack / OC-SORT / DeepSORT)
Assigns persistent IDs and tracks trajectories across frames.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

import numpy as np
import structlog

from app.pipeline.base import PipelineStage
from app.schemas.frame import BoundingBox, FramePacket, TrackInfo

logger = structlog.get_logger(__name__)

# Maximum trajectory history per track
_MAX_TRAJECTORY = 60


class TrackingStage(PipelineStage):
    """Lightweight IoU-based tracker (OC-SORT style).

    Drop-in replaceable with BoTrack, ByteTrack, or DeepSORT
    by swapping the _update method.  This implementation uses
    pure-CPU IoU matching — no GPU VRAM required.
    """

    name = "p4_tracking"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._next_id: int = 1
        self._tracks: Dict[int, _TrackState] = {}
        self._max_age: int = 30  # frames before track deletion
        self._iou_threshold: float = 0.3

    async def setup(self) -> None:
        await super().setup()
        logger.info("tracking.ready", method="iou_ocsort", max_age=self._max_age)

    async def process(self, packet: FramePacket) -> FramePacket:
        """Match detections to existing tracks, create new ones."""
        loop = asyncio.get_running_loop()
        tracks = await loop.run_in_executor(
            None, self._update, packet.detections
        )
        packet.tracks = tracks
        return packet

    # ── Core tracker logic ───────────────────────────────

    def _update(self, detections: list[BoundingBox]) -> list[TrackInfo]:
        """Hungarian IoU matching between predictions and detections."""
        det_boxes = np.array(
            [[d.x1, d.y1, d.x2, d.y2] for d in detections], dtype=np.float32
        ) if detections else np.empty((0, 4), dtype=np.float32)

        trk_ids = list(self._tracks.keys())
        trk_boxes = np.array(
            [self._tracks[tid].box for tid in trk_ids], dtype=np.float32
        ) if trk_ids else np.empty((0, 4), dtype=np.float32)

        # IoU matrix
        matched, unmatched_dets, unmatched_trks = self._iou_match(
            det_boxes, trk_boxes, self._iou_threshold
        )

        # Update matched tracks
        for d_idx, t_idx in matched:
            tid = trk_ids[t_idx]
            box = det_boxes[d_idx]
            self._tracks[tid].update(box, detections[d_idx].confidence)

        # Create new tracks for unmatched detections
        for d_idx in unmatched_dets:
            tid = self._next_id
            self._next_id += 1
            box = det_boxes[d_idx]
            self._tracks[tid] = _TrackState(
                track_id=tid,
                box=box.tolist(),
                confidence=detections[d_idx].confidence,
            )

        # Age unmatched tracks
        for t_idx in unmatched_trks:
            tid = trk_ids[t_idx]
            self._tracks[tid].age += 1

        # Remove stale tracks
        stale = [tid for tid, t in self._tracks.items() if t.age > self._max_age]
        for tid in stale:
            del self._tracks[tid]

        # Build output
        results = []
        for tid, t in self._tracks.items():
            center = ((t.box[0] + t.box[2]) / 2, (t.box[1] + t.box[3]) / 2)
            results.append(TrackInfo(
                track_id=tid,
                bbox=BoundingBox(
                    x1=t.box[0], y1=t.box[1], x2=t.box[2], y2=t.box[3],
                    confidence=t.confidence,
                ),
                velocity=t.velocity,
                trajectory=list(t.trajectory[-_MAX_TRAJECTORY:]),
                age=t.total_age,
            ))

        return results

    @staticmethod
    def _iou_match(
        dets: np.ndarray,
        trks: np.ndarray,
        threshold: float,
    ) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
        """Greedy IoU matching (fast, good enough for <200 detections)."""
        if len(dets) == 0:
            return [], [], list(range(len(trks)))
        if len(trks) == 0:
            return [], list(range(len(dets))), []

        iou_matrix = _compute_iou(dets, trks)

        matched = []
        used_dets = set()
        used_trks = set()

        # Greedy: pick highest IoU pairs first
        while True:
            idx = np.unravel_index(np.argmax(iou_matrix), iou_matrix.shape)
            if iou_matrix[idx] < threshold:
                break
            d_idx, t_idx = int(idx[0]), int(idx[1])
            matched.append((d_idx, t_idx))
            used_dets.add(d_idx)
            used_trks.add(t_idx)
            iou_matrix[d_idx, :] = 0
            iou_matrix[:, t_idx] = 0

        unmatched_dets = [i for i in range(len(dets)) if i not in used_dets]
        unmatched_trks = [i for i in range(len(trks)) if i not in used_trks]

        return matched, unmatched_dets, unmatched_trks


class _TrackState:
    """Internal mutable track state."""

    __slots__ = ("track_id", "box", "confidence", "age", "total_age",
                 "trajectory", "velocity", "_prev_center")

    def __init__(self, track_id: int, box: list, confidence: float):
        self.track_id = track_id
        self.box = box
        self.confidence = confidence
        self.age = 0
        self.total_age = 0
        self.trajectory: list[tuple[float, float]] = []
        self.velocity: tuple[float, float] = (0.0, 0.0)
        self._prev_center: Optional[Tuple[float, float]] = None

        cx = (box[0] + box[2]) / 2
        cy = (box[1] + box[3]) / 2
        self.trajectory.append((cx, cy))
        self._prev_center = (cx, cy)

    def update(self, box: np.ndarray, confidence: float) -> None:
        self.box = box.tolist()
        self.confidence = confidence
        self.age = 0
        self.total_age += 1

        cx = (box[0] + box[2]) / 2
        cy = (box[1] + box[3]) / 2

        if self._prev_center:
            self.velocity = (cx - self._prev_center[0], cy - self._prev_center[1])

        self._prev_center = (cx, cy)
        self.trajectory.append((cx, cy))
        if len(self.trajectory) > _MAX_TRAJECTORY:
            self.trajectory = self.trajectory[-_MAX_TRAJECTORY:]


def _compute_iou(boxes_a: np.ndarray, boxes_b: np.ndarray) -> np.ndarray:
    """Vectorised IoU between two sets of [x1, y1, x2, y2] boxes."""
    x1 = np.maximum(boxes_a[:, 0:1], boxes_b[:, 0].T)
    y1 = np.maximum(boxes_a[:, 1:2], boxes_b[:, 1].T)
    x2 = np.minimum(boxes_a[:, 2:3], boxes_b[:, 2].T)
    y2 = np.minimum(boxes_a[:, 3:4], boxes_b[:, 3].T)

    inter = np.maximum(0, x2 - x1) * np.maximum(0, y2 - y1)
    area_a = (boxes_a[:, 2] - boxes_a[:, 0]) * (boxes_a[:, 3] - boxes_a[:, 1])
    area_b = (boxes_b[:, 2] - boxes_b[:, 0]) * (boxes_b[:, 3] - boxes_b[:, 1])
    union = area_a[:, None] + area_b[None, :] - inter

    return inter / (union + 1e-6)
