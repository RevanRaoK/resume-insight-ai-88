"""
Integration tests for API endpoints
Tests complete end-to-end analysis workflow, authentication, authorization, and error handling.
This version mocks ML dependencies to avoid import issues during testing.
"""
import pytest
import sys
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from uuid import uuid4, UUID
from datetime import datetime
from io import BytesIO
from typing import Dict, Any

# Mock all ML-related modules before any imports
sys.modules['transformers'] = Mock()
sys.modules['sentence_transformers'] = Mock()
sys.modules['torch'] = Mock()
sys.modules['tensorflow'] = Mock()

# Setup test environment
from tests.test_config import setup_test_environment
setup_test_environment()

# Mock the ML utilities module
mock_model_cache = Mock()
mock_model_cache.load_models_at_startup = AsyncMock()
mock_model_cache.health_check = AsyncMock(return_value={"ner_model": True, "embedding_model": True})
mock_model_cache.get_model_info = Mock(return_value={
    "loaded_models": ["ner", "embeddings"],
    "model_health": {"ner": True, "embeddings": True},
    "memory_usage": {"ner": "100MB", "embeddings": "200MB"}
})

with patch.dict('sys.modules', {
    'app.utils.ml_utils': Mock(model_cache=mock_model_cache),
    'transformers': Mock(),
    'sentence_transformers': Mock()
}):
    from fastapi.testclient import TestClient
    from app.main import app


