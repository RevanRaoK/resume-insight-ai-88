"""
File processing utilities for secure file handling
"""
import os
import tempfile
from typing import Dict, Any, Optional
from fastapi import UploadFile

from app.utils.logger import get_logger
from app.core.security import FileValidator, TemporaryFileManager, InputSanitizer
from app.core.exceptions import ValidationError, FileSizeError, UnsupportedFormatError
from app.config import settings

logger = get_logger(__name__)


async def validate_upload_file(upload_file: UploadFile) -> Dict[str, Any]:
    """
    Validate uploaded file for security and format compliance
    
    Args:
        upload_file: FastAPI UploadFile object
        
    Returns:
        Dictionary with validation results and file metadata
        
    Raises:
        ValidationError: If file validation fails
        FileSizeError: If file exceeds size limits
        UnsupportedFormatError: If file type is not supported
    """
    if not upload_file.filename:
        raise ValidationError("Filename is required")
    
    # Read file content
    content = await upload_file.read()
    
    # Reset file pointer for potential future reads
    await upload_file.seek(0)
    
    # Validate filename
    safe_filename = InputSanitizer.validate_filename(upload_file.filename)
    
    # Perform security validation
    validator = FileValidator()
    validation_result = validator.validate_file_security(
        file_content=content,
        filename=safe_filename,
        expected_mime_types=settings.ALLOWED_FILE_TYPES
    )
    
    logger.info(
        "file_validation_completed",
        filename=safe_filename,
        file_size=validation_result["file_size"],
        mime_type=validation_result["detected_mime_type"],
        security_passed=True
    )
    
    return {
        "original_filename": upload_file.filename,
        "safe_filename": safe_filename,
        "content": content,
        "content_type": upload_file.content_type,
        **validation_result
    }


def create_secure_temp_file(content: bytes, filename: str) -> str:
    """
    Create a secure temporary file with proper cleanup tracking
    
    Args:
        content: File content bytes
        filename: Original filename (used for extension detection)
        
    Returns:
        Path to temporary file
    """
    # Extract file extension for proper handling
    _, ext = os.path.splitext(filename)
    
    # Create temporary file with proper extension
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
        temp_file.write(content)
        temp_path = temp_file.name
    
    logger.debug(
        "secure_temp_file_created",
        temp_path=temp_path,
        original_filename=filename,
        file_size=len(content)
    )
    
    return temp_path


def get_file_extension(filename: str) -> str:
    """
    Safely extract file extension from filename
    
    Args:
        filename: Input filename
        
    Returns:
        File extension (including dot) or empty string if no extension
    """
    if not filename:
        return ""
    
    # Use os.path.splitext for reliable extension extraction
    _, ext = os.path.splitext(filename.lower())
    return ext


def is_supported_file_type(mime_type: str) -> bool:
    """
    Check if MIME type is supported for processing
    
    Args:
        mime_type: MIME type string
        
    Returns:
        True if supported, False otherwise
    """
    return mime_type in settings.ALLOWED_FILE_TYPES


def get_max_file_size() -> int:
    """
    Get maximum allowed file size from configuration
    
    Returns:
        Maximum file size in bytes
    """
    return settings.MAX_FILE_SIZE


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format
    
    Args:
        size_bytes: File size in bytes
        
    Returns:
        Formatted file size string
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"