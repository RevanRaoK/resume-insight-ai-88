"""
Rate limiting middleware for API endpoints
"""
import time
from typing import Dict, Optional
from collections import defaultdict, deque
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import settings
from app.utils.logger import get_logger
from app.core.exceptions import RateLimitError

logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using sliding window algorithm
    
    Implements per-user rate limiting for analysis endpoints with configurable
    limits and time windows.
    """
    
    def __init__(self, app, requests_per_hour: int = None, window_seconds: int = None):
        super().__init__(app)
        self.requests_per_hour = requests_per_hour or settings.RATE_LIMIT_REQUESTS
        self.window_seconds = window_seconds or settings.RATE_LIMIT_WINDOW
        
        # In-memory storage for request tracking
        # In production, this should use Redis or similar distributed cache
        self.user_requests: Dict[str, deque] = defaultdict(deque)
        
        # Endpoints that require rate limiting
        self.rate_limited_paths = {
            "/api/v1/analyze",
            "/api/v1/upload"
        }
        
        logger.info(
            "rate_limit_middleware_initialized",
            requests_per_hour=self.requests_per_hour,
            window_seconds=self.window_seconds
        )
    
    async def dispatch(self, request: Request, call_next):
        """Process request and apply rate limiting if required"""
        
        # Skip rate limiting for non-protected paths
        if not self._should_rate_limit(request):
            return await call_next(request)
        
        # Get user ID from request state (set by auth middleware)
        user_id = getattr(request.state, 'user_id', None)
        if not user_id:
            # If no user ID, skip rate limiting (auth middleware will handle)
            return await call_next(request)
        
        try:
            # Check and update rate limit
            self._check_rate_limit(user_id, request)
            
            # Process request
            response = await call_next(request)
            
            # Add rate limit headers to response
            remaining_requests = self._get_remaining_requests(user_id)
            reset_time = self._get_reset_time(user_id)
            
            response.headers["X-RateLimit-Limit"] = str(self.requests_per_hour)
            response.headers["X-RateLimit-Remaining"] = str(remaining_requests)
            response.headers["X-RateLimit-Reset"] = str(reset_time)
            
            return response
            
        except RateLimitError as e:
            logger.warning(
                "rate_limit_exceeded",
                user_id=user_id,
                path=request.url.path,
                method=request.method,
                limit=self.requests_per_hour,
                window=self.window_seconds
            )
            
            # Calculate retry after time
            retry_after = self._get_retry_after(user_id)
            
            return JSONResponse(
                status_code=429,
                content={
                    "error_code": "RATE_LIMIT_EXCEEDED",
                    "message": str(e),
                    "details": {
                        "limit": self.requests_per_hour,
                        "window_seconds": self.window_seconds,
                        "retry_after": retry_after
                    },
                    "request_id": getattr(request.state, 'request_id', None)
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(self.requests_per_hour),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + retry_after)
                }
            )
    
    def _should_rate_limit(self, request: Request) -> bool:
        """Check if the request path requires rate limiting"""
        return any(
            request.url.path.startswith(path) 
            for path in self.rate_limited_paths
        )
    
    def _check_rate_limit(self, user_id: str, request: Request):
        """
        Check if user has exceeded rate limit and update request count
        
        Args:
            user_id: User identifier
            request: FastAPI request object
            
        Raises:
            RateLimitError: If rate limit is exceeded
        """
        current_time = time.time()
        user_requests = self.user_requests[user_id]
        
        # Remove requests outside the time window
        cutoff_time = current_time - self.window_seconds
        while user_requests and user_requests[0] < cutoff_time:
            user_requests.popleft()
        
        # Check if limit is exceeded
        if len(user_requests) >= self.requests_per_hour:
            raise RateLimitError(
                user_id=user_id,
                limit=self.requests_per_hour,
                window=self.window_seconds
            )
        
        # Add current request timestamp
        user_requests.append(current_time)
        
        logger.debug(
            "rate_limit_check_passed",
            user_id=user_id,
            current_requests=len(user_requests),
            limit=self.requests_per_hour,
            path=request.url.path
        )
    
    def _get_remaining_requests(self, user_id: str) -> int:
        """Get number of remaining requests for user"""
        current_time = time.time()
        user_requests = self.user_requests[user_id]
        
        # Remove expired requests
        cutoff_time = current_time - self.window_seconds
        while user_requests and user_requests[0] < cutoff_time:
            user_requests.popleft()
        
        return max(0, self.requests_per_hour - len(user_requests))
    
    def _get_reset_time(self, user_id: str) -> int:
        """Get timestamp when rate limit resets for user"""
        user_requests = self.user_requests[user_id]
        if not user_requests:
            return int(time.time())
        
        # Reset time is when the oldest request expires
        oldest_request = user_requests[0]
        return int(oldest_request + self.window_seconds)
    
    def _get_retry_after(self, user_id: str) -> int:
        """Get seconds until user can make another request"""
        user_requests = self.user_requests[user_id]
        if not user_requests:
            return 0
        
        current_time = time.time()
        oldest_request = user_requests[0]
        retry_after = int((oldest_request + self.window_seconds) - current_time)
        
        return max(0, retry_after)
    
    def cleanup_expired_entries(self):
        """
        Cleanup expired entries to prevent memory leaks
        Should be called periodically in production
        """
        current_time = time.time()
        cutoff_time = current_time - self.window_seconds
        
        users_to_remove = []
        for user_id, requests in self.user_requests.items():
            # Remove expired requests
            while requests and requests[0] < cutoff_time:
                requests.popleft()
            
            # Mark empty queues for removal
            if not requests:
                users_to_remove.append(user_id)
        
        # Remove empty entries
        for user_id in users_to_remove:
            del self.user_requests[user_id]
        
        logger.debug(
            "rate_limit_cleanup_completed",
            users_cleaned=len(users_to_remove),
            active_users=len(self.user_requests)
        )


class InMemoryRateLimiter:
    """
    Simple in-memory rate limiter for development and testing
    
    Note: In production, use Redis-based rate limiting for distributed systems
    """
    
    def __init__(self):
        self.requests: Dict[str, deque] = defaultdict(deque)
    
    def is_allowed(
        self, 
        key: str, 
        limit: int, 
        window_seconds: int
    ) -> tuple[bool, Dict[str, int]]:
        """
        Check if request is allowed under rate limit
        
        Args:
            key: Unique identifier (usually user_id)
            limit: Maximum requests allowed
            window_seconds: Time window in seconds
            
        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        current_time = time.time()
        user_requests = self.requests[key]
        
        # Remove expired requests
        cutoff_time = current_time - window_seconds
        while user_requests and user_requests[0] < cutoff_time:
            user_requests.popleft()
        
        # Check if limit exceeded
        is_allowed = len(user_requests) < limit
        
        if is_allowed:
            user_requests.append(current_time)
        
        # Calculate rate limit info
        remaining = max(0, limit - len(user_requests))
        reset_time = int(user_requests[0] + window_seconds) if user_requests else int(current_time)
        retry_after = max(0, reset_time - int(current_time)) if not is_allowed else 0
        
        rate_limit_info = {
            "limit": limit,
            "remaining": remaining,
            "reset": reset_time,
            "retry_after": retry_after
        }
        
        return is_allowed, rate_limit_info