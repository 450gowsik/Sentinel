"""
SENTINEL — Pipeline Stage Abstract Base Class
Every pipeline phase inherits from PipelineStage.
"""

from __future__ import annotations

import abc
from typing import TYPE_CHECKING, Optional

import structlog

from app.schemas.frame import FramePacket

if TYPE_CHECKING:
    from app.config import Settings
    from app.engine.frame_buffer import FrameBuffer
    from app.engine.gpu_manager import GPUManager
    import redis.asyncio as aioredis

logger = structlog.get_logger(__name__)


class PipelineStage(abc.ABC):
    """Abstract base for every pipeline stage.

    Subclasses must implement:
        name       — unique stage identifier
        process()  — async frame processing logic
    Optionally override:
        setup()    — one-time initialisation (model loading, warmup)
        teardown() — cleanup
        produce()  — for the acquisition stage that generates frames
    """

    def __init__(
        self,
        input_buffer: Optional["FrameBuffer"] = None,
        output_buffer: Optional["FrameBuffer"] = None,
        gpu_manager: Optional["GPUManager"] = None,
        redis: Optional["aioredis.Redis"] = None,
        settings: Optional["Settings"] = None,
    ):
        self.input_buffer = input_buffer
        self.output_buffer = output_buffer
        self.gpu = gpu_manager
        self.redis = redis
        self.settings = settings

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Unique stage identifier, e.g. 'p3_detection'."""
        ...

    async def setup(self) -> None:
        """Called once before the stage loop starts."""
        logger.info("stage.setup", stage=self.name)

    async def teardown(self) -> None:
        """Called when the pipeline is stopping."""
        logger.info("stage.teardown", stage=self.name)

    @abc.abstractmethod
    async def process(self, packet: FramePacket) -> FramePacket:
        """Process a single frame packet. Must return the (mutated) packet."""
        ...

    async def produce(self) -> Optional[FramePacket]:
        """Only used by acquisition stage to generate new frames."""
        return None
