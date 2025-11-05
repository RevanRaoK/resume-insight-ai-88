# SmartResume AI Resume Analyzer - Design Document

## Overview

The SmartResume AI Resume Analyzer is a FastAPI-based Python backend that provides intelligent resume analysis capabilities. The system integrates four specialized subsystems to deliver comprehensive career guidance: document ingestion, natural language understanding, semantic analysis, and AI-powered feedback generation.

The architecture follows a microservices-inspired modular design within a monolithic FastAPI application, ensuring maintainability while avoiding the complexity of distributed systems for this use case.

## Architecture

### High-Level System Architecture

```
┌─────────────────┐    ┌──────────────────────────────────────┐    ┌─────────────────┐
│   React Frontend │    │           FastAPI Backend            │    │   Supabase      │
│   (JavaScript)   │◄──►│                                      │◄──►│   Database      │
└─────────────────┘    │  ┌─────────────────────────────────┐ │    └─────────────────┘
                       │  │        API Layer (Routers)      │ │
                       │  └─────────────────────────────────┘ │
                       │  ┌─────────────────────────────────┐ │
                       │  │       Service Layer             │ │
                       │  │  ┌─────────┐ ┌─────────────────┐│ │
                       │  │  │Document │ │      NLU        ││ │
                       │  │  │Ingestion│ │    Service      ││ │
                       │  │  └─────────┘ └─────────────────┘│ │
                       │  │  ┌─────────┐ ┌─────────────────┐│ │
                       │  │  │Semantic │ │   AI Feedback   ││ │
                       │  │  │Analysis │ │    Service      ││ │
                       │  │  └─────────┘ └─────────────────┘│ │
                       │  └─────────────────────────────────┘ │
                       │  ┌─────────────────────────────────┐ │
                       │  │       Data Layer                │ │
                       │  └─────────────────────────────────┘ │
                       └──────────────────────────────────────┘
                                        │
                       ┌──────────────────────────────────────┐
                       │        External Services             │
                       │  ┌─────────────┐ ┌─────────────────┐ │
                       │  │   Hugging   │ │   Google        │ │
                       │  │    Face     │ │   Gemini API    │ │
                       │  │   Models    │ │                 │ │
                       │  └─────────────┘ └─────────────────┘ │
                       └──────────────────────────────────────┘
```

### Directory Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py              # Configuration and environment variables
│   ├── middleware/
│   │   ├── __init__.py
│   │   └── auth.py            # JWT authentication middleware
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── health.py          # Health check endpoints
│   │   ├── upload.py          # Document upload endpoints
│   │   ├── analysis.py        # Resume analysis endpoints
│   │   └── history.py         # Analysis history endpoints
│   ├── services/
│   │   ├── __init__.py
│   │   ├── document_service.py    # Document ingestion logic
│   │   ├── nlu_service.py         # NER and entity extraction
│   │   ├── semantic_service.py    # Semantic analysis and scoring
│   │   ├── ai_service.py          # AI feedback generation
│   │   └── database_service.py    # Database operations
│   ├── models/
│   │   ├── __init__.py
│   │   ├── requests.py        # Pydantic request models
│   │   ├── responses.py       # Pydantic response models
│   │   └── entities.py        # Domain entity models
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── file_utils.py      # File processing utilities
│   │   ├── text_utils.py      # Text processing utilities
│   │   ├── ml_utils.py        # ML model loading and caching
│   │   └── logger.py          # Structured logging setup
│   └── core/
│       ├── __init__.py
│       ├── exceptions.py      # Custom exception classes
│       └── security.py        # Security utilities
├── requirements.txt
├── .env.example
└── README.md
```

## Components and Interfaces

### 1. Document Ingestion Service

**Purpose**: Extract clean, structured text from various document formats with intelligent fallback mechanisms.

**Key Components**:
- `PDFProcessor`: Primary PDF text extraction using pdfplumber
- `OCRProcessor`: Fallback OCR processing using pdf2image + pytesseract
- `DOCXProcessor`: Microsoft Word document processing using python-docx
- `TextProcessor`: Plain text processing with encoding detection
- `FileValidator`: Security validation and MIME type verification

**Interface**:
```python
class DocumentService:
    async def process_document(self, file: UploadFile) -> ProcessedDocument:
        """
        Process uploaded document and extract clean text
        Returns: ProcessedDocument with extracted text and metadata
        Raises: UnsupportedFormatError, FileSizeError, ProcessingError
        """
