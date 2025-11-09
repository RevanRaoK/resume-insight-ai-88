"""
AI feedback generation service using Google Gemini API
"""
import asyncio
import json
import re
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from app.config import settings
from app.core.exceptions import AIServiceError, APIRateLimitError
from app.utils.logger import get_logger

logger = get_logger(__name__)


class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration"""
    failure_threshold: int = 5
    recovery_timeout: int = 60  # seconds
    success_threshold: int = 2  # for half-open state


class CircuitBreaker:
    """Circuit breaker pattern implementation for API reliability"""
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0
    
    def can_execute(self) -> bool:
        """Check if request can be executed based on circuit breaker state"""
        if self.state == CircuitBreakerState.CLOSED:
            return True
        elif self.state == CircuitBreakerState.OPEN:
            if time.time() - self.last_failure_time >= self.config.recovery_timeout:
                self.state = CircuitBreakerState.HALF_OPEN
                self.success_count = 0
                logger.info("circuit_breaker_half_open", state="half_open")
                return True
            return False
        elif self.state == CircuitBreakerState.HALF_OPEN:
            return True
        return False
    
    def record_success(self):
        """Record successful API call"""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
                logger.info("circuit_breaker_closed", state="closed")
        elif self.state == CircuitBreakerState.CLOSED:
            self.failure_count = 0
    
    def record_failure(self):
        """Record failed API call"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitBreakerState.CLOSED:
            if self.failure_count >= self.config.failure_threshold:
                self.state = CircuitBreakerState.OPEN
                logger.warning(
                    "circuit_breaker_opened",
                    state="open",
                    failure_count=self.failure_count
                )
        elif self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN
            logger.warning("circuit_breaker_reopened", state="open")


