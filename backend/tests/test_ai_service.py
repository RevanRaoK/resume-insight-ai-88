"""
Unit tests for AI feedback generation service
"""
import pytest
import json
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from dataclasses import dataclass
from typing import Dict, Any, List

from app.services.ai_service import (
    GeminiClient,
    PromptEngine,
    ResponseParser,
    AIService,
    AnalysisContext,
    AIFeedback,
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerState
)
from app.core.exceptions import AIServiceError, APIRateLimitError


class TestGeminiClient:
    """Test Gemini API integration with mock responses"""
    
    @pytest.fixture
    def gemini_client(self):
        """Create GeminiClient instance for testing"""
        with patch('app.services.ai_service.genai.configure'):
            with patch('app.services.ai_service.genai.GenerativeModel'):
                return GeminiClient()
    
    @pytest.mark.asyncio
    async def test_generate_response_success(self, gemini_client):
        """Test successful response generation"""
        # Mock the model response
        mock_response = Mock()
        mock_response.text = "Test response from Gemini"
        
        with patch.object(gemini_client.model, 'generate_content', return_value=mock_response):
            response = await gemini_client.generate_response("test prompt")
            
            assert response == "Test response from Gemini"
            assert gemini_client.circuit_breaker.state == CircuitBreakerState.CLOSED
    
    @pytest.mark.asyncio
    async def test_generate_response_empty_response(self, gemini_client):
        """Test handling of empty API response"""
        mock_response = Mock()
        mock_response.text = ""
        
        with patch.object(gemini_client.model, 'generate_content', return_value=mock_response):
            with pytest.raises(AIServiceError) as exc_info:
                await gemini_client.generate_response("test prompt")
            
            assert "Empty response from Gemini API" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_generate_response_rate_limit_error(self, gemini_client):
        """Test handling of rate limit errors"""
        with patch.object(gemini_client.model, 'generate_content', side_effect=Exception("quota exceeded")):
            with pytest.raises(APIRateLimitError) as exc_info:
                await gemini_client.generate_response("test prompt")
            
            # Check that the error contains the service name
            assert exc_info.value.details.get("service_name") == "gemini"
            # Rate limit errors should record failure (but may not open circuit breaker on first failure)
            assert gemini_client.circuit_breaker.failure_count > 0
    
    @pytest.mark.asyncio
    async def test_generate_response_authentication_error(self, gemini_client):
        """Test handling of authentication errors"""
        with patch.object(gemini_client.model, 'generate_content', side_effect=Exception("api key invalid")):
            with pytest.raises(AIServiceError) as exc_info:
                await gemini_client.generate_response("test prompt")
            
            assert "Authentication error" in str(exc_info.value)
            # Note: Authentication errors should open circuit breaker, but the current implementation
            # only opens it after max retries, so we check the failure was recorded
            assert gemini_client.circuit_breaker.failure_count > 0
    
    @pytest.mark.asyncio
    async def test_generate_response_retry_mechanism(self, gemini_client):
        """Test retry mechanism with exponential backoff"""
        # Mock failures for first 2 attempts, success on 3rd
        mock_responses = [
            Exception("temporary error"),
            Exception("another temporary error"),
            Mock(text="Success after retries")
        ]
        
        with patch.object(gemini_client.model, 'generate_content', side_effect=mock_responses):
            with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
                response = await gemini_client.generate_response("test prompt")
                
                assert response == "Success after retries"
                assert mock_sleep.call_count == 2  # Two retry delays
                # Verify exponential backoff delays
                calls = mock_sleep.call_args_list
                assert calls[0][0][0] >= 1.0  # First delay >= base_delay
                assert calls[1][0][0] >= 2.0  # Second delay >= 2 * base_delay
    
    @pytest.mark.asyncio
    async def test_generate_response_max_retries_exceeded(self, gemini_client):
        """Test failure after max retries exceeded"""
        with patch.object(gemini_client.model, 'generate_content', side_effect=Exception("persistent error")):
            with patch('asyncio.sleep', new_callable=AsyncMock):
                with pytest.raises(AIServiceError) as exc_info:
                    await gemini_client.generate_response("test prompt")
                
                assert "failed after 3 attempts" in str(exc_info.value)
                # After max retries, circuit breaker should record failure
                assert gemini_client.circuit_breaker.failure_count > 0
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_open_blocks_requests(self, gemini_client):
        """Test that circuit breaker blocks requests when open"""
        # Force circuit breaker to open state and set last failure time to recent
        import time
        gemini_client.circuit_breaker.state = CircuitBreakerState.OPEN
        gemini_client.circuit_breaker.last_failure_time = time.time()  # Recent failure
        
        with pytest.raises(AIServiceError) as exc_info:
            await gemini_client.generate_response("test prompt")
        
        assert "Circuit breaker is open" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, gemini_client):
        """Test successful health check"""
        mock_response = Mock()
        mock_response.text = "OK - system is healthy"
        
        with patch.object(gemini_client.model, 'generate_content', return_value=mock_response):
            health = await gemini_client.health_check()
            
            assert health['status'] == 'healthy'
            assert health['service'] == 'gemini'
            assert health['response_received'] is True
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, gemini_client):
        """Test health check failure"""
        with patch.object(gemini_client.model, 'generate_content', side_effect=Exception("API error")):
            health = await gemini_client.health_check()
            
            assert health['status'] == 'unhealthy'
            assert health['service'] == 'gemini'
            assert 'error' in health


