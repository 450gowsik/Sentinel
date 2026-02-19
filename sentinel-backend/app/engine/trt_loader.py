"""
SENTINEL — TensorRT Engine Loader
Loads serialised TensorRT engines (FP16) and provides sync/async inference wrappers.
Falls back to PyTorch ONNX Runtime if TRT unavailable.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Optional

import numpy as np
import structlog
import torch

logger = structlog.get_logger(__name__)


class TRTEngine:
    """Wrapper around a deserialised TensorRT engine.

    Usage
    ─────
        engine = TRTEngine.load("models/yolov8n.engine", device=0)
        output = engine.infer(input_tensor)
    """

    def __init__(self):
        self.engine = None
        self.context = None
        self.stream = None
        self.bindings: list = []
        self.binding_shapes: dict = {}
        self.device_id: int = 0
        self._ready = False

    @classmethod
    def load(cls, engine_path: str | Path, device: int = 0) -> "TRTEngine":
        """Deserialise a .engine file. Returns a ready-to-infer wrapper."""
        instance = cls()
        instance.device_id = device
        path = Path(engine_path)

        if not path.exists():
            logger.warning("trt.engine_not_found", path=str(path))
            instance._ready = False
            return instance

        try:
            import tensorrt as trt

            trt_logger = trt.Logger(trt.Logger.WARNING)
            runtime = trt.Runtime(trt_logger)

            with open(path, "rb") as f:
                engine_data = f.read()

            instance.engine = runtime.deserialize_cuda_engine(engine_data)
            instance.context = instance.engine.create_execution_context()
            instance.stream = torch.cuda.Stream(device=torch.device(f"cuda:{device}"))

            # Enumerate I/O bindings
            for i in range(instance.engine.num_io_tensors):
                name = instance.engine.get_tensor_name(i)
                shape = instance.engine.get_tensor_shape(name)
                dtype = trt.nptype(instance.engine.get_tensor_dtype(name))
                instance.bindings.append(name)
                instance.binding_shapes[name] = {"shape": tuple(shape), "dtype": dtype}

            instance._ready = True
            logger.info("trt.engine_loaded", path=str(path), bindings=instance.bindings)

        except ImportError:
            logger.warning("trt.not_installed — TensorRT import failed, engine disabled")
            instance._ready = False
        except Exception as exc:
            logger.error("trt.load_failed", path=str(path), error=str(exc))
            instance._ready = False

        return instance

    @property
    def ready(self) -> bool:
        return self._ready

    def infer(self, input_tensor: torch.Tensor) -> torch.Tensor:
        """Synchronous inference on a CUDA tensor.

        Args:
            input_tensor: NCHW float32/float16 tensor on GPU.

        Returns:
            Output tensor from the engine.
        """
        if not self._ready:
            raise RuntimeError("TRT engine not loaded")

        import tensorrt as trt

        # Allocate output
        out_name = self.bindings[-1]
        out_info = self.binding_shapes[out_name]
        output = torch.empty(
            out_info["shape"],
            dtype=torch.float32,
            device=input_tensor.device,
        )

        # Set tensor addresses
        self.context.set_tensor_address(self.bindings[0], input_tensor.data_ptr())
        self.context.set_tensor_address(out_name, output.data_ptr())

        # Execute
        with torch.cuda.stream(self.stream):
            self.context.execute_async_v3(stream_handle=self.stream.cuda_stream)

        self.stream.synchronize()
        return output

    async def infer_async(self, input_tensor: torch.Tensor) -> torch.Tensor:
        """Non-blocking inference — offloads to thread pool."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.infer, input_tensor)


# ── Convenience loader ───────────────────────────────────────

def load_trt_or_pytorch(
    trt_path: str | Path,
    pytorch_fallback: Any = None,
    device: int = 0,
) -> tuple[Any, bool]:
    """Try loading TensorRT engine; fall back to PyTorch model.

    Returns:
        (model_or_engine, is_trt: bool)
    """
    engine = TRTEngine.load(trt_path, device=device)
    if engine.ready:
        return engine, True
    if pytorch_fallback is not None:
        logger.info("trt.fallback_to_pytorch", path=str(trt_path))
        return pytorch_fallback, False
    raise FileNotFoundError(f"No TRT engine at {trt_path} and no PyTorch fallback provided")
