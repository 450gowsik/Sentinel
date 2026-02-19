"""
SENTINEL — Async Pipeline Runner (DAG Orchestrator)
Wires 14 pipeline stages as independent coroutines connected by FrameBuffers.
"""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Dict, List, Optional

import structlog

from app.engine.frame_buffer import FrameBuffer
from app.schemas.frame import FramePacket

if TYPE_CHECKING:
    from app.config import Settings
    from app.engine.gpu_manager import GPUManager
    import redis.asyncio as aioredis

logger = structlog.get_logger(__name__)


class PipelineRunner:
    """Orchestrates the 14-stage AI pipeline as an async DAG.

    Architecture
    ────────────
    Each stage is an independent asyncio.Task consuming from an input
    FrameBuffer and producing to an output FrameBuffer:

        [Acquire] → buf → [Preprocess] → buf → [Detect] → ... → [Visualize]

    Back-pressure is handled by the FrameBuffer drop policy.
    Per-stage latency is recorded inside FramePacket.stage_latencies.
    """

    def __init__(
        self,
        gpu_manager: "GPUManager",
        redis: "aioredis.Redis",
        settings: "Settings",
    ):
        self.gpu = gpu_manager
        self.redis = redis
        self.settings = settings

        self._stages: List = []
        self._buffers: Dict[str, FrameBuffer] = {}
        self._tasks: List[asyncio.Task] = []
        self._running = False

    # ── Build ────────────────────────────────────────────

    async def build(self) -> None:
        """Instantiate all stages and inter-stage buffers."""
        from app.pipeline.p1_acquisition import AcquisitionStage
        from app.pipeline.p2_preprocess import PreprocessStage
        from app.pipeline.p3_detection import DetectionStage
        from app.pipeline.p4_tracking import TrackingStage
        from app.pipeline.p5_optical_flow import OpticalFlowStage
        from app.pipeline.p5_pressure import PressureStage
        from app.pipeline.p6_density import DensityStage
        from app.pipeline.p7_trajectory import TrajectoryStage
        from app.pipeline.p8_anomaly import AnomalyStage
        from app.pipeline.p9_congestion import CongestionStage
        from app.pipeline.p10_risk import RiskStage
        from app.pipeline.p11_classify import ClassifyStage
        from app.pipeline.p12_safepath import SafePathStage
        from app.pipeline.p13_alert_gen import AlertGenStage
        from app.pipeline.p14_visualize import VisualizeStage
        from app.pipeline.p15_persistence import PersistenceStage

        q = self.settings.max_queue_size

        # Create named buffers between stages
        buffer_names = [
            "acq→pre", "pre→det", "det→trk", "trk→flow",
            "flow→pres", "pres→den", "den→traj", "traj→anom", "anom→cong",
            "cong→risk", "risk→cls", "cls→path", "path→alert",
            "alert→viz", "viz→pers", "pers→out",
        ]
        for name in buffer_names:
            self._buffers[name] = FrameBuffer(name=name, maxsize=q)

        # Instantiate stages (each gets input_buf, output_buf)
        stage_defs = [
            (AcquisitionStage,  None,            "acq→pre"),
            (PreprocessStage,   "acq→pre",       "pre→det"),
            (DetectionStage,    "pre→det",       "det→trk"),
            (TrackingStage,     "det→trk",       "trk→flow"),
            (OpticalFlowStage,  "trk→flow",      "flow→pres"),
            (PressureStage,     "flow→pres",     "pres→den"),
            (DensityStage,      "pres→den",      "den→traj"),
            (TrajectoryStage,   "den→traj",      "traj→anom"),
            (AnomalyStage,      "traj→anom",     "anom→cong"),
            (CongestionStage,   "anom→cong",     "cong→risk"),
            (RiskStage,         "cong→risk",     "risk→cls"),
            (ClassifyStage,     "risk→cls",      "cls→path"),
            (SafePathStage,     "cls→path",      "path→alert"),
            (AlertGenStage,     "path→alert",    "alert→viz"),
            (VisualizeStage,    "alert→viz",     "viz→pers"),
            (PersistenceStage,  "viz→pers",      "pers→out"),
        ]

        for cls, in_name, out_name in stage_defs:
            in_buf = self._buffers.get(in_name) if in_name else None
            out_buf = self._buffers[out_name]
            stage = cls(
                input_buffer=in_buf,
                output_buffer=out_buf,
                gpu_manager=self.gpu,
                redis=self.redis,
                settings=self.settings,
            )
            await stage.setup()
            self._stages.append(stage)

        logger.info("pipeline.built", stages=len(self._stages))

    @property
    def stage_count(self) -> int:
        return len(self._stages)

    # ── Run / Stop ───────────────────────────────────────

    async def start(self, camera_id: str = "cam_0", source: str | None = None) -> None:
        """Launch all stage coroutines as background tasks."""
        if self._running:
            logger.warning("pipeline.already_running")
            return

        self._running = True

        # Pass camera source to acquisition stage
        if source and self._stages:
            self._stages[0].source = source
            self._stages[0].camera_id = camera_id

        for stage in self._stages:
            task = asyncio.create_task(
                self._run_stage(stage),
                name=f"stage-{stage.name}",
            )
            self._tasks.append(task)

        logger.info("pipeline.started", camera=camera_id, tasks=len(self._tasks))

    async def stop(self) -> None:
        """Cancel all stage tasks and drain buffers."""
        self._running = False

        for task in self._tasks:
            task.cancel()

        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

        for buf in self._buffers.values():
            await buf.clear()

        logger.info("pipeline.stopped")

    # ── Stage Runner ─────────────────────────────────────

    async def _run_stage(self, stage) -> None:
        """Infinite loop: pull from input → process → push to output."""
        name = stage.name
        logger.info("stage.started", stage=name)

        try:
            while self._running:
                # Acquisition stage generates frames internally
                if stage.input_buffer is None:
                    packet = await stage.produce()
                    if packet is None:
                        await asyncio.sleep(0.001)
                        continue
                else:
                    try:
                        packet = await stage.input_buffer.get(timeout=1.0)
                    except asyncio.TimeoutError:
                        continue

                # Process
                t0 = time.perf_counter()
                try:
                    result = await stage.process(packet)
                except Exception as exc:
                    logger.error("stage.error", stage=name, error=str(exc))
                    continue
                elapsed_ms = (time.perf_counter() - t0) * 1000
                result.stage_latencies[name] = elapsed_ms

                # Push downstream
                await stage.output_buffer.put(result)

        except asyncio.CancelledError:
            logger.info("stage.cancelled", stage=name)
        except Exception as exc:
            logger.exception("stage.fatal", stage=name, error=str(exc))

    # ── Output Access ────────────────────────────────────

    @property
    def output_buffer(self) -> FrameBuffer:
        """The final pers→out buffer for WebSocket consumers."""
        return self._buffers["pers→out"]

    # ── One-Shot / Upload Processing ─────────────────────

    async def process_single_frame(self, frame: np.ndarray, camera_id: str = "upload") -> FramePacket:
        """Process a single image through the full AI pipeline."""
        from app.schemas.frame import FrameMetadata, FramePacket
        import numpy as np
        
        h, w = frame.shape[:2]
        packet = FramePacket(
            meta=FrameMetadata(
                camera_id=camera_id,
                frame_idx=0,
                timestamp=time.time(),
                width=w,
                height=h,
                fps=0,
            ),
            frame=frame,
        )

        # Skip acquisition [0], use the rest
        # We also skip Tracking [3] for single images as it needs history
        # We skip Persistence [14] to avoid duplicate saves (detect.py handles archival)
        for stage in self._stages[1:]:
            if stage.name in ["p4_tracking", "p15_persistence"]:
                continue
            packet = await stage.process(packet)
            
        return packet

    async def process_video_sequence(self, frames: list[np.ndarray], camera_id: str = "upload_video"):
        """Process a sequence of frames (video) through the full AI pipeline.
        
        Creates a transient TrackingStage to avoid state contamination with live feed.
        """
        from app.schemas.frame import FrameMetadata, FramePacket
        from app.pipeline.p4_tracking import TrackingStage
        
        # Instantiate a private tracker for this video
        private_tracker = TrackingStage(
            gpu_manager=self.gpu,
            redis=self.redis,
            settings=self.settings
        )
        await private_tracker.setup()

        results = []
        for i, frame in enumerate(frames):
            h, w = frame.shape[:2]
            packet = FramePacket(
                meta=FrameMetadata(
                    camera_id=camera_id,
                    frame_idx=i,
                    timestamp=time.time(),
                    width=w,
                    height=h,
                    fps=25,
                ),
                frame=frame,
            )

            # Process through all stages, substituting the private tracker
            # Skip Persistence [14] to avoid duplicate saves (detect.py handles archival)
            for stage in self._stages[1:]:
                if stage.name == "p4_tracking":
                    packet = await private_tracker.process(packet)
                elif stage.name == "p15_persistence":
                    continue
                else:
                    packet = await stage.process(packet)
            
            results.append(packet)
            
        return results

    # ── Diagnostics ──────────────────────────────────────

    def diagnostics(self) -> dict:
        """Per-buffer depth + drop stats for monitoring."""
        return {
            "running": self._running,
            "stages": len(self._stages),
            "buffers": {
                name: buf.stats() for name, buf in self._buffers.items()
            },
        }