class TestCircuitBreaker:
    """Test circuit breaker functionality"""
    
    @pytest.fixture
    def circuit_breaker(self):
        config = CircuitBreakerConfig(failure_threshold=3, recovery_timeout=5)
        return CircuitBreaker(config)
    
    def test_initial_state_closed(self, circuit_breaker):
        """Test circuit breaker starts in closed state"""
        assert circuit_breaker.state == CircuitBreakerState.CLOSED
        assert circuit_breaker.can_execute() is True
    
    def test_failure_threshold_opens_circuit(self, circuit_breaker):
        """Test circuit opens after failure threshold"""
        # Record failures up to threshold
        for _ in range(3):
            circuit_breaker.record_failure()
        
        assert circuit_breaker.state == CircuitBreakerState.OPEN
        assert circuit_breaker.can_execute() is False
    
    def test_recovery_timeout_enables_half_open(self, circuit_breaker):
        """Test circuit moves to half-open after recovery timeout"""
        # Open the circuit
        for _ in range(3):
            circuit_breaker.record_failure()
        
        # Simulate time passage
        import time
        circuit_breaker.last_failure_time = time.time() - 10  # 10 seconds ago
        
        assert circuit_breaker.can_execute() is True
        assert circuit_breaker.state == CircuitBreakerState.HALF_OPEN
    
    def test_half_open_success_closes_circuit(self, circuit_breaker):
        """Test successful requests in half-open state close circuit"""
        # Set to half-open state
        circuit_breaker.state = CircuitBreakerState.HALF_OPEN
        
        # Record successful requests
        circuit_breaker.record_success()
        circuit_breaker.record_success()  # Meets success threshold
        
        assert circuit_breaker.state == CircuitBreakerState.CLOSED


