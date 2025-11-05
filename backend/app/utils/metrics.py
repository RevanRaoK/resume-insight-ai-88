"""
Comprehensive metrics collection and monitoring system
"""
import time
import asyncio
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from enum import Enum

from app.utils.logger import get_logger

logger = get_logger(__name__)


class MetricType(Enum):
    """Types of metrics that can be collected"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class MetricPoint:
    """Individual metric data point"""
    name: str
    value: float
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    metric_type: MetricType = MetricType.GAUGE


@dataclass
class PerformanceMetrics:
    """Performance metrics for requests and operations"""
    request_count: int = 0
    error_count: int = 0
    total_latency: float = 0.0
    min_latency: float = float('inf')
    max_latency: float = 0.0
    p50_latency: float = 0.0
    p95_latency: float = 0.0
    p99_latency: float = 0.0
    
    def add_latency(self, latency: float):
        """Add a latency measurement"""
        self.request_count += 1
        self.total_latency += latency
        self.min_latency = min(self.min_latency, latency)
        self.max_latency = max(self.max_latency, latency)
    
    def add_error(self):
        """Record an error"""
        self.error_count += 1
    
    @property
    def average_latency(self) -> float:
        """Calculate average latency"""
        return self.total_latency / max(1, self.request_count)
    
    @property
    def error_rate(self) -> float:
        """Calculate error rate as percentage"""
        return (self.error_count / max(1, self.request_count)) * 100


class MetricsCollector:
    """
    Comprehensive metrics collection system for performance monitoring
    """
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history))
        self.performance_metrics: Dict[str, PerformanceMetrics] = defaultdict(PerformanceMetrics)
        self.latency_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history))
        self.active_sessions: Dict[str, datetime] = {}
        self.session_count = 0
        self._lock = asyncio.Lock()
    
    async def record_metric(
        self, 
        name: str, 
        value: float, 
        metric_type: MetricType = MetricType.GAUGE,
        labels: Optional[Dict[str, str]] = None
    ):
        """
        Record a metric value
        
        Args:
            name: Metric name
            value: Metric value
            metric_type: Type of metric
            labels: Optional labels for the metric
        """
        async with self._lock:
            metric_point = MetricPoint(
                name=name,
                value=value,
                timestamp=datetime.utcnow(),
                labels=labels or {},
                metric_type=metric_type
            )
            
            self.metrics[name].append(metric_point)
            
            logger.debug(
                "metric_recorded",
                metric_name=name,
                metric_value=value,
                metric_type=metric_type.value,
                labels=labels
            )
    
    async def record_request_latency(self, endpoint: str, latency: float, success: bool = True):
        """
        Record request latency and update performance metrics
        
        Args:
            endpoint: API endpoint name
            latency: Request latency in seconds
            success: Whether the request was successful
        """
        async with self._lock:
            # Update performance metrics
            perf_metrics = self.performance_metrics[endpoint]
            perf_metrics.add_latency(latency)
            
            if not success:
                perf_metrics.add_error()
            
            # Store latency for percentile calculations
            self.latency_history[endpoint].append(latency)
            
            # Update percentiles
            if len(self.latency_history[endpoint]) > 0:
                sorted_latencies = sorted(self.latency_history[endpoint])
                count = len(sorted_latencies)
                
                perf_metrics.p50_latency = sorted_latencies[int(count * 0.5)]
                perf_metrics.p95_latency = sorted_latencies[int(count * 0.95)]
                perf_metrics.p99_latency = sorted_latencies[int(count * 0.99)]
            
            # Record as metric points
            await self.record_metric(f"{endpoint}_latency", latency, MetricType.TIMER)
            await self.record_metric(f"{endpoint}_requests_total", perf_metrics.request_count, MetricType.COUNTER)
            
            if not success:
                await self.record_metric(f"{endpoint}_errors_total", perf_metrics.error_count, MetricType.COUNTER)
    
    async def record_model_inference_time(self, model_name: str, inference_time: float):
        """
        Record ML model inference time
        
        Args:
            model_name: Name of the ML model
            inference_time: Inference time in seconds
        """
        await self.record_metric(
            f"model_inference_time",
            inference_time,
            MetricType.TIMER,
            labels={"model": model_name}
        )
        
        logger.debug(
            "model_inference_recorded",
            model_name=model_name,
            inference_time=inference_time
        )
    
    async def record_database_query_time(self, query_type: str, execution_time: float):
        """
        Record database query execution time
        
        Args:
            query_type: Type of database query (select, insert, update, delete)
            execution_time: Query execution time in seconds
        """
        await self.record_metric(
            f"database_query_time",
            execution_time,
            MetricType.TIMER,
            labels={"query_type": query_type}
        )
        
        logger.debug(
            "database_query_recorded",
            query_type=query_type,
            execution_time=execution_time
        )
    
    async def record_external_api_call(self, api_name: str, response_time: float, success: bool):
        """
        Record external API call metrics
        
        Args:
            api_name: Name of the external API
            response_time: API response time in seconds
            success: Whether the API call was successful
        """
        await self.record_metric(
            f"external_api_response_time",
            response_time,
            MetricType.TIMER,
            labels={"api": api_name}
        )
        
        await self.record_metric(
            f"external_api_calls_total",
            1,
            MetricType.COUNTER,
            labels={"api": api_name, "status": "success" if success else "error"}
        )
        
        logger.debug(
            "external_api_call_recorded",
            api_name=api_name,
            response_time=response_time,
            success=success
        )
    
    async def start_user_session(self, user_id: str):
        """
        Start tracking a user session
        
        Args:
            user_id: User identifier
        """
        async with self._lock:
            self.active_sessions[user_id] = datetime.utcnow()
            self.session_count += 1
            
            await self.record_metric("active_sessions", len(self.active_sessions), MetricType.GAUGE)
            await self.record_metric("total_sessions", self.session_count, MetricType.COUNTER)
    
    async def end_user_session(self, user_id: str):
        """
        End tracking a user session
        
        Args:
            user_id: User identifier
        """
        async with self._lock:
            if user_id in self.active_sessions:
                session_start = self.active_sessions.pop(user_id)
                session_duration = (datetime.utcnow() - session_start).total_seconds()
                
                await self.record_metric("session_duration", session_duration, MetricType.TIMER)
                await self.record_metric("active_sessions", len(self.active_sessions), MetricType.GAUGE)
    
    async def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive metrics summary
        
        Returns:
            Dictionary containing all collected metrics
        """
        async with self._lock:
            summary = {
                "timestamp": datetime.utcnow().isoformat(),
                "performance_metrics": {},
                "current_metrics": {},
                "session_metrics": {
                    "active_sessions": len(self.active_sessions),
                    "total_sessions": self.session_count
                }
            }
            
            # Performance metrics by endpoint
            for endpoint, metrics in self.performance_metrics.items():
                summary["performance_metrics"][endpoint] = {
                    "request_count": metrics.request_count,
                    "error_count": metrics.error_count,
                    "error_rate": metrics.error_rate,
                    "average_latency": metrics.average_latency,
                    "min_latency": metrics.min_latency,
                    "max_latency": metrics.max_latency,
                    "p50_latency": metrics.p50_latency,
                    "p95_latency": metrics.p95_latency,
                    "p99_latency": metrics.p99_latency
                }
            
            # Current metric values (latest values)
            for metric_name, metric_points in self.metrics.items():
                if metric_points:
                    latest_point = metric_points[-1]
                    summary["current_metrics"][metric_name] = {
                        "value": latest_point.value,
                        "timestamp": latest_point.timestamp.isoformat(),
                        "labels": latest_point.labels
                    }
            
            return summary
    
    async def get_metrics_for_period(
        self, 
        metric_name: str, 
        start_time: datetime, 
        end_time: datetime
    ) -> List[MetricPoint]:
        """
        Get metrics for a specific time period
        
        Args:
            metric_name: Name of the metric
            start_time: Start of the time period
            end_time: End of the time period
            
        Returns:
            List of metric points within the time period
        """
        async with self._lock:
            if metric_name not in self.metrics:
                return []
            
            return [
                point for point in self.metrics[metric_name]
                if start_time <= point.timestamp <= end_time
            ]


