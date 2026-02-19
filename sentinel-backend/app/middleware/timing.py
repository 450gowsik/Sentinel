"""
SENTINEL — Timing Middleware
Request timing, performance tracking, and SLA monitoring.

Production patterns:
  • Precise request timing with perf_counter
  • Server-Timing header for debugging
  • Slow request logging
  • P99/P95/P50 latency tracking
  • SLA breach alerting
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, Optional

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger(__name__)


@dataclass
class LatencyStats:
    """Rolling window latency statistics."""
    window_size: int = 1000
    samples: Deque[float] = field(default_factory=lambda: deque(maxlen=1000))
    
    def add(self, latency_ms: float):
        self.samples.append(latency_ms)
    
    def percentile(self, p: float) -> float:
        """Calculate percentile from samples."""
        if not self.samples:
            return 0.0
        sorted_samples = sorted(self.samples)
        idx = int(len(sorted_samples) * p / 100)
        return sorted_samples[min(idx, len(sorted_samples) - 1)]
    
    @property
    def p50(self) -> float:
        return self.percentile(50)
    
    @property
    def p95(self) -> float:
        return self.percentile(95)
    
    @property
    def p99(self) -> float:
        return self.percentile(99)
    
    @property
    def avg(self) -> float:
        if not self.samples:
            return 0.0
        return sum(self.samples) / len(self.samples)


class TimingMiddleware(BaseHTTPMiddleware):
    """
    Production-grade request timing middleware.
    
    Features:
      • Microsecond-precision timing
      • Server-Timing header for browser DevTools
      • X-Response-Time header
      • Slow request logging (configurable threshold)
      • Rolling latency statistics
      • Per-endpoint tracking
    """
    
    # Default slow request threshold (milliseconds)
    DEFAULT_SLOW_THRESHOLD_MS = 500
    
    def __init__(
        self,
        app,
        slow_request_threshold_ms: float = DEFAULT_SLOW_THRESHOLD_MS,
        enable_server_timing: bool = True,
    ):
        super().__init__(app)
        self.slow_threshold_ms = slow_request_threshold_ms
        self.enable_server_timing = enable_server_timing
        
        # Per-endpoint latency tracking
        self._endpoint_stats: Dict[str, LatencyStats] = {}
        self._global_stats = LatencyStats()
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Start timing
        start_time = time.perf_counter()
        
        # Store timing context
        request.state.timing = {
            "start": start_time,
            "checkpoints": [],
        }
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        end_time = time.perf_counter()
        duration_ms = (end_time - start_time) * 1000
        
        # Track statistics
        self._track_latency(request.url.path, duration_ms)
        
        # Add timing headers
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
        
        if self.enable_server_timing:
            response.headers["Server-Timing"] = self._build_server_timing(
                request, duration_ms
            )
        
        # Log slow requests
        if duration_ms > self.slow_threshold_ms:
            logger.warning(
                "request.slow",
                path=request.url.path,
                method=request.method,
                duration_ms=round(duration_ms, 2),
                threshold_ms=self.slow_threshold_ms,
                status_code=response.status_code,
            )
        
        # Structured request log
        logger.info(
            "request.completed",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=round(duration_ms, 2),
        )
        
        return response
    
    def _track_latency(self, path: str, duration_ms: float):
        """Track latency for statistics."""
        # Normalize path (remove IDs)
        normalized_path = self._normalize_path(path)
        
        # Per-endpoint stats
        if normalized_path not in self._endpoint_stats:
            self._endpoint_stats[normalized_path] = LatencyStats()
        self._endpoint_stats[normalized_path].add(duration_ms)
        
        # Global stats
        self._global_stats.add(duration_ms)
    
    def _normalize_path(self, path: str) -> str:
        """
        Normalize paths by replacing IDs with placeholders.
        /api/v1/alerts/abc123 -> /api/v1/alerts/:id
        """
        parts = path.split("/")
        normalized = []
        
        for part in parts:
            # Replace UUIDs and numeric IDs
            if part and (
                len(part) == 36 and part.count("-") == 4 or  # UUID
                len(part) == 12 and part.isalnum() or        # Short ID
                part.isdigit()                                # Numeric
            ):
                normalized.append(":id")
            else:
                normalized.append(part)
        
        return "/".join(normalized)
    
    def _build_server_timing(self, request: Request, total_ms: float) -> str:
        """
        Build Server-Timing header value.
        Format: metric;dur=X;desc="Description"
        """
        timings = [f'total;dur={total_ms:.2f};desc="Total Request Time"']
        
        # Add checkpoints if available
        if hasattr(request.state, "timing"):
            checkpoints = request.state.timing.get("checkpoints", [])
            for name, duration in checkpoints:
                timings.append(f'{name};dur={duration:.2f}')
        
        return ", ".join(timings)
    
    def get_stats(self) -> Dict:
        """Get current latency statistics."""
        return {
            "global": {
                "p50_ms": round(self._global_stats.p50, 2),
                "p95_ms": round(self._global_stats.p95, 2),
                "p99_ms": round(self._global_stats.p99, 2),
                "avg_ms": round(self._global_stats.avg, 2),
                "sample_count": len(self._global_stats.samples),
            },
            "endpoints": {
                path: {
                    "p50_ms": round(stats.p50, 2),
                    "p95_ms": round(stats.p95, 2),
                    "p99_ms": round(stats.p99, 2),
                    "avg_ms": round(stats.avg, 2),
                }
                for path, stats in self._endpoint_stats.items()
            },
        }


def add_timing_checkpoint(request: Request, name: str, duration_ms: float):
    """
    Add a timing checkpoint for Server-Timing header.
    Call from route handlers to track sub-operations.
    
    Usage:
        from app.middleware.timing import add_timing_checkpoint
        
        @router.get("/analyze")
        async def analyze(request: Request):
            start = time.perf_counter()
            result = await run_model()
            add_timing_checkpoint(request, "model", (time.perf_counter() - start) * 1000)
    """
    if hasattr(request.state, "timing"):
        request.state.timing["checkpoints"].append((name, duration_ms))
