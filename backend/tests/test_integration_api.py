"""
Integration tests for API endpoints
Tests complete end-to-end analysis workflow with real files,
authentication, authorization, and error handling.
"""
import pytest
import asyncio
import tempfile
import os
from pathlib import Path
from typing import Dict, Any
from unittest.mock import AsyncMock, patch, Mock
from uuid import uuid4, UUID
from datetime import datetime
from io import BytesIO

from fastapi.testclient import TestClient
from fastapi import UploadFile
import httpx

# Setup test environment before importing app modules
from tests.test_config import setup_test_environment
setup_test_environment()

# Mock ML dependencies before importing app modules
with patch('app.utils.ml_utils.model_cache'):
    with patch('transformers.AutoTokenizer'):
        with patch('transformers.AutoModelForTokenClassification'):
            with patch('sentence_transformers.SentenceTransformer'):
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
    @patch('app.utils.ml_utils.model_cache.health_check')
    @patch('app.services.ai_service.ai_service.health_check')
    def test_detailed_health_check_all_healthy(self, mock_ai_health, mock_ml_health, mock_db_health):
        """Test detailed health check when all services are healthy"""
        # Mock all services as healthy
        mock_db_health.return_value = {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
        mock_ml_health.return_value = {"ner_model": True, "embedding_model": True}
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
    
    @patch('app.services.database_service.db_service.health_check')
    def test_database_health_endpoint(self, mock_db_health):
        """Test database-specific health endpoint"""
        mock_db_health.return_value = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "pool_info": {"active": 5, "idle": 10}
        }
        
        response = self.client.get("/api/v1/health/database")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "pool_info" in data


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
        
        from app.models.entities import ProcessedDocument, Resume
        mock_processed_doc = ProcessedDocument(
            text="John Doe\nSoftware Engineer\nPython, JavaScript",
            file_name="test_resume.pdf",
            file_size=1024,
            processing_method="pdfplumber",
            confidence_score=0.95
        )
        mock_process_doc.return_value = mock_processed_doc
        
        mock_resume = Resume(
            id=uuid4(),
            user_id=UUID(self.test_user_id),
            file_name="test_resume.pdf",
            file_url=None,
            parsed_text="John Doe\nSoftware Engineer\nPython, JavaScript",
            uploaded_at=datetime.utcnow()
        )
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
    def test_upload_without_authentication(self, mock_auth):
        """Test upload endpoint requires authentication"""
        mock_auth.side_effect = Exception("Authentication required")
        
        files = {"file": self.create_test_file("Test content", "test.pdf", "application/pdf")}
        
        with pytest.raises(Exception):
            self.client.post("/api/v1/upload", files=files)
    
    @patch('app.middleware.auth.get_current_user')
    @patch('app.services.document_service.DocumentService.process_document')
    def test_upload_unsupported_format(self, mock_process_doc, mock_auth):
        """Test upload with unsupported file format"""
        mock_auth.return_value = self.mock_user
        
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
    @patch('app.services.document_service.DocumentService.process_document')
    def test_upload_file_too_large(self, mock_process_doc, mock_auth):
        """Test upload with file exceeding size limit"""
        mock_auth.return_value = self.mock_user
        
        from app.core.exceptions import FileSizeError
        mock_process_doc.side_effect = FileSizeError(
            "File too large",
            file_size=15 * 1024 * 1024,  # 15MB
            max_size=10 * 1024 * 1024    # 10MB limit
        )
        
        files = {"file": self.create_test_file("x" * 1000, "large_file.pdf", "application/pdf")}
        
        response = self.client.post("/api/v1/upload", files=files)
        
        assert response.status_code == 413
        data = response.json()
        assert data["detail"]["error_code"] == "FILE_TOO_LARGE"
        assert data["detail"]["details"]["max_size"] == 10 * 1024 * 1024
    
    @patch('app.middleware.auth.get_current_user')
    @patch('app.services.database_service.db_service.resumes.get_user_resumes')
    def test_get_user_resumes(self, mock_get_resumes, mock_auth):
        """Test retrieving user's uploaded resumes"""
        mock_auth.return_value = self.mock_user
        
        from app.models.entities import Resume
        mock_resumes = [
            Resume(
                id=uuid4(),
                user_id=UUID(self.test_user_id),
                file_name="resume1.pdf",
                file_url=None,
                parsed_text="Resume 1 content",
                uploaded_at=datetime.utcnow()
            ),
            Resume(
                id=uuid4(),
                user_id=UUID(self.test_user_id),
                file_name="resume2.docx",
                file_url=None,
                parsed_text="Resume 2 content",
                uploaded_at=datetime.utcnow()
            )
        ]
        mock_get_resumes.return_value = mock_resumes
        
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
        
        from app.models.entities import Resume, ResumeEntities, CompatibilityAnalysis, AIFeedback
        
        # Mock resume retrieval
        mock_resume = Resume(
            id=self.test_resume_id,
            user_id=UUID(self.test_user_id),
            file_name="test_resume.pdf",
            file_url=None,
            parsed_text="John Doe\nSoftware Engineer\nPython, JavaScript, React",
            uploaded_at=datetime.utcnow()
        )
        mock_get_resume.return_value = mock_resume
        
        # Mock NLU service
        mock_entities = ResumeEntities(
            skills=["Python", "JavaScript", "React"],
            job_titles=["Software Engineer"],
            companies=["TechCorp"],
            education=["Computer Science"],
            contact_info={"email": "john@example.com"},
            experience_years=5,
            confidence_scores={"skills": 0.9}
        )
        mock_nlu.return_value = mock_entities
        
        # Mock semantic analysis
        mock_compatibility = CompatibilityAnalysis(
            match_score=85.5,
            matched_keywords=["Python", "JavaScript"],
            missing_keywords=["Docker", "AWS"],
            semantic_similarity=0.855,
            keyword_coverage=0.75
        )
        mock_semantic.return_value = mock_compatibility
        
        # Mock AI feedback
        mock_feedback = AIFeedback(
            recommendations=[
                {"category": "skills", "priority": "high", "suggestion": "Add Docker experience"}
            ],
            overall_assessment="Strong technical background",
            priority_improvements=["Add cloud experience"],
            strengths=["Strong programming skills"]
        )
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
    @patch('app.services.nlu_service.nlu_service.extract_entities')
    @patch('app.services.semantic_service.semantic_service.analyze_compatibility')
    @patch('app.services.ai_service.ai_service.generate_feedback')
    @patch('app.services.database_service.db_service.store_analysis')
    def test_analyze_resume_with_resume_text_success(
        self, mock_store_analysis, mock_ai_feedback, mock_semantic, mock_nlu, mock_auth
    ):
        """Test successful resume analysis using direct resume text"""
        # Setup mocks (similar to previous test but without resume retrieval)
        mock_auth.return_value = self.mock_user
        
        from app.models.entities import ResumeEntities, CompatibilityAnalysis, AIFeedback
        
        mock_entities = ResumeEntities(
            skills=["Python", "JavaScript"],
            job_titles=["Software Engineer"],
            companies=["TechCorp"],
            education=["Computer Science"],
            contact_info={"email": "john@example.com"},
            experience_years=3,
            confidence_scores={"skills": 0.85}
        )
        mock_nlu.return_value = mock_entities
        
        mock_compatibility = CompatibilityAnalysis(
            match_score=78.2,
            matched_keywords=["Python"],
            missing_keywords=["Docker", "AWS", "Kubernetes"],
            semantic_similarity=0.782,
            keyword_coverage=0.6
        )
        mock_semantic.return_value = mock_compatibility
        
        mock_feedback = AIFeedback(
            recommendations=[
                {"category": "skills", "priority": "high", "suggestion": "Learn containerization"}
            ],
            overall_assessment="Good foundation, needs cloud skills",
            priority_improvements=["Docker", "AWS"],
            strengths=["Python expertise"]
        )
        mock_ai_feedback.return_value = mock_feedback
        
        analysis_id = str(uuid4())
        mock_store_analysis.return_value = analysis_id
        
        # Make request with resume text
        request_data = {
            "job_description": "Python developer needed with Docker and Kubernetes experience",
            "job_title": "DevOps Engineer",
            "resume_text": "John Doe\nSoftware Engineer with 3 years Python experience\nWorked at TechCorp building web applications"
        }
        
        response = self.client.post("/api/v1/analyze", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["match_score"] == 78.2
        assert data["matched_keywords"] == ["Python"]
        assert data["missing_keywords"] == ["Docker", "AWS", "Kubernetes"]
    
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
    
    @patch('app.middleware.auth.get_current_user')
    @patch('app.services.database_service.db_service.resumes.get_resume_by_id')
    def test_analyze_resume_unauthorized_access(self, mock_get_resume, mock_auth):
        """Test analysis with resume belonging to different user"""
        mock_auth.return_value = self.mock_user
        
        from app.models.entities import Resume
        # Resume belongs to different user
        other_user_id = str(uuid4())
        mock_resume = Resume(
            id=self.test_resume_id,
            user_id=UUID(other_user_id),  # Different user
            file_name="test_resume.pdf",
            file_url=None,
            parsed_text="Resume content",
            uploaded_at=datetime.utcnow()
        )
        mock_get_resume.return_value = mock_resume
        
        request_data = {
            "job_description": "Python developer position",
            "resume_id": str(self.test_resume_id)
        }
        
        response = self.client.post("/api/v1/analyze", json=request_data)
        
        assert response.status_code == 403
        data = response.json()
        assert data["detail"]["error_code"] == "UNAUTHORIZED_RESUME_ACCESS"
    
    @patch('app.middleware.auth.get_current_user')
    def test_analyze_resume_insufficient_text(self, mock_auth):
        """Test analysis with insufficient resume text"""
        mock_auth.return_value = self.mock_user
        
        request_data = {
            "job_description": "Python developer position",
            "resume_text": "Short"  # Too short for analysis
        }
        
        response = self.client.post("/api/v1/analyze", json=request_data)
        
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error_code"] == "INSUFFICIENT_RESUME_TEXT"


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
        
        from app.models.entities import AnalysisResult
        
        # Mock analyses
        mock_analyses = [
            AnalysisResult(
                id=uuid4(),
                user_id=UUID(self.test_user_id),
                resume_id=uuid4(),
                job_title="Python Developer",
                job_description="Python development role",
                match_score=85.5,
                ai_feedback={"recommendations": []},
                matched_keywords=["Python", "Django"],
                missing_keywords=["Docker"],
                processing_time=2.5,
                created_at=datetime.utcnow()
            ),
            AnalysisResult(
                id=uuid4(),
                user_id=UUID(self.test_user_id),
                resume_id=uuid4(),
                job_title="Full Stack Developer",
                job_description="Full stack development role",
                match_score=78.2,
                ai_feedback={"recommendations": []},
                matched_keywords=["JavaScript", "React"],
                missing_keywords=["Node.js"],
                processing_time=3.1,
                created_at=datetime.utcnow()
            )
        ]
        mock_get_analyses.return_value = mock_analyses
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
        
        from app.models.entities import AnalysisResult
        
        analysis_id = uuid4()
        mock_analysis = AnalysisResult(
            id=analysis_id,
            user_id=UUID(self.test_user_id),
            resume_id=uuid4(),
            job_title="Senior Python Developer",
            job_description="Senior Python development position with Django",
            match_score=92.3,
            ai_feedback={
                "recommendations": [
                    {"category": "skills", "suggestion": "Add more cloud experience"}
                ],
                "overall_assessment": "Excellent match"
            },
            matched_keywords=["Python", "Django", "PostgreSQL"],
            missing_keywords=["AWS"],
            processing_time=2.8,
            created_at=datetime.utcnow()
        )
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
    
    @patch('app.middleware.auth.get_current_user')
    @patch('app.services.database_service.db_service.get_analysis_by_id')
    def test_get_analysis_unauthorized_access(self, mock_get_analysis, mock_auth):
        """Test retrieval of analysis belonging to different user"""
        mock_auth.return_value = self.mock_user
        
        from app.models.entities import AnalysisResult
        
        # Analysis belongs to different user
        other_user_id = str(uuid4())
        analysis_id = uuid4()
        mock_analysis = AnalysisResult(
            id=analysis_id,
            user_id=UUID(other_user_id),  # Different user
            resume_id=uuid4(),
            job_title="Python Developer",
            job_description="Python role",
            match_score=85.0,
            ai_feedback={},
            matched_keywords=[],
            missing_keywords=[],
            processing_time=2.0,
            created_at=datetime.utcnow()
        )
        mock_get_analysis.return_value = mock_analysis
        
        response = self.client.get(f"/api/v1/analyses/{analysis_id}")
        
        assert response.status_code == 403
        data = response.json()
        assert data["detail"]["error_code"] == "UNAUTHORIZED_ACCESS"
    
    @patch('app.middleware.auth.get_current_user')
    @patch('app.services.database_service.db_service.get_analysis_by_id')
    @patch('app.services.database_service.db_service.connection_manager.get_connection')
    def test_delete_analysis_success(self, mock_get_conn, mock_get_analysis, mock_auth):
        """Test successful analysis deletion"""
        mock_auth.return_value = self.mock_user
        
        from app.models.entities import AnalysisResult
        
        analysis_id = uuid4()
        mock_analysis = AnalysisResult(
            id=analysis_id,
            user_id=UUID(self.test_user_id),
            resume_id=uuid4(),
            job_title="Python Developer",
            job_description="Python role",
            match_score=85.0,
            ai_feedback={},
            matched_keywords=[],
            missing_keywords=[],
            processing_time=2.0,
            created_at=datetime.utcnow()
        )
        mock_get_analysis.return_value = mock_analysis
        
        # Mock database connection
        mock_conn = AsyncMock()
        mock_get_conn.return_value.__aenter__.return_value = mock_conn
        
        response = self.client.delete(f"/api/v1/analyses/{analysis_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Analysis deleted successfully"
        assert data["analysis_id"] == str(analysis_id)


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
    @patch('app.services.nlu_service.nlu_service.extract_entities')
    @patch('app.services.semantic_service.semantic_service.analyze_compatibility')
    @patch('app.services.ai_service.ai_service.generate_feedback')
    @patch('app.services.database_service.db_service.store_analysis')
    def test_complete_workflow_upload_and_analyze(
        self, mock_store_analysis, mock_ai_feedback, mock_semantic, 
        mock_nlu, mock_create_resume, mock_process_doc, mock_auth
    ):
        """Test complete workflow: upload resume -> analyze -> retrieve results"""
        # Setup authentication
        mock_auth.return_value = self.mock_user
        
        # Step 1: Upload resume
        from app.models.entities import ProcessedDocument, Resume, ResumeEntities, CompatibilityAnalysis, AIFeedback
        
        resume_text = """
        John Doe
        Senior Software Engineer
        Email: john.doe@example.com
        Phone: (555) 123-4567
        
        EXPERIENCE
        Senior Software Engineer at TechCorp (2020-2023)
        - Developed web applications using Python and React
        - Led a team of 5 developers
        - Implemented CI/CD pipelines using Docker
        
        SKILLS
        Python, JavaScript, React, Django, PostgreSQL, Docker, AWS
        """
        
        mock_processed_doc = ProcessedDocument(
            text=resume_text,
            file_name="john_doe_resume.pdf",
            file_size=2048,
            processing_method="pdfplumber",
            confidence_score=0.98
        )
        mock_process_doc.return_value = mock_processed_doc
        
        resume_id = uuid4()
        mock_resume = Resume(
            id=resume_id,
            user_id=UUID(self.test_user_id),
            file_name="john_doe_resume.pdf",
            file_url=None,
            parsed_text=resume_text,
            uploaded_at=datetime.utcnow()
        )
        mock_create_resume.return_value = mock_resume
        
        # Upload file
        files = {"file": self.create_test_file(resume_text, "john_doe_resume.pdf", "application/pdf")}
        upload_response = self.client.post("/api/v1/upload", files=files)
        
        assert upload_response.status_code == 200
        upload_data = upload_response.json()
        uploaded_resume_id = upload_data["resume_id"]
        
        # Step 2: Analyze resume
        # Mock analysis services
        mock_entities = ResumeEntities(
            skills=["Python", "JavaScript", "React", "Django", "PostgreSQL", "Docker", "AWS"],
            job_titles=["Senior Software Engineer"],
            companies=["TechCorp"],
            education=["Computer Science"],
            contact_info={"email": "john.doe@example.com", "phone": "(555) 123-4567"},
            experience_years=7,
            confidence_scores={"skills": 0.95, "job_titles": 0.92}
        )
        mock_nlu.return_value = mock_entities
        
        mock_compatibility = CompatibilityAnalysis(
            match_score=94.2,
            matched_keywords=["Python", "Django", "PostgreSQL", "Docker", "AWS", "CI/CD"],
            missing_keywords=["Kubernetes"],
            semantic_similarity=0.942,
            keyword_coverage=0.9
        )
        mock_semantic.return_value = mock_compatibility
        
        mock_feedback = AIFeedback(
            recommendations=[
                {
                    "category": "skills",
                    "priority": "medium",
                    "suggestion": "Consider adding Kubernetes experience to strengthen DevOps profile"
                },
                {
                    "category": "experience",
                    "priority": "low",
                    "suggestion": "Highlight specific achievements with metrics"
                }
            ],
            overall_assessment="Excellent match for the position with strong technical skills and relevant experience",
            priority_improvements=["Kubernetes", "Metrics in achievements"],
            strengths=["Strong Python/Django experience", "Leadership experience", "DevOps skills"]
        )
        mock_ai_feedback.return_value = mock_feedback
        
        analysis_id = str(uuid4())
        mock_store_analysis.return_value = analysis_id
        
        # Mock resume retrieval for analysis
        with patch('app.services.database_service.db_service.resumes.get_resume_by_id') as mock_get_resume:
            mock_get_resume.return_value = mock_resume
            
            # Perform analysis
            job_description = """
            We are seeking a Senior Python Developer to join our team.
            
            Requirements:
            - 5+ years of Python development experience
            - Experience with Django framework
            - Knowledge of PostgreSQL databases
            - Docker containerization experience
            - AWS cloud platform experience
            - CI/CD pipeline implementation
            - Leadership experience preferred
            
            Nice to have:
            - Kubernetes orchestration
            - React frontend experience
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
            assert "Docker" in analysis_data["matched_keywords"]
            assert "AWS" in analysis_data["matched_keywords"]
            assert "Kubernetes" in analysis_data["missing_keywords"]
            assert "ai_feedback" in analysis_data
            assert len(analysis_data["ai_feedback"]["recommendations"]) == 2
            assert analysis_data["ai_feedback"]["overall_assessment"].startswith("Excellent match")
        
        # Step 3: Verify we can retrieve the analysis
        with patch('app.services.database_service.db_service.get_analysis_by_id') as mock_get_analysis:
            from app.models.entities import AnalysisResult
            
            mock_stored_analysis = AnalysisResult(
                id=UUID(analysis_id),
                user_id=UUID(self.test_user_id),
                resume_id=resume_id,
                job_title="Senior Python Developer",
                job_description=job_description,
                match_score=94.2,
                ai_feedback=mock_feedback.dict(),
                matched_keywords=mock_compatibility.matched_keywords,
                missing_keywords=mock_compatibility.missing_keywords,
                processing_time=2.5,
                created_at=datetime.utcnow()
            )
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
    @patch('app.services.database_service.db_service.resumes.create_resume')
    def test_database_error_during_upload(self, mock_create_resume, mock_auth):
        """Test database error handling during upload"""
        mock_auth.return_value = self.mock_user
        
        from app.core.exceptions import DatabaseError
        mock_create_resume.side_effect = DatabaseError("Database connection failed")
        
        with patch('app.services.document_service.DocumentService.process_document') as mock_process:
            from app.models.entities import ProcessedDocument
            mock_process.return_value = ProcessedDocument(
                text="Test content",
                file_name="test.pdf",
                file_size=1024,
                processing_method="pdfplumber",
                confidence_score=0.9
            )
            
            files = {"file": ("test.pdf", BytesIO(b"test content"), "application/pdf")}
            response = self.client.post("/api/v1/upload", files=files)
            
            assert response.status_code == 500
            data = response.json()
            assert data["detail"]["error_code"] == "DATABASE_ERROR"
    
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
    
    @patch('app.middleware.auth.get_current_user')
    @patch('app.services.nlu_service.nlu_service.extract_entities')
    @patch('app.services.semantic_service.semantic_service.analyze_compatibility')
    def test_semantic_analysis_error_during_analysis(self, mock_semantic, mock_nlu, mock_auth):
        """Test semantic analysis error handling"""
        mock_auth.return_value = self.mock_user
        
        from app.models.entities import ResumeEntities
        from app.core.exceptions import SemanticAnalysisError
        
        mock_nlu.return_value = ResumeEntities(
            skills=["Python"],
            job_titles=["Engineer"],
            companies=[],
            education=[],
            contact_info={},
            experience_years=None,
            confidence_scores={}
        )
        
        mock_semantic.side_effect = SemanticAnalysisError("Embedding model failed")
        
        request_data = {
            "job_description": "Python developer position",
            "resume_text": "John Doe\nSoftware Engineer with Python experience"
        }
        
        response = self.client.post("/api/v1/analyze", json=request_data)
        
        assert response.status_code == 422
        data = response.json()
        assert data["detail"]["error_code"] == "SEMANTIC_ANALYSIS_FAILED"
    
    def test_invalid_uuid_in_endpoints(self):
        """Test endpoints with invalid UUID parameters"""
        with patch('app.middleware.auth.get_current_user') as mock_auth:
            mock_auth.return_value = self.mock_user
            
            # Test invalid analysis ID
            response = self.client.get("/api/v1/analyses/invalid-uuid")
            assert response.status_code == 422  # FastAPI validation error
            
            # Test invalid resume ID in analysis
            request_data = {
                "job_description": "Python developer position",
                "resume_id": "invalid-uuid"
            }
            response = self.client.post("/api/v1/analyze", json=request_data)
            assert response.status_code == 422  # FastAPI validation error
    
    def test_missing_required_fields(self):
        """Test endpoints with missing required fields"""
        with patch('app.middleware.auth.get_current_user') as mock_auth:
            mock_auth.return_value = self.mock_user
            
            # Test analysis without job_description
            request_data = {
                "resume_text": "John Doe resume"
                # Missing job_description
            }
            response = self.client.post("/api/v1/analyze", json=request_data)
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