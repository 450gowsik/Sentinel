"""
SENTINEL — Phase 5: Optical Flow (RAFT-Small)
Computes dense motion fields between consecutive frames.
"""

from __future__ import annotations

import asyncio
from typing import Optional

import cv2
import numpy as np
import structlog
import torch

from app.pipeline.base import PipelineStage
from app.schemas.frame import FramePacket

logger = structlog.get_logger(__name__)


class OpticalFlowStage(PipelineStage):
    """Dense optical flow using RAFT-Small (GPU) with Farneback CPU fallback.

    RAFT-Small: ~250 MB VRAM, ~25 FPS at 720p
    Farneback:  0 VRAM, ~15 FPS at 720p (fallback)

    Frame-skip applied for heavy models via settings.frame_skip_heavy.
    """

    name = "p5_optical_flow"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._model = None
        self._use_raft = False
        self._prev_gray: Optional[np.ndarray] = None
        self._frame_count = 0
        self._skip_interval = 3

    async def setup(self) -> None:
        await super().setup()
        self._skip_interval = self.settings.frame_skip_heavy if self.settings else 3

        # Try RAFT-Small
        try:
            from torchvision.models.optical_flow import raft_small, Raft_Small_Weights
            weights = Raft_Small_Weights.DEFAULT
            model = raft_small(weights=weights)
            device = self.gpu.device if self.gpu else torch.device("cpu")
            model = model.to(device).eval()

            # torch.compile for extra speed (disabled for stability on Windows)
            # try:
            #     model = torch.compile(model, mode="reduce-overhead")
            #     logger.info("optical_flow.torch_compiled")
            # except Exception:
            #     pass

            self._model = model
            self._use_raft = True
            if self.gpu:
                await self.gpu.register_model("raft_small", model)
            logger.info("optical_flow.raft_loaded")
        except Exception as exc:
            logger.warning("optical_flow.raft_failed, using farneback", error=str(exc))
            self._use_raft = False

    async def process(self, packet: FramePacket) -> FramePacket:
        """Compute flow magnitude, optionally skipping frames."""
        self._frame_count += 1

        # Frame skip for heavy models
        if self._frame_count % self._skip_interval != 0:
            return packet

        frame = packet.frame
        if frame is None:
            return packet

        loop = asyncio.get_running_loop()

        if self._use_raft:
            mag = await self._raft_flow(frame)
        else:
            mag = await loop.run_in_executor(None, self._farneback_flow, frame)

        packet.flow_magnitude = float(mag)
        return packet

    async def _raft_flow(self, frame: np.ndarray) -> float:
        """RAFT-Small GPU inference."""
        device = self.gpu.device if self.gpu else torch.device("cpu")

        # Convert to tensor
        img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, (520, 360))  # RAFT input size
        tensor = torch.from_numpy(img).permute(2, 0, 1).float().unsqueeze(0).to(device)

        if self._prev_gray is None:
            self._prev_gray = tensor
            return 0.0

        prev_tensor = self._prev_gray

        stream = self.gpu.get_stream("raft_small") if self.gpu else None

        with torch.no_grad():
            if stream:
                with torch.cuda.stream(stream):
                    flow = self._model(prev_tensor, tensor)[-1]
            else:
                flow = self._model(prev_tensor, tensor)[-1]

        self._prev_gray = tensor

        # Flow magnitude
        flow_np = flow[0].cpu().numpy()
        mag = np.sqrt(flow_np[0] ** 2 + flow_np[1] ** 2).mean()
        return float(mag)

    def _farneback_flow(self, frame: np.ndarray) -> float:
        """CPU Farneback optical flow fallback."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, (320, 240))

        if self._prev_gray is None:
            self._prev_gray = gray
            return 0.0

        flow = cv2.calcOpticalFlowFarneback(
            self._prev_gray, gray, None,
            pyr_scale=0.5, levels=3, winsize=15,
            iterations=3, poly_n=5, poly_sigma=1.2, flags=0,
        )
        self._prev_gray = gray

        mag = np.sqrt(flow[..., 0] ** 2 + flow[..., 1] ** 2).mean()
        return float(mag)
