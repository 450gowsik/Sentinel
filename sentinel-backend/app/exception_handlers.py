"""
SENTINEL — Exception Handlers
Global exception handlers for FastAPI with structured responses.

Production patterns:
  • Consistent error response format
  • Request ID correlation
  • Structured logging for all errors
  • Sentry/error tracking integration points
  • Development vs production error detail
"""

from __future__ import annotations

import traceback
from typing import Union

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.exceptions import (
    ErrorCode,
    ErrorResponse,
    SentinelException,
    ValidationError,
)

logger = structlog.get_logger(__name__)


def get_request_id(request: Request) -> str:
    """Extract request ID from request state."""
    if hasattr(request.state, "request_id"):
        return request.state.request_id
    return "unknown"


def setup_exception_handlers(app: FastAPI, debug: bool = False):
    """
    Register all exception handlers on the FastAPI app.
    
    Args:
        app: FastAPI application instance
        debug: If True, include stack traces in responses
    """
    
    @app.exception_handler(SentinelException)
    async def sentinel_exception_handler(
        request: Request, exc: SentinelException
    ) -> JSONResponse:
        """Handle all custom Sentinel exceptions."""
        request_id = get_request_id(request)
        
        # Log the error
        logger.error(
            "sentinel.exception",
            error_code=exc.code.value,
            message=exc.message,
            details=exc.details,
            request_id=request_id,
            path=request.url.path,
            exc_info=exc.cause,
        )
        
        response = exc.to_response(request_id=request_id)
        
        # Include stack trace in debug mode
        if debug and exc.cause:
            response.details = response.details or {}
            response.details["stack_trace"] = traceback.format_exception(
                type(exc.cause), exc.cause, exc.cause.__traceback__
            )
        
        return JSONResponse(
            status_code=exc.status_code,
            content=response.model_dump(exclude_none=True),
            headers={"X-Request-ID": request_id},
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Handle Pydantic validation errors from request parsing."""
        request_id = get_request_id(request)
        
        # Extract field-level errors
        field_errors = []
        for error in exc.errors():
            field_errors.append({
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            })
        
        logger.warning(
            "validation.failed",
            errors=field_errors,
            request_id=request_id,
            path=request.url.path,
        )
        
        response = ErrorResponse(
            error="ValidationError",
            code=ErrorCode.VALIDATION_ERROR.value,
            message="Request validation failed",
            details={"fields": field_errors},
            request_id=request_id,
        )
        
        return JSONResponse(
            status_code=422,
            content=response.model_dump(exclude_none=True),
            headers={"X-Request-ID": request_id},
        )
    
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        """Handle standard HTTP exceptions."""
        request_id = get_request_id(request)
        
        # Map status codes to error codes
        error_code_map = {
            400: ErrorCode.VALIDATION_ERROR,
            401: ErrorCode.UNAUTHORIZED,
            403: ErrorCode.FORBIDDEN,
            404: ErrorCode.NOT_FOUND,
            409: ErrorCode.CONFLICT,
            429: ErrorCode.RATE_LIMIT_EXCEEDED,
            500: ErrorCode.INTERNAL_ERROR,
            503: ErrorCode.EXTERNAL_SERVICE_ERROR,
        }
        
        error_code = error_code_map.get(exc.status_code, ErrorCode.INTERNAL_ERROR)
        
        logger.warning(
            "http.exception",
            status_code=exc.status_code,
            detail=exc.detail,
            request_id=request_id,
            path=request.url.path,
        )
        
        response = ErrorResponse(
            error="HTTPException",
            code=error_code.value,
            message=str(exc.detail) if exc.detail else "An error occurred",
            request_id=request_id,
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content=response.model_dump(exclude_none=True),
            headers={"X-Request-ID": request_id},
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """
        Catch-all handler for unexpected exceptions.
        In production, this prevents leaking internal details.
        """
        request_id = get_request_id(request)
        
        # Always log with full details
        logger.exception(
            "unhandled.exception",
            error_type=type(exc).__name__,
            error_message=str(exc),
            request_id=request_id,
            path=request.url.path,
        )
        
        # Build response
        response = ErrorResponse(
            error="InternalServerError",
            code=ErrorCode.INTERNAL_ERROR.value,
            message="An unexpected error occurred",
            request_id=request_id,
        )
        
        # Include details only in debug mode
        if debug:
            response.details = {
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "stack_trace": traceback.format_exc().split("\n"),
            }
        
        return JSONResponse(
            status_code=500,
            content=response.model_dump(exclude_none=True),
            headers={"X-Request-ID": request_id},
        )
