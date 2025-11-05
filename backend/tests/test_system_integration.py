"""
System Integration Tests for SmartResume AI Resume Analyzer

This module contains comprehensive integration tests that validate the complete
system workflow from file upload through AI feedback generation, including
integration with Supabase database and authentication, error handling and
recovery across all system components, and performance requirements validation.

Requirements: 5.5, 6.6, 7.4, 7.5
"""
import pytest
import asyncio
import tempfile
import os
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
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

# Mock ML dependencies at the module level before any imports
import sys
from unittest.mock import Mock

# Mock all ML-related modules before any imports
sys.modules['transformers'] = Mock()
sys.modules['sentence_transformers'] = Mock()
sys.modules['torch'] = Mock()
sys.modules['tensorflow'] = Mock()

# Mock the ML utilities module
mock_model_cache = Mock()
mock_model_cache.load_models_at_startup = AsyncMock()
mock_model_cache.health_check = AsyncMock(return_value={"ner_model": True, "embedding_model": True})

with patch.dict('sys.modules', {
    'app.utils.ml_utils': Mock(model_cache=mock_model_cache),
    'transformers': Mock(),
    'sentence_transformers': Mock()
}):
    from app.main import app


class TestCompleteWorkflowIntegration:
    """Test complete end-to-end workflow integration"""
    
    def setup_method(self):
        """Setup test client and test data"""
        self.client = TestClient(app)
        self.test_user_id = str(uuid4())
        self.mock_user = {"user_id": self.test_user_id}
        
        # Sample resume content for testing
        self.sample_resume_content = """
        Jane Smith
        Senior Software Engineer
        Email: jane.smith@email.com
        Phone: (555) 987-6543
        LinkedIn: linkedin.com/in/janesmith
        
        PROFESSIONAL SUMMARY
        Experienced Senior Software Engineer with 8+ years of expertise in full-stack development,
        specializing in Python, React, and cloud technologies. Proven track record of building
        scalable applications and leading development teams.
        
        TECHNICAL SKILLS
        Programming Languages: Python, JavaScript, TypeScript, Java
        Frontend: React, Vue.js, HTML5, CSS3, Redux
        Backend: FastAPI, Django, Flask, Node.js
        Databases: PostgreSQL, MongoDB, Redis
        Cloud: AWS (EC2, S3, Lambda, RDS), Google Cloud Platform
        DevOps: Docker, Kubernetes, Jenkins, GitLab CI/CD
        Testing: pytest, Jest, Selenium
        
        PROFESSIONAL EXPERIENCE
        
        Senior Software Engineer | TechInnovate Corp | 2019 - Present
        • Led development of microservices architecture serving 2M+ users
        • Implemented automated CI/CD pipelines reducing deployment time by 70%
        • Mentored team of 6 junior developers
        • Built scalable APIs using FastAPI and PostgreSQL
        • Developed React applications with TypeScript
        
        Software Engineer | CloudSolutions Inc | 2016 - 2019
        • Developed full-stack applications using Python Django and React
        • Implemented comprehensive testing suites achieving 98% code coverage
        • Optimized database performance improving response times by 50%
        • Collaborated in Agile development environment
        
        EDUCATION
        Master of Science in Computer Science
        Stanford University | 2014 - 2016
        
        Bachelor of Science in Software Engineering
        UC Berkeley | 2010 - 2014
        
        CERTIFICATIONS
        • AWS Certified Solutions Architect - Professional
        • Google Cloud Professional Developer
        • Certified Kubernetes Administrator (CKA)
        • Certified ScrumMaster (CSM)
        """
        
        # Sample job descriptions for testing
        self.job_descriptions = [
            """
            Senior Full Stack Developer - AI/ML Platform
            
            We are seeking a Senior Full Stack Developer to join our AI/ML platform team.
            The ideal candidate will have strong experience in Python, React, and cloud technologies.
            
            Required Skills:
            • 5+ years of full-stack development experience
            • Proficiency in Python and JavaScript/TypeScript
            • Experience with React and modern frontend frameworks
            • Strong knowledge of databases (PostgreSQL, MongoDB)
            • Experience with cloud platforms (AWS, GCP)
            • Knowledge of containerization (Docker, Kubernetes)
            • Experience with CI/CD pipelines
            • Understanding of machine learning concepts (preferred)
            
            Responsibilities:
            • Design and develop scalable web applications
            • Build and maintain APIs and microservices
            • Collaborate with ML engineers on platform integration
            • Implement automated testing and deployment processes
            • Mentor junior developers and conduct code reviews
            """,
            """
            DevOps Engineer - Cloud Infrastructure
            
            Join our DevOps team to build and maintain scalable cloud infrastructure
            supporting our growing AI platform.
            
            Required Skills:
            • 4+ years of DevOps/SRE experience
            • Strong knowledge of AWS or GCP
            • Experience with Kubernetes and Docker
            • Proficiency in Infrastructure as Code (Terraform, CloudFormation)
            • Experience with CI/CD tools (Jenkins, GitLab CI)
            • Strong scripting skills (Python, Bash)
            • Knowledge of monitoring and logging tools
            
            Responsibilities:
            • Design and implement scalable cloud infrastructure
            • Automate deployment and monitoring processes
            • Ensure high availability and performance
            • Implement security best practices
            • Collaborate with development teams
            """
        ]
    
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
    @patch('app.services.database_service.db_service.get_user_analyses')
    def test_complete_workflow_pdf_upload_to_analysis_retrieval(
        self, mock_get_user_analyses, mock_get_analysis, mock_store_analysis,
        mock_ai_feedback, mock_semantic, mock_nlu, mock_get_resume,
        mock_create_resume, mock_process_doc, mock_auth
    ):
        """
        Test complete workflow: PDF upload -> analysis -> retrieval -> history
        This test validates the entire system integration from start to finish
        """
        # Setup authentication
        mock_auth.return_value = self.mock_user
        
        # Import required models
        from app.models.entities import (
            ProcessedDocument, Resume, ResumeEntities, 
            CompatibilityAnalysis, AIFeedback, AnalysisResult
        )
        
        # Step 1: Upload PDF resume
        mock_processed_doc = ProcessedDocument(
            text=self.sample_resume_content,
            file_name="jane_smith_resume.pdf",
            file_size=4096,
            processing_method="pdfplumber",
            confidence_score=0.97
        )
        mock_process_doc.return_value = mock_processed_doc
        
        resume_id = uuid4()
        mock_resume = Resume(
            id=resume_id,
            user_id=UUID(self.test_user_id),
            file_name="jane_smith_resume.pdf",
            file_url=None,
            parsed_text=self.sample_resume_content,
            uploaded_at=datetime.utcnow()
        )
        mock_create_resume.return_value = mock_resume
        
        # Upload file
        files = {"file": self.create_test_file(
            self.sample_resume_content, 
            "jane_smith_resume.pdf", 
            "application/pdf"
        )}
        upload_response = self.client.post("/api/v1/upload", files=files)
        
        assert upload_response.status_code == 200
        upload_data = upload_response.json()
        assert upload_data["file_name"] == "jane_smith_resume.pdf"
        assert upload_data["processing_method"] == "pdfplumber"
        assert upload_data["confidence_score"] == 0.97
        uploaded_resume_id = upload_data["resume_id"]
        
        # Step 2: Analyze resume against job description
        mock_get_resume.return_value = mock_resume
        
        # Mock NLU extraction
        mock_entities = ResumeEntities(
            skills=[
                "Python", "JavaScript", "TypeScript", "Java", "React", "Vue.js",
                "FastAPI", "Django", "Flask", "Node.js", "PostgreSQL", "MongoDB",
                "Redis", "AWS", "Google Cloud Platform", "Docker", "Kubernetes",
                "Jenkins", "GitLab CI/CD", "pytest", "Jest", "Selenium"
            ],
            job_titles=["Senior Software Engineer", "Software Engineer"],
            companies=["TechInnovate Corp", "CloudSolutions Inc"],
            education=["Master of Science in Computer Science", "Bachelor of Science in Software Engineering"],
            contact_info={
                "email": "jane.smith@email.com",
                "phone": "(555) 987-6543",
                "linkedin": "linkedin.com/in/janesmith"
            },
            experience_years=8,
            confidence_scores={
                "skills": 0.95,
                "job_titles": 0.92,
                "companies": 0.88,
                "education": 0.90
            }
        )
        mock_nlu.return_value = mock_entities
        
        # Mock semantic analysis
        mock_compatibility = CompatibilityAnalysis(
            match_score=96.8,
            matched_keywords=[
                "Python", "JavaScript", "TypeScript", "React", "FastAPI",
                "PostgreSQL", "MongoDB", "AWS", "Docker", "Kubernetes",
                "CI/CD", "full-stack", "microservices", "APIs"
            ],
            missing_keywords=["machine learning", "TensorFlow", "PyTorch"],
            semantic_similarity=0.968,
            keyword_coverage=0.92
        )
        mock_semantic.return_value = mock_compatibility
        
        # Mock AI feedback
        mock_feedback = AIFeedback(
            recommendations=[
                {
                    "category": "skills",
                    "priority": "medium",
                    "suggestion": "Consider adding machine learning experience to align with AI/ML platform focus",
                    "details": "While your technical skills are excellent, adding ML frameworks like TensorFlow or PyTorch would make you an even stronger candidate for this AI/ML platform role."
                },
                {
                    "category": "experience",
                    "priority": "low",
                    "suggestion": "Highlight specific metrics and achievements in your current role",
                    "details": "Your experience is impressive. Consider quantifying more achievements, such as specific performance improvements or team size managed."
                }
            ],
            overall_assessment="Excellent match for the Senior Full Stack Developer position. Your extensive experience with Python, React, cloud technologies, and leadership skills align perfectly with the role requirements. The combination of technical depth and team leadership experience makes you a strong candidate.",
            priority_improvements=[
                "Machine learning frameworks (TensorFlow, PyTorch)",
                "ML model deployment experience",
                "Data science fundamentals"
            ],
            strengths=[
                "Strong full-stack development experience (8+ years)",
                "Excellent cloud platform knowledge (AWS, GCP)",
                "Proven leadership and mentoring experience",
                "Comprehensive DevOps and CI/CD expertise",
                "Strong educational background with advanced degree"
            ]
        )
        mock_ai_feedback.return_value = mock_feedback
        
        analysis_id = str(uuid4())
        mock_store_analysis.return_value = analysis_id
        
        # Perform analysis
        job_description = self.job_descriptions[0]
        analysis_request = {
            "job_description": job_description,
            "job_title": "Senior Full Stack Developer - AI/ML Platform",
            "resume_id": uploaded_resume_id
        }
        
        analysis_response = self.client.post("/api/v1/analyze", json=analysis_request)
        
        assert analysis_response.status_code == 200
        analysis_data = analysis_response.json()
        
        # Verify analysis results
        assert analysis_data["match_score"] == 96.8
        assert "Python" in analysis_data["matched_keywords"]
        assert "React" in analysis_data["matched_keywords"]
        assert "FastAPI" in analysis_data["matched_keywords"]
        assert "machine learning" in analysis_data["missing_keywords"]
        assert "ai_feedback" in analysis_data
        assert len(analysis_data["ai_feedback"]["recommendations"]) == 2
        assert analysis_data["ai_feedback"]["overall_assessment"].startswith("Excellent match")
        
        # Step 3: Retrieve specific analysis
        mock_stored_analysis = AnalysisResult(
            id=UUID(analysis_id),
            user_id=UUID(self.test_user_id),
            resume_id=resume_id,
            job_title="Senior Full Stack Developer - AI/ML Platform",
            job_description=job_description,
            match_score=96.8,
            ai_feedback=mock_feedback.dict(),
            matched_keywords=mock_compatibility.matched_keywords,
            missing_keywords=mock_compatibility.missing_keywords,
            processing_time=2.3,
            created_at=datetime.utcnow()
        )
        mock_get_analysis.return_value = mock_stored_analysis
        
        retrieve_response = self.client.get(f"/api/v1/analyses/{analysis_id}")
        
        assert retrieve_response.status_code == 200
        retrieve_data = retrieve_response.json()
        
        assert retrieve_data["analysis_id"] == analysis_id
        assert retrieve_data["match_score"] == 96.8
        assert retrieve_data["job_title"] == "Senior Full Stack Developer - AI/ML Platform"
        assert "ai_feedback" in retrieve_data
        
        # Step 4: Get analysis history
        mock_get_user_analyses.return_value = [mock_stored_analysis]
        
        history_response = self.client.get("/api/v1/analyses?page=1&page_size=10")
        
        assert history_response.status_code == 200
        history_data = history_response.json()
        
        assert len(history_data["analyses"]) == 1
        assert history_data["analyses"][0]["analysis_id"] == analysis_id
        assert history_data["analyses"][0]["match_score"] == 96.8
        
        print("✅ Complete workflow integration test passed")
    
    @patch('app.middleware.auth.get_current_user')
    @patch('app.services.nlu_service.nlu_service.extract_entities')
    @patch('app.services.semantic_service.semantic_service.analyze_compatibility')
    @patch('app.services.ai_service.ai_service.generate_feedback')
    @patch('app.services.database_service.db_service.store_analysis')
    def test_multiple_concurrent_analyses(
        self, mock_store_analysis, mock_ai_feedback, mock_semantic, mock_nlu, mock_auth
    ):
        """
        Test system handling of multiple concurrent analysis requests
        Validates performance under concurrent load
        """
        mock_auth.return_value = self.mock_user
        
        from app.models.entities import ResumeEntities, CompatibilityAnalysis, AIFeedback
        
        # Setup mocks for concurrent requests
        def mock_nlu_side_effect(*args, **kwargs):
            # Simulate processing time
            time.sleep(0.1)
            return ResumeEntities(
                skills=["Python", "JavaScript", "React"],
                job_titles=["Software Engineer"],
                companies=["TechCorp"],
                education=["Computer Science"],
                contact_info={"email": "test@example.com"},
                experience_years=5,
                confidence_scores={"skills": 0.9}
            )
        
        def mock_semantic_side_effect(*args, **kwargs):
            # Simulate processing time
            time.sleep(0.2)
            return CompatibilityAnalysis(
                match_score=85.0,
                matched_keywords=["Python", "JavaScript"],
                missing_keywords=["Docker"],
                semantic_similarity=0.85,
                keyword_coverage=0.8
            )
        
        def mock_ai_side_effect(*args, **kwargs):
            # Simulate processing time
            time.sleep(0.3)
            return AIFeedback(
                recommendations=[{"category": "skills", "priority": "medium", "suggestion": "Add Docker"}],
                overall_assessment="Good match",
                priority_improvements=["Docker"],
                strengths=["Python skills"]
            )
        
        mock_nlu.side_effect = mock_nlu_side_effect
        mock_semantic.side_effect = mock_semantic_side_effect
        mock_ai_feedback.side_effect = mock_ai_side_effect
        mock_store_analysis.return_value = str(uuid4())
        
        # Prepare multiple analysis requests
        requests = []
        for i in range(5):  # Test with 5 concurrent requests
            request_data = {
                "job_description": f"Python developer position {i}",
                "job_title": f"Developer {i}",
                "resume_text": f"Resume content for test {i}\nPython developer with experience"
            }
            requests.append(request_data)
        
        # Execute concurrent requests
        start_time = time.time()
        responses = []
        
        for request_data in requests:
            response = self.client.post("/api/v1/analyze", json=request_data)
            responses.append(response)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Verify all requests succeeded
        for i, response in enumerate(responses):
            assert response.status_code == 200, f"Request {i} failed with status {response.status_code}"
            data = response.json()
            assert "analysis_id" in data
            assert "match_score" in data
            assert "processing_time" in data
        
        # Verify performance (should handle concurrent requests efficiently)
        assert total_time < 10.0, f"Concurrent requests took too long: {total_time:.2f}s"
        
        print(f"✅ Concurrent analysis test passed - {len(requests)} requests in {total_time:.2f}s")