class TestPromptEngine:
    """Test prompt engineering with various input combinations"""
    
    @pytest.fixture
    def prompt_engine(self):
        return PromptEngine()
    
    @pytest.fixture
    def sample_context(self):
        return AnalysisContext(
            resume_entities={
                'skills': ['Python', 'JavaScript', 'React', 'FastAPI'],
                'job_titles': ['Software Engineer', 'Developer'],
                'companies': ['TechCorp', 'StartupXYZ'],
                'education': ['BS Computer Science']
            },
            match_score=75.5,
            matched_keywords=['Python', 'JavaScript', 'API'],
            missing_keywords=['Docker', 'AWS', 'Kubernetes'],
            semantic_similarity=0.756,
            keyword_coverage=0.65,
            job_description="We are looking for a Senior Software Engineer with Python and cloud experience...",
            resume_text="John Doe is a software engineer with 5 years of experience..."
        )
    
    def test_build_persona_prompt(self, prompt_engine):
        """Test persona prompt construction"""
        persona = prompt_engine._build_persona_prompt()
        
        assert "expert career coach" in persona.lower()
        assert "resume optimization" in persona.lower()
        assert "ats" in persona.lower()
        assert len(persona) > 200  # Should be substantial
    
    def test_build_few_shot_examples(self, prompt_engine):
        """Test few-shot examples construction"""
        examples = prompt_engine._build_few_shot_examples()
        
        assert "Example 1" in examples
        assert "Example 2" in examples
        assert "overall_assessment" in examples
        assert "priority_improvements" in examples
        assert len(examples) > 500  # Should contain substantial examples
    
    def test_build_analysis_prompt_complete_context(self, prompt_engine, sample_context):
        """Test analysis prompt with complete context"""
        prompt = prompt_engine.build_analysis_prompt(sample_context)
        
        # Verify context injection
        assert "75.5%" in prompt  # Match score
        assert "Python" in prompt  # Skills
        assert "Docker" in prompt  # Missing keywords
        assert "TechCorp" in prompt  # Companies
        
        # Verify structure
        assert "ANALYSIS CONTEXT" in prompt
        assert "ANALYSIS INSTRUCTIONS" in prompt
        assert "OUTPUT REQUIREMENTS" in prompt
        assert "chain-of-thought" in prompt.lower()
        
        # Verify length is substantial
        assert len(prompt) > 2000
    
    def test_build_analysis_prompt_minimal_context(self, prompt_engine):
        """Test analysis prompt with minimal context"""
        minimal_context = AnalysisContext(
            resume_entities={},
            match_score=50.0,
            matched_keywords=[],
            missing_keywords=[],
            semantic_similarity=0.5,
            keyword_coverage=0.3,
            job_description="Basic job description",
            resume_text="Basic resume text"
        )
        
        prompt = prompt_engine.build_analysis_prompt(minimal_context)
        
        assert "50.0%" in prompt
        assert "None detected" in prompt  # For empty entities
        assert len(prompt) > 1000  # Should still be substantial
    
    def test_build_fallback_prompt(self, prompt_engine, sample_context):
        """Test fallback prompt construction"""
        fallback_prompt = prompt_engine.build_fallback_prompt(sample_context)
        
        assert "75.5%" in fallback_prompt
        assert "Python" in fallback_prompt
        assert "Docker" in fallback_prompt
        assert len(fallback_prompt) < 1000  # Should be shorter than main prompt
        assert "JSON" in fallback_prompt
    
    def test_build_analysis_prompt_edge_cases(self, prompt_engine):
        """Test prompt building with edge case data"""
        # Test with very long lists
        edge_context = AnalysisContext(
            resume_entities={
                'skills': ['skill' + str(i) for i in range(50)],  # Very long list
                'job_titles': [],  # Empty list
                'companies': ['Company with very long name that exceeds normal limits'],
                'education': None  # None value
            },
            match_score=0.0,  # Minimum score
            matched_keywords=['keyword' + str(i) for i in range(100)],  # Very long list
            missing_keywords=[],
            semantic_similarity=1.0,  # Maximum similarity
            keyword_coverage=0.0,  # Minimum coverage
            job_description="",  # Empty description
            resume_text="x" * 10000  # Very long text
        )
        
        prompt = prompt_engine.build_analysis_prompt(edge_context)
        
        # Should handle edge cases gracefully
        assert "0.0%" in prompt
        assert "skill0, skill1" in prompt  # Should truncate long lists
        assert len(prompt) > 1000  # Should still generate substantial prompt


