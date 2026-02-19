"""
SENTINEL — Request Context Middleware
Adds correlation IDs, request tracing, and structured logging context.

Production patterns:
  • X-Request-ID header propagation
  • Correlation ID generation for tracing
  • Context variables for async logging
  • Request/response metadata capture
"""

from __future__ import annotations

import contextvars
import time
import uuid
from typing import Callable

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Context variables for request-scoped data
request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default=""
)
correlation_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id", default=""
)

logger = structlog.get_logger(__name__)


def get_request_id() -> str:
    """Get the current request ID from context."""
    return request_id_ctx.get()


def get_correlation_id() -> str:
    """Get the current correlation ID from context."""
    return correlation_id_ctx.get()


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Production-grade request context middleware.
    
    Features:
      • Generates unique request IDs for each request
      • Propagates existing X-Request-ID headers
      • Supports X-Correlation-ID for distributed tracing
      • Injects IDs into response headers
      • Binds context to structlog for all handlers
    """

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        # Extract or generate request ID
        request_id = request.headers.get(
            "X-Request-ID", 
            f"req_{uuid.uuid4().hex[:12]}"
        )
        
        # Extract or propagate correlation ID
        correlation_id = request.headers.get(
            "X-Correlation-ID",
            request.headers.get("X-Request-ID", request_id)
        )
        
        # Set context variables
        request_id_ctx.set(request_id)
        correlation_id_ctx.set(correlation_id)
        
        # Bind to structlog for all downstream logging
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            correlation_id=correlation_id,
            method=request.method,
            path=request.url.path,
            client_ip=self._get_client_ip(request),
        )
        
        # Store in request state for access in routes
        request.state.request_id = request_id
        request.state.correlation_id = correlation_id
        request.state.start_time = time.perf_counter()
        
        # Process request
        response = await call_next(request)
        
        # Add headers to response
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Correlation-ID"] = correlation_id
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP, respecting proxy headers."""
        # Check for forwarded headers (reverse proxy)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Direct connection
        if request.client:
            return request.client.host
        
        return "unknown"
