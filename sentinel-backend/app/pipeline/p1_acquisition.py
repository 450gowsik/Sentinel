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
        self._cap: Optional[cv2.VideoCapture] = None
        self._frame_idx: int = 0
        self._target_fps: int = 25
        self._frame_interval: float = 1.0 / 25
        self._loop = None

    async def setup(self) -> None:
        await super().setup()
        self._target_fps = self.settings.target_fps if self.settings else 25
        self._frame_interval = 1.0 / self._target_fps

    def _open_capture(self) -> cv2.VideoCapture:
        """Open the video source (file path, RTSP URL, or device index).
        
        For integer (webcam) sources on Windows, tries multiple backends:
        CAP_DSHOW → CAP_MSMF → default, to maximize compatibility.
        """
        source = self.source or 0
        is_webcam = str(source).isdigit()
        
        if is_webcam:
            source = int(source)
            # Try multiple backends for Windows webcam compatibility
            backends = [
                (cv2.CAP_DSHOW, "DirectShow"),
                (cv2.CAP_MSMF, "MediaFoundation"),
                (cv2.CAP_ANY, "Default"),
            ]
            cap = None
            for backend, name in backends:
                logger.info("acquisition.trying_backend", backend=name, source=source)
                try:
                    c = cv2.VideoCapture(source, backend)
                    if c.isOpened():
                        ret, frame = c.read()
                        if ret and frame is not None:
                            logger.info("acquisition.backend_ok", backend=name)
                            cap = c
                            break
                    c.release()
                except Exception as exc:
                    logger.warning("acquisition.backend_failed", backend=name, error=str(exc))
            
            if cap is None:
                raise RuntimeError(f"Cannot open webcam {source} with any backend")
        else:
            # IP cameras / RTSP streams / file paths
            cap = cv2.VideoCapture(source)
            if not cap.isOpened():
                raise RuntimeError(f"Cannot open video source: {source}")

        # Optimise buffer for RTSP
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)
        logger.info(
            "acquisition.opened",
            source=str(source),
            width=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            fps=cap.get(cv2.CAP_PROP_FPS),
        )
        return cap

    async def produce(self) -> Optional[FramePacket]:
        """Read a single frame, throttle to target FPS."""
        if self._cap is None:
            try:
                loop = asyncio.get_running_loop()
                self._cap = await loop.run_in_executor(None, self._open_capture)
            except Exception as exc:
                logger.error("acquisition.open_failed", error=str(exc))
                await asyncio.sleep(2.0)
                return None

        loop = asyncio.get_running_loop()

        t0 = time.perf_counter()
        ret, frame = await loop.run_in_executor(None, self._cap.read)

        if not ret or frame is None:
            # End of file or stream lost — attempt reconnect
            logger.warning("acquisition.frame_lost", idx=self._frame_idx)
            self._cap.release()
            self._cap = None
            await asyncio.sleep(1.0)
            return None

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
            frame=frame,
        )

        # Throttle to target FPS
        elapsed = time.perf_counter() - t0
        sleep_time = self._frame_interval - elapsed
        if sleep_time > 0:
            await asyncio.sleep(sleep_time)

        return packet

    async def process(self, packet: FramePacket) -> FramePacket:
        """Not used — acquisition is a producer stage."""
        return packet

    async def teardown(self) -> None:
        if self._cap:
            self._cap.release()
        await super().teardown()
