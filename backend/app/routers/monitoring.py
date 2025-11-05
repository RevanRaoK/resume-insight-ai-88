"""
Monitoring and metrics endpoints
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Query, HTTPException, Depends
from pydantic import BaseModel

from app.utils.logger import get_logger
from app.utils.metrics import metrics_collector, alerting_system
from app.utils.system_monitor import system_monitor
from app.utils.async_utils import background_processor
from app.middleware.auth import get_current_user_optional
from app.services.database_service import db_service

logger = get_logger(__name__)

router = APIRouter()


class MetricsSummaryResponse(BaseModel):
    """Response model for metrics summary"""
    timestamp: str
    performance_metrics: Dict[str, Any]
    current_metrics: Dict[str, Any]
    session_metrics: Dict[str, Any]


class AlertResponse(BaseModel):
    """Response model for alerts"""
    type: str
    severity: str
    message: str
    current_value: float
    threshold: float
    timestamp: str
    endpoint: Optional[str] = None


class SystemHealthResponse(BaseModel):
    """Response model for system health"""
    status: str
    timestamp: str
    components: Dict[str, Any]
    alerts: List[AlertResponse]
    performance_summary: Dict[str, Any]


@router.get("/metrics", response_model=MetricsSummaryResponse)
async def get_metrics_summary(
    current_user = Depends(get_current_user_optional)
) -> MetricsSummaryResponse:
    """
    Get comprehensive metrics summary
    
    Returns:
        Complete metrics summary including performance and session data
    """
    logger.info("metrics_summary_requested", user_id=str(current_user.id) if current_user else None)
    
    try:
        summary = await metrics_collector.get_metrics_summary()
        
        return MetricsSummaryResponse(
            timestamp=summary["timestamp"],
            performance_metrics=summary["performance_metrics"],
            current_metrics=summary["current_metrics"],
            session_metrics=summary["session_metrics"]
        )
        
    except Exception as e:
        logger.error("metrics_summary_error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve metrics summary: {str(e)}"
        )


@router.get("/metrics/{metric_name}")
async def get_metric_history(
    metric_name: str,
    hours: int = Query(default=1, ge=1, le=168),  # 1 hour to 1 week
    current_user = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """
    Get historical data for a specific metric
    
    Args:
        metric_name: Name of the metric to retrieve
        hours: Number of hours of history to retrieve (1-168)
        
    Returns:
        Historical metric data
    """
    logger.info(
        "metric_history_requested",
        metric_name=metric_name,
        hours=hours,
        user_id=str(current_user.id) if current_user else None
    )
    
    try:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        metric_points = await metrics_collector.get_metrics_for_period(
            metric_name, start_time, end_time
        )
        
        # Convert metric points to serializable format
        history_data = [
            {
                "value": point.value,
                "timestamp": point.timestamp.isoformat(),
                "labels": point.labels
            }
            for point in metric_points
        ]
        
        return {
            "metric_name": metric_name,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "data_points": len(history_data),
            "history": history_data
        }
        
    except Exception as e:
        logger.error(
            "metric_history_error",
            metric_name=metric_name,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve metric history: {str(e)}"
        )


@router.get("/alerts", response_model=List[AlertResponse])
async def get_active_alerts(
    current_user = Depends(get_current_user_optional)
) -> List[AlertResponse]:
    """
    Get currently active alerts
    
    Returns:
        List of active system alerts
    """
    logger.info("active_alerts_requested", user_id=str(current_user.id) if current_user else None)
    
    try:
        active_alerts = await alerting_system.check_alerts()
        
        return [
            AlertResponse(
                type=alert["type"],
                severity=alert["severity"],
                message=alert["message"],
                current_value=alert["current_value"],
                threshold=alert["threshold"],
                timestamp=alert["timestamp"],
                endpoint=alert.get("endpoint")
            )
            for alert in active_alerts
        ]
        
    except Exception as e:
        logger.error("active_alerts_error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve active alerts: {str(e)}"
        )


@router.get("/alerts/history")
async def get_alert_history(
    hours: int = Query(default=24, ge=1, le=168),  # 1 hour to 1 week
    current_user = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """
    Get alert history for the specified time period
    
    Args:
        hours: Number of hours of alert history to retrieve
        
    Returns:
        Historical alert data
    """
    logger.info(
        "alert_history_requested",
        hours=hours,
        user_id=str(current_user.id) if current_user else None
    )
    
    try:
        alert_history = alerting_system.get_alert_history(hours)
        
        return {
            "period_hours": hours,
            "total_alerts": len(alert_history),
            "alerts": alert_history
        }
        
    except Exception as e:
        logger.error("alert_history_error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve alert history: {str(e)}"
        )


@router.get("/health/detailed", response_model=SystemHealthResponse)
async def get_detailed_system_health(
    current_user = Depends(get_current_user_optional)
) -> SystemHealthResponse:
    """
    Get comprehensive system health status including all components
    
    Returns:
        Detailed system health information
    """
    logger.info("detailed_health_check_requested", user_id=str(current_user.id) if current_user else None)
    
    try:
        # Get database health
        db_health = await db_service.health_check()
        
        # Get metrics summary for performance data
        metrics_summary = await metrics_collector.get_metrics_summary()
        
        # Get active alerts
        active_alerts = await alerting_system.check_alerts()
        
        # Determine overall system status
        overall_status = "healthy"
        
        if db_health["status"] != "healthy":
            overall_status = "degraded"
        
        if any(alert["severity"] == "high" for alert in active_alerts):
            overall_status = "unhealthy"
        
        # Calculate performance summary
        performance_summary = _calculate_performance_summary(metrics_summary["performance_metrics"])
        
        return SystemHealthResponse(
            status=overall_status,
            timestamp=datetime.utcnow().isoformat(),
            components={
                "database": db_health,
                "metrics_collector": {
                    "status": "healthy",
                    "active_metrics": len(metrics_summary["current_metrics"]),
                    "session_count": metrics_summary["session_metrics"]["active_sessions"]
                }
            },
            alerts=[
                AlertResponse(
                    type=alert["type"],
                    severity=alert["severity"],
                    message=alert["message"],
                    current_value=alert["current_value"],
                    threshold=alert["threshold"],
                    timestamp=alert["timestamp"],
                    endpoint=alert.get("endpoint")
                )
                for alert in active_alerts
            ],
            performance_summary=performance_summary
        )
        
    except Exception as e:
        logger.error("detailed_health_check_error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve detailed system health: {str(e)}"
        )


@router.get("/performance/endpoints")
async def get_endpoint_performance(
    current_user = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """
    Get performance metrics for all endpoints
    
    Returns:
        Performance data for all monitored endpoints
    """
    logger.info("endpoint_performance_requested", user_id=str(current_user.id) if current_user else None)
    
    try:
        metrics_summary = await metrics_collector.get_metrics_summary()
        
        endpoint_performance = {}
        
        for endpoint, metrics in metrics_summary["performance_metrics"].items():
            endpoint_performance[endpoint] = {
                "request_count": metrics["request_count"],
                "error_rate": round(metrics["error_rate"], 2),
                "average_latency": round(metrics["average_latency"], 3),
                "p95_latency": round(metrics["p95_latency"], 3),
                "p99_latency": round(metrics["p99_latency"], 3),
                "status": _get_endpoint_status(metrics)
            }
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "endpoints": endpoint_performance,
            "summary": _calculate_performance_summary(metrics_summary["performance_metrics"])
        }
        
    except Exception as e:
        logger.error("endpoint_performance_error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve endpoint performance: {str(e)}"
        )


def _calculate_performance_summary(performance_metrics: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate overall performance summary from endpoint metrics
    
    Args:
        performance_metrics: Performance metrics by endpoint
        
    Returns:
        Summary performance statistics
    """
    if not performance_metrics:
        return {
            "total_requests": 0,
            "total_errors": 0,
            "overall_error_rate": 0.0,
            "average_response_time": 0.0,
            "slowest_endpoint": None,
            "highest_error_rate_endpoint": None
        }
    
    total_requests = sum(metrics["request_count"] for metrics in performance_metrics.values())
    total_errors = sum(metrics["error_count"] for metrics in performance_metrics.values())
    
    overall_error_rate = (total_errors / max(1, total_requests)) * 100
    
    # Calculate weighted average response time
    total_latency_weighted = sum(
        metrics["average_latency"] * metrics["request_count"]
        for metrics in performance_metrics.values()
    )
    average_response_time = total_latency_weighted / max(1, total_requests)
    
    # Find slowest endpoint
    slowest_endpoint = max(
        performance_metrics.items(),
        key=lambda x: x[1]["p95_latency"]
    )[0] if performance_metrics else None
    
    # Find endpoint with highest error rate
    highest_error_rate_endpoint = max(
        performance_metrics.items(),
        key=lambda x: x[1]["error_rate"]
    )[0] if performance_metrics else None
    
    return {
        "total_requests": total_requests,
        "total_errors": total_errors,
        "overall_error_rate": round(overall_error_rate, 2),
        "average_response_time": round(average_response_time, 3),
        "slowest_endpoint": slowest_endpoint,
        "highest_error_rate_endpoint": highest_error_rate_endpoint
    }