```

### 2. Natural Language Understanding Service

**Purpose**: Transform unstructured resume text into structured entities using pre-trained NER models.

**Key Components**:
- `NERProcessor`: Hugging Face transformer model integration (yashpwr/resume-ner-bert-v2)
- `EntityPostProcessor`: Entity grouping, filtering, and deduplication
- `FallbackExtractor`: Rule-based extraction for model failures
- `SkillDictionary`: Curated technical skills database

**Interface**:
```python
class NLUService:
    async def extract_entities(self, text: str) -> ResumeEntities:
        """
        Extract structured entities from resume text
        Returns: ResumeEntities with skills, experience, education, etc.
        """
```

### 3. Semantic Analysis Service

**Purpose**: Calculate meaningful compatibility scores between resumes and job descriptions using semantic embeddings.

**Key Components**:
- `EmbeddingGenerator`: Sentence transformer model integration (all-MiniLM-L6-v2)
- `SimilarityCalculator`: Cosine similarity computation and normalization
- `KeywordAnalyzer`: Intelligent keyword matching using spaCy NLP
- `ScoreNormalizer`: Score transformation and user-friendly formatting

**Interface**:
```python
class SemanticService:
    async def analyze_compatibility(self, resume_text: str, job_description: str) -> CompatibilityAnalysis:
        """
        Calculate semantic compatibility between resume and job description
        Returns: CompatibilityAnalysis with score, matched/missing keywords
        """
```

### 4. AI Feedback Service

**Purpose**: Generate personalized, actionable career coaching recommendations using Google Gemini API.

**Key Components**:
- `PromptEngine`: Advanced prompt engineering with chain-of-thought approach
- `GeminiClient`: Google Gemini API integration with retry logic
- `ResponseParser`: JSON extraction and validation from AI responses
- `FeedbackStructurer`: Standardized feedback formatting

**Interface**:
```python
class AIService:
    async def generate_feedback(self, analysis_context: AnalysisContext) -> AIFeedback:
        """
        Generate personalized resume improvement recommendations
        Returns: AIFeedback with structured recommendations and priorities
        """
```

### 5. Database Service

**Purpose**: Manage all database operations with the existing Supabase PostgreSQL schema.

**Key Components**:
- `UserRepository`: User data operations
- `ResumeRepository`: Resume storage and retrieval
- `AnalysisRepository`: Analysis results management
- `ConnectionManager`: Async database connection handling

**Interface**:
```python
class DatabaseService:
    async def store_analysis(self, analysis: AnalysisResult) -> str:
        """Store complete analysis results and return analysis_id"""
    
    async def get_user_analyses(self, user_id: str) -> List[AnalysisResult]:
        """Retrieve all analyses for a specific user"""
```

## Data Models

### Core Domain Models

```python
@dataclass
class ProcessedDocument:
    text: str
    file_name: str
    file_size: int
    processing_method: str  # "pdfplumber", "ocr", "docx", "text"
    confidence_score: float

@dataclass
class ResumeEntities:
    skills: List[str]
    job_titles: List[str]
    companies: List[str]
    education: List[str]
    contact_info: Dict[str, str]
    experience_years: Optional[int]
    confidence_scores: Dict[str, float]

@dataclass
class CompatibilityAnalysis:
    match_score: float  # 0-100
    matched_keywords: List[str]
    missing_keywords: List[str]
    semantic_similarity: float
    keyword_coverage: float

@dataclass
class AIFeedback:
    recommendations: List[Dict[str, Any]]
    overall_assessment: str
    priority_improvements: List[str]
    strengths: List[str]
```

### API Request/Response Models

```python
class AnalysisRequest(BaseModel):
    job_description: str
    resume_id: Optional[str] = None
    resume_text: Optional[str] = None

class AnalysisResponse(BaseModel):
    analysis_id: str
    match_score: float
    ai_feedback: Dict[str, Any]
    matched_keywords: List[str]
    missing_keywords: List[str]
    processing_time: float
    created_at: datetime
```

## Error Handling

### Exception Hierarchy

```python
class SmartResumeException(Exception):
    """Base exception for all SmartResume errors"""

