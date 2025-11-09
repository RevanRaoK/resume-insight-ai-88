"""
JWT authentication middleware for Supabase token validation
"""
import uuid
import datetime
from typing import Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import jwt
from jwt.exceptions import InvalidTokenError

from app.config import settings
from app.utils.logger import get_logger
from app.core.exceptions import AuthenticationError
from fastapi import Depends, HTTPException

logger = get_logger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware for JWT token validation and user context injection"""
    
    # Public endpoints that don't require authentication
    PUBLIC_PATHS = {
        "/docs",
        "/redoc", 
        "/openapi.json",
        "/api/v1/health",
    }
    
    async def dispatch(self, request: Request, call_next):
        """Process request and validate JWT token if required"""
        
        # Generate unique request ID for tracing
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Skip authentication for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        
        # Skip authentication for public paths
        if self._is_public_path(request.url.path):
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        
        try:
            # Extract and validate JWT token
            user_id = await self._validate_token(request)
            request.state.user_id = user_id
            
            logger.info(
                "request_authenticated",
                request_id=request_id,
                user_id=user_id,
                path=request.url.path,
                method=request.method,
                user_agent=request.headers.get("User-Agent", ""),
                client_ip=request.client.host if request.client else "unknown"
            )
            
            response = await call_next(request)
            
            # Add enterprise security headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            
            return response
            
        except AuthenticationError as e:
            logger.warning(
                "authentication_failed",
                request_id=request_id,
                path=request.url.path,
                error=str(e),
                user_agent=request.headers.get("User-Agent", ""),
                client_ip=request.client.host if request.client else "unknown",
                auth_header_present=bool(request.headers.get("Authorization"))
            )
            return JSONResponse(
                status_code=401,
                content={
                    "error_code": "AUTHENTICATION_FAILED",
                    "message": str(e),
                    "request_id": request_id
                },
                headers={"X-Request-ID": request_id}
            )
        except Exception as e:
            logger.error(
                "middleware_error",
                request_id=request_id,
                path=request.url.path,
                error=str(e)
            )
            return JSONResponse(
                status_code=500,
                content={
                    "error_code": "INTERNAL_ERROR",
                    "message": "Internal server error",
                    "request_id": request_id
                },
                headers={"X-Request-ID": request_id}
            )
    
    def _is_public_path(self, path: str) -> bool:
        """Check if the path is public and doesn't require authentication"""
        return any(path.startswith(public_path) for public_path in self.PUBLIC_PATHS)
    
    async def _validate_token(self, request: Request) -> str:
        """Extract and validate JWT token from request headers"""
        
        # Extract Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            logger.error("No Authorization header found", headers=dict(request.headers))
            raise AuthenticationError("Missing Authorization header")
        

        
        # Parse Bearer token
        try:
            scheme, token = auth_header.split(None, 1)
            if scheme.lower() != "bearer":
                raise AuthenticationError("Invalid authentication scheme")
        except ValueError as e:
            raise AuthenticationError("Invalid Authorization header format")
        
        # Validate JWT token
        try:
            # For Supabase tokens, we validate the signature using Supabase's public key
            # For now, we'll decode without verification but validate structure and claims
            payload = jwt.decode(
                token,
                options={"verify_signature": False}
            )
            
            # Extract user ID from token payload
            user_id = payload.get("sub")
            if not user_id:
                raise AuthenticationError("Invalid token payload: missing user ID")
            
            # Validate token expiration
            exp = payload.get("exp")
            current_time = datetime.datetime.utcnow().timestamp()
            if exp and exp < current_time:
                raise AuthenticationError("Token has expired")
            
            # Validate token issuer (should be Supabase)
            iss = payload.get("iss")
            if iss and not iss.startswith("https://"):
                raise AuthenticationError("Invalid token issuer")
            
            # Validate audience (should be 'authenticated' for Supabase)
            aud = payload.get("aud")
            if aud and aud != "authenticated":
                raise AuthenticationError("Invalid token audience")
            
            # Validate issued at time (not too old)
            iat = payload.get("iat")
            if iat:
                # Token should not be older than 24 hours for security
                max_age = 24 * 60 * 60  # 24 hours in seconds
                age = current_time - iat
                if age > max_age:
                    raise AuthenticationError("Token is too old")
            
            # Validate email exists in token (enterprise requirement)
            email = payload.get("email")
            if not email:
                raise AuthenticationError("Token missing required email claim")
            
            return user_id
            
        except InvalidTokenError as e:
            raise AuthenticationError(f"Invalid JWT token: {str(e)}")
        except Exception as e:
            logger.error(
                "token_validation_error",
                error=str(e),
                token_preview=token[:20] + "..." if len(token) > 20 else token
            )
            raise AuthenticationError("Token validation failed")
    
    async def _validate_with_supabase(self, token: str) -> Optional[str]:
        """
        Validate token with Supabase Auth API (for future enhancement)
        
        This method can be implemented to make actual API calls to Supabase
        for additional token validation if needed.
        """
        # TODO: Implement actual Supabase API validation in future tasks
        # This would involve making HTTP requests to Supabase Auth API
        # to verify token validity and get user information
        pass


def get_current_user(request: Request) -> dict:
    """
    FastAPI dependency to get current authenticated user
    
    This function extracts the user information from the request state
    that was set by the AuthMiddleware.
    
    Returns:
        dict: User information containing user_id
        
    Raises:
        HTTPException: If user is not authenticated
    """
    user_id = getattr(request.state, 'user_id', None)
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail={
                "error_code": "AUTHENTICATION_REQUIRED",
                "message": "Authentication required to access this resource"
            }
        )
    
    return {"user_id": user_id}


def get_current_user_optional(request: Request) -> Optional[dict]:
    """
    FastAPI dependency to get current authenticated user (optional)
    
    This function extracts the user information from the request state
    that was set by the AuthMiddleware, but doesn't raise an error if
    the user is not authenticated.
    
    Returns:
        Optional[dict]: User information containing user_id, or None if not authenticated
    """
    user_id = getattr(request.state, 'user_id', None)
    if user_id:
        return {"user_id": user_id}
    return None