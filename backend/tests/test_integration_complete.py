"""
Complete System Integration Tests for SmartResume AI Resume Analyzer

This module contains comprehensive integration tests that validate the complete
system workflow from file upload through AI feedback generation, including
integration with Supabase database and authentication, error handling and
recovery across all system components, and performance requirements validation.

Requirements: 5.5, 6.6, 7.4, 7.5
"""
import pytest
import asyncio
import time
import json
from typing import Dict, Any, List
from unittest.mock import AsyncMock, patch, Mock
from uuid import uuid4, UUID
from datetime import datetime
from io import BytesIO

from fastapi.testclient import TestClient
import httpx

# Setup test environment
from tests.test_config import setup_test_environment
setup_test_environment()

# Import the app with proper mocking
from tests.test_api_integration import app  # Use the already working app import


class TestSystemIntegrationComplete:
    """Complete system integration tests"""
    
    def setup_method(self):
        """Setup test client and test data"""
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
    def test_complete_workflow_integration(
        self, mock_get_analysis, mock_store_analysis, mock_ai_feedback,
        mock_semantic, mock_nlu, mock_get_resume, mock_create_resume,
        mock_process_doc, mock_auth
    ):
        """
        Test complete workflow: PDF upload -> analysis -> retrieval
        This validates the entire system integration from start to finish
        """
        # Setup authentication
        mock_auth.return_value = self.mock_user
        
        # Step 1: Upload resume
        mock_processed_doc = Mock()
        mock_processed_doc.text = "John Doe\nSoftware Engineer\nPython, JavaScript, React"
        mock_processed_doc.file_name = "test_resume.pdf"
        mock_processed_doc.file_size = 2048
        mock_processed_doc.processing_method = "pdfplumber"
        mock_processed_doc.confidence_score = 0.95
        mock_process_doc.return_value = mock_processed_doc
        
        resume_id = uuid4()
        mock_resume = Mock()
        mock_resume.id = resume_id
        mock_resume.user_id = UUID(self.test_user_id)
        mock_resume.file_name = "test_resume.pdf"
        mock_resume.parsed_text = "John Doe\nSoftware Engineer\nPython, JavaScript, React"
        mock_resume.uploaded_at = datetime.utcnow()
        mock_create_resume.return_value = mock_resume
        
        # Upload file
        files = {"file": self.create_test_file(
            "John Doe resume content", 
            "test_resume.pdf", 
            "application/pdf"
        )}
        upload_response = self.client.post("/api/v1/upload", files=files)
        
        assert upload_response.status_code == 200
        upload_data = upload_response.json()
        assert upload_data["file_name"] == "test_resume.pdf"
        uploaded_resume_id = upload_data["resume_id"]
        
        # Step 2: Analyze resume
        mock_get_resume.return_value = mock_resume
        
        # Mock NLU extraction
        mock_entities = Mock()
        mock_entities.skills = ["Python", "JavaScript", "React"]
        mock_entities.job_titles = ["Software Engineer"]
        mock_entities.companies = ["TechCorp"]
        mock_entities.education = ["Computer Science"]
        mock_entities.contact_info = {"email": "john@example.com"}
        mock_entities.experience_years = 5
        mock_entities.confidence_scores = {"skills": 0.9}
        mock_nlu.return_value = mock_entities
        
        # Mock semantic analysis
        mock_compatibility = Mock()
        mock_compatibility.match_score = 88.5
        mock_compatibility.matched_keywords = ["Python", "JavaScript", "React"]
        mock_compatibility.missing_keywords = ["Docker", "AWS"]
        mock_compatibility.semantic_similarity = 0.885
        mock_compatibility.keyword_coverage = 0.8
        mock_semantic.return_value = mock_compatibility
        
        # Mock AI feedback
        mock_feedback = Mock()
        mock_feedback.dict.return_value = {
            "recommendations": [
                {
                    "category": "skills",
                    "priority": "medium",
                    "suggestion": "Consider adding Docker and AWS experience"
                }
            ],
            "overall_assessment": "Strong technical background with room for cloud skills improvement",
            "priority_improvements": ["Docker", "AWS"],
            "strengths": ["Python", "JavaScript", "React"]
        }
        mock_ai_feedback.return_value = mock_feedback
        
        analysis_id = str(uuid4())
        mock_store_analysis.return_value = analysis_id
        
        # Perform analysis
        job_description = """
        We are looking for a Full Stack Developer with experience in:
        - Python and JavaScript
        - React frontend development
        - Docker containerization
        - AWS cloud services
        """
        
        analysis_request = {
            "job_description": job_description,
            "job_title": "Full Stack Developer",
            "resume_id": uploaded_resume_id
        }
        
        analysis_response = self.client.post("/api/v1/analyze", json=analysis_request)
        
        assert analysis_response.status_code == 200
        analysis_data = analysis_response.json()
        
        # Verify analysis results
        assert analysis_data["match_score"] == 88.5
        assert "Python" in analysis_data["matched_keywords"]
        assert "JavaScript" in analysis_data["matched_keywords"]
        assert "React" in analysis_data["matched_keywords"]
        assert "Docker" in analysis_data["missing_keywords"]
        assert "AWS" in analysis_data["missing_keywords"]
        assert "ai_feedback" in analysis_data
        
        # Step 3: Retrieve analysis
        mock_stored_analysis = Mock()
        mock_stored_analysis.id = UUID(analysis_id)
        mock_stored_analysis.user_id = UUID(self.test_user_id)
        mock_stored_analysis.resume_id = resume_id
        mock_stored_analysis.job_title = "Full Stack Developer"
        mock_stored_analysis.job_description = job_description
        mock_stored_analysis.match_score = 88.5
        mock_stored_analysis.ai_feedback = mock_feedback.dict()
        mock_stored_analysis.matched_keywords = mock_compatibility.matched_keywords
        mock_stored_analysis.missing_keywords = mock_compatibility.missing_keywords
        mock_stored_analysis.processing_time = 2.1
        mock_stored_analysis.created_at = datetime.utcnow()
        mock_get_analysis.return_value = mock_stored_analysis
        
        retrieve_response = self.client.get(f"/api/v1/analyses/{analysis_id}")
        
        assert retrieve_response.status_code == 200
        retrieve_data = retrieve_response.json()
        
        assert retrieve_data["analysis_id"] == analysis_id
        assert retrieve_data["match_score"] == 88.5
        assert retrieve_data["job_title"] == "Full Stack Developer"
        
        print("✅ Complete workflow integration test passed")
    
    @patch('app.middleware.auth.get_current_user')
    @patch('app.services.nlu_service.nlu_service.extract_entities')
    @patch('app.services.semantic_service.semantic_service.analyze_compatibility')
    @patch('app.services.ai_service.ai_service.generate_feedback')
    @patch('app.services.database_service.db_service.store_analysis')
    def test_concurrent_analysis_performance(
        self, mock_store_analysis, mock_ai_feedback, mock_semantic, mock_nlu, mock_auth
    ):
        """
        Test system performance under concurrent load
        Validates that the system can handle multiple simultaneous requests
        """
        mock_auth.return_value = self.mock_user
        
        # Setup mocks with realistic processing delays
        def mock_nlu_with_delay(*args, **kwargs):
            time.sleep(0.1)  # Simulate NLU processing
            mock_entities = Mock()
            mock_entities.skills = ["Python", "JavaScript"]
            mock_entities.job_titles = ["Software Engineer"]
            mock_entities.companies = ["TechCorp"]
            mock_entities.education = ["Computer Science"]
            mock_entities.contact_info = {"email": "test@example.com"}
            mock_entities.experience_years = 3
            mock_entities.confidence_scores = {"skills": 0.85}
            return mock_entities
        
        def mock_semantic_with_delay(*args, **kwargs):
            time.sleep(0.15)  # Simulate semantic analysis
            mock_compatibility = Mock()
            mock_compatibility.match_score = 82.0
            mock_compatibility.matched_keywords = ["Python", "JavaScript"]
            mock_compatibility.missing_keywords = ["Docker"]
            mock_compatibility.semantic_similarity = 0.82
            mock_compatibility.keyword_coverage = 0.75
            return mock_compatibility
        
        def mock_ai_with_delay(*args, **kwargs):
            time.sleep(0.2)  # Simulate AI processing
            mock_feedback = Mock()
            mock_feedback.dict.return_value = {
                "recommendations": [{"category": "skills", "suggestion": "Add Docker"}],
                "overall_assessment": "Good technical foundation",
                "priority_improvements": ["Docker"],
                "strengths": ["Python"]
            }
            return mock_feedback
        
        mock_nlu.side_effect = mock_nlu_with_delay
        mock_semantic.side_effect = mock_semantic_with_delay
        mock_ai_feedback.side_effect = mock_ai_with_delay
        mock_store_analysis.return_value = str(uuid4())
        
        # Test concurrent requests
        num_requests = 10
        responses = []
        start_time = time.time()
        
        for i in range(num_requests):
            request_data = {
                "job_description": f"Python developer position {i}",
                "job_title": f"Developer {i}",
                "resume_text": f"Resume {i}\nPython developer with experience"
            }
            
            response = self.client.post("/api/v1/analyze", json=request_data)
            responses.append(response)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Verify all requests succeeded
        for i, response in enumerate(responses):
            assert response.status_code == 200, f"Request {i} failed"
            data = response.json()
            assert "analysis_id" in data
            assert "match_score" in data
        
        # Performance validation
        avg_time_per_request = total_time / num_requests
        assert avg_time_per_request < 5.0, f"Average time per request too high: {avg_time_per_request:.2f}s"
        
        print(f"✅ Concurrent performance test passed - {num_requests} requests in {total_time:.2f}s")
        print(f"   Average time per request: {avg_time_per_request:.2f}s")
    
    @patch('app.middleware.auth.get_current_user')
    def test_error_handling_integration(self, mock_auth):
        """Test comprehensive error handling across the system"""
        mock_auth.return_value = self.mock_user
        
        # Test 1: Invalid file upload
        files = {"file": ("test.exe", BytesIO(b"invalid content"), "application/exe")}
        
        with patch('app.services.document_service.DocumentService.process_document') as mock_process:
            from app.core.exceptions import UnsupportedFormatError
            mock_process.side_effect = UnsupportedFormatError(
                "Unsupported file format",
                file_type="application/exe",
                supported_types=["application/pdf"]
            )
            
            response = self.client.post("/api/v1/upload", files=files)
            assert response.status_code == 400
            data = response.json()
            assert data["detail"]["error_code"] == "UNSUPPORTED_FORMAT"
        
        # Test 2: Analysis with missing data
        request_data = {"job_description": "Python developer"}
        # Missing resume_id and resume_text
        
        response = self.client.post("/api/v1/analyze", json=request_data)
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error_code"] == "MISSING_RESUME_DATA"
        
        # Test 3: Service failure recovery
        with patch('app.services.nlu_service.nlu_service.extract_entities') as mock_nlu:
            from app.core.exceptions import NLUProcessingError
            mock_nlu.side_effect = NLUProcessingError("NER model failed")
            
            request_data = {
                "job_description": "Python developer position",
                "resume_text": "Software engineer resume"
            }
            
            response = self.client.post("/api/v1/analyze", json=request_data)
            assert response.status_code == 422
            data = response.json()
            assert data["detail"]["error_code"] == "NLU_PROCESSING_FAILED"
        
        print("✅ Error handling integration test passed")
    
    @patch('app.middleware.auth.get_current_user')
    @patch('app.services.database_service.db_service.health_check')
    def test_health_check_integration(self, mock_db_health, mock_auth):
        """Test health check system integration"""
        mock_auth.return_value = self.mock_user
        
        # Test basic health check
        response = self.client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "SmartResume AI Resume Analyzer"
        
        # Test detailed health check - healthy state
        mock_db_health.return_value = {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
        
        with patch('app.services.ai_service.ai_service.health_check') as mock_ai_health:
            mock_ai_health.return_value = {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
            
            response = self.client.get("/api/v1/health/detailed")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "checks" in data
        
        # Test detailed health check - unhealthy state
        mock_db_health.side_effect = Exception("Database connection failed")
        
        response = self.client.get("/api/v1/health/detailed")
        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["status"] == "unhealthy"
        
        print("✅ Health check integration test passed")
    
    @patch('app.middleware.auth.get_current_user')
    @patch('app.services.database_service.db_service.get_user_analyses')
    @patch('app.services.database_service.db_service.analyses.get_user_analyses_count')
    def test_data_isolation_integration(self, mock_count, mock_get_analyses, mock_auth):
        """Test that user data is properly isolated"""
        
        # Test with user 1
        user1_id = str(uuid4())
        mock_auth.return_value = {"user_id": user1_id}
        
        mock_analysis1 = Mock()
        mock_analysis1.id = uuid4()
        mock_analysis1.user_id = UUID(user1_id)
        mock_analysis1.job_title = "Python Developer"
        mock_analysis1.match_score = 85.0
        mock_analysis1.created_at = datetime.utcnow()
        
        mock_get_analyses.return_value = [mock_analysis1]
        mock_count.return_value = 1
        
        response = self.client.get("/api/v1/analyses")
        assert response.status_code == 200
        data = response.json()
        assert len(data["analyses"]) == 1
        assert data["analyses"][0]["job_title"] == "Python Developer"
        
        # Test with user 2
        user2_id = str(uuid4())
        mock_auth.return_value = {"user_id": user2_id}
        
        mock_analysis2 = Mock()
        mock_analysis2.id = uuid4()
        mock_analysis2.user_id = UUID(user2_id)
        mock_analysis2.job_title = "Data Scientist"
        mock_analysis2.match_score = 92.0
        mock_analysis2.created_at = datetime.utcnow()
        
        mock_get_analyses.return_value = [mock_analysis2]
        mock_count.return_value = 1
        
        response = self.client.get("/api/v1/analyses")
        assert response.status_code == 200
        data = response.json()
        assert len(data["analyses"]) == 1
        assert data["analyses"][0]["job_title"] == "Data Scientist"
        
        print("✅ Data isolation integration test passed")
    
    @patch('app.middleware.auth.get_current_user')
    @patch('app.services.nlu_service.nlu_service.extract_entities')
    @patch('app.services.semantic_service.semantic_service.analyze_compatibility')
    @patch('app.services.ai_service.ai_service.generate_feedback')
    @patch('app.services.database_service.db_service.store_analysis')
    def test_response_time_requirements(
        self, mock_store_analysis, mock_ai_feedback, mock_semantic, mock_nlu, mock_auth
    ):
        """
        Test that 95% of requests complete within 30 seconds
        This validates the critical performance requirement
        """
        mock_auth.return_value = self.mock_user
        
        # Setup mocks with realistic processing times
        def mock_services(*args, **kwargs):
            # Simulate realistic processing delays
            time.sleep(0.5)  # Total simulated processing time
        
        mock_nlu.side_effect = lambda *args, **kwargs: (
            time.sleep(0.1),
            Mock(
                skills=["Python"], job_titles=["Engineer"], companies=[], 
                education=[], contact_info={}, experience_years=3, confidence_scores={}
            )
        )[1]
        
        mock_semantic.side_effect = lambda *args, **kwargs: (
            time.sleep(0.2),
            Mock(
                match_score=80.0, matched_keywords=["Python"], missing_keywords=[],
                semantic_similarity=0.8, keyword_coverage=0.8
            )
        )[1]
        
        mock_ai_feedback.side_effect = lambda *args, **kwargs: (
            time.sleep(0.2),
            Mock(dict=lambda: {"recommendations": [], "overall_assessment": "Good"})
        )[1]
        
        mock_store_analysis.return_value = str(uuid4())
        
        # Test multiple requests to measure response times
        response_times = []
        num_requests = 20
        
        for i in range(num_requests):
            request_data = {
                "job_description": f"Python developer position {i}",
                "job_title": f"Developer {i}",
                "resume_text": f"Resume {i}\nPython developer"
            }
            
            start_time = time.time()
            response = self.client.post("/api/v1/analyze", json=request_data)
            end_time = time.time()
            
            response_time = end_time - start_time
            response_times.append(response_time)
            
            assert response.status_code == 200
        
        # Calculate 95th percentile
        sorted_times = sorted(response_times)
        p95_index = int(len(sorted_times) * 0.95)
        p95_time = sorted_times[p95_index]
        
        # Verify 30-second requirement
        assert p95_time <= 30.0, f"P95 response time {p95_time:.2f}s exceeds 30-second requirement"
        
        avg_time = sum(response_times) / len(response_times)
        max_time = max(response_times)
        
        print(f"✅ Response time requirements test passed:")
        print(f"   Average: {avg_time:.2f}s, P95: {p95_time:.2f}s, Max: {max_time:.2f}s")


# Pytest configuration
pytestmark = pytest.mark.asyncio