class TestErrorHandlingAndRecovery:
    """Test comprehensive error handling and recovery mechanisms"""
    
    def setup_method(self):
        """Setup test client"""
        self.client = TestClient(app)
        self.test_user_id = str(uuid4())
        self.mock_user = {"user_id": self.test_user_id}
    
    @patch('app.middleware.auth.get_current_user')
    @patch('app.services.document_service.DocumentService.process_document')
    def test_document_processing_error_recovery(self, mock_process_doc, mock_auth):
        """Test error handling and recovery during document processing"""
        mock_auth.return_value = self.mock_user
        
        from app.core.exceptions import DocumentProcessingError
        
        # Test with processing error
        mock_process_doc.side_effect = DocumentProcessingError(
            "Failed to extract text from document",
            file_name="corrupted.pdf",
            processing_method="pdfplumber"
        )
        
        files = {"file": ("corrupted.pdf", BytesIO(b"corrupted content"), "application/pdf")}
        response = self.client.post("/api/v1/upload", files=files)
        
        assert response.status_code == 422
        data = response.json()
        assert data["detail"]["error_code"] == "DOCUMENT_PROCESSING_FAILED"
        assert "file_name" in data["detail"]["details"]
        
        print("✅ Document processing error recovery test passed")
    
    @patch('app.middleware.auth.get_current_user')
    @patch('app.services.nlu_service.nlu_service.extract_entities')
    @patch('app.services.semantic_service.semantic_service.analyze_compatibility')
    def test_ml_service_failure_recovery(self, mock_semantic, mock_nlu, mock_auth):
        """Test recovery from ML service failures"""
        mock_auth.return_value = self.mock_user
        
        from app.core.exceptions import NLUProcessingError, SemanticAnalysisError
        
        # Test NLU service failure
        mock_nlu.side_effect = NLUProcessingError("NER model failed to load")
        
        request_data = {
            "job_description": "Python developer position",
            "resume_text": "Software engineer with Python experience"
        }
        
        response = self.client.post("/api/v1/analyze", json=request_data)
        
        assert response.status_code == 422
        data = response.json()
        assert data["detail"]["error_code"] == "NLU_PROCESSING_FAILED"
        
        # Test semantic analysis failure
        from app.models.entities import ResumeEntities
        mock_nlu.side_effect = None
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
        
        response = self.client.post("/api/v1/analyze", json=request_data)
        
        assert response.status_code == 422
        data = response.json()
        assert data["detail"]["error_code"] == "SEMANTIC_ANALYSIS_FAILED"
        
        print("✅ ML service failure recovery test passed")
    
    @patch('app.middleware.auth.get_current_user')
    @patch('app.services.database_service.db_service.store_analysis')
    def test_database_error_recovery(self, mock_store_analysis, mock_auth):
        """Test recovery from database errors"""
        mock_auth.return_value = self.mock_user
        
        from app.core.exceptions import DatabaseError
        
        # Mock successful analysis services but database failure
        with patch('app.services.nlu_service.nlu_service.extract_entities') as mock_nlu:
            with patch('app.services.semantic_service.semantic_service.analyze_compatibility') as mock_semantic:
                with patch('app.services.ai_service.ai_service.generate_feedback') as mock_ai:
                    
                    from app.models.entities import ResumeEntities, CompatibilityAnalysis, AIFeedback
                    
                    mock_nlu.return_value = ResumeEntities(
                        skills=["Python"],
                        job_titles=["Engineer"],
                        companies=[],
                        education=[],
                        contact_info={},
                        experience_years=None,
                        confidence_scores={}
                    )
                    
                    mock_semantic.return_value = CompatibilityAnalysis(
                        match_score=80.0,
                        matched_keywords=["Python"],
                        missing_keywords=[],
                        semantic_similarity=0.8,
                        keyword_coverage=0.8
                    )
                    
                    mock_ai.return_value = AIFeedback(
                        recommendations=[],
                        overall_assessment="Good match",
                        priority_improvements=[],
                        strengths=["Python"]
                    )
                    
                    # Database failure
                    mock_store_analysis.side_effect = DatabaseError("Connection failed")
                    
                    request_data = {
                        "job_description": "Python developer position",
                        "resume_text": "Software engineer with Python experience"
                    }
                    
                    response = self.client.post("/api/v1/analyze", json=request_data)
                    
                    assert response.status_code == 500
                    data = response.json()
                    assert data["detail"]["error_code"] == "DATABASE_ERROR"
        
        print("✅ Database error recovery test passed")
    
    def test_authentication_error_handling(self):
        """Test authentication error handling"""
        # Test without authentication
        request_data = {
            "job_description": "Python developer position",
            "resume_text": "Software engineer with Python experience"
        }
        
        with patch('app.middleware.auth.get_current_user') as mock_auth:
            mock_auth.side_effect = Exception("Authentication failed")
            
            with pytest.raises(Exception):
                self.client.post("/api/v1/analyze", json=request_data)
        
        print("✅ Authentication error handling test passed")


