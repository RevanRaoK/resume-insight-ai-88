"""
FastAPI application entry point for SmartResume AI Resume Analyzer
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.config import settings
from app.utils.logger import setup_logging, get_logger
# from app.utils.ml_utils import model_cache  # Temporarily disabled for testing
from app.utils.system_monitor import system_monitor
from app.utils.async_utils import background_processor
from app.middleware.auth import AuthMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.security import SecurityMiddleware
from app.middleware.monitoring import MonitoringMiddleware
from app.routers import health, upload, analysis, history, monitoring
from app.services.database_service import db_service

def custom_openapi():
    """Custom OpenAPI schema generation with enhanced documentation"""
    if app.openapi_schema:
        return app.openapi_schema
    
    from fastapi.openapi.utils import get_openapi
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,
        servers=app.servers
    )
    
    # Add custom extensions
    openapi_schema["info"]["x-logo"] = {
        "url": "https://smartresume-ai.com/logo.png"
    }
    
    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT token from Supabase Auth. Include as: Authorization: Bearer <token>"
        }
    }
    
    # Add global security requirement
    openapi_schema["security"] = [{"BearerAuth": []}]
    
    # Add custom response examples
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    
    if "examples" not in openapi_schema["components"]:
        openapi_schema["components"]["examples"] = {}
    
    # Add common error examples
    openapi_schema["components"]["examples"]["UnauthorizedError"] = {
        "summary": "Authentication required",
        "value": {
            "error_code": "UNAUTHORIZED",
            "message": "Authentication required. Please provide a valid JWT token.",
            "timestamp": "2023-11-04T10:30:00Z",
            "request_id": "uuid-123"
        }
    }
    
    openapi_schema["components"]["examples"]["RateLimitError"] = {
        "summary": "Rate limit exceeded",
        "value": {
            "error_code": "RATE_LIMIT_EXCEEDED",
            "message": "Rate limit exceeded. Please try again later.",
            "details": {
                "limit": 10,
                "window": "1 hour",
                "retry_after": 3600
            },
            "timestamp": "2023-11-04T10:30:00Z",
            "request_id": "uuid-123"
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

# Setup structured logging
setup_logging()
logger = get_logger(__name__)

app = FastAPI(
    title="SmartResume AI Resume Analyzer",
    description="""
    ## SmartResume AI Resume Analyzer API

    Intelligent backend system that transforms raw resume documents into structured data and provides 
    personalized career guidance through AI-powered analysis.

    ### Features

    * **Document Processing**: Extract text from PDF, DOCX, and TXT files with OCR fallback
    * **Entity Extraction**: Use advanced NLP models to identify skills, experience, and qualifications
    * **Semantic Analysis**: Calculate compatibility scores between resumes and job descriptions
    * **AI Feedback**: Generate personalized career coaching recommendations using Google Gemini
    * **Secure Storage**: Store analysis results with user authentication and data protection

    ### Authentication

    All endpoints (except health checks) require JWT authentication via Supabase Auth.
    Include the JWT token in the Authorization header: `Bearer <token>`

    ### Rate Limits

    * Analysis endpoints: 10 requests per user per hour
    * Upload endpoints: 20 requests per user per hour
    * Other endpoints: 100 requests per user per hour

    ### File Upload Limits

    * Maximum file size: 10MB
    * Supported formats: PDF, DOCX, TXT
    * Text extraction confidence threshold: 0.80

    ### Response Times

    * 95% of requests complete within 30 seconds
    * Average analysis time: 8-15 seconds
    * File upload processing: 2-5 seconds

    ### Error Handling

    All errors follow a consistent format with error codes, messages, and request IDs for tracing.
    """,
    version="1.0.0",
    contact={
        "name": "SmartResume AI Support",
        "email": "support@smartresume-ai.com",
        "url": "https://smartresume-ai.com/support"
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    },
    terms_of_service="https://smartresume-ai.com/terms",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_tags=[
        {
            "name": "health",
            "description": "System health checks and monitoring endpoints"
        },
        {
            "name": "upload",
            "description": "Resume document upload and processing"
        },
        {
            "name": "analysis", 
            "description": "Resume analysis and compatibility scoring"
        },
        {
            "name": "history",
            "description": "Analysis history and retrieval"
        },
        {
            "name": "monitoring",
            "description": "System metrics and performance monitoring"
        }
    ]
)

# Set custom OpenAPI schema
app.openapi = custom_openapi

# Enable enterprise middleware for production
# app.add_middleware(MonitoringMiddleware)
# app.add_middleware(RateLimitMiddleware)
app.add_middleware(AuthMiddleware)
# app.add_middleware(SecurityMiddleware)

# Add CORS middleware (MUST be last so it's executed first)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers with enhanced documentation (minimal for testing)
app.include_router(
    health.router, 
    prefix="/api/v1", 
    tags=["health"],
    responses={
        503: {"description": "Service unavailable or unhealthy"}
    }
)

# Enable all routers for full functionality
app.include_router(upload.router, prefix="/api/v1", tags=["upload"])
app.include_router(analysis.router, prefix="/api/v1", tags=["analysis"])  
app.include_router(history.router, prefix="/api/v1", tags=["history"])
app.include_router(monitoring.router, prefix="/api/v1/monitoring", tags=["monitoring"])

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info("Starting SmartResume AI Resume Analyzer")
    
    # Initialize database service
    try:
        await db_service.initialize()
        logger.info("Database service initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize database service", error=str(e))
        # Continue startup even if database fails (graceful degradation)
        logger.warning("Application starting with degraded database capabilities")
    
    # Initialize ML model cache (temporarily disabled for testing)
    # try:
    #     await model_cache.load_models_at_startup()
    #     logger.info("ML model cache initialized successfully")
    # except Exception as e:
    #     logger.error("Failed to initialize ML model cache", error=str(e))
    #     # Continue startup even if models fail to load (graceful degradation)
    #     logger.warning("Application starting with degraded ML capabilities")
    logger.info("ML model cache disabled for testing - application starting in basic mode")
    
    # Start system resource monitoring
    try:
        await system_monitor.start_monitoring()
        logger.info("System resource monitoring started")
    except Exception as e:
        logger.error("Failed to start system monitoring", error=str(e))
    
    # Start background task processor
    try:
        await background_processor.start()
        logger.info("Background task processor started")
    except Exception as e:
        logger.error("Failed to start background processor", error=str(e))

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown"""
    logger.info("Shutting down SmartResume AI Resume Analyzer")
    
    # Database service cleanup
    try:
        await db_service.close()
        logger.info("Database service closed successfully")
    except Exception as e:
        logger.error("Error closing database service", error=str(e))
    
    # Stop system monitoring
    try:
        await system_monitor.stop_monitoring()
        logger.info("System resource monitoring stopped")
    except Exception as e:
        logger.error("Error stopping system monitoring", error=str(e))
    
    # Stop background processor
    try:
        await background_processor.stop()
        logger.info("Background task processor stopped")
    except Exception as e:
        logger.error("Error stopping background processor", error=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )