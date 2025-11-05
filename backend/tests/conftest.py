"""
Pytest configuration and shared fixtures for document processing tests
"""
import pytest
import tempfile
import os
from pathlib import Path
from typing import Generator
from unittest.mock import Mock

from fastapi import UploadFile
from io import BytesIO

# Setup test environment before importing app modules
from tests.test_config import setup_test_environment, cleanup_test_environment

# Setup test environment
setup_test_environment()

# Test data directory
TEST_DATA_DIR = Path(__file__).parent / "test_data"


@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    """Create a temporary directory for test files"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def sample_text_content() -> str:
    """Sample resume text content for testing"""
    return """
John Doe
Software Engineer
Email: john.doe@example.com
Phone: (555) 123-4567

EXPERIENCE
Senior Software Engineer at TechCorp (2020-2023)
- Developed web applications using Python and React
- Led a team of 5 developers
- Implemented CI/CD pipelines

Software Developer at StartupXYZ (2018-2020)
- Built REST APIs using FastAPI
- Worked with PostgreSQL databases
- Collaborated with cross-functional teams

EDUCATION
Bachelor of Science in Computer Science
University of Technology (2014-2018)

SKILLS
Python, JavaScript, React, FastAPI, PostgreSQL, Docker, AWS
"""


@pytest.fixture
def mock_upload_file() -> Mock:
    """Create a mock UploadFile for testing"""
    mock_file = Mock(spec=UploadFile)
    mock_file.filename = "test_resume.pdf"
    mock_file.content_type = "application/pdf"
    return mock_file


@pytest.fixture
def create_test_pdf(temp_dir: str, sample_text_content: str) -> str:
    """Create a simple test PDF file"""
    # This is a minimal PDF structure for testing
    # In a real scenario, you'd use a proper PDF library
    pdf_content = f"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj

4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
72 720 Td
({sample_text_content[:50]}...) Tj
ET
endstream
endobj

xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000206 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
300
%%EOF"""
    
    pdf_path = os.path.join(temp_dir, "test_resume.pdf")
    with open(pdf_path, "w") as f:
        f.write(pdf_content)
    
    return pdf_path


@pytest.fixture
def create_test_docx(temp_dir: str, sample_text_content: str) -> str:
    """Create a simple test DOCX file"""
    from docx import Document
    
    doc = Document()
    doc.add_paragraph(sample_text_content)
    
    docx_path = os.path.join(temp_dir, "test_resume.docx")
    doc.save(docx_path)
    
    return docx_path


@pytest.fixture
def create_test_txt(temp_dir: str, sample_text_content: str) -> str:
    """Create a simple test text file"""
    txt_path = os.path.join(temp_dir, "test_resume.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(sample_text_content)
    
    return txt_path


@pytest.fixture
def create_corrupted_pdf(temp_dir: str) -> str:
    """Create a corrupted PDF file for error testing"""
    corrupted_path = os.path.join(temp_dir, "corrupted.pdf")
    with open(corrupted_path, "wb") as f:
        f.write(b"This is not a valid PDF file content")
    
    return corrupted_path


@pytest.fixture
def create_unsupported_file(temp_dir: str) -> str:
    """Create an unsupported file type for error testing"""
    unsupported_path = os.path.join(temp_dir, "test.exe")
    with open(unsupported_path, "wb") as f:
        f.write(b"MZ\x90\x00")  # PE executable header
    
    return unsupported_path


@pytest.fixture
def create_large_file(temp_dir: str) -> str:
    """Create a file that exceeds size limits"""
    large_path = os.path.join(temp_dir, "large_file.txt")
    # Create a 15MB file (exceeds 10MB limit)
    with open(large_path, "wb") as f:
        f.write(b"x" * (15 * 1024 * 1024))
    
    return large_path


@pytest.fixture
def mock_fastapi_upload_file():
    """Create a mock FastAPI UploadFile"""
    def _create_upload_file(content: bytes, filename: str, content_type: str):
        file_obj = BytesIO(content)
        upload_file = UploadFile(
            file=file_obj,
            filename=filename,
            headers={"content-type": content_type}
        )
        return upload_file
    
    return _create_upload_file


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Setup and cleanup test environment for the entire test session"""
    setup_test_environment()
    yield
    cleanup_test_environment()