class GeminiClient:
    """Google Gemini API client with retry mechanism and circuit breaker"""
    
    def __init__(self):
        self.api_key = settings.GOOGLE_GEMINI_API_KEY
        self.model_name = settings.GOOGLE_GEMINI_MODEL
        self.max_retries = 3
        self.base_delay = 1.0  # Base delay for exponential backoff
        self.max_delay = 60.0  # Maximum delay between retries
        
        # Initialize circuit breaker
        self.circuit_breaker = CircuitBreaker(CircuitBreakerConfig())
        
        # Check if API key is properly configured
        if not self.api_key or self.api_key == "your-google-gemini-api-key":
            logger.warning("Google Gemini API key not configured - AI feedback will be simulated")
            self.model = None
            return
        
        # Configure Gemini API
        try:
            genai.configure(api_key=self.api_key)
        except Exception as e:
            logger.error("Failed to configure Gemini API", error=str(e))
            self.model = None
            return
        
        # Initialize model with safety settings
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            safety_settings={
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            }
        )
        
        logger.info("gemini_client_initialized", model_name=self.model_name)
    
    async def generate_response(self, prompt: str) -> str:
        """
        Generate response from Gemini API with retry mechanism and circuit breaker
        
        Args:
            prompt: The prompt to send to Gemini API
            
        Returns:
            Generated response text
            
        Raises:
            AIServiceError: If API call fails after all retries
            APIRateLimitError: If rate limit is exceeded
        """
        # Fallback if API key is not configured
        if self.model is None:
            logger.info("Using simulated AI feedback - API key not configured")
            return self._generate_simulated_feedback(prompt)
        
        if not self.circuit_breaker.can_execute():
            raise AIServiceError(
                message="Circuit breaker is open, API temporarily unavailable",
                service_name="gemini",
                details={"circuit_breaker_state": self.circuit_breaker.state.value}
            )
        
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                logger.info(
                    "gemini_api_request_attempt",
                    attempt=attempt + 1,
                    max_retries=self.max_retries,
                    prompt_length=len(prompt)
                )
                
                # Generate response
                response = await asyncio.to_thread(
                    self.model.generate_content,
                    prompt
                )
                
                # Validate response
                if not response or not response.text:
                    raise AIServiceError(
                        message="Empty response from Gemini API",
                        service_name="gemini",
                        details={"attempt": attempt + 1}
                    )
                
                # Record success and return
                self.circuit_breaker.record_success()
                
                logger.info(
                    "gemini_api_request_success",
                    attempt=attempt + 1,
                    response_length=len(response.text)
                )
                
                return response.text
                
            except Exception as e:
                last_exception = e
                error_message = str(e)
                
                # Check for rate limiting
                if "quota" in error_message.lower() or "rate limit" in error_message.lower():
                    self.circuit_breaker.record_failure()
                    raise APIRateLimitError(
                        service_name="gemini",
                        details={
                            "attempt": attempt + 1,
                            "original_error": error_message
                        }
                    )
                
                # Check for authentication errors (don't retry)
                if "api key" in error_message.lower() or "authentication" in error_message.lower():
                    self.circuit_breaker.record_failure()
                    raise AIServiceError(
                        message=f"Authentication error with Gemini API: {error_message}",
                        service_name="gemini",
                        details={
                            "attempt": attempt + 1,
                            "error_type": "authentication"
                        }
                    )
                
                # Log the error
                logger.warning(
                    "gemini_api_request_failed",
                    attempt=attempt + 1,
                    error=error_message,
                    will_retry=attempt < self.max_retries - 1
                )
                
                # If this is the last attempt, record failure and raise
                if attempt == self.max_retries - 1:
                    self.circuit_breaker.record_failure()
                    break
                
                # Calculate delay for exponential backoff with jitter
                delay = min(
                    self.base_delay * (2 ** attempt) + (time.time() % 1),  # Add jitter
                    self.max_delay
                )
                
                logger.info(
                    "gemini_api_retry_delay",
                    attempt=attempt + 1,
                    delay_seconds=delay
                )
                
                await asyncio.sleep(delay)
        
        # All retries failed
        self.circuit_breaker.record_failure()
        raise AIServiceError(
            message=f"Gemini API request failed after {self.max_retries} attempts: {str(last_exception)}",
            service_name="gemini",
            details={
                "max_retries": self.max_retries,
                "last_error": str(last_exception)
            }
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on Gemini API
        
        Returns:
            Health check results
        """
        try:
            test_prompt = "Respond with 'OK' if you can process this request."
            response = await self.generate_response(test_prompt)
            
            is_healthy = "ok" in response.lower()
            
            return {
                "status": "healthy" if is_healthy else "degraded",
                "service": "gemini",
                "response_received": bool(response),
                "circuit_breaker_state": self.circuit_breaker.state.value,
                "failure_count": self.circuit_breaker.failure_count
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "service": "gemini",
                "error": str(e),
                "circuit_breaker_state": self.circuit_breaker.state.value,
                "failure_count": self.circuit_breaker.failure_count
            }
    
    def _generate_simulated_feedback(self, prompt: str) -> str:
        """Generate simulated AI feedback when API key is not configured"""
        return """{
            "overall_assessment": "This is a simulated analysis since the Google Gemini API key is not configured. The resume shows good potential with relevant skills and experience. Consider adding more specific keywords and quantifiable achievements to improve ATS compatibility.",
            "strengths": [
                "Relevant technical skills identified",
                "Professional experience demonstrated",
                "Clear career progression shown"
            ],
            "recommendations": [
                {
                    "category": "Skills Enhancement",
                    "priority": "high",
                    "suggestion": "Add more specific technical keywords that match the job description",
                    "impact": "Improves ATS keyword matching and recruiter visibility"
                },
                {
                    "category": "Experience Quantification",
                    "priority": "high", 
                    "suggestion": "Include specific metrics and achievements in your experience descriptions",
                    "impact": "Demonstrates concrete value and results to employers"
                },
                {
                    "category": "Format Optimization",
                    "priority": "medium",
                    "suggestion": "Ensure consistent formatting and use standard section headers",
                    "impact": "Improves ATS parsing and professional appearance"
                }
            ],
            "match_score_interpretation": "This is a simulated score. Configure the Google Gemini API key for accurate AI-powered analysis.",
            "missing_keywords_analysis": {
                "critical_missing": ["Configure API key for detailed analysis"],
                "suggestions": "Set up Google Gemini API key in environment variables for comprehensive keyword analysis"
            },
            "ats_optimization_tips": [
                "Use standard section headers (Experience, Education, Skills)",
                "Include relevant keywords from the job description naturally in your content",
                "Save resume in both PDF and Word formats for different ATS systems",
                "Configure Google Gemini API key for personalized ATS optimization recommendations"
            ]
        }"""


# Global Gemini client instance
gemini_client = GeminiClient()


@dataclass
class AnalysisContext:
    """Context data for AI feedback generation"""
    resume_entities: Dict[str, Any]
    match_score: float
    matched_keywords: List[str]
    missing_keywords: List[str]
    semantic_similarity: float
    keyword_coverage: float
    job_description: str
    resume_text: str


class PromptEngine:
    """Advanced prompt engineering system with chain-of-thought approach"""
    
    def __init__(self):
        self.persona_prompt = self._build_persona_prompt()
        self.few_shot_examples = self._build_few_shot_examples()
    
    def _build_persona_prompt(self) -> str:
        """Build persona priming for career coach expertise simulation"""
        return """You are an expert career coach and resume optimization specialist with over 15 years of experience helping job seekers improve their resumes and land their dream jobs. You have deep expertise in:

- Applicant Tracking System (ATS) optimization
- Industry-specific resume best practices
- Keyword optimization and semantic matching
- Professional branding and positioning
- Career progression strategies
- Technical and soft skills assessment

Your approach is:
- Data-driven and analytical
- Constructive and encouraging
- Specific and actionable
- Focused on measurable improvements
- Tailored to individual career goals

You provide feedback that is honest but supportive, helping candidates understand both their strengths and areas for improvement."""
    
    def _build_few_shot_examples(self) -> str:
        """Create few-shot learning examples for consistent JSON output formatting"""
        return """Here are examples of the expected JSON response format:

Example 1 - High Match Score:
{
  "overall_assessment": "Strong alignment with the role requirements. Your technical skills and experience match well with what the employer is seeking.",
  "match_score_interpretation": "Your 87% match score indicates excellent compatibility with this position. You meet most of the key requirements.",
  "strengths": [
    "Strong technical skill set with Python, React, and cloud technologies",
    "Relevant experience in similar roles and industries",
    "Good educational background aligned with requirements"
  ],
  "priority_improvements": [
    {
      "category": "Skills Enhancement",
      "priority": "High",
      "recommendation": "Add experience with Kubernetes and Docker to strengthen your DevOps profile",
      "impact": "This would address a key requirement mentioned in the job description"
    },
    {
      "category": "Resume Formatting",
      "priority": "Medium", 
      "recommendation": "Include specific metrics and achievements in your project descriptions",
      "impact": "Quantified results make your contributions more compelling to hiring managers"
    }
  ],
  "missing_keywords_analysis": {
    "critical_missing": ["Kubernetes", "Docker", "CI/CD"],
    "suggestions": "Consider adding these technologies to your skills section if you have any experience, or mention related containerization work"
  },
  "ats_optimization_tips": [
    "Use exact keyword matches from the job description",
    "Include both acronyms and full terms (e.g., 'AI' and 'Artificial Intelligence')",
    "Ensure your most relevant skills appear in the first third of your resume"
  ]
}

Example 2 - Medium Match Score:
{
  "overall_assessment": "Moderate alignment with some strong points but several areas need attention to improve your candidacy.",
  "match_score_interpretation": "Your 64% match score suggests you have foundational qualifications but need to strengthen key areas to be competitive.",
  "strengths": [
    "Solid educational foundation in computer science",
    "Good problem-solving and analytical skills demonstrated through projects"
  ],
  "priority_improvements": [
    {
      "category": "Experience Gap",
      "priority": "Critical",
      "recommendation": "Highlight any relevant internships, projects, or freelance work that demonstrates the required skills",
      "impact": "Addressing the experience gap is crucial for this mid-level position"
    },
    {
      "category": "Skills Development",
      "priority": "High",
      "recommendation": "Gain hands-on experience with the specific technologies mentioned in the job posting",
      "impact": "Direct experience with required tools will significantly improve your match score"
    }
  ],
  "missing_keywords_analysis": {
    "critical_missing": ["AWS", "Microservices", "Agile", "Scrum"],
    "suggestions": "Consider taking online courses or working on projects that involve these technologies and methodologies"
  },
  "ats_optimization_tips": [
    "Restructure your resume to lead with your most relevant experiences",
    "Use industry-standard terminology and avoid overly creative job titles",
    "Include a skills section that mirrors the job requirements"
  ]
}"""
    
    def build_analysis_prompt(self, context: AnalysisContext) -> str:
        """
        Build comprehensive analysis prompt with chain-of-thought approach
        
        Args:
            context: Analysis context with resume entities, scores, and keywords
            
        Returns:
            Complete prompt for AI feedback generation
        """
        # Extract key information from context
        skills = context.resume_entities.get('skills', [])
        job_titles = context.resume_entities.get('job_titles', [])
        companies = context.resume_entities.get('companies', [])
        education = context.resume_entities.get('education', [])
        
        # Build context injection
        context_section = f"""
ANALYSIS CONTEXT:
=================

Resume Analysis Results:
- Overall Match Score: {context.match_score:.1f}%
- Semantic Similarity: {context.semantic_similarity:.3f}
- Keyword Coverage: {context.keyword_coverage:.1f}%

Extracted Resume Information:
- Skills: {', '.join(skills[:10]) if skills else 'None detected'}
- Job Titles: {', '.join(job_titles[:5]) if job_titles else 'None detected'}
- Companies: {', '.join(companies[:5]) if companies else 'None detected'}
- Education: {', '.join(education[:3]) if education else 'None detected'}

Keyword Analysis:
- Matched Keywords ({len(context.matched_keywords)}): {', '.join(context.matched_keywords[:15])}
- Missing Keywords ({len(context.missing_keywords)}): {', '.join(context.missing_keywords[:15])}

Job Description (First 500 chars):
{context.job_description[:500]}...
"""
        
        # Build chain-of-thought reasoning prompt
        reasoning_prompt = """
ANALYSIS INSTRUCTIONS:
=====================

Please analyze this resume against the job description using the following chain-of-thought approach:

1. COMPATIBILITY ASSESSMENT:
   - Evaluate the match score and what it indicates about overall fit
   - Consider both semantic similarity and keyword coverage
   - Identify the strongest alignment areas

2. STRENGTHS IDENTIFICATION:
   - What skills and experiences align well with the job requirements?
   - What makes this candidate competitive?
   - What unique value do they bring?

3. GAP ANALYSIS:
   - What critical requirements are missing or underrepresented?
   - Which missing keywords represent the biggest opportunities?
   - What experience gaps need to be addressed?

4. PRIORITIZED RECOMMENDATIONS:
   - What are the highest-impact improvements they could make?
   - Which changes would most improve their ATS compatibility?
   - What specific actions should they take?

5. ATS OPTIMIZATION:
   - How can they better align with automated screening systems?
   - What formatting or keyword improvements are needed?
   - How can they improve their keyword density and relevance?
"""
        
        # Build output format specification
        output_format = """
OUTPUT REQUIREMENTS:
===================

Provide your analysis as a valid JSON object with the following structure:
- overall_assessment: A comprehensive 2-3 sentence summary
- match_score_interpretation: What the match score means for their candidacy
- strengths: Array of 3-5 key strengths with specific examples
- priority_improvements: Array of 3-5 improvement recommendations, each with:
  - category: The type of improvement (Skills, Experience, Formatting, etc.)
  - priority: Critical/High/Medium/Low
  - recommendation: Specific, actionable advice
  - impact: Why this improvement matters
- missing_keywords_analysis: Object with:
  - critical_missing: Array of most important missing keywords
  - suggestions: How to address the missing keywords
- ats_optimization_tips: Array of 3-5 specific ATS improvement suggestions

Ensure your response is valid JSON that can be parsed programmatically.
"""
        
        # Combine all sections
        complete_prompt = f"""{self.persona_prompt}

{context_section}

{reasoning_prompt}

{output_format}

{self.few_shot_examples}

Now, please analyze the provided resume against the job description and provide your feedback in the specified JSON format:"""
        
        return complete_prompt
    
    def build_fallback_prompt(self, context: AnalysisContext) -> str:
        """
        Build simplified fallback prompt for when the main prompt fails
        
        Args:
            context: Analysis context
            
        Returns:
            Simplified prompt for fallback scenarios
        """
        return f"""As a career coach, analyze this resume for a job with {context.match_score:.1f}% compatibility.

Key Info:
- Skills found: {', '.join(context.resume_entities.get('skills', [])[:5])}
- Missing keywords: {', '.join(context.missing_keywords[:5])}

Provide JSON with:
- overall_assessment: Brief summary
- strengths: Top 3 strengths
- priority_improvements: Top 3 improvements with category, priority, recommendation, impact
- ats_optimization_tips: 3 ATS tips

Keep response under 1000 characters and ensure valid JSON format."""


@dataclass
class AIFeedback:
    """Structured AI feedback response"""
    overall_assessment: str
    match_score_interpretation: str
    strengths: List[str]
    priority_improvements: List[Dict[str, str]]
    missing_keywords_analysis: Dict[str, Any]
    ats_optimization_tips: List[str]
    raw_response: Optional[str] = None
    parsing_confidence: float = 1.0


class ResponseParser:
    """Parser for extracting and validating JSON from AI responses"""
    
    def __init__(self):
        # JSON extraction patterns
        self.json_patterns = [
            r'```json\s*(\{.*?\})\s*```',  # JSON in code blocks
            r'```\s*(\{.*?\})\s*```',      # JSON in generic code blocks
            r'(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})',  # Balanced braces
            r'(\{.*\})',                    # Simple JSON object
        ]
        
        # Required fields for validation
        self.required_fields = {
            'overall_assessment': str,
            'strengths': list,
            'priority_improvements': list,
        }
        
        # Optional fields with defaults
        self.optional_fields = {
            'match_score_interpretation': '',
            'missing_keywords_analysis': {},
            'ats_optimization_tips': [],
        }
    
    def parse_response(self, response_text: str) -> AIFeedback:
        """
        Parse AI response and extract structured feedback
        
        Args:
            response_text: Raw response from AI service
            
        Returns:
            Structured AIFeedback object
            
        Raises:
            AIServiceError: If parsing fails completely
        """
        logger.info(
            "parsing_ai_response",
            response_length=len(response_text),
            response_preview=response_text[:200]
        )
        
        # Try to extract JSON using different patterns
        extracted_json = None
        parsing_method = None
        
        for i, pattern in enumerate(self.json_patterns):
            matches = re.findall(pattern, response_text, re.DOTALL | re.IGNORECASE)
            if matches:
                # Try each match until we find valid JSON
                for match in matches:
                    try:
                        extracted_json = json.loads(match)
                        parsing_method = f"pattern_{i}"
                        logger.info(
                            "json_extraction_success",
                            method=parsing_method,
                            pattern_index=i
                        )
                        break
                    except json.JSONDecodeError:
                        continue
                
                if extracted_json:
                    break
        
        # If no JSON found, try fallback parsing
        if not extracted_json:
            extracted_json = self._fallback_parsing(response_text)
            parsing_method = "fallback"
        
        # If still no JSON, create minimal response
        if not extracted_json:
            logger.warning(
                "json_parsing_failed",
                response_text=response_text[:500]
            )
            return self._create_minimal_feedback(response_text)
        
        # Validate and structure the response
        try:
            validated_feedback = self._validate_and_structure(extracted_json, response_text)
            validated_feedback.parsing_confidence = self._calculate_confidence(
                extracted_json, parsing_method
            )
            
            logger.info(
                "response_parsing_success",
                method=parsing_method,
                confidence=validated_feedback.parsing_confidence
            )
            
            return validated_feedback
            
        except Exception as e:
            logger.warning(
                "response_validation_failed",
                error=str(e),
                extracted_json=extracted_json
            )
            return self._create_minimal_feedback(response_text)
    
    def _fallback_parsing(self, response_text: str) -> Optional[Dict[str, Any]]:
        """
        Attempt to extract structured data using text parsing as fallback
        
        Args:
            response_text: Raw response text
            
        Returns:
            Extracted data dictionary or None
        """
        try:
            # Look for key-value patterns in the text
            fallback_data = {}
            
            # Extract overall assessment
            assessment_match = re.search(
                r'(?:overall[_\s]*assessment|summary)[:\s]*([^.\n]+)',
                response_text,
                re.IGNORECASE
            )
            if assessment_match:
                fallback_data['overall_assessment'] = assessment_match.group(1).strip()
            
            # Extract strengths
            strengths_section = re.search(
                r'strengths?[:\s]*\n?((?:[-*•]\s*[^\n]+\n?)+)',
                response_text,
                re.IGNORECASE | re.MULTILINE
            )
            if strengths_section:
                strengths = re.findall(r'[-*•]\s*([^\n]+)', strengths_section.group(1))
                fallback_data['strengths'] = [s.strip() for s in strengths[:5]]
            
            # Extract improvements
            improvements_section = re.search(
                r'(?:improvements?|recommendations?)[:\s]*\n?((?:[-*•]\s*[^\n]+\n?)+)',
                response_text,
                re.IGNORECASE | re.MULTILINE
            )
            if improvements_section:
                improvements = re.findall(r'[-*•]\s*([^\n]+)', improvements_section.group(1))
                fallback_data['priority_improvements'] = [
                    {
                        'category': 'General',
                        'priority': 'Medium',
                        'recommendation': imp.strip(),
                        'impact': 'Will improve overall resume quality'
                    }
                    for imp in improvements[:5]
                ]
            
            # Only return if we have minimum required data
            if len(fallback_data) >= 2:
                logger.info("fallback_parsing_success", fields_extracted=list(fallback_data.keys()))
                return fallback_data
            
        except Exception as e:
            logger.warning("fallback_parsing_failed", error=str(e))
        
        return None
    
    def _validate_and_structure(self, data: Dict[str, Any], raw_response: str) -> AIFeedback:
        """
        Validate extracted JSON and create structured feedback
        
        Args:
            data: Extracted JSON data
            raw_response: Original response text
            
        Returns:
            Validated AIFeedback object
        """
        # Validate required fields
        for field, expected_type in self.required_fields.items():
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
            
            if not isinstance(data[field], expected_type):
                # Try to convert if possible
                if expected_type == list and isinstance(data[field], str):
                    data[field] = [data[field]]
                elif expected_type == str and isinstance(data[field], list):
                    data[field] = '. '.join(str(item) for item in data[field])
                else:
                    raise ValueError(f"Invalid type for {field}: expected {expected_type}")
        
        # Add optional fields with defaults
        for field, default_value in self.optional_fields.items():
            if field not in data:
                data[field] = default_value
        
        # Validate priority_improvements structure
        if 'priority_improvements' in data:
            validated_improvements = []
            for imp in data['priority_improvements']:
                if isinstance(imp, dict):
                    validated_improvements.append({
                        'category': imp.get('category', 'General'),
                        'priority': imp.get('priority', 'Medium'),
                        'recommendation': imp.get('recommendation', str(imp)),
                        'impact': imp.get('impact', 'Will improve resume quality')
                    })
                elif isinstance(imp, str):
                    validated_improvements.append({
                        'category': 'General',
                        'priority': 'Medium',
                        'recommendation': imp,
                        'impact': 'Will improve resume quality'
                    })
            data['priority_improvements'] = validated_improvements
        
        # Create AIFeedback object
        return AIFeedback(
            overall_assessment=data['overall_assessment'],
            match_score_interpretation=data.get('match_score_interpretation', ''),
            strengths=data['strengths'],
            priority_improvements=data['priority_improvements'],
            missing_keywords_analysis=data.get('missing_keywords_analysis', {}),
            ats_optimization_tips=data.get('ats_optimization_tips', []),
            raw_response=raw_response
        )
    
    def _create_minimal_feedback(self, response_text: str) -> AIFeedback:
        """
        Create minimal feedback when parsing fails
        
        Args:
            response_text: Original response text
            
        Returns:
            Minimal AIFeedback object
        """
        return AIFeedback(
            overall_assessment="Unable to parse detailed feedback. Please review the raw response.",
            match_score_interpretation="Analysis completed but formatting issues occurred.",
            strengths=["Resume submitted for analysis"],
            priority_improvements=[{
                'category': 'System',
                'priority': 'Low',
                'recommendation': 'Review raw AI response for insights',
                'impact': 'Manual review may provide additional insights'
            }],
            missing_keywords_analysis={'critical_missing': [], 'suggestions': 'See raw response'},
            ats_optimization_tips=['Review raw AI response for specific recommendations'],
            raw_response=response_text,
            parsing_confidence=0.1
        )
    
    def _calculate_confidence(self, data: Dict[str, Any], parsing_method: str) -> float:
        """
        Calculate confidence score for parsed response
        
        Args:
            data: Parsed data
            parsing_method: Method used for parsing
            
        Returns:
            Confidence score between 0 and 1
        """
        confidence = 0.5  # Base confidence
        
        # Boost confidence based on parsing method
        if parsing_method.startswith('pattern_0'):  # JSON in code blocks
            confidence += 0.4
        elif parsing_method.startswith('pattern_1'):  # Generic code blocks
            confidence += 0.3
        elif parsing_method.startswith('pattern_2'):  # Balanced braces
            confidence += 0.2
        elif parsing_method == 'fallback':
            confidence = 0.3
        
        # Boost confidence based on data completeness
        required_fields_present = sum(1 for field in self.required_fields if field in data)
        optional_fields_present = sum(1 for field in self.optional_fields if field in data)
        
        completeness_score = (required_fields_present / len(self.required_fields)) * 0.3
        completeness_score += (optional_fields_present / len(self.optional_fields)) * 0.2
        
        confidence += completeness_score
        
        return min(confidence, 1.0)


class AIService:
    """Complete AI feedback generation service"""
    
    def __init__(self):
        self.gemini_client = gemini_client
        self.prompt_engine = PromptEngine()
        self.response_parser = ResponseParser()
    
    async def generate_feedback(self, context: AnalysisContext) -> AIFeedback:
        """
        Generate comprehensive AI feedback for resume analysis
        
        Args:
            context: Analysis context with resume data and job description
            
        Returns:
            Structured AI feedback
            
        Raises:
            AIServiceError: If feedback generation fails
        """
        try:
            logger.info(
                "generating_ai_feedback",
                match_score=context.match_score,
                matched_keywords_count=len(context.matched_keywords),
                missing_keywords_count=len(context.missing_keywords)
            )
            print(f"DEBUG: Starting AI feedback generation with match_score: {context.match_score}")
            
            # Build the analysis prompt
            prompt = self.prompt_engine.build_analysis_prompt(context)
            
            # Generate response from Gemini
            print("DEBUG: About to call Gemini API...")
            try:
                raw_response = await self.gemini_client.generate_response(prompt)
                print(f"DEBUG: Gemini API response received, length: {len(raw_response)}")
            except (AIServiceError, APIRateLimitError) as e:
                # Try fallback prompt if main prompt fails
                print(f"DEBUG: Main prompt failed: {str(e)}, trying fallback...")
                logger.warning("main_prompt_failed_trying_fallback", error=str(e))
                fallback_prompt = self.prompt_engine.build_fallback_prompt(context)
                raw_response = await self.gemini_client.generate_response(fallback_prompt)
                print(f"DEBUG: Fallback response received, length: {len(raw_response)}")
            
            # Parse and validate the response
            feedback = self.response_parser.parse_response(raw_response)
            
            logger.info(
                "ai_feedback_generated",
                parsing_confidence=feedback.parsing_confidence,
                strengths_count=len(feedback.strengths),
                improvements_count=len(feedback.priority_improvements)
            )
            
            return feedback
            
        except Exception as e:
            logger.error(
                "ai_feedback_generation_failed",
                error=str(e),
                context_match_score=context.match_score
            )
            raise AIServiceError(
                message=f"Failed to generate AI feedback: {str(e)}",
                service_name="ai_service",
                details={
                    "match_score": context.match_score,
                    "error_type": type(e).__name__
                }
            )
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check of AI service
        
        Returns:
            Health check results
        """
        try:
            # Check Gemini client health
            gemini_health = await self.gemini_client.health_check()
            
            # Test prompt generation
            test_context = AnalysisContext(
                resume_entities={'skills': ['Python', 'JavaScript']},
                match_score=75.0,
                matched_keywords=['Python', 'API'],
                missing_keywords=['Docker', 'AWS'],
                semantic_similarity=0.75,
                keyword_coverage=0.60,
                job_description="Test job description for health check",
                resume_text="Test resume text"
            )
            
            test_prompt = self.prompt_engine.build_analysis_prompt(test_context)
            prompt_generated = len(test_prompt) > 100
            
            # Overall health status
            overall_healthy = (
                gemini_health.get('status') == 'healthy' and
                prompt_generated
            )
            
            return {
                'status': 'healthy' if overall_healthy else 'degraded',
                'service': 'ai_service',
                'components': {
                    'gemini_client': gemini_health,
                    'prompt_engine': {
                        'status': 'healthy' if prompt_generated else 'unhealthy',
                        'prompt_length': len(test_prompt) if prompt_generated else 0
                    },
                    'response_parser': {
                        'status': 'healthy',
                        'patterns_loaded': len(self.response_parser.json_patterns)
                    }
                }
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'service': 'ai_service',
                'error': str(e)
            }


# Global AI service instance
ai_service = AIService()