class TestHealthEndpoints:
    """Test health check endpoints"""
    
    def setup_method(self):
        """Setup test client"""
        self.client = TestClient(app)
    
    def test_basic_health_check(self):
        """Test basic health endpoint returns 200"""
        response = self.client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["service"] == "SmartResume AI Resume Analyzer"
        assert data["version"] == "1.0.0"
    
    @patch('app.services.database_service.db_service.health_check')
    @patch('app.services.ai_service.ai_service.health_check')
    def test_detailed_health_check_all_healthy(self, mock_ai_health, mock_db_health):
        """Test detailed health check when all services are healthy"""
        # Mock all services as healthy
        mock_db_health.return_value = {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
        mock_ai_health.return_value = {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
        
        response = self.client.get("/api/v1/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "checks" in data
        assert "database" in data["checks"]
        assert "ml_models" in data["checks"]
        assert "external_apis" in data["checks"]
    
    @patch('app.services.database_service.db_service.health_check')
    def test_detailed_health_check_database_unhealthy(self, mock_db_health):
        """Test detailed health check when database is unhealthy"""
        mock_db_health.side_effect = Exception("Database connection failed")
        
        response = self.client.get("/api/v1/health/detailed")
        
        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["status"] == "unhealthy"


class TestUploadEndpoints:
    """Test document upload endpoints"""
    
    def setup_method(self):
        """Setup test client and mocks"""
        self.client = TestClient(app)
        self.test_user_id = str(uuid4())
        self.mock_user = {"user_id": self.test_user_id}
    
    def create_test_file(self, content: str, filename: str, content_type: str) -> tuple:
        """Helper to create test file data"""
        file_content = content.encode('utf-8')
        return (filename, BytesIO(file_content), content_type)
    
    @patch('app.middleware.auth.get_current_user')
    @patch('app.services.document_service.DocumentService.process_document')
    @patch('app.services.database_service.db_service.resumes.create_resume')
    def test_upload_pdf_success(self, mock_create_resume, mock_process_doc, mock_auth):
        """Test successful PDF upload and processing"""
        # Setup mocks
        mock_auth.return_value = self.mock_user
        
        # Mock processed document
        mock_processed_doc = Mock()
        mock_processed_doc.text = "John Doe\nSoftware Engineer\nPython, JavaScript"
        mock_processed_doc.file_name = "test_resume.pdf"
        mock_processed_doc.file_size = 1024
        mock_processed_doc.processing_method = "pdfplumber"
        mock_processed_doc.confidence_score = 0.95
        mock_process_doc.return_value = mock_processed_doc
        
        # Mock resume creation
        mock_resume = Mock()
        mock_resume.id = uuid4()
        mock_resume.user_id = UUID(self.test_user_id)
        mock_resume.file_name = "test_resume.pdf"
        mock_resume.uploaded_at = datetime.utcnow()
        mock_create_resume.return_value = mock_resume
        
        # Create test file
        files = {"file": self.create_test_file("Test PDF content", "test_resume.pdf", "application/pdf")}
        
        response = self.client.post("/api/v1/upload", files=files)
        
        assert response.status_code == 200
        data = response.json()
        assert data["file_name"] == "test_resume.pdf"
        assert data["processing_method"] == "pdfplumber"
        assert data["confidence_score"] == 0.95
        assert "resume_id" in data
        assert "uploaded_at" in data
    
    @patch('app.middleware.auth.get_current_user')
    @patch('app.services.document_service.DocumentService.process_document')
    def test_upload_unsupported_format(self, mock_process_doc, mock_auth):
        """Test upload with unsupported file format"""
        mock_auth.return_value = self.mock_user
        
        # Mock unsupported format error
        from app.core.exceptions import UnsupportedFormatError
        mock_process_doc.side_effect = UnsupportedFormatError(
            "Unsupported file format",
            file_type="application/exe",
            supported_types=["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "text/plain"]
        )
        
        files = {"file": self.create_test_file("MZ\x90\x00", "malware.exe", "application/exe")}
        
        response = self.client.post("/api/v1/upload", files=files)
        
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error_code"] == "UNSUPPORTED_FORMAT"
        assert "supported_formats" in data["detail"]["details"]
    
    @patch('app.middleware.auth.get_current_user')
    @patch('app.services.database_service.db_service.resumes.get_user_resumes')
    def test_get_user_resumes(self, mock_get_resumes, mock_auth):
        """Test retrieving user's uploaded resumes"""
        mock_auth.return_value = self.mock_user
        
        # Mock resumes
        mock_resume1 = Mock()
        mock_resume1.id = uuid4()
        mock_resume1.file_name = "resume1.pdf"
        mock_resume1.parsed_text = "Resume 1 content"
        mock_resume1.uploaded_at = datetime.utcnow()
        
        mock_resume2 = Mock()
        mock_resume2.id = uuid4()
        mock_resume2.file_name = "resume2.docx"
        mock_resume2.parsed_text = "Resume 2 content"
        mock_resume2.uploaded_at = datetime.utcnow()
        
        mock_get_resumes.return_value = [mock_resume1, mock_resume2]
        
        response = self.client.get("/api/v1/resumes")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["file_name"] == "resume1.pdf"
        assert data[1]["file_name"] == "resume2.docx"
        assert "resume_id" in data[0]
        assert "uploaded_at" in data[0]


class TestAnalysisEndpoints:
    """Test resume analysis endpoints"""
    
    def setup_method(self):
        """Setup test client and mocks"""
        self.client = TestClient(app)
        self.test_user_id = str(uuid4())
        self.mock_user = {"user_id": self.test_user_id}
        self.test_resume_id = uuid4()
    
    @patch('app.middleware.auth.get_current_user')
    @patch('app.services.database_service.db_service.resumes.get_resume_by_id')
    @patch('app.services.nlu_service.nlu_service.extract_entities')
    @patch('app.services.semantic_service.semantic_service.analyze_compatibility')
    @patch('app.services.ai_service.ai_service.generate_feedback')
    @patch('app.services.database_service.db_service.store_analysis')
    def test_analyze_resume_with_resume_id_success(
        self, mock_store_analysis, mock_ai_feedback, mock_semantic, 
        mock_nlu, mock_get_resume, mock_auth
    ):
        """Test successful resume analysis using resume_id"""
        # Setup mocks
        mock_auth.return_value = self.mock_user
        
        # Mock resume retrieval
        mock_resume = Mock()
        mock_resume.id = self.test_resume_id
        mock_resume.user_id = UUID(self.test_user_id)
        mock_resume.parsed_text = "John Doe\nSoftware Engineer\nPython, JavaScript, React"
        mock_get_resume.return_value = mock_resume
        
        # Mock NLU service
        mock_entities = Mock()
        mock_entities.skills = ["Python", "JavaScript", "React"]
        mock_entities.job_titles = ["Software Engineer"]
        mock_entities.companies = ["TechCorp"]
        mock_nlu.return_value = mock_entities
        
        # Mock semantic analysis
        mock_compatibility = Mock()
        mock_compatibility.match_score = 85.5
        mock_compatibility.matched_keywords = ["Python", "JavaScript"]
        mock_compatibility.missing_keywords = ["Docker", "AWS"]
        mock_semantic.return_value = mock_compatibility
        
        # Mock AI feedback
        mock_feedback = Mock()
        mock_feedback.dict.return_value = {
            "recommendations": [
                {"category": "skills", "priority": "high", "suggestion": "Add Docker experience"}
            ],
            "overall_assessment": "Strong technical background"
        }
        mock_ai_feedback.return_value = mock_feedback
        
        # Mock analysis storage
        analysis_id = str(uuid4())
        mock_store_analysis.return_value = analysis_id
        
        # Make request
        request_data = {
            "job_description": "We are looking for a Python developer with Docker and AWS experience",
            "job_title": "Senior Python Developer",
            "resume_id": str(self.test_resume_id)
        }
        
        response = self.client.post("/api/v1/analyze", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["match_score"] == 85.5
        assert "ai_feedback" in data
        assert data["matched_keywords"] == ["Python", "JavaScript"]
        assert data["missing_keywords"] == ["Docker", "AWS"]
        assert "analysis_id" in data
        assert "processing_time" in data
    
    @patch('app.middleware.auth.get_current_user')
    def test_analyze_resume_missing_data(self, mock_auth):
        """Test analysis endpoint with missing resume data"""
        mock_auth.return_value = self.mock_user
        
        request_data = {
            "job_description": "Python developer position"
            # Missing both resume_id and resume_text
        }
        
        response = self.client.post("/api/v1/analyze", json=request_data)
        
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error_code"] == "MISSING_RESUME_DATA"
    
    @patch('app.middleware.auth.get_current_user')
    @patch('app.services.database_service.db_service.resumes.get_resume_by_id')
    def test_analyze_resume_not_found(self, mock_get_resume, mock_auth):
        """Test analysis with non-existent resume_id"""
        mock_auth.return_value = self.mock_user
        mock_get_resume.return_value = None
        
        request_data = {
            "job_description": "Python developer position",
            "resume_id": str(uuid4())
        }
        
        response = self.client.post("/api/v1/analyze", json=request_data)
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error_code"] == "RESUME_NOT_FOUND"


class TestHistoryEndpoints:
    """Test analysis history endpoints"""
    
    def setup_method(self):
        """Setup test client and mocks"""
        self.client = TestClient(app)
        self.test_user_id = str(uuid4())
        self.mock_user = {"user_id": self.test_user_id}
    
    @patch('app.middleware.auth.get_current_user')
    @patch('app.services.database_service.db_service.get_user_analyses')
    @patch('app.services.database_service.db_service.analyses.get_user_analyses_count')
    def test_get_user_analyses_success(self, mock_count, mock_get_analyses, mock_auth):
        """Test successful retrieval of user analyses"""
        mock_auth.return_value = self.mock_user
        
        # Mock analyses
        mock_analysis1 = Mock()
        mock_analysis1.id = uuid4()
        mock_analysis1.job_title = "Python Developer"
        mock_analysis1.match_score = 85.5
        mock_analysis1.matched_keywords = ["Python", "Django"]
        mock_analysis1.missing_keywords = ["Docker"]
        mock_analysis1.created_at = datetime.utcnow()
        
        mock_analysis2 = Mock()
        mock_analysis2.id = uuid4()
        mock_analysis2.job_title = "Full Stack Developer"
        mock_analysis2.match_score = 78.2
        mock_analysis2.matched_keywords = ["JavaScript", "React"]
        mock_analysis2.missing_keywords = ["Node.js"]
        mock_analysis2.created_at = datetime.utcnow()
        
        mock_get_analyses.return_value = [mock_analysis1, mock_analysis2]
        mock_count.return_value = 2
        
        response = self.client.get("/api/v1/analyses?page=1&page_size=10")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 2
        assert data["page"] == 1
        assert data["page_size"] == 10
        assert len(data["analyses"]) == 2
        assert data["analyses"][0]["job_title"] == "Python Developer"
        assert data["analyses"][0]["match_score"] == 85.5
    
    @patch('app.middleware.auth.get_current_user')
    @patch('app.services.database_service.db_service.get_analysis_by_id')
    def test_get_analysis_by_id_success(self, mock_get_analysis, mock_auth):
        """Test successful retrieval of specific analysis"""
        mock_auth.return_value = self.mock_user
        
        analysis_id = uuid4()
        mock_analysis = Mock()
        mock_analysis.id = analysis_id
        mock_analysis.user_id = UUID(self.test_user_id)
        mock_analysis.job_title = "Senior Python Developer"
        mock_analysis.job_description = "Senior Python development position with Django"
        mock_analysis.match_score = 92.3
        mock_analysis.ai_feedback = {
            "recommendations": [
                {"category": "skills", "suggestion": "Add more cloud experience"}
            ],
            "overall_assessment": "Excellent match"
        }
        mock_analysis.matched_keywords = ["Python", "Django", "PostgreSQL"]
        mock_analysis.missing_keywords = ["AWS"]
        mock_analysis.resume_id = uuid4()
        mock_analysis.created_at = datetime.utcnow()
        mock_get_analysis.return_value = mock_analysis
        
        response = self.client.get(f"/api/v1/analyses/{analysis_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["analysis_id"] == str(analysis_id)
        assert data["job_title"] == "Senior Python Developer"
        assert data["match_score"] == 92.3
        assert "ai_feedback" in data
        assert data["matched_keywords"] == ["Python", "Django", "PostgreSQL"]
        assert data["missing_keywords"] == ["AWS"]
    
    @patch('app.middleware.auth.get_current_user')
    @patch('app.services.database_service.db_service.get_analysis_by_id')
    def test_get_analysis_by_id_not_found(self, mock_get_analysis, mock_auth):
        """Test retrieval of non-existent analysis"""
        mock_auth.return_value = self.mock_user
        mock_get_analysis.return_value = None
        
        analysis_id = uuid4()
        response = self.client.get(f"/api/v1/analyses/{analysis_id}")
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error_code"] == "ANALYSIS_NOT_FOUND"


class TestEndToEndWorkflow:
    """Test complete end-to-end analysis workflow"""
    
    def setup_method(self):
        """Setup test client and mocks"""
        self.client = TestClient(app)
        self.test_user_id = str(uuid4())
        self.mock_user = {"user_id": self.test_user_id}
    
    def create_test_file(self, content: str, filename: str, content_type: str) -> tuple:
        """Helper to create test file data"""
        file_content = content.encode('utf-8')
        return (filename, BytesIO(file_content), content_type)
    
    @patch('app.middleware.auth.get_current_user')
    @patch('app.services.document_service.DocumentService.process_document')
    @patch('app.services.database_service.db_service.resumes.create_resume')
    @patch('app.services.database_service.db_service.resumes.get_resume_by_id')
    @patch('app.services.nlu_service.nlu_service.extract_entities')
    @patch('app.services.semantic_service.semantic_service.analyze_compatibility')
    @patch('app.services.ai_service.ai_service.generate_feedback')
    @patch('app.services.database_service.db_service.store_analysis')
    @patch('app.services.database_service.db_service.get_analysis_by_id')
    def test_complete_workflow_upload_and_analyze(
        self, mock_get_analysis, mock_store_analysis, mock_ai_feedback, 
        mock_semantic, mock_nlu, mock_get_resume, mock_create_resume, 
        mock_process_doc, mock_auth
    ):
        """Test complete workflow: upload resume -> analyze -> retrieve results"""
        # Setup authentication
        mock_auth.return_value = self.mock_user
        
        # Step 1: Upload resume
        resume_text = """
        John Doe
        Senior Software Engineer
        Email: john.doe@example.com
        
        EXPERIENCE
        Senior Software Engineer at TechCorp (2020-2023)
        - Developed web applications using Python and React
        - Led a team of 5 developers
        
        SKILLS
        Python, JavaScript, React, Django, PostgreSQL, Docker, AWS
        """
        
        mock_processed_doc = Mock()
        mock_processed_doc.text = resume_text
        mock_processed_doc.file_name = "john_doe_resume.pdf"
        mock_processed_doc.file_size = 2048
        mock_processed_doc.processing_method = "pdfplumber"
        mock_processed_doc.confidence_score = 0.98
        mock_process_doc.return_value = mock_processed_doc
        
        resume_id = uuid4()
        mock_resume = Mock()
        mock_resume.id = resume_id
        mock_resume.user_id = UUID(self.test_user_id)
        mock_resume.file_name = "john_doe_resume.pdf"
        mock_resume.parsed_text = resume_text
        mock_resume.uploaded_at = datetime.utcnow()
        mock_create_resume.return_value = mock_resume
        
        # Upload file
        files = {"file": self.create_test_file(resume_text, "john_doe_resume.pdf", "application/pdf")}
        upload_response = self.client.post("/api/v1/upload", files=files)
        
        assert upload_response.status_code == 200
        upload_data = upload_response.json()
        uploaded_resume_id = upload_data["resume_id"]
        
        # Step 2: Analyze resume
        mock_get_resume.return_value = mock_resume
        
        # Mock analysis services
        mock_entities = Mock()
        mock_entities.skills = ["Python", "JavaScript", "React", "Django", "PostgreSQL", "Docker", "AWS"]
        mock_entities.job_titles = ["Senior Software Engineer"]
        mock_entities.companies = ["TechCorp"]
        mock_nlu.return_value = mock_entities
        
        mock_compatibility = Mock()
        mock_compatibility.match_score = 94.2
        mock_compatibility.matched_keywords = ["Python", "Django", "PostgreSQL", "Docker", "AWS"]
        mock_compatibility.missing_keywords = ["Kubernetes"]
        mock_semantic.return_value = mock_compatibility
        
        mock_feedback = Mock()
        mock_feedback.dict.return_value = {
            "recommendations": [
                {
                    "category": "skills",
                    "priority": "medium",
                    "suggestion": "Consider adding Kubernetes experience"
                }
            ],
            "overall_assessment": "Excellent match for the position"
        }
        mock_ai_feedback.return_value = mock_feedback
        
        analysis_id = str(uuid4())
        mock_store_analysis.return_value = analysis_id
        
        # Perform analysis
        job_description = """
        We are seeking a Senior Python Developer to join our team.
        Requirements: Python, Django, PostgreSQL, Docker, AWS, Kubernetes
        """
        
        analysis_request = {
            "job_description": job_description,
            "job_title": "Senior Python Developer",
            "resume_id": uploaded_resume_id
        }
        
        analysis_response = self.client.post("/api/v1/analyze", json=analysis_request)
        
        assert analysis_response.status_code == 200
        analysis_data = analysis_response.json()
        
        # Verify analysis results
        assert analysis_data["match_score"] == 94.2
        assert "Python" in analysis_data["matched_keywords"]
        assert "Django" in analysis_data["matched_keywords"]
        assert "Kubernetes" in analysis_data["missing_keywords"]
        assert "ai_feedback" in analysis_data
        
        # Step 3: Verify we can retrieve the analysis
        mock_stored_analysis = Mock()
        mock_stored_analysis.id = UUID(analysis_id)
        mock_stored_analysis.user_id = UUID(self.test_user_id)
        mock_stored_analysis.job_title = "Senior Python Developer"
        mock_stored_analysis.job_description = job_description
        mock_stored_analysis.match_score = 94.2
        mock_stored_analysis.ai_feedback = mock_feedback.dict()
        mock_stored_analysis.matched_keywords = mock_compatibility.matched_keywords
        mock_stored_analysis.missing_keywords = mock_compatibility.missing_keywords
        mock_stored_analysis.resume_id = resume_id
        mock_stored_analysis.created_at = datetime.utcnow()
        mock_get_analysis.return_value = mock_stored_analysis
        
        # Retrieve analysis
        retrieve_response = self.client.get(f"/api/v1/analyses/{analysis_id}")
        
        assert retrieve_response.status_code == 200
        retrieve_data = retrieve_response.json()
        
        assert retrieve_data["analysis_id"] == analysis_id
        assert retrieve_data["match_score"] == 94.2
        assert retrieve_data["job_title"] == "Senior Python Developer"
        assert "ai_feedback" in retrieve_data


class TestErrorHandlingAndEdgeCases:
    """Test error handling and edge cases across all endpoints"""
    
    def setup_method(self):
        """Setup test client"""
        self.client = TestClient(app)
        self.test_user_id = str(uuid4())
        self.mock_user = {"user_id": self.test_user_id}
    
    @patch('app.middleware.auth.get_current_user')
    @patch('app.services.nlu_service.nlu_service.extract_entities')
    def test_nlu_processing_error_during_analysis(self, mock_nlu, mock_auth):
        """Test NLU processing error handling during analysis"""
        mock_auth.return_value = self.mock_user
        
        from app.core.exceptions import NLUProcessingError
        mock_nlu.side_effect = NLUProcessingError("NER model failed to load")
        
        request_data = {
            "job_description": "Python developer position",
            "resume_text": "John Doe\nSoftware Engineer with Python experience"
        }
        
        response = self.client.post("/api/v1/analyze", json=request_data)
        
        assert response.status_code == 422
        data = response.json()
        assert data["detail"]["error_code"] == "NLU_PROCESSING_FAILED"
    
    def test_invalid_uuid_in_endpoints(self):
        """Test endpoints with invalid UUID parameters"""
        with patch('app.middleware.auth.get_current_user') as mock_auth:
            mock_auth.return_value = self.mock_user
            
            # Test invalid analysis ID
            response = self.client.get("/api/v1/analyses/invalid-uuid")
            assert response.status_code == 422  # FastAPI validation error
    
    def test_pagination_edge_cases(self):
        """Test pagination with edge case parameters"""
        with patch('app.middleware.auth.get_current_user') as mock_auth:
            mock_auth.return_value = self.mock_user
            
            with patch('app.services.database_service.db_service.get_user_analyses') as mock_get_analyses:
                with patch('app.services.database_service.db_service.analyses.get_user_analyses_count') as mock_count:
                    mock_get_analyses.return_value = []
                    mock_count.return_value = 0
                    
                    # Test with page 0 (should be rejected)
                    response = self.client.get("/api/v1/analyses?page=0")
                    assert response.status_code == 422
                    
                    # Test with negative page size
                    response = self.client.get("/api/v1/analyses?page_size=-1")
                    assert response.status_code == 422
                    
                    # Test with page size exceeding limit
                    response = self.client.get("/api/v1/analyses?page_size=200")
                    assert response.status_code == 422


# Pytest markers for test organization
pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio
]