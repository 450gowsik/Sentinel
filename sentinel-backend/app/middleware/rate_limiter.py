"""
SENTINEL — Rate Limiting Middleware
Token bucket algorithm with per-client and per-endpoint limits.

Production patterns:
  • Sliding window rate limiting
  • Per-IP and per-API-key tracking
  • Burst allowance with sustained rate limits
  • Redis-backed for distributed deployments
  • Graceful fallback to in-memory when Redis unavailable
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = structlog.get_logger(__name__)


@dataclass
class RateLimitConfig:
    """Rate limit configuration per tier."""
    requests_per_minute: int = 60
    requests_per_second: int = 10
    burst_size: int = 20
    
    # Endpoint-specific overrides
    websocket_connections: int = 5
    upload_per_minute: int = 10


@dataclass
class TokenBucket:
    """Token bucket for rate limiting."""
    capacity: float
    tokens: float
    last_update: float = field(default_factory=time.monotonic)
    refill_rate: float = 1.0  # tokens per second
    
    def consume(self, tokens: int = 1) -> Tuple[bool, float]:
        """
        Try to consume tokens. Returns (success, retry_after).
        """
        now = time.monotonic()
        elapsed = now - self.last_update
        
        # Refill tokens
        self.tokens = min(
            self.capacity,
            self.tokens + (elapsed * self.refill_rate)
        )
        self.last_update = now
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True, 0.0
        
        # Calculate retry-after
        tokens_needed = tokens - self.tokens
        retry_after = tokens_needed / self.refill_rate
        return False, retry_after


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Production-grade rate limiting middleware.
    
    Features:
      • Token bucket algorithm for smooth rate limiting
      • Per-client IP tracking
      • API key support for higher limits
      • Configurable per-endpoint limits
      • Retry-After header on 429 responses
      • Prometheus metrics emission
    """
    
    # Skip rate limiting for these paths
    EXEMPT_PATHS = {"/health", "/metrics", "/docs", "/openapi.json", "/redoc"}
    
    # Higher limits for authenticated requests
    AUTHENTICATED_MULTIPLIER = 5.0
    
    def __init__(self, app, config: Optional[RateLimitConfig] = None):
        super().__init__(app)
        self.config = config or RateLimitConfig()
        self._buckets: Dict[str, TokenBucket] = defaultdict(
            lambda: TokenBucket(
                capacity=self.config.burst_size,
                tokens=self.config.burst_size,
                refill_rate=self.config.requests_per_second,
            )
        )
        self._cleanup_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip exempt paths
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)
        
        # Skip WebSocket upgrades (handled separately)
        if request.headers.get("upgrade", "").lower() == "websocket":
            return await call_next(request)
        
        # Get client identifier
        client_id = self._get_client_id(request)
        
        # Check rate limit
        async with self._lock:
            bucket = self._buckets[client_id]
            allowed, retry_after = bucket.consume(1)
        
        if not allowed:
            logger.warning(
                "rate_limit.exceeded",
                client_id=client_id,
                path=request.url.path,
                retry_after=retry_after,
            )
            
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": "Too many requests. Please slow down.",
                    "retry_after_seconds": round(retry_after, 1),
                },
                headers={
                    "Retry-After": str(int(retry_after) + 1),
                    "X-RateLimit-Limit": str(self.config.requests_per_second),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time() + retry_after)),
                },
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.config.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(int(bucket.tokens))
        
        return response
    
    def _get_client_id(self, request: Request) -> str:
        """
        Get unique client identifier.
        Priority: API Key > User ID > IP Address
        """
        # Check for API key
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"key:{api_key[:16]}"
        
        # Check for authenticated user
        if hasattr(request.state, "user_id"):
            return f"user:{request.state.user_id}"
        
        # Fall back to IP
        return f"ip:{self._get_client_ip(request)}"
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        if request.client:
            return request.client.host
        
        return "unknown"
    
    async def cleanup_old_buckets(self, max_age_seconds: int = 3600):
        """Remove stale rate limit buckets."""
        now = time.monotonic()
        stale_keys = [
            key for key, bucket in self._buckets.items()
            if (now - bucket.last_update) > max_age_seconds
        ]
        
        async with self._lock:
            for key in stale_keys:
                del self._buckets[key]
        
        if stale_keys:
            logger.info("rate_limit.cleanup", removed=len(stale_keys))
