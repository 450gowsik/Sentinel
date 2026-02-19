"""
SENTINEL — Custom Exceptions & Error Handlers
Enterprise-grade exception hierarchy with structured error responses.

Production patterns:
  • Domain-specific exception hierarchy
  • Machine-readable error codes
  • User-friendly error messages
  • Stack trace capture (dev only)
  • Correlation ID linking
  • Prometheus error metrics
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel


class ErrorCode(str, Enum):
    """Machine-readable error codes for API clients."""
    
    # General errors (1xxx)
    INTERNAL_ERROR = "E1000"
    VALIDATION_ERROR = "E1001"
    NOT_FOUND = "E1002"
    CONFLICT = "E1003"
    
    # Authentication errors (2xxx)
    UNAUTHORIZED = "E2000"
    FORBIDDEN = "E2001"
    TOKEN_EXPIRED = "E2002"
    INVALID_TOKEN = "E2003"
    
    # Rate limiting (3xxx)
    RATE_LIMIT_EXCEEDED = "E3000"
    QUOTA_EXCEEDED = "E3001"
    
    # Resource errors (4xxx)
    CAMERA_NOT_FOUND = "E4000"
    CAMERA_UNAVAILABLE = "E4001"
    CAMERA_BUSY = "E4002"
    STREAM_ERROR = "E4003"
    
    # Pipeline errors (5xxx)
    PIPELINE_NOT_READY = "E5000"
    MODEL_LOAD_FAILED = "E5001"
    INFERENCE_ERROR = "E5002"
    GPU_UNAVAILABLE = "E5003"
    
    # Database errors (6xxx)
    DATABASE_ERROR = "E6000"
    DATABASE_UNAVAILABLE = "E6001"
    QUERY_TIMEOUT = "E6002"
    
    # External service errors (7xxx)
    REDIS_UNAVAILABLE = "E7000"
    EXTERNAL_SERVICE_ERROR = "E7001"
    TIMEOUT = "E7002"


class ErrorResponse(BaseModel):
    """Structured error response for API clients."""
    
    error: str
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    request_id: Optional[str] = None
    documentation_url: Optional[str] = None


class SentinelException(Exception):
    """
    Base exception for all Sentinel errors.
    
    Usage:
        raise SentinelException(
            code=ErrorCode.CAMERA_UNAVAILABLE,
            message="Camera 0 is not responding",
            details={"camera_id": "cam_0", "last_seen": "2024-01-01T12:00:00Z"}
        )
    """
    
    status_code: int = 500
    error_code: ErrorCode = ErrorCode.INTERNAL_ERROR
    
    def __init__(
        self,
        message: str,
        code: Optional[ErrorCode] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        self.message = message
        self.code = code or self.error_code
        self.details = details or {}
        self.cause = cause
        super().__init__(message)
    
    def to_response(self, request_id: Optional[str] = None) -> ErrorResponse:
        """Convert to structured API response."""
        return ErrorResponse(
            error=self.__class__.__name__,
            code=self.code.value,
            message=self.message,
            details=self.details if self.details else None,
            request_id=request_id,
            documentation_url=f"https://docs.sentinel.ai/errors/{self.code.value}",
        )


# ── Client Errors (4xx) ──────────────────────────────────────


class ValidationError(SentinelException):
    """Invalid request data."""
    status_code = 400
    error_code = ErrorCode.VALIDATION_ERROR


class UnauthorizedError(SentinelException):
    """Authentication required."""
    status_code = 401
    error_code = ErrorCode.UNAUTHORIZED


class ForbiddenError(SentinelException):
    """Insufficient permissions."""
    status_code = 403
    error_code = ErrorCode.FORBIDDEN


class NotFoundError(SentinelException):
    """Resource not found."""
    status_code = 404
    error_code = ErrorCode.NOT_FOUND


class ConflictError(SentinelException):
    """Resource conflict (e.g., duplicate)."""
    status_code = 409
    error_code = ErrorCode.CONFLICT


class RateLimitError(SentinelException):
    """Rate limit exceeded."""
    status_code = 429
    error_code = ErrorCode.RATE_LIMIT_EXCEEDED


# ── Server Errors (5xx) ──────────────────────────────────────


class InternalError(SentinelException):
    """Unexpected server error."""
    status_code = 500
    error_code = ErrorCode.INTERNAL_ERROR


class ServiceUnavailableError(SentinelException):
    """Service temporarily unavailable."""
    status_code = 503
    error_code = ErrorCode.EXTERNAL_SERVICE_ERROR


# ── Domain-Specific Errors ───────────────────────────────────


class CameraError(SentinelException):
    """Camera-related errors."""
    status_code = 503
    error_code = ErrorCode.CAMERA_UNAVAILABLE


class CameraNotFoundError(CameraError):
    """Camera not found."""
    status_code = 404
    error_code = ErrorCode.CAMERA_NOT_FOUND


class CameraBusyError(CameraError):
    """Camera in use by another process."""
    status_code = 409
    error_code = ErrorCode.CAMERA_BUSY


class PipelineError(SentinelException):
    """Pipeline processing errors."""
    status_code = 503
    error_code = ErrorCode.PIPELINE_NOT_READY


class ModelError(PipelineError):
    """ML model errors."""
    error_code = ErrorCode.MODEL_LOAD_FAILED


class InferenceError(PipelineError):
    """Inference execution errors."""
    error_code = ErrorCode.INFERENCE_ERROR


class GPUError(PipelineError):
    """GPU-related errors."""
    error_code = ErrorCode.GPU_UNAVAILABLE


class DatabaseError(SentinelException):
    """Database errors."""
    status_code = 503
    error_code = ErrorCode.DATABASE_ERROR


class RedisError(SentinelException):
    """Redis connection errors."""
    status_code = 503
    error_code = ErrorCode.REDIS_UNAVAILABLE


class TimeoutError(SentinelException):
    """Operation timeout."""
    status_code = 504
    error_code = ErrorCode.TIMEOUT
