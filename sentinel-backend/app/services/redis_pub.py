"""
SENTINEL — Redis Pub/Sub Publisher & Subscriber
Event bus for decoupling inference from delivery.
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Coroutine, Dict, List, Optional

import orjson
import structlog
import redis.asyncio as aioredis

logger = structlog.get_logger(__name__)

# Event channels
CHANNELS = {
    "frame_processed": "frame.processed",
    "risk_updated": "risk.updated",
    "alert_created": "alert.created",
    "metrics_updated": "metrics.updated",
}


class RedisEventBus:
    """Async Redis Pub/Sub manager.

    Publishers call `publish(channel, data)`.
    Subscribers register via `subscribe(channel, callback)`.
    """

    def __init__(self, redis: aioredis.Redis):
        self._redis = redis
        self._pubsub: Optional[aioredis.client.PubSub] = None
        self._handlers: Dict[str, List[Callable]] = {}
        self._listener_task: Optional[asyncio.Task] = None

    # ── Publish ──────────────────────────────────────────

    async def publish(self, channel: str, data: dict | bytes) -> int:
        """Publish a message to a Redis channel.

        Args:
            channel: Channel name (e.g. 'alert.created')
            data: Dict (auto-serialized) or raw bytes

        Returns:
            Number of subscribers that received the message.
        """
        payload = orjson.dumps(data) if isinstance(data, dict) else data
        count = await self._redis.publish(channel, payload)
        return count

    # ── Subscribe ────────────────────────────────────────

    async def subscribe(
        self,
        channel: str,
        handler: Callable[[str, dict], Coroutine],
    ) -> None:
        """Register an async handler for a channel."""
        if channel not in self._handlers:
            self._handlers[channel] = []
        self._handlers[channel].append(handler)

        if self._pubsub is None:
            self._pubsub = self._redis.pubsub()

        await self._pubsub.subscribe(channel)
        logger.info("redis.subscribed", channel=channel)

    async def start_listening(self) -> None:
        """Start background listener task."""
        if self._pubsub is None:
            return
        self._listener_task = asyncio.create_task(self._listen())
        logger.info("redis.listener_started")

    async def stop_listening(self) -> None:
        """Stop background listener."""
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        if self._pubsub:
            await self._pubsub.unsubscribe()
            await self._pubsub.close()

    async def _listen(self) -> None:
        """Background message listener dispatching to handlers."""
        try:
            async for message in self._pubsub.listen():
                if message["type"] != "message":
                    continue

                channel = message["channel"]
                if isinstance(channel, bytes):
                    channel = channel.decode()

                try:
                    data = orjson.loads(message["data"])
                except Exception:
                    data = message["data"]

                handlers = self._handlers.get(channel, [])
                for handler in handlers:
                    try:
                        await handler(channel, data)
                    except Exception as exc:
                        logger.error(
                            "redis.handler_error",
                            channel=channel,
                            error=str(exc),
                        )
        except asyncio.CancelledError:
            logger.info("redis.listener_stopped")
        except Exception as exc:
            logger.exception("redis.listener_fatal", error=str(exc))