def _get_endpoint_status(metrics: Dict[str, Any]) -> str:
    """
    Determine endpoint status based on performance metrics
    
    Args:
        metrics: Performance metrics for the endpoint
        
    Returns:
        Status string (healthy, degraded, unhealthy)
    """
    error_rate = metrics["error_rate"]
    p95_latency = metrics["p95_latency"]
    
    if error_rate > 10 or p95_latency > 60:
        return "unhealthy"
    elif error_rate > 5 or p95_latency > 30:
        return "degraded"
    else:
        return "healthy"


@router.get("/system/resources")
async def get_system_resources(
    current_user = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """
    Get current system resource usage
    
    Returns:
        Current system resource information
    """
    logger.info("system_resources_requested", user_id=str(current_user.id) if current_user else None)
    
    try:
        system_status = await system_monitor.get_current_system_status()
        
        # Add background processor stats
        processor_stats = background_processor.get_stats()
        system_status["background_processor"] = processor_stats
        
        return system_status
        
    except Exception as e:
        logger.error("system_resources_error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve system resources: {str(e)}"
        )


@router.get("/system/status")
async def get_system_status_summary(
    current_user = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """
    Get summarized system status for dashboard
    
    Returns:
        Summarized system status information
    """
    logger.info("system_status_summary_requested", user_id=str(current_user.id) if current_user else None)
    
    try:
        # Get system resources
        system_status = await system_monitor.get_current_system_status()
        
        # Get metrics summary
        metrics_summary = await metrics_collector.get_metrics_summary()
        
        # Get database health
        db_health = await db_service.health_check()
        
        # Get active alerts
        active_alerts = await alerting_system.check_alerts()
        
        # Calculate overall health score
        health_score = _calculate_health_score(system_status, metrics_summary, db_health, active_alerts)
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_health": health_score,
            "system_summary": {
                "cpu_percent": system_status.get("cpu", {}).get("percent", 0),
                "memory_percent": system_status.get("memory", {}).get("percent", 0),
                "disk_percent": system_status.get("disk", {}).get("percent", 0)
            },
            "performance_summary": {
                "active_sessions": metrics_summary["session_metrics"]["active_sessions"],
                "total_requests": sum(
                    metrics["request_count"] 
                    for metrics in metrics_summary["performance_metrics"].values()
                ),
                "average_error_rate": sum(
                    metrics["error_rate"] 
                    for metrics in metrics_summary["performance_metrics"].values()
                ) / max(1, len(metrics_summary["performance_metrics"]))
            },
            "database_status": db_health["status"],
            "active_alerts": len(active_alerts),
            "high_severity_alerts": len([
                alert for alert in active_alerts 
                if alert["severity"] == "high"
            ])
        }
        
    except Exception as e:
        logger.error("system_status_summary_error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve system status summary: {str(e)}"
        )


def _calculate_health_score(
    system_status: Dict[str, Any],
    metrics_summary: Dict[str, Any],
    db_health: Dict[str, Any],
    active_alerts: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Calculate overall system health score
    
    Args:
        system_status: System resource status
        metrics_summary: Performance metrics summary
        db_health: Database health status
        active_alerts: List of active alerts
        
    Returns:
        Health score and status
    """
    score = 100
    status = "healthy"
    issues = []
    
    # Check system resources
    if "cpu" in system_status:
        cpu_percent = system_status["cpu"].get("percent", 0)
        if cpu_percent > 90:
            score -= 20
            issues.append("High CPU usage")
        elif cpu_percent > 70:
            score -= 10
            issues.append("Elevated CPU usage")
    
    if "memory" in system_status:
        memory_percent = system_status["memory"].get("percent", 0)
        if memory_percent > 90:
            score -= 20
            issues.append("High memory usage")
        elif memory_percent > 80:
            score -= 10
            issues.append("Elevated memory usage")
    
    if "disk" in system_status:
        disk_percent = system_status["disk"].get("percent", 0)
        if disk_percent > 95:
            score -= 15
            issues.append("Disk space critical")
        elif disk_percent > 85:
            score -= 5
            issues.append("Low disk space")
    
    # Check database health
    if db_health["status"] != "healthy":
        score -= 30
        issues.append("Database issues")
    
    # Check alerts
    high_severity_alerts = [alert for alert in active_alerts if alert["severity"] == "high"]
    medium_severity_alerts = [alert for alert in active_alerts if alert["severity"] == "medium"]
    
    score -= len(high_severity_alerts) * 15
    score -= len(medium_severity_alerts) * 5
    
    if high_severity_alerts:
        issues.extend([alert["message"] for alert in high_severity_alerts])
    
    # Determine status based on score
    if score >= 90:
        status = "healthy"
    elif score >= 70:
        status = "degraded"
    else:
        status = "unhealthy"
    
    return {
        "score": max(0, score),
        "status": status,
        "issues": issues
    }