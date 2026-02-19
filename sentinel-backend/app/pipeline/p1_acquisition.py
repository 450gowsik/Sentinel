"""
SENTINEL — Phase 1: Multi-Modal Data Acquisition
Async video/RTSP/webcam reader producing FramePackets.
"""

from __future__ import annotations

import asyncio
import time
from typing import Optional

import cv2
import numpy as np
import structlog

from app.pipeline.base import PipelineStage
from app.schemas.frame import FrameMetadata, FramePacket
from app.services.camera_manager import camera_manager

logger = structlog.get_logger(__name__)


class AcquisitionStage(PipelineStage):
    """Reads frames from video file, RTSP stream, or webcam.

    This is the only stage that uses `produce()` instead of `process()`.
    It runs a background thread for OpenCV capture to avoid blocking asyncio.
    """

    name = "p1_acquisition"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.source: Optional[str] = None  # set by PipelineRunner
        self.camera_id: str = "cam_0"
        self._frame_idx: int = 0

    async def setup(self) -> None:
        await super().setup()
        self._target_fps = self.settings.target_fps if self.settings else 25
        self._frame_interval = 1.0 / self._target_fps

    async def produce(self) -> Optional[FramePacket]:
        """
        Zero-Latency Production:
        Awaits the next frame signal from CameraManager (Shared Memory).
        No polling, no sleep, no direct cv2 access.
        """
        try:
            # Ensure camera manager is running for this source
            # (Safe to call repeatedly, it's idempotent)
            camera_manager.start_background(self.source or 0)
            
            # 1. AWAIT SIGNAL (Zero Latency)
            # This yields the event loop until the exact moment a frame is ready
            frame = await camera_manager.get_next_frame()
            
            # 2. Process Metadata
            h, w = frame.shape[:2]
            self._frame_idx += 1
            
            packet = FramePacket(
                meta=FrameMetadata(
                    camera_id=self.camera_id,
                    frame_idx=self._frame_idx,
                    timestamp=time.time(),
                    width=w,
                    height=h,
                    fps=self._target_fps,
                ),
                frame=frame, # Shared reference (Zero Copy)
            )
            
            return packet
            
        except Exception as exc:
            logger.error("acquisition.error", error=str(exc))
            await asyncio.sleep(1.0)
            return None

    async def process(self, packet: FramePacket) -> FramePacket:
        """Not used — acquisition is a producer stage."""
        return packet
    async def teardown(self) -> None:
        """Cleanup acquisition resources."""
        await super().teardown()
