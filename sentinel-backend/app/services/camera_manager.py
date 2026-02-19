"""
SENTINEL — Camera Manager Service (Production-Grade)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Non-blocking camera management with:
  • Background thread that NEVER blocks the event loop
  • Per-backend timeouts (Windows MediaFoundation can hang 30s+)
  • Auto-fallback to demo frames
  • Thread-safe frame sharing via lock + latest-frame pattern
"""

from __future__ import annotations

import asyncio
import math
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Tuple

import cv2
import numpy as np
import structlog

logger = structlog.get_logger(__name__)

# Single-thread pool used ONLY for camera open attempts (with timeout)
_cam_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="cam-open")


class CameraState:
    IDLE = "idle"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    FAILED = "failed"
    STOPPED = "stopped"


class CameraManager:
    """
    Manages video capture in a background thread.

    Design contract:
      • start_background() returns IMMEDIATELY (spawns daemon thread)
      • get_frame() is async, NEVER blocks, returns within microseconds
      • If camera unavailable → returns synthetic demo frame automatically
      • cv2.VideoCapture is ONLY touched inside the background thread
    """

    _instance: Optional["CameraManager"] = None
    _cls_lock = threading.Lock()

    def __new__(cls):
        with cls._cls_lock:
            if cls._instance is None:
                inst = super().__new__(cls)
                inst._initialized = False
                cls._instance = inst
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        # Thread synchronization
        self._frame_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

        # Configuration
        self.source: int | str = 0
        self.target_fps: int = 25

        # Shared state (read by async code, written by bg thread)
        self.latest_frame: Optional[np.ndarray] = None
        self.frame_id: int = 0
        self.state: str = CameraState.IDLE
        self.last_frame_time: float = 0.0
        self.error_msg: str = ""

        # Demo frame counter
        self._demo_idx: int = 0
        
        # Async Bridge
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._frame_queue: Optional[asyncio.Queue] = None

    # ── Public API ──────────────────────────────────────────

    def start_background(self, source: int | str = 0) -> None:
        """Spawn bg thread. Returns in <1ms. Safe to call multiple times."""
        if self._thread and self._thread.is_alive():
            logger.info("camera_manager.already_running")
            return

        self.source = source
        self.state = CameraState.CONNECTING
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._capture_loop, name="sentinel-cam", daemon=True
        )
        self._thread.start()
        logger.info("camera_manager.thread_spawned", source=source)

    async def stop(self) -> None:
        """Signal the bg thread to stop and wait briefly."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        self.state = CameraState.STOPPED
        logger.info("camera_manager.stopped")

    async def get_next_frame(self) -> np.ndarray:
        """
        Zero-Latency Access: Awaits the next frame directly from the background thread.
        Uses an asyncio.Queue to bridge the sync thread -> async loop.
        """
        # Lazy initialization of the async bridge
        if self._loop is None:
            self._loop = asyncio.get_running_loop()
            self._frame_queue = asyncio.Queue(maxsize=1)
            
        return await self._frame_queue.get()

    async def get_frame(self) -> Tuple[np.ndarray, bool]:
        """
        Legacy Polling API (for HTTP endpoints).
        """
        # Fast path: camera is live and frame is fresh (< 2s old)
        if (
            self.state == CameraState.CONNECTED
            and self.latest_frame is not None
            and (time.time() - self.last_frame_time) < 2.0
        ):
            with self._frame_lock:
                return self.latest_frame.copy(), False

        # Slow path: generate demo frame (pure CPU, ~1ms)
        self._demo_idx += 1
        return self._generate_demo_frame(self._demo_idx), True

    # ── Background Thread ───────────────────────────────────

    def _capture_loop(self) -> None:
        """
        Runs in background thread. Owns the cv2.VideoCapture lifecycle.
        Never touches asyncio. Uses time.sleep for throttling.
        """
        cap: Optional[cv2.VideoCapture] = None
        retry_delay = 1.0

        while not self._stop_event.is_set():
            # --- Phase 1: Open camera if not connected ---
            if cap is None or not cap.isOpened():
                self.state = CameraState.CONNECTING
                cap = self._try_open_with_timeout(self.source, timeout=3.0)

                if cap is None:
                    self.state = CameraState.FAILED
                    self.error_msg = f"No camera at source={self.source}"
                    logger.warning(
                        "camera_manager.open_failed",
                        source=self.source,
                        retry_in=retry_delay,
                    )
                    # Exponential backoff, cap at 10s
                    self._stop_event.wait(retry_delay)
                    retry_delay = min(retry_delay * 1.5, 10.0)
                    continue
                else:
                    self.state = CameraState.CONNECTED
                    retry_delay = 1.0
                    logger.info("camera_manager.connected", source=self.source)

            # --- Phase 2: Read frames ---
            try:
                ret, frame = cap.read()
                if ret and frame is not None:
                    with self._frame_lock:
                        self.latest_frame = frame
                        self.frame_id += 1
                        self.last_frame_time = time.time()
                        
                        # ZERO-LATENCY SIGNAL
                        # Notify the async loop immediately
                        if self._loop and self._frame_queue:
                            self._loop.call_soon_threadsafe(
                                self._async_put_frame_nowait, frame
                            )
                else:
                    # Camera returned empty frame — likely disconnected
                    logger.warning("camera_manager.empty_frame")
                    cap.release()
                    cap = None
                    self.state = CameraState.CONNECTING
                    continue
            except Exception as exc:
                logger.error("camera_manager.read_error", error=str(exc))
                try:
                    cap.release()
                except Exception:
                    pass
                cap = None
                continue

            # Throttle
            time.sleep(1.0 / self.target_fps)

        # Cleanup
        if cap:
            try:
                cap.release()
            except Exception:
                pass
        logger.info("camera_manager.thread_exited")

    def _try_open_with_timeout(
        self, source, timeout: float = 3.0
    ) -> Optional[cv2.VideoCapture]:
        """
        Try opening camera with a strict timeout PER backend.
        On Windows, cv2.VideoCapture(0, CAP_MSMF) can hang for 30+ seconds
        if no camera exists. We use a thread pool + timeout to prevent this.
        """
        is_webcam = str(source).isdigit()
        if not is_webcam:
            # RTSP / file — try directly (usually fast or fails fast)
            try:
                cap = cv2.VideoCapture(str(source))
                if cap.isOpened():
                    return cap
                cap.release()
            except Exception:
                pass
            return None

        source_int = int(source)
        
        # Senior Backend Fix: 
        # 1. Always use CAP_DSHOW for Windows webcams (avoids MSMF hangs)
        # 2. Retry loop because camera driver might be busy/locked
        
        # We try DSHOW 3 times with a delay
        for attempt in range(3):
            if self._stop_event.is_set():
                return None
                
            logger.info("camera_manager.trying", backend="DirectShow", attempt=attempt+1)
            
            try:
                # Run in a separate thread with timeout
                future = _cam_executor.submit(
                    self._open_single_backend, source_int, cv2.CAP_DSHOW
                )
                cap = future.result(timeout=timeout)
                if cap is not None:
                    logger.info("camera_manager.backend_ok", backend="DirectShow")
                    return cap
            except Exception as exc:
                logger.debug(
                    "camera_manager.dshow_failed",
                    attempt=attempt+1,
                    error=str(exc),
                )
            
            # Wait before retry (essential for driver release)
            time.sleep(1.0)

        # Fallback to MediaFoundation ONLY if DSHOW fails all attempts
        # (Some older cams might require it, but we prioritize DSHOW)
        if self._stop_event.is_set():
            return None
            
        logger.info("camera_manager.trying_fallback", backend="MediaFoundation")
        try:
            future = _cam_executor.submit(
                self._open_single_backend, source_int, cv2.CAP_MSMF
            )
            cap = future.result(timeout=timeout)
            if cap is not None:
                logger.info("camera_manager.backend_ok", backend="MediaFoundation")
                return cap
        except Exception:
            pass

        return None

    @staticmethod
    def _open_single_backend(
        source: int, backend: int
    ) -> Optional[cv2.VideoCapture]:
        """Open a single camera+backend combo. Called from thread pool."""
        try:
            cap = cv2.VideoCapture(source, backend)
            if cap.isOpened():
                # Senior Hardening 1: Explicit Resolution & FPS
                # Forces camera to a known good state (640x480 @ 30)
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                cap.set(cv2.CAP_PROP_FPS, 30)
                
                # Senior Hardening 2: Warm-up Frames
                # Discard initial frames (often black/auto-exposure adjusting)
                for _ in range(5):
                    cap.read()
                
                # Verify reading one real frame
                ret, _ = cap.read()
                if ret:
                    # PRO LOGGING: confirming backend usage
                    backend_name = cap.getBackendName()
                    logger.info("camera_manager.opened_success", backend=backend_name)
                    return cap
            
            cap.release()
        except Exception:
            pass
        return None

    def _async_put_frame_nowait(self, frame: np.ndarray):
        """Helper to put frame in queue from the event loop thread."""
        if self._frame_queue is None:
            return
            
        # Drop old frame if queue is full (latest-is-greatest)
        if self._frame_queue.full():
            try:
                self._frame_queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        
        # Pass REFERENCE to frame (Zero Copy)
        self._frame_queue.put_nowait(frame)

    # ── Demo Frame Generator ────────────────────────────────

    def _generate_demo_frame(self, idx: int) -> np.ndarray:
        """Generate a visually interesting synthetic surveillance frame."""
        W, H = 640, 480
        frame = np.zeros((H, W, 3), dtype=np.uint8)
        frame[:] = (15, 15, 20)

        # Grid
        for x in range(0, W, 40):
            cv2.line(frame, (x, 0), (x, H), (25, 35, 25), 1)
        for y in range(0, H, 40):
            cv2.line(frame, (0, y), (W, y), (25, 35, 25), 1)

        t = idx * 0.05

        # Simulated detections
        n_persons = 3 + int(abs(math.sin(t * 0.3)) * 4)
        for i in range(n_persons):
            seed = i * 137
            cx = int(W * 0.15 + W * 0.7 * ((math.sin(t * 0.4 + seed) + 1) / 2))
            cy = int(H * 0.2 + H * 0.6 * ((math.cos(t * 0.3 + seed * 0.7) + 1) / 2))
            bw, bh = 40, 85
            x1, y1 = max(0, cx - bw // 2), max(0, cy - bh // 2)
            x2, y2 = min(W, cx + bw // 2), min(H, cy + bh // 2)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 229, 0), 2)
            cv2.putText(
                frame, f"P{i+1} 92%", (x1, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 229, 0), 1
            )
            # Flow arrow
            dx = int(20 * math.cos(t * 0.5 + i))
            dy = int(20 * math.sin(t * 0.5 + i))
            cv2.arrowedLine(
                frame, (cx, cy), (cx + dx, cy + dy), (0, 180, 0), 1, tipLength=0.4
            )

        # Header
        cv2.rectangle(frame, (0, 0), (W, 30), (20, 20, 30), -1)
        cv2.putText(
            frame, "SENTINEL LIVE — DEMO MODE", (10, 20),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 229, 255), 1
        )
        ts = time.strftime("%H:%M:%S")
        cv2.putText(
            frame, ts, (W - 90, 20),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 229, 255), 1
        )

        # Footer
        cv2.rectangle(frame, (0, H - 25), (W, H), (20, 20, 30), -1)
        info = f"Detections: {n_persons} | FPS: 15 | Camera: {self.state}"
        cv2.putText(
            frame, info, (10, H - 8),
            cv2.FONT_HERSHEY_SIMPLEX, 0.35, (100, 200, 100), 1
        )

        # Blinking REC
        if int(t * 2) % 2 == 0:
            cv2.circle(frame, (W - 15, 15), 5, (0, 0, 255), -1)

        return frame


# ── Module-level singleton ──────────────────────────────────
camera_manager = CameraManager()
