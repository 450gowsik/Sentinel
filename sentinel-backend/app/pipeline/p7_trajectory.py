"""
SENTINEL — Phase 7: Trajectory Prediction (Social-STGCNN style)
Predicts future positions for tracked people using LSTM-based model.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

import numpy as np
import structlog
import torch
import torch.nn as nn

from app.pipeline.base import PipelineStage
from app.schemas.frame import FramePacket

logger = structlog.get_logger(__name__)

# Observation / prediction lengths
_OBS_LEN = 8
_PRED_LEN = 12


class _TrajectoryLSTM(nn.Module):
    """Simplified Social-STGCNN trajectory predictor.

    Input: (batch, obs_len, 2)  — xy positions
    Output: (batch, pred_len, 2) — predicted xy
    ~100 MB VRAM
    """

    def __init__(self, input_dim=2, hidden_dim=64, pred_len=_PRED_LEN):
        super().__init__()
        self.encoder = nn.LSTM(input_dim, hidden_dim, num_layers=1, batch_first=True)
        self.decoder = nn.LSTM(input_dim, hidden_dim, num_layers=1, batch_first=True)
        self.fc = nn.Linear(hidden_dim, input_dim)
        self.pred_len = pred_len

    def forward(self, obs: torch.Tensor) -> torch.Tensor:
        # Encode observed trajectory
        _, (h, c) = self.encoder(obs)

        # Decode predicted trajectory autoregressively
        last_pos = obs[:, -1:, :]  # (batch, 1, 2)
        preds = []
        for _ in range(self.pred_len):
            out, (h, c) = self.decoder(last_pos, (h, c))
            pred = self.fc(out)
            preds.append(pred)
            last_pos = pred
        return torch.cat(preds, dim=1)  # (batch, pred_len, 2)


class TrajectoryStage(PipelineStage):
    """Predicts future trajectories for all active tracks."""

    name = "p7_trajectory"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._model: Optional[nn.Module] = None
        self._frame_count = 0
        self._skip = 5  # predict every N frames

    async def setup(self) -> None:
        await super().setup()
        device = self.gpu.device if self.gpu else torch.device("cpu")

        model = _TrajectoryLSTM().to(device).eval()

        # Load pretrained weights if available
        model_path = self.settings.stgcnn_model_path if self.settings else "models/stgcnn.pth"
        try:
            from app.config import settings as s
            full_path = s.resolve_model(model_path)
            if full_path.exists():
                state = torch.load(str(full_path), map_location=device)
                model.load_state_dict(state, strict=False)
                logger.info("trajectory.weights_loaded", path=str(full_path))
        except Exception:
            logger.warning("trajectory.no_weights — using random init")

        self._model = model
        if self.gpu:
            await self.gpu.register_model("trajectory_lstm", model)
        logger.info("trajectory.ready")

    async def process(self, packet: FramePacket) -> FramePacket:
        """Predict future positions for tracks with enough history."""
        self._frame_count += 1
        if self._frame_count % self._skip != 0:
            return packet

        if not packet.tracks or self._model is None:
            return packet

        loop = asyncio.get_running_loop()
        predictions = await loop.run_in_executor(None, self._predict, packet)
        packet.predicted_positions = predictions
        return packet

    def _predict(self, packet: FramePacket) -> Dict[int, List[Tuple[float, float]]]:
        """Batch predict trajectories for all eligible tracks."""
        device = self.gpu.device if self.gpu else torch.device("cpu")

        eligible = [t for t in packet.tracks if len(t.trajectory) >= _OBS_LEN]
        if not eligible:
            return {}

        # Build batch tensor
        batch = []
        track_ids = []
        for track in eligible:
            obs = track.trajectory[-_OBS_LEN:]
            batch.append(obs)
            track_ids.append(track.track_id)

        tensor = torch.tensor(batch, dtype=torch.float32).to(device)  # (N, obs, 2)

        with torch.no_grad():
            pred = self._model(tensor)  # (N, pred_len, 2)

        predictions = {}
        pred_np = pred.cpu().numpy()
        for i, tid in enumerate(track_ids):
            predictions[tid] = [(float(p[0]), float(p[1])) for p in pred_np[i]]

        return predictions
