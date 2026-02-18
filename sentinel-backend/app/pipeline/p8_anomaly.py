"""
SENTINEL — Phase 8: Anomaly Detection (LSTM Autoencoder)
Detects crowd surge / crush events via reconstruction error.
"""

from __future__ import annotations

import asyncio
from collections import deque
from typing import Optional

import numpy as np
import structlog
import torch
import torch.nn as nn

from app.pipeline.base import PipelineStage
from app.schemas.frame import FramePacket

logger = structlog.get_logger(__name__)

_SEQ_LEN = 30  # sliding window of feature vectors
_FEATURE_DIM = 5  # [person_count, density, flow_mag, avg_velocity, congestion]
_ANOMALY_THRESHOLD = 0.75  # reconstruction error threshold


class _LSTMAutoencoder(nn.Module):
    """LSTM Autoencoder for time-series anomaly detection.

    Encodes a sequence of crowd-state features and reconstructs it.
    High reconstruction error → anomaly (surge/crush).
    ~200 MB VRAM.
    """

    def __init__(self, input_dim=_FEATURE_DIM, hidden_dim=32, num_layers=2):
        super().__init__()
        self.encoder = nn.LSTM(
            input_dim, hidden_dim, num_layers=num_layers, batch_first=True
        )
        self.decoder = nn.LSTM(
            hidden_dim, hidden_dim, num_layers=num_layers, batch_first=True
        )
        self.fc = nn.Linear(hidden_dim, input_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # Encode
        _, (h, c) = self.encoder(x)
        # Decode — repeat last hidden state
        seq_len = x.shape[1]
        decoder_input = h[-1].unsqueeze(1).repeat(1, seq_len, 1)
        decoded, _ = self.decoder(decoder_input, (h, c))
        reconstructed = self.fc(decoded)
        return reconstructed


class AnomalyStage(PipelineStage):
    """Detects anomalous crowd behaviour using reconstruction error."""

    name = "p8_anomaly"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._model: Optional[nn.Module] = None
        self._history: deque = deque(maxlen=_SEQ_LEN)
        self._threshold = _ANOMALY_THRESHOLD

    async def setup(self) -> None:
        await super().setup()
        device = self.gpu.device if self.gpu else torch.device("cpu")

        model = _LSTMAutoencoder().to(device).eval()

        model_path = self.settings.lstm_ae_model_path if self.settings else "models/lstm_ae.pth"
        try:
            from app.config import settings as s
            full_path = s.resolve_model(model_path)
            if full_path.exists():
                state = torch.load(str(full_path), map_location=device)
                model.load_state_dict(state, strict=False)
                logger.info("anomaly.weights_loaded")
        except Exception:
            logger.warning("anomaly.no_weights — using random init")

        self._model = model
        if self.gpu:
            await self.gpu.register_model("lstm_ae", model)
        logger.info("anomaly.ready")

    async def process(self, packet: FramePacket) -> FramePacket:
        """Accumulate features and detect anomalies."""
        # Build feature vector from current packet
        avg_vel = 0.0
        if packet.tracks:
            vels = [
                np.sqrt(t.velocity[0] ** 2 + t.velocity[1] ** 2)
                for t in packet.tracks
            ]
            avg_vel = float(np.mean(vels)) if vels else 0.0

        feature = [
            len(packet.detections),
            packet.density_count,
            packet.flow_magnitude,
            avg_vel,
            packet.congestion_score,
        ]
        self._history.append(feature)

        if len(self._history) < _SEQ_LEN:
            return packet

        if self._model is None:
            return packet

        loop = asyncio.get_running_loop()
        score, is_anomaly = await loop.run_in_executor(None, self._detect)

        packet.anomaly_score = score
        packet.is_anomaly = is_anomaly
        return packet

    def _detect(self) -> tuple[float, bool]:
        """Run LSTM-AE and compute reconstruction error."""
        device = self.gpu.device if self.gpu else torch.device("cpu")

        data = np.array(list(self._history), dtype=np.float32)

        # Normalize
        mean = data.mean(axis=0, keepdims=True) + 1e-8
        std = data.std(axis=0, keepdims=True) + 1e-8
        normalized = (data - mean) / std

        tensor = torch.from_numpy(normalized).unsqueeze(0).to(device)  # (1, seq, feat)

        with torch.no_grad():
            reconstructed = self._model(tensor)

        error = torch.nn.functional.mse_loss(reconstructed, tensor).item()
        is_anomaly = error > self._threshold

        return float(error), is_anomaly
