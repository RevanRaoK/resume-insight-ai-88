"""
Security utilities for input sanitization and validation
"""
import re
import html
import tempfile
import os
from typing import Optional, List, Dict, Any
from pathlib import Path

# Try to import magic, fall back to mimetypes if not available
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    import mimetypes
    MAGIC_AVAILABLE = False

from app.utils.logger import get_logger
from app.config import settings
from app.core.exceptions import ValidationError, FileSizeError, UnsupportedFormatError

logger = get_logger(__name__)


class InputSanitizer:
    """Utilities for sanitizing user inputs to prevent security vulnerabilities"""
    
    # Patterns for potentially harmful content
    HTML_TAG_PATTERN = re.compile(r'<[^>]+>')
    SCRIPT_PATTERN = re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL)
    SQL_INJECTION_PATTERNS = [
        re.compile(r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)", re.IGNORECASE),
        re.compile(r"(\b(OR|AND)\s+\d+\s*=\s*\d+)", re.IGNORECASE),
        re.compile(r"['\";]", re.IGNORECASE)
    ]
    
    # Maximum text lengths to prevent DoS attacks
    MAX_TEXT_LENGTH = 50000  # 50KB of text
    MAX_JOB_DESCRIPTION_LENGTH = 10000  # 10KB for job descriptions
    
    @classmethod
    def sanitize_text_input(cls, text: str, max_length: Optional[int] = None) -> str:
        """
        Sanitize text input by removing potentially harmful content
        
        Args:
            text: Input text to sanitize
            max_length: Maximum allowed length (defaults to MAX_TEXT_LENGTH)
            
        Returns:
            Sanitized text string
            
        Raises:
            ValidationError: If text contains harmful content or exceeds length limits
        """
        if not isinstance(text, str):
            raise ValidationError("Input must be a string")
        
        # Check length limits
        max_len = max_length or cls.MAX_TEXT_LENGTH
        if len(text) > max_len:
            raise ValidationError(
                f"Text length {len(text)} exceeds maximum allowed length of {max_len}",
                details={"text_length": len(text), "max_length": max_len}
            )
        
        # Remove HTML tags and script content
        sanitized = cls.SCRIPT_PATTERN.sub('', text)
        sanitized = cls.HTML_TAG_PATTERN.sub('', sanitized)
        
        # HTML escape remaining content
        sanitized = html.escape(sanitized)
        
        # Check for SQL injection patterns
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if pattern.search(sanitized):
                logger.warning(
                    "potential_sql_injection_detected",
                    text_preview=text[:100],
                    pattern=pattern.pattern
                )
                raise ValidationError("Input contains potentially harmful content")
        
        # Normalize Unicode characters
        sanitized = sanitized.encode('utf-8', errors='ignore').decode('utf-8')
        
        # Remove excessive whitespace
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        
        return sanitized
    
    @classmethod
    def sanitize_job_description(cls, job_description: str) -> str:
        """
        Sanitize job description input with specific length limits
        
        Args:
            job_description: Job description text to sanitize
            
        Returns:
            Sanitized job description
        """
        return cls.sanitize_text_input(job_description, cls.MAX_JOB_DESCRIPTION_LENGTH)
    
    @classmethod
    def validate_filename(cls, filename: str) -> str:
        """
        Validate and sanitize filename to prevent path traversal attacks
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename
            
        Raises:
            ValidationError: If filename is invalid
        """
        if not filename:
            raise ValidationError("Filename cannot be empty")
        
        # Remove path components
        filename = os.path.basename(filename)
        
        # Remove potentially harmful characters
        sanitized = re.sub(r'[^\w\-_\.]', '_', filename)
        
        # Ensure filename is not too long
        if len(sanitized) > 255:
            name, ext = os.path.splitext(sanitized)
            sanitized = name[:250] + ext
        
        # Ensure filename has an extension
        if '.' not in sanitized:
            raise ValidationError("Filename must have an extension")
        
        return sanitized