class DocumentProcessingError(SmartResumeException):
    """Errors during document ingestion"""

class NLUProcessingError(SmartResumeException):
    """Errors during entity extraction"""

class SemanticAnalysisError(SmartResumeException):
    """Errors during semantic analysis"""

class AIServiceError(SmartResumeException):
    """Errors from AI feedback generation"""

class DatabaseError(SmartResumeException):
    """Database operation errors"""
```

### Error Response Format

```python
class ErrorResponse(BaseModel):
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime
    request_id: str
```

### Retry and Fallback Strategies

1. **AI Service**: Exponential backoff retry (3 attempts) with circuit breaker
2. **Database Operations**: Connection retry with jitter
3. **Model Loading**: Graceful degradation to fallback extraction methods
4. **File Processing**: Format-specific fallback chains (PDF → OCR, etc.)

## Testing Strategy

### Unit Testing
- **Coverage Target**: 90% code coverage minimum
- **Framework**: pytest with async support
- **Mocking**: Mock external APIs (Gemini, Supabase) and ML models
- **Test Data**: Curated set of sample resumes and job descriptions

### Integration Testing
- **Database Integration**: Test with real Supabase connection using test database
- **Model Integration**: Test with actual Hugging Face models (cached for speed)
- **API Integration**: End-to-end API testing with realistic payloads

### Performance Testing
- **Load Testing**: Simulate 50 concurrent users using locust
- **Latency Testing**: Ensure 95% of requests complete under 30 seconds
- **Memory Testing**: Monitor ML model memory usage under load

### Security Testing
- **Input Validation**: Test malicious file uploads and injection attempts
- **Authentication**: Verify JWT validation and authorization flows
- **Rate Limiting**: Test rate limiting enforcement

## Performance Optimization

### Model Caching Strategy
```python
class ModelCache:
    """Singleton pattern for ML model caching"""
    _instance = None
    _models = {}
    
    def load_models_at_startup(self):
        """Load all ML models into memory during application startup"""
        self._models['ner'] = AutoModelForTokenClassification.from_pretrained(
            "yashpwr/resume-ner-bert-v2"
        )
        self._models['embeddings'] = SentenceTransformer(
            "sentence-transformers/all-MiniLM-L6-v2"
        )
```

### Async Processing Pipeline
- All I/O operations (database, API calls) use async/await
- Document processing pipeline uses async generators for streaming
- Background task queue for long-running analyses (optional future enhancement)

### Database Optimization
- Connection pooling with asyncpg
- Prepared statements for frequent queries
- Proper indexing on user_id and created_at columns
- Query result caching for user analysis history

## Security Considerations

### Authentication & Authorization
- JWT token validation middleware on all protected endpoints
- User context injection for database operations
- Role-based access control (future enhancement)

### Input Sanitization
```python
def sanitize_text_input(text: str) -> str:
    """Remove potentially harmful content from user text inputs"""
    # Remove HTML tags, script content, SQL injection patterns
    # Limit text length to prevent DoS attacks
    # Normalize Unicode characters
```

### File Upload Security
- MIME type validation using python-magic
- File size limits (10MB maximum)
- Virus scanning integration (future enhancement)
- Temporary file cleanup with automatic garbage collection

### API Security
- Rate limiting: 10 requests per user per hour for analysis endpoints
- Request size limits: 50MB maximum payload
- CORS configuration for frontend domain only
- Security headers (HSTS, CSP, etc.)

## Monitoring and Observability

### Structured Logging
```python
import structlog

logger = structlog.get_logger()

# Example usage
logger.info(
    "analysis_completed",
    user_id=user_id,
    analysis_id=analysis_id,
    processing_time=elapsed_time,
    match_score=score
)
```

### Metrics Collection
- Request latency percentiles (P50, P95, P99)
- Error rates by endpoint and error type
- ML model inference times
- Database query performance
- Active user sessions

### Health Checks
```python
@router.get("/health")
async def health_check():
    """Comprehensive health check including dependencies"""
    return {
        "status": "healthy",
        "database": await check_database_connection(),
        "ml_models": await check_model_availability(),
        "external_apis": await check_gemini_api(),
        "timestamp": datetime.utcnow()
    }
```

This design provides a robust, scalable foundation for the SmartResume AI Resume Analyzer that addresses all requirements while maintaining high performance, security, and maintainability standards.