class PerformanceMonitor:
    """
    Performance monitoring context manager for automatic metric collection
    """
    
    def __init__(self, metrics_collector: MetricsCollector, operation_name: str):
        self.metrics_collector = metrics_collector
        self.operation_name = operation_name
        self.start_time = None
        self.success = True
    
    async def __aenter__(self):
        self.start_time = time.time()
        logger.debug("performance_monitoring_started", operation=self.operation_name)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            
            if exc_type is not None:
                self.success = False
                logger.error(
                    "performance_monitoring_error",
                    operation=self.operation_name,
                    duration=duration,
                    error=str(exc_val)
                )
            else:
                logger.debug(
                    "performance_monitoring_completed",
                    operation=self.operation_name,
                    duration=duration
                )
            
            # Record the performance metric
            await self.metrics_collector.record_request_latency(
                self.operation_name,
                duration,
                self.success
            )
    
    def mark_error(self):
        """Mark the operation as failed"""
        self.success = False


class AlertingSystem:
    """
    Alerting system for performance degradation and system failures
    """
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self.alert_thresholds = {
            "error_rate": 5.0,  # 5% error rate
            "response_time_p95": 30.0,  # 30 seconds P95 response time
            "active_sessions": 100,  # 100 concurrent sessions
            "database_connection_failures": 10  # 10 failed connections
        }
        self.alert_history: List[Dict[str, Any]] = []
        self.alert_cooldown = {}  # Prevent alert spam
        self.cooldown_period = 300  # 5 minutes cooldown
    
    async def check_alerts(self) -> List[Dict[str, Any]]:
        """
        Check for alert conditions and return active alerts
        
        Returns:
            List of active alerts
        """
        current_time = datetime.utcnow()
        active_alerts = []
        
        metrics_summary = await self.metrics_collector.get_metrics_summary()
        
        # Check error rate alerts
        for endpoint, perf_metrics in metrics_summary["performance_metrics"].items():
            error_rate = perf_metrics["error_rate"]
            
            if error_rate > self.alert_thresholds["error_rate"]:
                alert_key = f"error_rate_{endpoint}"
                
                if self._should_send_alert(alert_key, current_time):
                    alert = {
                        "type": "error_rate",
                        "severity": "high" if error_rate > 10 else "medium",
                        "message": f"High error rate on {endpoint}: {error_rate:.2f}%",
                        "endpoint": endpoint,
                        "current_value": error_rate,
                        "threshold": self.alert_thresholds["error_rate"],
                        "timestamp": current_time.isoformat()
                    }
                    
                    active_alerts.append(alert)
                    self.alert_cooldown[alert_key] = current_time
                    
                    logger.warning(
                        "alert_triggered",
                        alert_type="error_rate",
                        endpoint=endpoint,
                        error_rate=error_rate
                    )
            
            # Check response time alerts
            p95_latency = perf_metrics["p95_latency"]
            
            if p95_latency > self.alert_thresholds["response_time_p95"]:
                alert_key = f"response_time_{endpoint}"
                
                if self._should_send_alert(alert_key, current_time):
                    alert = {
                        "type": "response_time",
                        "severity": "high" if p95_latency > 60 else "medium",
                        "message": f"High response time on {endpoint}: {p95_latency:.2f}s",
                        "endpoint": endpoint,
                        "current_value": p95_latency,
                        "threshold": self.alert_thresholds["response_time_p95"],
                        "timestamp": current_time.isoformat()
                    }
                    
                    active_alerts.append(alert)
                    self.alert_cooldown[alert_key] = current_time
                    
                    logger.warning(
                        "alert_triggered",
                        alert_type="response_time",
                        endpoint=endpoint,
                        p95_latency=p95_latency
                    )
        
        # Check session count alerts
        active_sessions = metrics_summary["session_metrics"]["active_sessions"]
        
        if active_sessions > self.alert_thresholds["active_sessions"]:
            alert_key = "active_sessions"
            
            if self._should_send_alert(alert_key, current_time):
                alert = {
                    "type": "active_sessions",
                    "severity": "medium",
                    "message": f"High number of active sessions: {active_sessions}",
                    "current_value": active_sessions,
                    "threshold": self.alert_thresholds["active_sessions"],
                    "timestamp": current_time.isoformat()
                }
                
                active_alerts.append(alert)
                self.alert_cooldown[alert_key] = current_time
                
                logger.warning(
                    "alert_triggered",
                    alert_type="active_sessions",
                    active_sessions=active_sessions
                )
        
        # Store alerts in history
        self.alert_history.extend(active_alerts)
        
        # Keep only recent alerts (last 24 hours)
        cutoff_time = current_time - timedelta(hours=24)
        self.alert_history = [
            alert for alert in self.alert_history
            if datetime.fromisoformat(alert["timestamp"]) > cutoff_time
        ]
        
        return active_alerts
    
    def _should_send_alert(self, alert_key: str, current_time: datetime) -> bool:
        """
        Check if an alert should be sent based on cooldown period
        
        Args:
            alert_key: Unique key for the alert
            current_time: Current timestamp
            
        Returns:
            True if alert should be sent, False if in cooldown
        """
        if alert_key not in self.alert_cooldown:
            return True
        
        last_alert_time = self.alert_cooldown[alert_key]
        time_since_last_alert = (current_time - last_alert_time).total_seconds()
        
        return time_since_last_alert > self.cooldown_period
    
    def get_alert_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get alert history for the specified number of hours
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            List of alerts from the specified time period
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        return [
            alert for alert in self.alert_history
            if datetime.fromisoformat(alert["timestamp"]) > cutoff_time
        ]


# Global instances
metrics_collector = MetricsCollector()
alerting_system = AlertingSystem(metrics_collector)


def monitor_performance(operation_name: str):
    """
    Decorator for automatic performance monitoring
    
    Args:
        operation_name: Name of the operation being monitored
        
    Returns:
        Decorated function with performance monitoring
    """
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                async with PerformanceMonitor(metrics_collector, operation_name) as monitor:
                    try:
                        return await func(*args, **kwargs)
                    except Exception as e:
                        monitor.mark_error()
                        raise
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                # For sync functions, we'll need to handle differently
                start_time = time.time()
                success = True
                
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    success = False
                    raise
                finally:
                    duration = time.time() - start_time
                    # Note: This won't work for sync functions with async metrics
                    # In practice, all our functions should be async
                    logger.debug(
                        "sync_performance_monitoring",
                        operation=operation_name,
                        duration=duration,
                        success=success
                    )
            
            return sync_wrapper
    
    return decorator