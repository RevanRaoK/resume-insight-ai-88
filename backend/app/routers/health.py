"""
Health check endpoints with comprehensive system monitoring
"""
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, HTTPException
from app.utils.logger import get_logger
# from app.services.database_service import db_service  # Temporarily disabled
# from app.utils.ml_utils import model_cache  # Disabled for testing
from app.services.ai_service import ai_service

logger = get_logger(__name__)
router = APIRouter()


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Basic health check endpoint
    
    Provides a quick health status check for load balancers and monitoring systems.
    Returns basic service information and overall status.
    
    Requirements: 6.1, 6.6
    """
    logger.info("health_check_requested")
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "SmartResume AI Resume Analyzer",
        "version": "1.0.0"
    }


@router.get("/health/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """
    Comprehensive health check including all dependencies
    
    Performs health checks on all critical system components:
    - Database connectivity and performance
    - ML model availability and functionality
    - External API connectivity (Gemini)
    
    Returns detailed status for each component with appropriate HTTP status codes.
    
    Requirements: 6.1, 6.6
    """
    logger.info("detailed_health_check_requested")
    
    health_status = {
        "service": "SmartResume AI Resume Analyzer",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "status": "healthy",
        "checks": {}
    }
    
    # Database health check (disabled for testing)
    health_status["checks"]["database"] = {
        "status": "disabled",
        "message": "Database service disabled for testing",
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # ML Models health check (disabled for testing)
    health_status["checks"]["ml_models"] = {
        "status": "disabled",
        "message": "ML models disabled for testing",
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # External APIs health check (Gemini)
    try:
        api_health = await ai_service.health_check()
        health_status["checks"]["external_apis"] = api_health
        
        if api_health["status"] != "healthy":
            if health_status["status"] == "healthy":
                health_status["status"] = "degraded"
                
    except Exception as e:
        logger.error("External APIs health check failed", error=str(e))
        health_status["checks"]["external_apis"] = {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
        if health_status["status"] != "unhealthy":
            health_status["status"] = "degraded"
    
    # Return appropriate HTTP status code
    if health_status["status"] == "unhealthy":
        raise HTTPException(status_code=503, detail=health_status)
    elif health_status["status"] == "degraded":
        # Return 200 for degraded but still functional
        pass
    
    return health_status


@router.get("/health/database")
async def database_health_check() -> Dict[str, Any]:
    """
    Database-specific health check (disabled for testing)
    
    Returns status indicating database service is disabled for testing.
    
    Requirements: 6.1, 6.6
    """
    logger.info("database_health_check_requested")
    
    response = {
        "status": "disabled",
        "message": "Database service disabled for testing",
        "timestamp": datetime.utcnow().isoformat()
    }
    
    return response


@router.get("/health/models")
async def ml_models_health_check() -> Dict[str, Any]:
    """
    ML models health check (disabled for testing)
    
    Returns status indicating ML models are disabled for testing.
    
    Requirements: 6.1, 6.6
    """
    logger.info("ml_models_health_check_requested")
    
    response = {
        "status": "disabled",
        "message": "ML models disabled for testing",
        "timestamp": datetime.utcnow().isoformat()
    }
    
    return response


@router.get("/health/apis")
async def external_apis_health_check() -> Dict[str, Any]:
    """
    External APIs health check
    
    Checks connectivity and functionality of external services
    including Google Gemini API.
    
    Requirements: 6.1, 6.6
    """
    logger.info("external_apis_health_check_requested")
    
    try:
        api_health = await ai_service.health_check()
        
        if api_health["status"] != "healthy":
            raise HTTPException(status_code=503, detail=api_health)
        
        return api_health
        
    except Exception as e:
        logger.error("External APIs health check failed", error=str(e))
        error_response = {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
        raise HTTPException(status_code=503, detail=error_response)


@router.get("/metrics")
async def system_metrics() -> Dict[str, Any]:
    """
    System performance metrics endpoint
    
    Provides key performance indicators and system metrics
    for monitoring and alerting systems.
    
    Requirements: 6.1, 6.6
    """
    logger.info("system_metrics_requested")
    
    try:
        # Get database metrics
        db_health = await db_service.health_check()
        
        # Get ML model metrics
        model_info = model_cache.get_model_info()
        
        # Basic system metrics
        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "database": {
                "status": db_health.get("status", "unknown"),
                "pool_info": db_health.get("pool_info", {})
            },
            "ml_models": {
                "loaded_models": model_info.get("loaded_models", []),
                "model_health": model_info.get("model_health", {}),
                "memory_usage": model_info.get("memory_usage", {})
            },
            "service": {
                "name": "SmartResume AI Resume Analyzer",
                "version": "1.0.0",
                "uptime_check": "healthy"
            }
        }
        
        return metrics
        
    except Exception as e:
        logger.error("Failed to collect system metrics", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to collect system metrics",
                "details": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )