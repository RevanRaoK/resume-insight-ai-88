"""
Monitoring middleware for automatic metrics collection
"""
import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.utils.logger import get_logger
from app.utils.metrics import metrics_collector, monitor_performance

logger = get_logger(__name__)


class MonitoringMiddleware(BaseHTTPMiddleware):
    """
    Middleware for automatic request monitoring and metrics collection
    """
    
    def __init__(self, app, collect_detailed_metrics: bool = True):
        super().__init__(app)
        self.collect_detailed_metrics = collect_detailed_metrics
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with comprehensive monitoring
        
        Args:
            request: FastAPI request object
            call_next: Next middleware/handler in the chain
            
        Returns:
            Response with monitoring data
        """
        # Generate unique request ID for tracing
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Extract request information
        method = request.method
        path = request.url.path
        endpoint = f"{method} {path}"
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Start timing
        start_time = time.time()
        
        # Log request start
        logger.info(
            "request_started",
            request_id=request_id,
            method=method,
            path=path,
            client_ip=client_ip,
            user_agent=user_agent
        )
        
        # Track user session if authenticated
        user_id = None
        if hasattr(request.state, 'user_id'):
            user_id = request.state.user_id
            await metrics_collector.start_user_session(user_id)
        
        response = None
        success = True
        error_type = None
        
        try:
            # Process request
            response = await call_next(request)
            
            # Check if response indicates an error
            if response.status_code >= 400:
                success = False
                error_type = f"http_{response.status_code}"
            
        except Exception as e:
            success = False
            error_type = type(e).__name__
            
            logger.error(
                "request_exception",
                request_id=request_id,
                method=method,
                path=path,
                error=str(e),
                error_type=error_type
            )
            
            # Re-raise the exception to be handled by FastAPI
            raise
        
        finally:
            # Calculate request duration
            duration = time.time() - start_time
            
            # Record metrics
            await self._record_request_metrics(
                endpoint=endpoint,
                duration=duration,
                success=success,
                status_code=response.status_code if response else 500,
                error_type=error_type,
                user_id=user_id
            )
            
            # Log request completion
            logger.info(
                "request_completed",
                request_id=request_id,
                method=method,
                path=path,
                status_code=response.status_code if response else 500,
                duration=duration,
                success=success,
                error_type=error_type
            )
        
        # Add monitoring headers to response
        if response:
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration:.3f}s"
        
        return response
    
    async def _record_request_metrics(
        self,
        endpoint: str,
        duration: float,
        success: bool,
        status_code: int,
        error_type: str = None,
        user_id: str = None
    ):
        """
        Record comprehensive request metrics
        
        Args:
            endpoint: API endpoint
            duration: Request duration in seconds
            success: Whether request was successful
            status_code: HTTP status code
            error_type: Type of error if any
            user_id: User ID if authenticated
        """
        # Record basic request latency
        await metrics_collector.record_request_latency(endpoint, duration, success)
        
        if self.collect_detailed_metrics:
            # Record status code metrics
            await metrics_collector.record_metric(
                "http_requests_total",
                1,
                labels={
                    "method": endpoint.split()[0],
                    "endpoint": endpoint.split()[1],
                    "status_code": str(status_code)
                }
            )
            
            # Record error metrics if applicable
            if not success and error_type:
                await metrics_collector.record_metric(
                    "http_errors_total",
                    1,
                    labels={
                        "endpoint": endpoint,
                        "error_type": error_type
                    }
                )
            
            # Record user-specific metrics if authenticated
            if user_id:
                await metrics_collector.record_metric(
                    "user_requests_total",
                    1,
                    labels={
                        "user_id": user_id,
                        "endpoint": endpoint
                    }
                )


class DatabaseMonitoringMixin:
    """
    Mixin for adding database monitoring to repository classes
    """
    
    async def _monitor_query(self, query_type: str, query_func: Callable, *args, **kwargs):
        """
        Monitor database query execution
        
        Args:
            query_type: Type of query (select, insert, update, delete)
            query_func: Database query function to execute
            *args: Arguments for the query function
            **kwargs: Keyword arguments for the query function
            
        Returns:
            Query result with monitoring
        """
        start_time = time.time()
        success = True
        
        try:
            result = await query_func(*args, **kwargs)
            return result
            
        except Exception as e:
            success = False
            
            logger.error(
                "database_query_error",
                query_type=query_type,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
            
        finally:
            duration = time.time() - start_time
            
            # Record database query metrics
            await metrics_collector.record_database_query_time(query_type, duration)
            
            # Record query success/failure
            await metrics_collector.record_metric(
                "database_queries_total",
                1,
                labels={
                    "query_type": query_type,
                    "status": "success" if success else "error"
                }
            )
            
            logger.debug(
                "database_query_completed",
                query_type=query_type,
                duration=duration,
                success=success
            )


class ExternalAPIMonitoringMixin:
    """
    Mixin for monitoring external API calls
    """
    
    async def _monitor_api_call(
        self, 
        api_name: str, 
        api_func: Callable, 
        *args, 
        **kwargs
    ):
        """
        Monitor external API call
        
        Args:
            api_name: Name of the external API
            api_func: API function to execute
            *args: Arguments for the API function
            **kwargs: Keyword arguments for the API function
            
        Returns:
            API result with monitoring
        """
        start_time = time.time()
        success = True
        
        try:
            result = await api_func(*args, **kwargs)
            return result
            
        except Exception as e:
            success = False
            
            logger.error(
                "external_api_error",
                api_name=api_name,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
            
        finally:
            duration = time.time() - start_time
            
            # Record external API metrics
            await metrics_collector.record_external_api_call(api_name, duration, success)
            
            logger.debug(
                "external_api_call_completed",
                api_name=api_name,
                duration=duration,
                success=success
            )


class ModelInferenceMonitoringMixin:
    """
    Mixin for monitoring ML model inference
    """
    
    async def _monitor_model_inference(
        self,
        model_name: str,
        inference_func: Callable,
        *args,
        **kwargs
    ):
        """
        Monitor ML model inference
        
        Args:
            model_name: Name of the ML model
            inference_func: Model inference function
            *args: Arguments for the inference function
            **kwargs: Keyword arguments for the inference function
            
        Returns:
            Inference result with monitoring
        """
        start_time = time.time()
        success = True
        
        try:
            result = await inference_func(*args, **kwargs)
            return result
            
        except Exception as e:
            success = False
            
            logger.error(
                "model_inference_error",
                model_name=model_name,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
            
        finally:
            duration = time.time() - start_time
            
            # Record model inference metrics
            await metrics_collector.record_model_inference_time(model_name, duration)
            
            # Record inference success/failure
            await metrics_collector.record_metric(
                "model_inferences_total",
                1,
                labels={
                    "model": model_name,
                    "status": "success" if success else "error"
                }
            )
            
            logger.debug(
                "model_inference_completed",
                model_name=model_name,
                duration=duration,
                success=success
            )