# SmartResume AI Resume Analyzer Backend

Intelligent backend system for resume analysis and career guidance using FastAPI, ML models, and AI-powered feedback generation.

## Project Structure

```
backend/
├── app/
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py              # Configuration and environment variables
│   ├── middleware/            # Authentication and other middleware
│   ├── routers/               # API endpoint routers
│   ├── services/              # Business logic services
│   ├── models/                # Pydantic data models
│   ├── utils/                 # Utility functions and helpers
│   └── core/                  # Core functionality (exceptions, security)
├── requirements.txt           # Python dependencies
├── .env.example              # Environment variables template
└── README.md                 # This file
```

## Setup Instructions

1. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your actual configuration values
   ```

4. **Run the application:**
   ```bash
   python -m app.main
   ```

## Configuration

The application uses environment variables for configuration. Copy `.env.example` to `.env` and update the values:

- **Database**: Supabase connection details
- **API Keys**: Google Gemini API key for AI feedback
- **Security**: JWT secret key and CORS origins
- **Performance**: Rate limiting and file upload settings

## API Documentation

When running in debug mode, API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Development Status

This is the initial project structure. Core functionality will be implemented in subsequent tasks:

- [ ] Document ingestion system (PDF, DOCX, TXT processing)
- [ ] Natural Language Understanding (NER, entity extraction)
- [ ] Semantic analysis and compatibility scoring
- [ ] AI-powered feedback generation
- [ ] Database operations and data persistence
- [ ] API endpoints and request handling

## Logging

The application uses structured JSON logging with contextual information:
- Request IDs for tracing
- User IDs for audit trails
- Timestamps and log levels
- Custom fields for business context

## Error Handling

Comprehensive exception hierarchy for different error types:
- `DocumentProcessingError`: File processing issues
- `NLUProcessingError`: ML model and NLP errors
- `SemanticAnalysisError`: Semantic analysis failures
- `AIServiceError`: External API errors
- `DatabaseError`: Database operation failures
- `AuthenticationError`: Authentication and authorization issues