class FileValidator:
    """Security validation for file uploads"""
    
    def __init__(self):
        if MAGIC_AVAILABLE:
            try:
                self.magic = magic.Magic(mime=True)
                self.use_magic = True
            except Exception:
                self.use_magic = False
        else:
            self.use_magic = False
    
    def validate_file_security(
        self, 
        file_content: bytes, 
        filename: str,
        expected_mime_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive security validation for uploaded files
        
        Args:
            file_content: Raw file content bytes
            filename: Original filename
            expected_mime_types: List of allowed MIME types (defaults to config)
            
        Returns:
            Dictionary with validation results
            
        Raises:
            FileSizeError: If file exceeds size limits
            UnsupportedFormatError: If file type is not allowed
            ValidationError: If file fails security checks
        """
        allowed_types = expected_mime_types or settings.ALLOWED_FILE_TYPES
        
        # Validate file size
        file_size = len(file_content)
        if file_size > settings.MAX_FILE_SIZE:
            raise FileSizeError(file_size, settings.MAX_FILE_SIZE)
        
        if file_size == 0:
            raise ValidationError("File is empty")
        
        # Detect actual MIME type
        if self.use_magic:
            try:
                detected_mime = self.magic.from_buffer(file_content)
            except Exception:
                # Fallback to filename-based detection
                detected_mime = self._detect_mime_from_filename(filename)
        else:
            detected_mime = self._detect_mime_from_filename(filename)
        
        # Validate MIME type
        if detected_mime not in allowed_types:
            raise UnsupportedFormatError(detected_mime, allowed_types)
        
        # Additional security checks
        security_checks = {
            "has_executable_content": self._check_executable_content(file_content),
            "has_suspicious_headers": self._check_suspicious_headers(file_content),
            "filename_safe": self._validate_filename_security(filename)
        }
        
        # Fail if any security check fails
        if any(security_checks.values()):
            failed_checks = [k for k, v in security_checks.items() if v]
            raise ValidationError(
                f"File failed security checks: {', '.join(failed_checks)}",
                details={"failed_checks": failed_checks}
            )
        
        return {
            "file_size": file_size,
            "detected_mime_type": detected_mime,
            "filename": InputSanitizer.validate_filename(filename),
            "security_checks": security_checks
        }
    
    def _check_executable_content(self, content: bytes) -> bool:
        """Check for executable file signatures"""
        # Common executable file signatures
        executable_signatures = [
            b'\x4d\x5a',  # PE executable (Windows)
            b'\x7f\x45\x4c\x46',  # ELF executable (Linux)
            b'\xfe\xed\xfa\xce',  # Mach-O executable (macOS)
            b'\xfe\xed\xfa\xcf',  # Mach-O 64-bit executable
            b'#!/bin/',  # Shell script
            b'#!/usr/bin/',  # Shell script
        ]
        
        return any(content.startswith(sig) for sig in executable_signatures)
    
    def _check_suspicious_headers(self, content: bytes) -> bool:
        """Check for suspicious content in file headers"""
        # Check first 1KB for suspicious patterns
        header = content[:1024].lower()
        
        suspicious_patterns = [
            b'<script',
            b'javascript:',
            b'vbscript:',
            b'onload=',
            b'onerror=',
            b'eval(',
            b'document.cookie'
        ]
        
        return any(pattern in header for pattern in suspicious_patterns)
    
    def _validate_filename_security(self, filename: str) -> bool:
        """Check filename for security issues"""
        # Check for path traversal attempts
        if '..' in filename or '/' in filename or '\\' in filename:
            return True
        
        # Check for suspicious extensions
        suspicious_extensions = [
            '.exe', '.bat', '.cmd', '.com', '.scr', '.pif',
            '.js', '.vbs', '.jar', '.app', '.deb', '.rpm'
        ]
        
        file_ext = Path(filename).suffix.lower()
        return file_ext in suspicious_extensions
    
    def _detect_mime_from_filename(self, filename: str) -> str:
        """Fallback MIME type detection based on filename extension"""
        mime_type, _ = mimetypes.guess_type(filename)
        
        # Map common extensions to expected MIME types
        if mime_type is None:
            ext = Path(filename).suffix.lower()
            extension_map = {
                '.pdf': 'application/pdf',
                '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                '.txt': 'text/plain',
                '.doc': 'application/msword'
            }
            mime_type = extension_map.get(ext, 'application/octet-stream')
        
        return mime_type


class TemporaryFileManager:
    """Secure temporary file management with automatic cleanup"""
    
    def __init__(self):
        self.temp_files: List[str] = []
    
    def create_temp_file(self, content: bytes, suffix: str = '') -> str:
        """
        Create a temporary file with automatic cleanup tracking
        
        Args:
            content: File content bytes
            suffix: File extension suffix
            
        Returns:
            Path to temporary file
        """
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(content)
            temp_path = temp_file.name
        
        self.temp_files.append(temp_path)
        
        logger.debug(
            "temporary_file_created",
            temp_path=temp_path,
            file_size=len(content)
        )
        
        return temp_path
    
    def cleanup_temp_files(self):
        """Remove all tracked temporary files"""
        for temp_path in self.temp_files:
            try:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    logger.debug("temporary_file_cleaned", temp_path=temp_path)
            except OSError as e:
                logger.warning(
                    "temp_file_cleanup_failed",
                    temp_path=temp_path,
                    error=str(e)
                )
        
        self.temp_files.clear()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup_temp_files()