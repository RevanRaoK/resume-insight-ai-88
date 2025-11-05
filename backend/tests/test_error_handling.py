"""
Unit tests for error handling in document processing
"""
import pytest
import os
from unittest.mock import patch, Mock
from io import BytesIO

from fastapi import UploadFile

from app.services.document_service import DocumentService
from app.core.exceptions import (
    DocumentProcessingError,
    UnsupportedFormatError,
    FileSizeError,
    ValidationError
)


class TestErrorHandling:
    """Test cases for error handling scenarios"""
    
    @pytest.fixture
    def document_service(self):
        return DocumentService()
    
    @pytest.mark.asyncio
    async def test_corrupted_pdf_handling(self, document_service, mock_fastapi_upload_file):
        """Test handling of corrupted PDF files"""
        # Create corrupted PDF content
        corrupted_content = b"This is not a valid PDF file"
        upload_file = mock_fastapi_upload_file(corrupted_content, "corrupted.pdf", "application/pdf")
        
        with patch('app.services.document_service.validate_upload_file') as mock_validate:
            mock_validate.return_value = {
                "detected_mime_type": "application/pdf",
                "safe_filename": "corrupted.pdf",
                "content": corrupted_content
            }
            
            with patch('app.services.document_service.TemporaryFileManager') as mock_temp_manager:
                mock_context = Mock()
                mock_context.create_temp_file.return_value = "/tmp/corrupted.pdf"
                mock_temp_manager.return_value.__enter__.return_value = mock_context
                mock_temp_manager.return_value.__exit__.return_value = None
                
                # Mock both processors to fail with different errors
                with patch('app.services.document_service.pdfplumber') as mock_pdfplumber, \
                     patch('app.services.document_service.convert_from_path') as mock_convert:
                    
                    mock_pdfplumber.open.side_effect = Exception("Invalid PDF structure")
                    mock_convert.side_effect = Exception("Cannot convert corrupted PDF to images")
                    
                    with pytest.raises(Exception) as exc_info:
                        await document_service.process_document(upload_file)
                    
                    # Should get the last error (OCR failure)
                    assert "Cannot convert corrupted PDF to images" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_corrupted_docx_handling(self, document_service, mock_fastapi_upload_file):
        """Test handling of corrupted DOCX files"""
        corrupted_content = b"PK\x03\x04\x14\x00\x00\x00corrupted"  # Fake ZIP header
        upload_file = mock_fastapi_upload_file(
            corrupted_content, 
            "corrupted.docx", 
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        
        with patch('app.services.document_service.validate_upload_file') as mock_validate:
            mock_validate.return_value = {
                "detected_mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "safe_filename": "corrupted.docx",
                "content": corrupted_content
            }
            
            with patch('app.services.document_service.TemporaryFileManager') as mock_temp_manager:
                mock_context = Mock()
                mock_context.create_temp_file.return_value = "/tmp/corrupted.docx"
                mock_temp_manager.return_value.__enter__.return_value = mock_context
                mock_temp_manager.return_value.__exit__.return_value = None
                
                # Mock Document to raise exception
                with patch('app.services.document_service.Document') as mock_document:
                    mock_document.side_effect = Exception("Corrupted DOCX file")
                    
                    with pytest.raises(DocumentProcessingError) as exc_info:
                        await document_service.process_document(upload_file)
                    
                    assert "Failed to process DOCX" in str(exc_info.value)
                    assert exc_info.value.details["file_name"] == "corrupted.docx"
                    assert exc_info.value.details["processing_stage"] == "docx_extraction"
    
    @pytest.mark.asyncio
    async def test_file_size_limit_exceeded(self, document_service, mock_fastapi_upload_file):
        """Test handling of files exceeding size limits"""
        # Create large file content (15MB)
        large_content = b"x" * (15 * 1024 * 1024)
        upload_file = mock_fastapi_upload_file(large_content, "large.pdf", "application/pdf")
        
        # Mock validation to raise FileSizeError
        with patch('app.services.document_service.validate_upload_file') as mock_validate:
            mock_validate.side_effect = FileSizeError(
                file_size=len(large_content),
                max_size=10 * 1024 * 1024
            )
            
            with pytest.raises(FileSizeError) as exc_info:
                await document_service.process_document(upload_file)
            
            assert exc_info.value.details["file_size"] == len(large_content)
            assert exc_info.value.details["max_size"] == 10 * 1024 * 1024
            assert "exceeds maximum allowed size" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_unsupported_file_type_error(self, document_service, mock_fastapi_upload_file):
        """Test handling of unsupported file types"""
        # Create executable file content
        exe_content = b"MZ\x90\x00\x03\x00\x00\x00"  # PE header
        upload_file = mock_fastapi_upload_file(exe_content, "malware.exe", "application/x-executable")
        
        with patch('app.services.document_service.validate_upload_file') as mock_validate:
            mock_validate.return_value = {
                "detected_mime_type": "application/x-executable",
                "safe_filename": "malware.exe",
                "content": exe_content
            }
            
            with pytest.raises(UnsupportedFormatError) as exc_info:
                await document_service.process_document(upload_file)
            
            assert exc_info.value.details["file_type"] == "application/x-executable"
            assert "application/pdf" in exc_info.value.details["supported_types"]
            assert "text/plain" in exc_info.value.details["supported_types"]
            assert "Unsupported file format" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_malicious_filename_handling(self, document_service, mock_fastapi_upload_file):
        """Test handling of malicious filenames"""
        pdf_content = b"%PDF-1.4\ntest"
        # Malicious filename with path traversal
        malicious_filename = "../../../etc/passwd.pdf"
        upload_file = mock_fastapi_upload_file(pdf_content, malicious_filename, "application/pdf")
        
        with patch('app.services.document_service.validate_upload_file') as mock_validate:
            # Mock validation to sanitize filename
            mock_validate.return_value = {
                "detected_mime_type": "application/pdf",
                "safe_filename": "passwd.pdf",  # Sanitized filename
                "content": pdf_content
            }
            
            with patch('app.services.document_service.TemporaryFileManager') as mock_temp_manager, \
                 patch('app.services.document_service.pdfplumber') as mock_pdfplumber, \
                 patch('os.path.getsize', return_value=1024):
                
                mock_context = Mock()
                mock_context.create_temp_file.return_value = "/tmp/passwd.pdf"
                mock_temp_manager.return_value.__enter__.return_value = mock_context
                mock_temp_manager.return_value.__exit__.return_value = None
                
                mock_pdf = Mock()
                mock_page = Mock()
                mock_page.extract_text.return_value = "Safe content"
                mock_pdf.pages = [mock_page]
                mock_pdfplumber.open.return_value.__enter__.return_value = mock_pdf
                
                result = await document_service.process_document(upload_file)
                
                # Should use sanitized filename
                assert result.file_name == "passwd.pdf"
                assert "../" not in result.file_name
    
    @pytest.mark.asyncio
    async def test_empty_file_handling(self, document_service, mock_fastapi_upload_file):
        """Test handling of empty files"""
        empty_content = b""
        upload_file = mock_fastapi_upload_file(empty_content, "empty.txt", "text/plain")
        
        with patch('app.services.document_service.validate_upload_file') as mock_validate:
            mock_validate.return_value = {
                "detected_mime_type": "text/plain",
                "safe_filename": "empty.txt",
                "content": empty_content
            }
            
            with patch('app.services.document_service.TemporaryFileManager') as mock_temp_manager, \
                 patch('app.services.document_service.chardet') as mock_chardet, \
                 patch('os.path.getsize', return_value=0):
                
                mock_context = Mock()
                mock_context.create_temp_file.return_value = "/tmp/empty.txt"
                mock_temp_manager.return_value.__enter__.return_value = mock_context
                mock_temp_manager.return_value.__exit__.return_value = None
                
                mock_chardet.detect.return_value = {'encoding': 'utf-8', 'confidence': 0.99}
                
                with patch('builtins.open', create=True) as mock_open:
                    mock_open.return_value.__enter__.return_value.read.return_value = empty_content
                    
                    result = await document_service.process_document(upload_file)
                    
                    assert result.text == ""
                    assert result.file_size == 0
                    assert result.processing_method == "text"
    
    @pytest.mark.asyncio
    async def test_missing_filename_error(self, document_service):
        """Test handling of upload files without filenames"""
        file_obj = BytesIO(b"test content")
        upload_file = UploadFile(file=file_obj, filename=None)  # No filename
        
        with patch('app.services.document_service.validate_upload_file') as mock_validate:
            mock_validate.side_effect = ValidationError("Filename is required")
            
            with pytest.raises(ValidationError) as exc_info:
                await document_service.process_document(upload_file)
            
            assert "Filename is required" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_ocr_processing_failure(self, document_service, mock_fastapi_upload_file):
        """Test handling of OCR processing failures"""
        pdf_content = b"%PDF-1.4\nscanned"
        upload_file = mock_fastapi_upload_file(pdf_content, "scanned.pdf", "application/pdf")
        
        with patch('app.services.document_service.validate_upload_file') as mock_validate:
            mock_validate.return_value = {
                "detected_mime_type": "application/pdf",
                "safe_filename": "scanned.pdf",
                "content": pdf_content
            }
            
            with patch('app.services.document_service.TemporaryFileManager') as mock_temp_manager:
                mock_context = Mock()
                mock_context.create_temp_file.return_value = "/tmp/scanned.pdf"
                mock_temp_manager.return_value.__enter__.return_value = mock_context
                mock_temp_manager.return_value.__exit__.return_value = None
                
                with patch('app.services.document_service.pdfplumber') as mock_pdfplumber, \
                     patch('app.services.document_service.convert_from_path') as mock_convert:
                    
                    # PDF extraction returns minimal text (triggers OCR)
                    mock_pdf = Mock()
                    mock_page = Mock()
                    mock_page.extract_text.return_value = "Short"
                    mock_pdf.pages = [mock_page]
                    mock_pdfplumber.open.return_value.__enter__.return_value = mock_pdf
                    
                    # OCR fails
                    mock_convert.side_effect = Exception("Tesseract not installed")
                    
                    with pytest.raises(Exception) as exc_info:
                        await document_service.process_document(upload_file)
                    
                    assert "Tesseract not installed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_text_encoding_error_recovery(self, document_service, mock_fastapi_upload_file, temp_dir):
        """Test recovery from text encoding errors"""
        # Create file with invalid UTF-8 sequences
        invalid_content = b"Valid text\xff\xfe\x00Invalid UTF-8 bytes\x80\x81"
        
        upload_file = mock_fastapi_upload_file(invalid_content, "invalid_encoding.txt", "text/plain")
        
        with patch('app.services.document_service.validate_upload_file') as mock_validate:
            mock_validate.return_value = {
                "detected_mime_type": "text/plain",
                "safe_filename": "invalid_encoding.txt",
                "content": invalid_content
            }
            
            with patch('app.services.document_service.TemporaryFileManager') as mock_temp_manager, \
                 patch('app.services.document_service.chardet') as mock_chardet, \
                 patch('os.path.getsize', return_value=len(invalid_content)):
                
                mock_context = Mock()
                temp_path = "/tmp/invalid_encoding.txt"
                mock_context.create_temp_file.return_value = temp_path
                mock_temp_manager.return_value.__enter__.return_value = mock_context
                mock_temp_manager.return_value.__exit__.return_value = None
                
                # Mock chardet to detect invalid encoding
                mock_chardet.detect.return_value = {
                    'encoding': 'invalid-encoding',
                    'confidence': 0.3
                }
                
                with patch('builtins.open', create=True) as mock_open:
                    # First call (binary read) returns raw bytes
                    # Second call (decode attempt) should handle gracefully
                    mock_open.return_value.__enter__.return_value.read.return_value = invalid_content
                    
                    result = await document_service.process_document(upload_file)
                    
                    # Should handle encoding errors gracefully
                    assert isinstance(result.text, str)
                    assert result.processing_method == "text"
                    # Confidence should be lower due to encoding issues
                    assert result.confidence_score <= 0.6
    
    @pytest.mark.asyncio
    async def test_network_timeout_simulation(self, document_service, mock_fastapi_upload_file):
        """Test handling of network-like timeouts during processing"""
        pdf_content = b"%PDF-1.4\ntest"
        upload_file = mock_fastapi_upload_file(pdf_content, "timeout.pdf", "application/pdf")
        
        with patch('app.services.document_service.validate_upload_file') as mock_validate:
            mock_validate.return_value = {
                "detected_mime_type": "application/pdf",
                "safe_filename": "timeout.pdf",
                "content": pdf_content
            }
            
            with patch('app.services.document_service.TemporaryFileManager') as mock_temp_manager:
                mock_context = Mock()
                mock_context.create_temp_file.return_value = "/tmp/timeout.pdf"
                mock_temp_manager.return_value.__enter__.return_value = mock_context
                mock_temp_manager.return_value.__exit__.return_value = None
                
                # Simulate timeout during PDF processing
                with patch('app.services.document_service.pdfplumber') as mock_pdfplumber:
                    mock_pdfplumber.open.side_effect = TimeoutError("Processing timeout")
                    
                    with pytest.raises(DocumentProcessingError) as exc_info:
                        await document_service.process_document(upload_file)
                    
                    assert "Failed to process PDF" in str(exc_info.value)
                    assert exc_info.value.details["processing_stage"] == "pdf_extraction"


class TestSpecificErrorScenarios:
    """Test specific error scenarios mentioned in requirements"""
    
    @pytest.fixture
    def document_service(self):
        return DocumentService()
    
    @pytest.mark.asyncio
    async def test_requirement_1_5_unsupported_format_error(self, document_service, mock_fastapi_upload_file):
        """Test Requirement 1.5: Clear error message for unsupported formats"""
        # Test various unsupported formats
        unsupported_files = [
            (b"GIF89a", "image.gif", "image/gif"),
            (b"\x89PNG\r\n\x1a\n", "image.png", "image/png"),
            (b"PK\x03\x04", "archive.zip", "application/zip"),
            (b"Rar!\x1a\x07\x00", "archive.rar", "application/x-rar-compressed")
        ]
        
        for content, filename, mime_type in unsupported_files:
            upload_file = mock_fastapi_upload_file(content, filename, mime_type)
            
            with patch('app.services.document_service.validate_upload_file') as mock_validate:
                mock_validate.return_value = {
                    "detected_mime_type": mime_type,
                    "safe_filename": filename,
                    "content": content
                }
                
                with pytest.raises(UnsupportedFormatError) as exc_info:
                    await document_service.process_document(upload_file)
                
                # Verify clear error message
                assert f"Unsupported file format: {mime_type}" in str(exc_info.value)
                assert "application/pdf" in str(exc_info.value)
                assert "text/plain" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_requirement_5_1_file_size_validation(self, document_service, mock_fastapi_upload_file):
        """Test Requirement 5.1: 10MB file size limit validation"""
        # Create file exactly at limit (should pass validation layer)
        limit_content = b"x" * (10 * 1024 * 1024)  # Exactly 10MB
        upload_file = mock_fastapi_upload_file(limit_content, "limit.pdf", "application/pdf")
        
        with patch('app.services.document_service.validate_upload_file') as mock_validate:
            # Should pass validation
            mock_validate.return_value = {
                "detected_mime_type": "application/pdf",
                "safe_filename": "limit.pdf",
                "content": limit_content
            }
            
            # Mock successful processing
            with patch('app.services.document_service.TemporaryFileManager') as mock_temp_manager, \
                 patch('app.services.document_service.pdfplumber') as mock_pdfplumber, \
                 patch('os.path.getsize', return_value=len(limit_content)):
                
                mock_context = Mock()
                mock_context.create_temp_file.return_value = "/tmp/limit.pdf"
                mock_temp_manager.return_value.__enter__.return_value = mock_context
                mock_temp_manager.return_value.__exit__.return_value = None
                
                mock_pdf = Mock()
                mock_page = Mock()
                mock_page.extract_text.return_value = "Test content"
                mock_pdf.pages = [mock_page]
                mock_pdfplumber.open.return_value.__enter__.return_value = mock_pdf
                
                result = await document_service.process_document(upload_file)
                
                # Should succeed at exactly 10MB
                assert result.file_size == len(limit_content)
    
    @pytest.mark.asyncio
    async def test_requirement_5_2_mime_type_verification(self, document_service, mock_fastapi_upload_file):
        """Test Requirement 5.2: MIME type verification with python-magic"""
        # Test file with misleading extension but correct MIME type
        pdf_content = b"%PDF-1.4\ntest content"
        upload_file = mock_fastapi_upload_file(pdf_content, "resume.txt", "text/plain")  # Wrong extension
        
        with patch('app.services.document_service.validate_upload_file') as mock_validate:
            # Validation should detect actual MIME type
            mock_validate.return_value = {
                "detected_mime_type": "application/pdf",  # Actual detected type
                "safe_filename": "resume.txt",
                "content": pdf_content
            }
            
            with patch('app.services.document_service.TemporaryFileManager') as mock_temp_manager, \
                 patch('app.services.document_service.pdfplumber') as mock_pdfplumber, \
                 patch('os.path.getsize', return_value=len(pdf_content)):
                
                mock_context = Mock()
                mock_context.create_temp_file.return_value = "/tmp/resume.txt"
                mock_temp_manager.return_value.__enter__.return_value = mock_context
                mock_temp_manager.return_value.__exit__.return_value = None
                
                mock_pdf = Mock()
                mock_page = Mock()
                mock_page.extract_text.return_value = "PDF content"
                mock_pdf.pages = [mock_page]
                mock_pdfplumber.open.return_value.__enter__.return_value = mock_pdf
                
                result = await document_service.process_document(upload_file)
                
                # Should process as PDF despite .txt extension
                assert result.processing_method == "pdfplumber"
                assert result.text == "PDF content"