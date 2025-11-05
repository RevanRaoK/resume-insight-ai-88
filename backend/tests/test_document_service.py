"""
Unit tests for DocumentService orchestration and OCR fallback logic
"""
import pytest
import os
from unittest.mock import patch, Mock, AsyncMock
from io import BytesIO

from fastapi import UploadFile

from app.services.document_service import DocumentService
from app.core.exceptions import (
    DocumentProcessingError, 
    UnsupportedFormatError, 
    FileSizeError
)
from app.models.entities import ProcessedDocument


class TestDocumentService:
    """Test cases for DocumentService orchestration"""
    
    @pytest.fixture
    def document_service(self):
        return DocumentService()
    
    @pytest.mark.asyncio
    async def test_process_pdf_success(self, document_service, mock_fastapi_upload_file, sample_text_content):
        """Test successful PDF processing"""
        # Create mock upload file
        pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\nxref\n0 1\ntrailer\n<<\n/Root 1 0 R\n>>\n%%EOF"
        upload_file = mock_fastapi_upload_file(pdf_content, "resume.pdf", "application/pdf")
        
        # Mock file validation
        with patch('app.services.document_service.validate_upload_file') as mock_validate:
            mock_validate.return_value = {
                "detected_mime_type": "application/pdf",
                "safe_filename": "resume.pdf",
                "content": pdf_content
            }
            
            # Mock TemporaryFileManager and PDF processing
            with patch('app.services.document_service.TemporaryFileManager') as mock_temp_manager, \
                 patch('app.services.document_service.pdfplumber') as mock_pdfplumber:
                
                # Setup temp file manager
                mock_context = Mock()
                mock_context.create_temp_file.return_value = "/tmp/test.pdf"
                mock_temp_manager.return_value.__enter__.return_value = mock_context
                mock_temp_manager.return_value.__exit__.return_value = None
                
                # Setup PDF processing
                mock_pdf = Mock()
                mock_page = Mock()
                mock_page.extract_text.return_value = sample_text_content
                mock_pdf.pages = [mock_page]
                mock_pdfplumber.open.return_value.__enter__.return_value = mock_pdf
                
                # Mock file size
                with patch('os.path.getsize', return_value=1024):
                    result = await document_service.process_document(upload_file)
                
                assert isinstance(result, ProcessedDocument)
                assert result.text == sample_text_content.strip()
                assert result.processing_method == "pdfplumber"
                assert result.file_name == "resume.pdf"
    
    @pytest.mark.asyncio
    async def test_pdf_ocr_fallback(self, document_service, mock_fastapi_upload_file):
        """Test OCR fallback when PDF text extraction yields insufficient text"""
        pdf_content = b"%PDF-1.4\nscanned content"
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
                
                # Mock PDF processor to return insufficient text (triggers OCR fallback)
                with patch('app.services.document_service.pdfplumber') as mock_pdfplumber, \
                     patch('app.services.document_service.convert_from_path') as mock_convert, \
                     patch('app.services.document_service.pytesseract') as mock_tesseract, \
                     patch('os.path.getsize', return_value=2048):
                    
                    # PDF extraction returns minimal text
                    mock_pdf = Mock()
                    mock_page = Mock()
                    mock_page.extract_text.return_value = "Short"  # Less than 200 chars
                    mock_pdf.pages = [mock_page]
                    mock_pdfplumber.open.return_value.__enter__.return_value = mock_pdf
                    
                    # OCR processing returns full text
                    mock_image = Mock()
                    mock_convert.return_value = [mock_image]
                    mock_tesseract.image_to_string.return_value = "Full OCR extracted text content from scanned document"
                    
                    result = await document_service.process_document(upload_file)
                    
                    assert result.processing_method == "ocr"
                    assert "Full OCR extracted text" in result.text
                    # The OCR text should be longer than the original short text
                    assert len(result.text) > len("Short")
    
    @pytest.mark.asyncio
    async def test_process_docx_success(self, document_service, mock_fastapi_upload_file, temp_dir, sample_text_content):
        """Test successful DOCX processing"""
        # Create real DOCX file for testing
        from docx import Document
        doc = Document()
        doc.add_paragraph(sample_text_content)
        docx_path = os.path.join(temp_dir, "test.docx")
        doc.save(docx_path)
        
        # Read DOCX content
        with open(docx_path, "rb") as f:
            docx_content = f.read()
        
        upload_file = mock_fastapi_upload_file(
            docx_content, 
            "resume.docx", 
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        
        with patch('app.services.document_service.validate_upload_file') as mock_validate:
            mock_validate.return_value = {
                "detected_mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "safe_filename": "resume.docx",
                "content": docx_content
            }
            
            with patch('app.services.document_service.TemporaryFileManager') as mock_temp_manager:
                mock_context = Mock()
                mock_context.create_temp_file.return_value = docx_path
                mock_temp_manager.return_value.__enter__.return_value = mock_context
                mock_temp_manager.return_value.__exit__.return_value = None
                
                result = await document_service.process_document(upload_file)
                
                assert isinstance(result, ProcessedDocument)
                assert result.processing_method == "docx"
                assert len(result.text) > 0
                assert result.confidence_score == 0.95
    
    @pytest.mark.asyncio
    async def test_process_text_success(self, document_service, mock_fastapi_upload_file, sample_text_content):
        """Test successful text file processing"""
        text_content = sample_text_content.encode('utf-8')
        upload_file = mock_fastapi_upload_file(text_content, "resume.txt", "text/plain")
        
        with patch('app.services.document_service.validate_upload_file') as mock_validate:
            mock_validate.return_value = {
                "detected_mime_type": "text/plain",
                "safe_filename": "resume.txt",
                "content": text_content
            }
            
            with patch('app.services.document_service.TemporaryFileManager') as mock_temp_manager, \
                 patch('app.services.document_service.chardet') as mock_chardet, \
                 patch('os.path.getsize', return_value=len(text_content)):
                
                mock_context = Mock()
                temp_path = "/tmp/resume.txt"
                mock_context.create_temp_file.return_value = temp_path
                mock_temp_manager.return_value.__enter__.return_value = mock_context
                mock_temp_manager.return_value.__exit__.return_value = None
                
                # Mock chardet for encoding detection
                mock_chardet.detect.return_value = {
                    'encoding': 'utf-8',
                    'confidence': 0.99
                }
                
                # Mock file reading
                with patch('builtins.open', create=True) as mock_open:
                    mock_open.return_value.__enter__.return_value.read.return_value = text_content
                    
                    result = await document_service.process_document(upload_file)
                    
                    assert isinstance(result, ProcessedDocument)
                    assert result.processing_method == "text"
                    assert result.text == sample_text_content.strip()
    
    @pytest.mark.asyncio
    async def test_unsupported_file_format(self, document_service, mock_fastapi_upload_file):
        """Test handling of unsupported file formats"""
        exe_content = b"MZ\x90\x00"  # PE executable header
        upload_file = mock_fastapi_upload_file(exe_content, "malware.exe", "application/x-executable")
        
        with patch('app.services.document_service.validate_upload_file') as mock_validate:
            mock_validate.return_value = {
                "detected_mime_type": "application/x-executable",
                "safe_filename": "malware.exe",
                "content": exe_content
            }
            
            with pytest.raises(UnsupportedFormatError) as exc_info:
                await document_service.process_document(upload_file)
            
            assert "application/x-executable" in str(exc_info.value)
            assert "application/pdf" in exc_info.value.details["supported_types"]
    
    @pytest.mark.asyncio
    async def test_all_processors_fail(self, document_service, mock_fastapi_upload_file):
        """Test when all processors fail for a supported format"""
        pdf_content = b"corrupted pdf content"
        upload_file = mock_fastapi_upload_file(pdf_content, "corrupted.pdf", "application/pdf")
        
        with patch('app.services.document_service.validate_upload_file') as mock_validate:
            mock_validate.return_value = {
                "detected_mime_type": "application/pdf",
                "safe_filename": "corrupted.pdf",
                "content": pdf_content
            }
            
            with patch('app.services.document_service.TemporaryFileManager') as mock_temp_manager:
                mock_context = Mock()
                mock_context.create_temp_file.return_value = "/tmp/corrupted.pdf"
                mock_temp_manager.return_value.__enter__.return_value = mock_context
                mock_temp_manager.return_value.__exit__.return_value = None
                
                # Mock both PDF and OCR processors to fail
                with patch('app.services.document_service.pdfplumber') as mock_pdfplumber, \
                     patch('app.services.document_service.convert_from_path') as mock_convert:
                    
                    mock_pdfplumber.open.side_effect = Exception("PDF parsing failed")
                    mock_convert.side_effect = Exception("Image conversion failed")
                    
                    with pytest.raises(Exception) as exc_info:
                        await document_service.process_document(upload_file)
                    
                    # Should raise the last error encountered
                    assert "Image conversion failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_file_validation_error_propagation(self, document_service, mock_fastapi_upload_file):
        """Test that file validation errors are properly propagated"""
        large_content = b"x" * (15 * 1024 * 1024)  # 15MB file
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
    
    def test_processor_initialization(self, document_service):
        """Test that processors are properly initialized"""
        assert "application/pdf" in document_service.processors
        assert "application/vnd.openxmlformats-officedocument.wordprocessingml.document" in document_service.processors
        assert "text/plain" in document_service.processors
        
        # PDF should have both PDF and OCR processors for fallback
        pdf_processors = document_service.processors["application/pdf"]
        assert len(pdf_processors) == 2
        
        # Other formats should have single processors
        docx_processors = document_service.processors["application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
        assert len(docx_processors) == 1
        
        text_processors = document_service.processors["text/plain"]
        assert len(text_processors) == 1
    
    @pytest.mark.asyncio
    async def test_temporary_file_cleanup(self, document_service, mock_fastapi_upload_file, sample_text_content):
        """Test that temporary files are properly cleaned up"""
        text_content = sample_text_content.encode('utf-8')
        upload_file = mock_fastapi_upload_file(text_content, "resume.txt", "text/plain")
        
        with patch('app.services.document_service.validate_upload_file') as mock_validate:
            mock_validate.return_value = {
                "detected_mime_type": "text/plain",
                "safe_filename": "resume.txt",
                "content": text_content
            }
            
            # Track TemporaryFileManager context manager usage
            with patch('app.services.document_service.TemporaryFileManager') as mock_temp_manager:
                mock_context = Mock()
                mock_context.create_temp_file.return_value = "/tmp/resume.txt"
                mock_temp_manager.return_value.__enter__.return_value = mock_context
                mock_temp_manager.return_value.__exit__.return_value = None
                
                with patch('app.services.document_service.chardet') as mock_chardet, \
                     patch('os.path.getsize', return_value=len(text_content)), \
                     patch('builtins.open', create=True) as mock_open:
                    
                    mock_chardet.detect.return_value = {'encoding': 'utf-8', 'confidence': 0.99}
                    mock_open.return_value.__enter__.return_value.read.return_value = text_content
                    
                    await document_service.process_document(upload_file)
                    
                    # Verify context manager was used (ensures cleanup)
                    mock_temp_manager.assert_called_once()
                    mock_temp_manager.return_value.__enter__.assert_called_once()
                    mock_temp_manager.return_value.__exit__.assert_called_once()


class TestOCRFallbackLogic:
    """Specific tests for OCR fallback logic"""
    
    @pytest.fixture
    def document_service(self):
        return DocumentService()
    
    @pytest.mark.asyncio
    async def test_ocr_fallback_threshold(self, document_service, mock_fastapi_upload_file):
        """Test that OCR fallback is triggered at exactly 200 character threshold"""
        pdf_content = b"%PDF-1.4\ntest content"
        upload_file = mock_fastapi_upload_file(pdf_content, "test.pdf", "application/pdf")
        
        with patch('app.services.document_service.validate_upload_file') as mock_validate:
            mock_validate.return_value = {
                "detected_mime_type": "application/pdf",
                "safe_filename": "test.pdf",
                "content": pdf_content
            }
            
            with patch('app.services.document_service.TemporaryFileManager') as mock_temp_manager:
                mock_context = Mock()
                mock_context.create_temp_file.return_value = "/tmp/test.pdf"
                mock_temp_manager.return_value.__enter__.return_value = mock_context
                mock_temp_manager.return_value.__exit__.return_value = None
                
                # Test with exactly 199 characters (should trigger OCR)
                short_text = "x" * 199
                
                with patch('app.services.document_service.pdfplumber') as mock_pdfplumber, \
                     patch('app.services.document_service.convert_from_path') as mock_convert, \
                     patch('app.services.document_service.pytesseract') as mock_tesseract, \
                     patch('os.path.getsize', return_value=1024):
                    
                    # PDF returns short text
                    mock_pdf = Mock()
                    mock_page = Mock()
                    mock_page.extract_text.return_value = short_text
                    mock_pdf.pages = [mock_page]
                    mock_pdfplumber.open.return_value.__enter__.return_value = mock_pdf
                    
                    # OCR returns longer text
                    mock_image = Mock()
                    mock_convert.return_value = [mock_image]
                    mock_tesseract.image_to_string.return_value = "OCR extracted longer text content"
                    
                    result = await document_service.process_document(upload_file)
                    
                    # Should use OCR result
                    assert result.processing_method == "ocr"
                    assert "OCR extracted" in result.text
    
    @pytest.mark.asyncio
    async def test_no_ocr_fallback_sufficient_text(self, document_service, mock_fastapi_upload_file):
        """Test that OCR fallback is NOT triggered when PDF has sufficient text"""
        pdf_content = b"%PDF-1.4\ntest content"
        upload_file = mock_fastapi_upload_file(pdf_content, "test.pdf", "application/pdf")
        
        with patch('app.services.document_service.validate_upload_file') as mock_validate:
            mock_validate.return_value = {
                "detected_mime_type": "application/pdf",
                "safe_filename": "test.pdf",
                "content": pdf_content
            }
            
            with patch('app.services.document_service.TemporaryFileManager') as mock_temp_manager:
                mock_context = Mock()
                mock_context.create_temp_file.return_value = "/tmp/test.pdf"
                mock_temp_manager.return_value.__enter__.return_value = mock_context
                mock_temp_manager.return_value.__exit__.return_value = None
                
                # Test with 200+ characters (should NOT trigger OCR)
                long_text = "x" * 250
                
                with patch('app.services.document_service.pdfplumber') as mock_pdfplumber, \
                     patch('app.services.document_service.convert_from_path') as mock_convert, \
                     patch('os.path.getsize', return_value=1024):
                    
                    # PDF returns sufficient text
                    mock_pdf = Mock()
                    mock_page = Mock()
                    mock_page.extract_text.return_value = long_text
                    mock_pdf.pages = [mock_page]
                    mock_pdfplumber.open.return_value.__enter__.return_value = mock_pdf
                    
                    result = await document_service.process_document(upload_file)
                    
                    # Should use PDF result, not OCR
                    assert result.processing_method == "pdfplumber"
                    assert result.text == long_text
                    
                    # OCR should not have been called
                    mock_convert.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_ocr_fallback_with_processor_failure(self, document_service, mock_fastapi_upload_file):
        """Test OCR fallback when PDF processor completely fails"""
        pdf_content = b"%PDF-1.4\ntest content"
        upload_file = mock_fastapi_upload_file(pdf_content, "test.pdf", "application/pdf")
        
        with patch('app.services.document_service.validate_upload_file') as mock_validate:
            mock_validate.return_value = {
                "detected_mime_type": "application/pdf",
                "safe_filename": "test.pdf",
                "content": pdf_content
            }
            
            with patch('app.services.document_service.TemporaryFileManager') as mock_temp_manager:
                mock_context = Mock()
                mock_context.create_temp_file.return_value = "/tmp/test.pdf"
                mock_temp_manager.return_value.__enter__.return_value = mock_context
                mock_temp_manager.return_value.__exit__.return_value = None
                
                with patch('app.services.document_service.pdfplumber') as mock_pdfplumber, \
                     patch('app.services.document_service.convert_from_path') as mock_convert, \
                     patch('app.services.document_service.pytesseract') as mock_tesseract, \
                     patch('os.path.getsize', return_value=1024):
                    
                    # PDF processor fails completely
                    mock_pdfplumber.open.side_effect = Exception("PDF parsing failed")
                    
                    # OCR succeeds
                    mock_image = Mock()
                    mock_convert.return_value = [mock_image]
                    mock_tesseract.image_to_string.return_value = "OCR fallback text"
                    
                    result = await document_service.process_document(upload_file)
                    
                    # Should fall back to OCR
                    assert result.processing_method == "ocr"
                    assert result.text == "OCR fallback text"