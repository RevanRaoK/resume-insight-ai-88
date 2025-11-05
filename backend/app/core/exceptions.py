"""
Custom exception hierarchy for different error types
"""
from typing import Optional, Dict, Any


class SmartResumeException(Exception):
    """Base exception for all SmartResume errors"""
    
    def __init__(
        self, 
        message: str, 
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code or self.__class__.__name__.upper()
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(SmartResumeException):
    """Authentication and authorization errors"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            details=details
        )


class ValidationError(SmartResumeException):
    """Input validation errors"""
    
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        error_details = details or {}
        if field:
            error_details["field"] = field
        
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            details=error_details
        )


class DocumentProcessingError(SmartResumeException):
    """Errors during document ingestion and processing"""
    
    def __init__(
        self, 
        message: str, 
        file_name: Optional[str] = None,
        processing_stage: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if file_name:
            error_details["file_name"] = file_name
        if processing_stage:
            error_details["processing_stage"] = processing_stage
        
        super().__init__(
            message=message,
            error_code="DOCUMENT_PROCESSING_ERROR",
            details=error_details
        )


class UnsupportedFormatError(DocumentProcessingError):
    """Unsupported file format errors"""
    
    def __init__(self, file_type: str, supported_types: list, details: Optional[Dict[str, Any]] = None):
        error_details = details or {}
        error_details.update({
            "file_type": file_type,
            "supported_types": supported_types
        })
        
        super().__init__(
            message=f"Unsupported file format: {file_type}. Supported formats: {', '.join(supported_types)}",
            file_name=None,
            processing_stage="format_validation",
            details=error_details
        )


class FileSizeError(DocumentProcessingError):
    """File size limit exceeded errors"""
    
    def __init__(self, file_size: int, max_size: int, details: Optional[Dict[str, Any]] = None):
        error_details = details or {}
        error_details.update({
            "file_size": file_size,
            "max_size": max_size
        })
        
        super().__init__(
            message=f"File size {file_size} bytes exceeds maximum allowed size of {max_size} bytes",
            file_name=None,
            processing_stage="size_validation",
            details=error_details
        )


class NLUProcessingError(SmartResumeException):
    """Errors during Natural Language Understanding processing"""
    
    def __init__(
        self, 
        message: str, 
        model_name: Optional[str] = None,
        processing_stage: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if model_name:
            error_details["model_name"] = model_name
        if processing_stage:
            error_details["processing_stage"] = processing_stage
        
        super().__init__(
            message=message,
            error_code="NLU_PROCESSING_ERROR",
            details=error_details
        )


class ModelLoadError(NLUProcessingError):
    """ML model loading errors"""
    
    def __init__(self, model_name: str, error_message: str, details: Optional[Dict[str, Any]] = None):
        error_details = details or {}
        error_details["original_error"] = error_message
        
        super().__init__(
            message=f"Failed to load model {model_name}: {error_message}",
            model_name=model_name,
            processing_stage="model_loading",
            error_code="MODEL_LOAD_ERROR",
            details=error_details
        )


class SemanticAnalysisError(SmartResumeException):
    """Errors during semantic analysis and scoring"""
    
    def __init__(
        self, 
        message: str, 
        analysis_stage: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if analysis_stage:
            error_details["analysis_stage"] = analysis_stage
        
        super().__init__(
            message=message,
            error_code="SEMANTIC_ANALYSIS_ERROR",
            details=error_details
        )


class EmbeddingGenerationError(SemanticAnalysisError):
    """Errors during embedding generation"""
    
    def __init__(self, text_length: int, error_message: str, details: Optional[Dict[str, Any]] = None):
        error_details = details or {}
        error_details.update({
            "text_length": text_length,
            "original_error": error_message
        })
        
        super().__init__(
            message=f"Failed to generate embeddings for text of length {text_length}: {error_message}",
            analysis_stage="embedding_generation",
            error_code="EMBEDDING_GENERATION_ERROR",
            details=error_details
        )


class AIServiceError(SmartResumeException):
    """Errors from AI feedback generation services"""
    
    def __init__(
        self, 
        message: str, 
        service_name: Optional[str] = None,
        api_response_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if service_name:
            error_details["service_name"] = service_name
        if api_response_code:
            error_details["api_response_code"] = api_response_code
        
        super().__init__(
            message=message,
            error_code="AI_SERVICE_ERROR",
            details=error_details
        )


class APIRateLimitError(AIServiceError):
    """API rate limit exceeded errors"""
    
    def __init__(self, service_name: str, retry_after: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        error_details = details or {}
        if retry_after:
            error_details["retry_after"] = retry_after
        
        super().__init__(
            message=f"Rate limit exceeded for {service_name}",
            service_name=service_name,
            details=error_details
        )


class DatabaseError(SmartResumeException):
    """Database operation errors"""
    
    def __init__(
        self, 
        message: str, 
        operation: Optional[str] = None,
        table: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if operation:
            error_details["operation"] = operation
        if table:
            error_details["table"] = table
        
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            details=error_details
        )


class ConnectionError(DatabaseError):
    """Database connection errors"""
    
    def __init__(self, connection_string: str, error_message: str, details: Optional[Dict[str, Any]] = None):
        error_details = details or {}
        error_details["original_error"] = error_message
        
        super().__init__(
            message=f"Failed to connect to database: {error_message}",
            operation="connection",
            error_code="DATABASE_CONNECTION_ERROR",
            details=error_details
        )


class RateLimitError(SmartResumeException):
    """Rate limiting errors"""
    
    def __init__(
        self, 
        user_id: str, 
        limit: int, 
        window: int,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        error_details.update({
            "user_id": user_id,
            "limit": limit,
            "window": window
        })
        
        super().__init__(
            message=f"Rate limit exceeded: {limit} requests per {window} seconds",
            error_code="RATE_LIMIT_ERROR",
            details=error_details
        )