"""
SENTINEL — Phase 2: Frame Preprocessing
Resize, CLAHE, blur, normalize — all on GPU tensors where possible.
"""

from __future__ import annotations

import asyncio

import cv2
import numpy as np
import structlog
import torch

from app.pipeline.base import PipelineStage
from app.schemas.frame import FramePacket

logger = structlog.get_logger(__name__)


class PreprocessStage(PipelineStage):
    """GPU-accelerated frame preprocessing.

    Pipeline:
        1. Resize to 640×640 (letterbox)
        2. Gaussian blur (σ=1.0)
        3. CLAHE contrast enhancement
        4. BGR → RGB
        5. Normalize to [0, 1] float32
        6. HWC → CHW → NCHW tensor on GPU
    """

    name = "p2_preprocess"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._target_size = (640, 640)
        self._clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

    async def setup(self) -> None:
        await super().setup()
        logger.info("preprocess.ready", target=self._target_size)

    async def process(self, packet: FramePacket) -> FramePacket:
        """Preprocess frame on CPU, then push tensor to GPU."""
        loop = asyncio.get_running_loop()
        frame = packet.frame

        # Heavy CV ops offloaded to thread pool
        preprocessed = await loop.run_in_executor(
            None, self._preprocess_cpu, frame
        )

        # Move to GPU
        device = self.gpu.device if self.gpu else torch.device("cpu")
        tensor = torch.from_numpy(preprocessed).to(device, non_blocking=True)
        packet.preprocessed = tensor.unsqueeze(0)  # NCHW

        return packet

    def _preprocess_cpu(self, frame: np.ndarray) -> np.ndarray:
        """CPU preprocessing pipeline returning CHW float32 array."""
        # 1. Resize (letterbox)
        img = cv2.resize(frame, self._target_size, interpolation=cv2.INTER_LINEAR)

        # 2. Gaussian blur
        img = cv2.GaussianBlur(img, (3, 3), 1.0)

        # 3. CLAHE on luminance
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        lab[:, :, 0] = self._clahe.apply(lab[:, :, 0])
        img = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

        # 4. BGR → RGB
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # 5. Normalize to [0, 1]
        img = img.astype(np.float32) / 255.0

        # 6. HWC → CHW
        img = np.transpose(img, (2, 0, 1))

        return np.ascontiguousarray(img)