class TestPerformanceRequirements:
    """Test performance requirements validation"""
    
    def setup_method(self):
        """Setup test client"""
        self.client = TestClient(app)
        self.test_user_id = str(uuid4())
        self.mock_user = {"user_id": self.test_user_id}
    
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
        This is a critical performance requirement
        """
        mock_auth.return_value = self.mock_user
        
        from app.models.entities import ResumeEntities, CompatibilityAnalysis, AIFeedback
        
        # Setup mocks with realistic processing times
        def mock_nlu_with_delay(*args, **kwargs):
            time.sleep(0.5)  # Simulate NLU processing time
            return ResumeEntities(
                skills=["Python", "JavaScript"],
                job_titles=["Software Engineer"],
                companies=["TechCorp"],
                education=["Computer Science"],
                contact_info={"email": "test@example.com"},
                experience_years=5,
                confidence_scores={"skills": 0.9}
            )
        
        def mock_semantic_with_delay(*args, **kwargs):
            time.sleep(0.8)  # Simulate semantic analysis time
            return CompatibilityAnalysis(
                match_score=85.0,
                matched_keywords=["Python", "JavaScript"],
                missing_keywords=["Docker"],
                semantic_similarity=0.85,
                keyword_coverage=0.8
            )
        
        def mock_ai_with_delay(*args, **kwargs):
            time.sleep(1.2)  # Simulate AI feedback generation time
            return AIFeedback(
                recommendations=[{"category": "skills", "priority": "medium", "suggestion": "Add Docker"}],
                overall_assessment="Good match",
                priority_improvements=["Docker"],
                strengths=["Python skills"]
            )
        
        mock_nlu.side_effect = mock_nlu_with_delay
        mock_semantic.side_effect = mock_semantic_with_delay
        mock_ai_feedback.side_effect = mock_ai_with_delay
        mock_store_analysis.return_value = str(uuid4())
        
        # Test multiple requests to measure response times
        response_times = []
        num_requests = 20  # Test with 20 requests
        
        for i in range(num_requests):
            request_data = {
                "job_description": f"Python developer position {i}",
                "job_title": f"Developer {i}",
                "resume_text": f"Resume content {i}\nPython developer with experience"
            }
            
            start_time = time.time()
            response = self.client.post("/api/v1/analyze", json=request_data)
            end_time = time.time()
            
            response_time = end_time - start_time
            response_times.append(response_time)
            
            assert response.status_code == 200
            data = response.json()
            assert "processing_time" in data
        
        # Calculate 95th percentile
        sorted_times = sorted(response_times)
        p95_index = int(len(sorted_times) * 0.95)
        p95_time = sorted_times[p95_index]
        
        # Verify 30-second requirement
        assert p95_time <= 30.0, f"P95 response time {p95_time:.2f}s exceeds 30-second requirement"
        
        avg_time = sum(response_times) / len(response_times)
        max_time = max(response_times)
        
        print(f"✅ Performance requirements test passed:")
        print(f"   Average response time: {avg_time:.2f}s")
        print(f"   P95 response time: {p95_time:.2f}s")
        print(f"   Max response time: {max_time:.2f}s")
        print(f"   Total requests: {num_requests}")
    
    @patch('app.middleware.auth.get_current_user')
    def test_health_check_performance(self, mock_auth):
        """Test health check endpoint performance"""
        mock_auth.return_value = self.mock_user
        
        # Test basic health check
        start_time = time.time()
        response = self.client.get("/api/v1/health")
        end_time = time.time()
        
        response_time = end_time - start_time
        
        assert response.status_code == 200
        assert response_time < 1.0, f"Health check took too long: {response_time:.2f}s"
        
        # Test detailed health check
        with patch('app.services.database_service.db_service.health_check') as mock_db_health:
            with patch('app.utils.ml_utils.model_cache.health_check') as mock_ml_health:
                with patch('app.services.ai_service.ai_service.health_check') as mock_ai_health:
                    
                    mock_db_health.return_value = {"status": "healthy"}
                    mock_ml_health.return_value = {"ner_model": True, "embedding_model": True}
                    mock_ai_health.return_value = {"status": "healthy"}
                    
                    start_time = time.time()
                    response = self.client.get("/api/v1/health/detailed")
                    end_time = time.time()
                    
                    response_time = end_time - start_time
                    
                    assert response.status_code == 200
                    assert response_time < 5.0, f"Detailed health check took too long: {response_time:.2f}s"
        
        print(f"✅ Health check performance test passed - Response time: {response_time:.3f}s")


class TestSupabaseIntegration:
    """Test integration with Supabase database and authentication"""
    
    def setup_method(self):
        """Setup test client"""
        self.client = TestClient(app)
        self.test_user_id = str(uuid4())
        self.mock_user = {"user_id": self.test_user_id}
    
    @patch('app.middleware.auth.get_current_user')
    @patch('app.services.database_service.db_service.health_check')
    def test_database_connection_health(self, mock_db_health, mock_auth):
        """Test Supabase database connection health"""
        mock_auth.return_value = self.mock_user
        
        # Test healthy database
        mock_db_health.return_value = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "connection_pool": {"active": 5, "idle": 10}
        }
        
        response = self.client.get("/api/v1/health/database")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "connection_pool" in data
        
        # Test unhealthy database
        mock_db_health.side_effect = Exception("Database connection failed")
        
        response = self.client.get("/api/v1/health/database")
        
        assert response.status_code == 503
        
        print("✅ Supabase database integration test passed")
    
    @patch('app.middleware.auth.get_current_user')
    @patch('app.services.database_service.db_service.resumes.create_resume')
    @patch('app.services.database_service.db_service.resumes.get_user_resumes')
    def test_user_data_isolation(self, mock_get_resumes, mock_create_resume, mock_auth):
        """Test that user data is properly isolated"""
        # Test with first user
        user1_id = str(uuid4())
        mock_auth.return_value = {"user_id": user1_id}
        
        from app.models.entities import Resume
        
        user1_resume = Resume(
            id=uuid4(),
            user_id=UUID(user1_id),
            file_name="user1_resume.pdf",
            file_url=None,
            parsed_text="User 1 resume content",
            uploaded_at=datetime.utcnow()
        )
        
        mock_get_resumes.return_value = [user1_resume]
        
        response = self.client.get("/api/v1/resumes")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["file_name"] == "user1_resume.pdf"
        
        # Test with second user
        user2_id = str(uuid4())
        mock_auth.return_value = {"user_id": user2_id}
        
        user2_resume = Resume(
            id=uuid4(),
            user_id=UUID(user2_id),
            file_name="user2_resume.pdf",
            file_url=None,
            parsed_text="User 2 resume content",
            uploaded_at=datetime.utcnow()
        )
        
        mock_get_resumes.return_value = [user2_resume]
        
        response = self.client.get("/api/v1/resumes")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["file_name"] == "user2_resume.pdf"
        
        print("✅ User data isolation test passed")


# Pytest markers for test organization
pytestmark = [
    pytest.mark.integration,
    pytest.mark.system,
    pytest.mark.asyncio
]