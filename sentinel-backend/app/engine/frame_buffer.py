"""
SENTINEL — Async Frame Buffer
Bounded asyncio.Queue with frame-drop policy for back-pressure.
"""

from __future__ import annotations

import asyncio
import time
from typing import Generic, Optional, TypeVar

import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")


class FrameBuffer(Generic[T]):
    """Bounded async queue with automatic oldest-frame drop.

    When the buffer is full, the oldest item is discarded so that
    the pipeline never blocks upstream producers.

    Attributes
    ──────────
        name:       Human label for logging.
        maxsize:    Maximum queue depth.
        dropped:    Running count of dropped frames.
    """

    def __init__(self, name: str = "buffer", maxsize: int = 30):
        self.name = name
        self.maxsize = maxsize
        self._queue: asyncio.Queue[T] = asyncio.Queue(maxsize=maxsize)
        self.dropped: int = 0
        self._total_put: int = 0
        self._total_get: int = 0

    # ── Producer side ────────────────────────────────────

    async def put(self, item: T) -> None:
        """Enqueue an item.  If full, drop the oldest item first."""
        if self._queue.full():
            try:
                self._queue.get_nowait()
                self.dropped += 1
            except asyncio.QueueEmpty:
                pass
        await self._queue.put(item)
        self._total_put += 1

    def put_nowait(self, item: T) -> None:
        """Non-blocking put; drops oldest if full."""
        if self._queue.full():
            try:
                self._queue.get_nowait()
                self.dropped += 1
            except asyncio.QueueEmpty:
                pass
        self._queue.put_nowait(item)
        self._total_put += 1

    # ── Consumer side ────────────────────────────────────

    async def get(self, timeout: float | None = None) -> T:
        """Dequeue an item, optionally with timeout (seconds)."""
        if timeout is not None:
            item = await asyncio.wait_for(self._queue.get(), timeout=timeout)
        else:
            item = await self._queue.get()
        self._total_get += 1
        return item

    def get_nowait(self) -> Optional[T]:
        try:
            item = self._queue.get_nowait()
            self._total_get += 1
            return item
        except asyncio.QueueEmpty:
            return None

    # ── Introspection ────────────────────────────────────

    @property
    def depth(self) -> int:
        return self._queue.qsize()

    @property
    def empty(self) -> bool:
        return self._queue.empty()

    def stats(self) -> dict:
        return {
            "name": self.name,
            "depth": self.depth,
            "maxsize": self.maxsize,
            "total_put": self._total_put,
            "total_get": self._total_get,
            "dropped": self.dropped,
        }

    async def clear(self) -> int:
        """Drain the buffer. Returns number of items removed."""
        count = 0
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                count += 1
            except asyncio.QueueEmpty:
                break
        return count
