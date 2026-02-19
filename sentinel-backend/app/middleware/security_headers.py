"""
SENTINEL — Security Headers Middleware
OWASP-compliant security headers for production deployments.

Production patterns:
  • Content Security Policy (CSP)
  • XSS Protection
  • Frame Options (Clickjacking prevention)
  • Content Type Options (MIME sniffing)
  • Strict Transport Security (HSTS)
  • Referrer Policy
  • Permissions Policy
"""

from __future__ import annotations

from typing import Dict, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Production-grade security headers middleware.
    
    Implements OWASP security header recommendations:
      • Prevents XSS attacks
      • Prevents clickjacking
      • Prevents MIME type sniffing
      • Enforces HTTPS in production
      • Controls referrer information
      • Restricts browser features
    """
    
    # Default security headers
    DEFAULT_HEADERS: Dict[str, str] = {
        # Prevent XSS attacks
        "X-XSS-Protection": "1; mode=block",
        
        # Prevent clickjacking
        "X-Frame-Options": "DENY",
        
        # Prevent MIME type sniffing
        "X-Content-Type-Options": "nosniff",
        
        # Control referrer information
        "Referrer-Policy": "strict-origin-when-cross-origin",
        
        # Restrict browser features
        "Permissions-Policy": (
            "accelerometer=(), "
            "camera=(), "
            "geolocation=(), "
            "gyroscope=(), "
            "magnetometer=(), "
            "microphone=(), "
            "payment=(), "
            "usb=()"
        ),
        
        # Cache control for API responses
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
    }
    
    # Headers for production (HTTPS) environments
    PRODUCTION_HEADERS: Dict[str, str] = {
        # Enforce HTTPS for 1 year, include subdomains
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
    }
    
    def __init__(
        self,
        app,
        production: bool = False,
        custom_csp: Optional[str] = None,
        allowed_frame_ancestors: Optional[str] = None,
    ):
        super().__init__(app)
        self.production = production
        self.custom_csp = custom_csp
        self.allowed_frame_ancestors = allowed_frame_ancestors
    
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        
        # Add default security headers
        for header, value in self.DEFAULT_HEADERS.items():
            if header not in response.headers:
                response.headers[header] = value
        
        # Add production headers (HSTS)
        if self.production:
            for header, value in self.PRODUCTION_HEADERS.items():
                response.headers[header] = value
        
        # Add Content Security Policy
        if self.custom_csp:
            response.headers["Content-Security-Policy"] = self.custom_csp
        else:
            response.headers["Content-Security-Policy"] = self._default_csp()
        
        # Override X-Frame-Options if frame ancestors specified
        if self.allowed_frame_ancestors:
            response.headers["X-Frame-Options"] = f"ALLOW-FROM {self.allowed_frame_ancestors}"
            response.headers["Content-Security-Policy"] = (
                f"frame-ancestors {self.allowed_frame_ancestors}"
            )
        
        return response
    
    def _default_csp(self) -> str:
        """
        Default Content Security Policy.
        Restrictive but allows typical API/WebSocket usage.
        """
        directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline'",  # Allow inline for error pages
            "style-src 'self' 'unsafe-inline'",   # Allow inline styles
            "img-src 'self' data: blob:",          # Allow data URIs for images
            "font-src 'self'",
            "connect-src 'self' ws: wss:",         # Allow WebSocket connections
            "frame-ancestors 'none'",
            "form-action 'self'",
            "base-uri 'self'",
        ]
        return "; ".join(directives)