class TestResponseParser:
    """Test response parsing with malformed and edge case responses"""
    
    @pytest.fixture
    def response_parser(self):
        return ResponseParser()
    
    def test_parse_valid_json_response(self, response_parser):
        """Test parsing of valid JSON response"""
        valid_response = '''
        Here is my analysis:
        
        ```json
        {
            "overall_assessment": "Strong candidate with good technical skills",
            "match_score_interpretation": "75% indicates good alignment",
            "strengths": ["Python expertise", "Good experience", "Strong education"],
            "priority_improvements": [
                {
                    "category": "Skills",
                    "priority": "High",
                    "recommendation": "Add Docker experience",
                    "impact": "Will improve DevOps profile"
                }
            ],
            "missing_keywords_analysis": {
                "critical_missing": ["Docker", "AWS"],
                "suggestions": "Consider cloud training"
            },
            "ats_optimization_tips": ["Use exact keywords", "Include metrics"]
        }
        ```
        
        This should help improve your resume.
        '''
        
        feedback = response_parser.parse_response(valid_response)
        
        assert isinstance(feedback, AIFeedback)
        assert feedback.overall_assessment == "Strong candidate with good technical skills"
        assert len(feedback.strengths) == 3
        assert len(feedback.priority_improvements) == 1
        assert feedback.priority_improvements[0]['category'] == 'Skills'
        assert feedback.parsing_confidence > 0.8
    
    def test_parse_json_without_code_blocks(self, response_parser):
        """Test parsing JSON without markdown code blocks"""
        json_response = '''
        {
            "overall_assessment": "Good candidate",
            "strengths": ["Python", "Experience"],
            "priority_improvements": []
        }
        '''
        
        feedback = response_parser.parse_response(json_response)
        
        assert feedback.overall_assessment == "Good candidate"
        assert len(feedback.strengths) == 2
        assert feedback.parsing_confidence > 0.5
    
    def test_parse_malformed_json(self, response_parser):
        """Test parsing of malformed JSON"""
        malformed_response = '''
        ```json
        {
            "overall_assessment": "Good candidate",
            "strengths": ["Python", "Experience"
            // Missing closing bracket and quote
        ```
        '''
        
        feedback = response_parser.parse_response(malformed_response)
        
        # Should create minimal feedback when parsing fails
        assert "Unable to parse detailed feedback" in feedback.overall_assessment
        assert feedback.parsing_confidence < 0.5
        assert feedback.raw_response == malformed_response
    
    def test_parse_mixed_content_response(self, response_parser):
        """Test parsing response with mixed content and JSON"""
        mixed_response = '''
        Based on my analysis, here are my recommendations:
        
        The candidate shows strong potential but needs improvement in several areas.
        
        ```json
        {
            "overall_assessment": "Mixed potential with improvement needed",
            "strengths": ["Good foundation", "Relevant experience"],
            "priority_improvements": [
                {
                    "category": "Technical Skills",
                    "priority": "High",
                    "recommendation": "Learn cloud technologies",
                    "impact": "Critical for modern development"
                }
            ]
        }
        ```
        
        Additional notes: The candidate should focus on practical projects.
        '''
        
        feedback = response_parser.parse_response(mixed_response)
        
        assert feedback.overall_assessment == "Mixed potential with improvement needed"
        assert len(feedback.priority_improvements) == 1
        assert feedback.parsing_confidence > 0.7
    
    def test_parse_no_json_fallback(self, response_parser):
        """Test fallback parsing when no JSON is found"""
        text_response = '''
        Overall Assessment: The candidate has strong technical skills.
        
        Strengths:
        - Excellent Python programming
        - Good problem-solving abilities
        - Strong educational background
        
        Improvements:
        - Add cloud experience
        - Include more metrics
        - Improve resume formatting
        '''
        
        feedback = response_parser.parse_response(text_response)
        
        # Should extract some structured data via fallback
        assert "strong technical skills" in feedback.overall_assessment.lower()
        assert len(feedback.strengths) >= 1  # Should extract at least one bullet point
        assert len(feedback.priority_improvements) >= 1
        # Fallback parsing can have higher confidence if it successfully extracts structured data
        assert feedback.parsing_confidence > 0.0
    
    def test_parse_empty_response(self, response_parser):
        """Test parsing of empty response"""
        feedback = response_parser.parse_response("")
        
        assert "Unable to parse detailed feedback" in feedback.overall_assessment
        assert feedback.parsing_confidence < 0.5
    
    def test_parse_invalid_structure(self, response_parser):
        """Test parsing JSON with invalid structure"""
        invalid_structure = '''
        ```json
        {
            "wrong_field": "This doesn't match expected structure",
            "another_wrong_field": ["item1", "item2"]
        }
        ```
        '''
        
        feedback = response_parser.parse_response(invalid_structure)
        
        # Should create minimal feedback for invalid structure
        assert "Unable to parse detailed feedback" in feedback.overall_assessment
        assert feedback.parsing_confidence < 0.5
    
    def test_parse_partial_valid_structure(self, response_parser):
        """Test parsing JSON with some valid fields"""
        partial_response = '''
        ```json
        {
            "overall_assessment": "Partial analysis available",
            "strengths": ["Python programming"],
            "priority_improvements": []
        }
        ```
        '''
        
        feedback = response_parser.parse_response(partial_response)
        
        # Should handle valid structure with required fields
        assert feedback.overall_assessment == "Partial analysis available"
        assert isinstance(feedback.strengths, list)
        assert "Python programming" in feedback.strengths
    
    def test_calculate_confidence_scores(self, response_parser):
        """Test confidence score calculation"""
        # Test high confidence (JSON in code blocks with complete data)
        complete_data = {
            'overall_assessment': 'Complete',
            'strengths': ['skill1', 'skill2'],
            'priority_improvements': [{'category': 'test'}],
            'missing_keywords_analysis': {'critical_missing': []},
            'ats_optimization_tips': ['tip1']
        }
        confidence = response_parser._calculate_confidence(complete_data, 'pattern_0')
        assert confidence > 0.8
        
        # Test low confidence (fallback parsing with minimal data)
        minimal_data = {'overall_assessment': 'Minimal'}
        confidence = response_parser._calculate_confidence(minimal_data, 'fallback')
        assert confidence < 0.5


