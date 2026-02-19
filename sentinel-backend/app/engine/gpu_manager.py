"""
SENTINEL — GPU Manager
Manages CUDA device, streams, VRAM monitoring, model registry, and warm-up.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import structlog
import torch

logger = structlog.get_logger(__name__)


@dataclass
class ModelEntry:
    """Registry entry for a loaded model."""
    name: str
    model: Any
    vram_mb: float = 0.0
    stream: Optional[torch.cuda.Stream] = None
    warm: bool = False


class GPUManager:
    """Centralised GPU resource controller.

    Responsibilities
    ─────────────────
    • Select and lock CUDA device
    • Maintain per-model CUDA streams for parallel compute
    • Track VRAM usage against the 6 GB budget
    • Provide warm-up utility
    • Expose health snapshot
    """

    def __init__(self, device_id: int = 0, vram_limit_mb: int = 5120):
        self.device_id = device_id
        self.vram_limit_mb = vram_limit_mb
        self.device: Optional[torch.device] = None
        self._models: Dict[str, ModelEntry] = {}
        self._lock = asyncio.Lock()

    # ── Lifecycle ────────────────────────────────────────

    async def initialize(self) -> None:
        """Set device, log GPU info, create default stream."""
        if not torch.cuda.is_available():
            logger.warning("gpu.cuda_not_available — falling back to CPU")
            self.device = torch.device("cpu")
            return

        torch.cuda.set_device(self.device_id)
        self.device = torch.device(f"cuda:{self.device_id}")

        props = torch.cuda.get_device_properties(self.device_id)
        total_mem = getattr(props, 'total_memory', getattr(props, 'total_mem', 0))
        logger.info(
            "gpu.initialised",
            name=props.name,
            vram_total_mb=total_mem // (1024 * 1024),
            compute=f"{props.major}.{props.minor}",
        )

    async def shutdown(self) -> None:
        """Release all models and empty cache."""
        async with self._lock:
            for name in list(self._models):
                await self.unload_model(name)
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            logger.info("gpu.shutdown_complete")

    # ── Model Registry ───────────────────────────────────

    async def register_model(
        self,
        name: str,
        model: Any,
        dedicated_stream: bool = True,
    ) -> ModelEntry:
        """Register a model and optionally assign a private CUDA stream."""
        async with self._lock:
            stream = (
                torch.cuda.Stream(device=self.device)
                if dedicated_stream and self.device and self.device.type == "cuda"
                else None
            )
            vram = self._current_vram_mb()
            entry = ModelEntry(
                name=name,
                model=model,
                vram_mb=0.0,
                stream=stream,
            )
            self._models[name] = entry
            after_vram = self._current_vram_mb()
            entry.vram_mb = max(0, after_vram - vram)
            logger.info("gpu.model_registered", model=name, vram_mb=entry.vram_mb)

            if after_vram > self.vram_limit_mb:
                logger.warning(
                    "gpu.vram_over_budget",
                    used=after_vram,
                    limit=self.vram_limit_mb,
                )
            return entry

    async def unload_model(self, name: str) -> None:
        """Remove model from registry and free GPU memory."""
        async with self._lock:
            entry = self._models.pop(name, None)
            if entry:
                del entry.model
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                logger.info("gpu.model_unloaded", model=name)

    def get_model(self, name: str) -> ModelEntry:
        """Retrieve a registered model entry."""
        entry = self._models.get(name)
        if entry is None:
            raise KeyError(f"Model '{name}' not registered")
        return entry

    def get_stream(self, name: str) -> Optional[torch.cuda.Stream]:
        """Get the dedicated CUDA stream for a model."""
        return self._models[name].stream if name in self._models else None

    # ── Warm-up ──────────────────────────────────────────

    async def warmup_model(self, name: str, dummy_input: torch.Tensor, runs: int = 3) -> None:
        """Run N forward passes to warm JIT / TensorRT caches."""
        entry = self.get_model(name)
        model = entry.model
        stream = entry.stream

        for i in range(runs):
            if stream:
                with torch.cuda.stream(stream):
                    with torch.no_grad():
                        _ = model(dummy_input)
            else:
                with torch.no_grad():
                    _ = model(dummy_input)

        if torch.cuda.is_available():
            torch.cuda.synchronize()

        entry.warm = True
        logger.info("gpu.warmup_complete", model=name, runs=runs)

    # ── Health / Status ──────────────────────────────────

    def status(self) -> dict:
        """Return GPU health snapshot for the /gpu-status endpoint."""
        if not torch.cuda.is_available():
            return {"device_id": self.device_id, "available": False}

        props = torch.cuda.get_device_properties(self.device_id)
        mem = torch.cuda.mem_get_info(self.device_id)
        total_mem = getattr(props, 'total_memory', getattr(props, 'total_mem', 0))

        return {
            "device_id": self.device_id,
            "name": props.name,
            "vram_total_mb": total_mem // (1024 * 1024),
            "vram_used_mb": (total_mem - mem[0]) // (1024 * 1024),
            "vram_free_mb": mem[0] // (1024 * 1024),
            "utilization_pct": self._gpu_util(),
            "temperature_c": self._gpu_temp(),
            "models_loaded": [
                {"name": e.name, "vram_mb": e.vram_mb, "warm": e.warm}
                for e in self._models.values()
            ],
        }

    # ── Internal ─────────────────────────────────────────

    def _current_vram_mb(self) -> float:
        if not torch.cuda.is_available():
            return 0.0
        return torch.cuda.memory_allocated(self.device_id) / (1024 * 1024)

    @staticmethod
    def _gpu_util() -> float:
        """Best-effort GPU utilisation via pynvml."""
        try:
            import pynvml
            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
            return float(util.gpu)
        except Exception:
            return -1.0

    @staticmethod
    def _gpu_temp() -> float:
        try:
            import pynvml
            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            return float(pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU))
        except Exception:
            return -1.0
