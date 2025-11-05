"""
Security middleware for input sanitization and request validation
"""
import json
from typing import Dict, Any
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.utils.logger import get_logger
from app.core.security import InputSanitizer
from app.core.exceptions import ValidationError

logger = get_logger(__name__)


class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Middleware for input sanitization and security validation
    
    Automatically sanitizes text inputs in request bodies and validates
    request size limits to prevent DoS attacks.
    """
    
    # Maximum request body size (50MB)
    MAX_REQUEST_SIZE = 50 * 1024 * 1024
    
    # Paths that require input sanitization
    SANITIZE_PATHS = {
        "/api/v1/analyze",
        "/api/v1/upload"
    }
    
    def __init__(self, app):
        super().__init__(app)
        self.sanitizer = InputSanitizer()
    
    async def dispatch(self, request: Request, call_next):
        """Process request with security validation and input sanitization"""
        
        try:
            # Validate request size
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > self.MAX_REQUEST_SIZE:
                logger.warning(
                    "request_size_exceeded",
                    content_length=content_length,
                    max_size=self.MAX_REQUEST_SIZE,
                    path=request.url.path
                )
                return JSONResponse(
                    status_code=413,
                    content={
                        "error_code": "REQUEST_TOO_LARGE",
                        "message": f"Request size exceeds maximum allowed size of {self.MAX_REQUEST_SIZE} bytes",
                        "details": {
                            "content_length": int(content_length),
                            "max_size": self.MAX_REQUEST_SIZE
                        }
                    }
                )
            
            # Apply input sanitization for specific endpoints
            if self._should_sanitize(request):
                await self._sanitize_request_body(request)
            
            # Process request
            response = await call_next(request)
            
            # Add security headers
            self._add_security_headers(response)
            
            return response
            
        except ValidationError as e:
            logger.warning(
                "input_validation_failed",
                path=request.url.path,
                error=str(e),
                request_id=getattr(request.state, 'request_id', None)
            )
            return JSONResponse(
                status_code=400,
                content={
                    "error_code": e.error_code,
                    "message": e.message,
                    "details": e.details,
                    "request_id": getattr(request.state, 'request_id', None)
                }
            )
        except Exception as e:
            logger.error(
                "security_middleware_error",
                path=request.url.path,
                error=str(e),
                request_id=getattr(request.state, 'request_id', None)
            )
            return JSONResponse(
                status_code=500,
                content={
                    "error_code": "SECURITY_ERROR",
                    "message": "Security validation failed",
                    "request_id": getattr(request.state, 'request_id', None)
                }
            )
    
    def _should_sanitize(self, request: Request) -> bool:
        """Check if request requires input sanitization"""
        return any(
            request.url.path.startswith(path) 
            for path in self.SANITIZE_PATHS
        )
    
    async def _sanitize_request_body(self, request: Request):
        """
        Sanitize JSON request body for text inputs
        
        This method modifies the request body to sanitize text fields
        that could contain harmful content.
        """
        if request.headers.get("content-type", "").startswith("application/json"):
            try:
                # Read and parse JSON body
                body = await request.body()
                if body:
                    data = json.loads(body)
                    
                    # Sanitize text fields
                    sanitized_data = self._sanitize_json_data(data)
                    
                    # Replace request body with sanitized version
                    sanitized_body = json.dumps(sanitized_data).encode()
                    
                    # Store sanitized body for route handlers
                    request._body = sanitized_body
                    
                    logger.debug(
                        "request_body_sanitized",
                        path=request.url.path,
                        original_size=len(body),
                        sanitized_size=len(sanitized_body)
                    )
                    
            except json.JSONDecodeError:
                # Invalid JSON will be handled by FastAPI validation
                pass
            except Exception as e:
                logger.warning(
                    "request_sanitization_failed",
                    path=request.url.path,
                    error=str(e)
                )
    
    def _sanitize_json_data(self, data: Any) -> Any:
        """
        Recursively sanitize JSON data structure
        
        Args:
            data: JSON data (dict, list, or primitive)
            
        Returns:
            Sanitized data structure
        """
        if isinstance(data, dict):
            return {
                key: self._sanitize_json_data(value)
                for key, value in data.items()
            }
        elif isinstance(data, list):
            return [self._sanitize_json_data(item) for item in data]
        elif isinstance(data, str):
            # Sanitize string values
            try:
                # Use different max lengths based on expected content type
                if len(data) > 10000:  # Likely job description or resume text
                    return self.sanitizer.sanitize_text_input(data)
                else:
                    # Basic sanitization for other string fields
                    return self.sanitizer.sanitize_text_input(data, max_length=1000)
            except ValidationError:
                # If sanitization fails, return empty string
                logger.warning(
                    "string_sanitization_failed",
                    string_preview=data[:100] if len(data) > 100 else data
                )
                return ""
        else:
            # Return primitive values as-is
            return data
    
    def _add_security_headers(self, response: Response):
        """Add security headers to response"""
        
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Enable XSS protection
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Content Security Policy (basic)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self'"
        )
        
        # HSTS (only in production)
        # response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"