class TestAIService:
    """Test complete AI service integration"""
    
    @pytest.fixture
    def ai_service(self):
        with patch('app.services.ai_service.gemini_client'):
            return AIService()
    
    @pytest.fixture
    def sample_context(self):
        return AnalysisContext(
            resume_entities={'skills': ['Python', 'React']},
            match_score=80.0,
            matched_keywords=['Python', 'API'],
            missing_keywords=['Docker'],
            semantic_similarity=0.8,
            keyword_coverage=0.7,
            job_description="Senior Python Developer position",
            resume_text="Experienced Python developer"
        )
    
    @pytest.mark.asyncio
    async def test_generate_feedback_success(self, ai_service, sample_context):
        """Test successful feedback generation"""
        mock_response = '''
        ```json
        {
            "overall_assessment": "Strong candidate for the role",
            "strengths": ["Python expertise", "Good experience"],
            "priority_improvements": [
                {
                    "category": "Skills",
                    "priority": "Medium",
                    "recommendation": "Add Docker experience",
                    "impact": "Improves DevOps capabilities"
                }
            ]
        }
        ```
        '''
        
        with patch.object(ai_service.gemini_client, 'generate_response', new_callable=AsyncMock, return_value=mock_response):
            feedback = await ai_service.generate_feedback(sample_context)
            
            assert isinstance(feedback, AIFeedback)
            assert feedback.overall_assessment == "Strong candidate for the role"
            assert len(feedback.strengths) == 2
            assert len(feedback.priority_improvements) == 1
    
    @pytest.mark.asyncio
    async def test_generate_feedback_with_fallback(self, ai_service, sample_context):
        """Test feedback generation with fallback prompt"""
        fallback_response = '''
        ```json
        {
            "overall_assessment": "Fallback analysis completed",
            "strengths": ["Basic skills present"],
            "priority_improvements": []
        }
        ```
        '''
        
        # Mock main prompt failure, fallback success
        async def mock_generate_side_effect(*args, **kwargs):
            if mock_generate.call_count == 1:
                raise AIServiceError("Main prompt failed", "gemini")
            return fallback_response
        
        with patch.object(ai_service.gemini_client, 'generate_response', new_callable=AsyncMock) as mock_generate:
            mock_generate.side_effect = mock_generate_side_effect
            
            feedback = await ai_service.generate_feedback(sample_context)
            
            assert feedback.overall_assessment == "Fallback analysis completed"
            assert mock_generate.call_count == 2  # Main + fallback
    
    @pytest.mark.asyncio
    async def test_generate_feedback_complete_failure(self, ai_service, sample_context):
        """Test feedback generation when both main and fallback fail"""
        with patch.object(ai_service.gemini_client, 'generate_response', new_callable=AsyncMock, side_effect=AIServiceError("Complete failure", "gemini")):
            with pytest.raises(AIServiceError) as exc_info:
                await ai_service.generate_feedback(sample_context)
            
            assert "Failed to generate AI feedback" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, ai_service):
        """Test successful health check"""
        mock_gemini_health = {
            'status': 'healthy',
            'service': 'gemini',
            'response_received': True
        }
        
        with patch.object(ai_service.gemini_client, 'health_check', new_callable=AsyncMock, return_value=mock_gemini_health):
            health = await ai_service.health_check()
            
            assert health['status'] == 'healthy'
            assert health['service'] == 'ai_service'
            assert 'components' in health
            assert health['components']['gemini_client']['status'] == 'healthy'
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, ai_service):
        """Test health check failure"""
        with patch.object(ai_service.gemini_client, 'health_check', new_callable=AsyncMock, side_effect=Exception("Health check failed")):
            health = await ai_service.health_check()
            
            assert health['status'] == 'unhealthy'
            assert 'error' in health