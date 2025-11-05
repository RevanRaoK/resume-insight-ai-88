# SmartResume AI Resume Analyzer - API Documentation

## Overview

The SmartResume AI Resume Analyzer provides a comprehensive REST API for intelligent resume analysis and career guidance. This document provides detailed information about all available endpoints, authentication, error handling, and usage examples.

## Base URL

- **Development**: `http://localhost:8000`
- **Production**: `https://api.smartresume-ai.com`

## API Version

Current API version: `v1`

All endpoints are prefixed with `/api/v1`

## Authentication

### JWT Token Authentication

All API endpoints (except health checks) require authentication using JWT tokens issued by Supabase Auth.

**Header Format:**
```
Authorization: Bearer <jwt_token>
```

**Example:**
```bash
curl -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
     https://api.smartresume-ai.com/api/v1/upload
```

### Getting Authentication Tokens

Tokens are obtained through the frontend application's Supabase Auth integration. The backend validates these tokens and extracts user context.

## Rate Limiting

The API implements rate limiting to ensure fair usage and system stability:

| Endpoint Category | Limit | Window |
|------------------|-------|---------|
| Analysis endpoints | 10 requests | 1 hour |
| Upload endpoints | 20 requests | 1 hour |
| History endpoints | 50 requests | 1 hour |
| Health endpoints | No limit | - |

Rate limit headers are included in responses:
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Requests remaining in current window
- `X-RateLimit-Reset`: Time when the rate limit resets

## Error Handling

### Standard Error Response Format

All errors follow a consistent JSON format:

```json
{
  "error_code": "ERROR_TYPE",
  "message": "Human-readable error description",
  "details": {
    "additional": "context-specific information"
  },
  "timestamp": "2023-11-04T10:30:00Z",
  "request_id": "uuid-for-tracing"
}
```

### HTTP Status Codes

| Status Code | Description | Usage |
|-------------|-------------|-------|
| 200 | OK | Successful request |
| 201 | Created | Resource created successfully |
| 400 | Bad Request | Invalid request parameters |
| 401 | Unauthorized | Missing or invalid authentication |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 413 | Payload Too Large | File size exceeds limit |
| 422 | Unprocessable Entity | Processing error (ML/AI failures) |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Unexpected server error |
| 503 | Service Unavailable | Service temporarily unavailable |

### Common Error Codes

| Error Code | Description | Resolution |
|------------|-------------|------------|
| `UNSUPPORTED_FORMAT` | File format not supported | Use PDF, DOCX, or TXT files |
| `FILE_TOO_LARGE` | File exceeds size limit | Reduce file size to under 10MB |
| `PROCESSING_FAILED` | Document processing error | Check file integrity, try different format |
| `NLU_PROCESSING_FAILED` | Entity extraction failed | Ensure resume has sufficient text content |
| `SEMANTIC_ANALYSIS_FAILED` | Compatibility analysis failed | Verify job description content |
| `AI_FEEDBACK_FAILED` | AI service unavailable | Retry request, check service status |
| `DATABASE_ERROR` | Database operation failed | Contact support if persistent |
| `RATE_LIMIT_EXCEEDED` | Too many requests | Wait for rate limit reset |

## API Endpoints

### Health Check Endpoints

#### GET /api/v1/health

Basic health check for load balancers and monitoring.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2023-11-04T10:30:00Z",
  "service": "SmartResume AI Resume Analyzer",
  "version": "1.0.0"
}
```

#### GET /api/v1/health/detailed

Comprehensive health check including all dependencies.

**Response:**
```json
{
  "service": "SmartResume AI Resume Analyzer",
  "version": "1.0.0",
  "timestamp": "2023-11-04T10:30:00Z",
  "status": "healthy",
  "checks": {
    "database": {
      "status": "healthy",
      "response_time_ms": 45,
      "pool_info": {
        "active_connections": 5,
        "idle_connections": 15
      }
    },
    "ml_models": {
      "status": "healthy",
      "models": {
        "ner_model": true,
        "embedding_model": true
      }
    },
    "external_apis": {
      "status": "healthy",
      "gemini_api": {
        "status": "healthy",
        "response_time_ms": 120
      }
    }
  }
}
```

### Document Upload Endpoints

#### POST /api/v1/upload

Upload and process a resume document.

**Authentication:** Required

**Request:**
- Content-Type: `multipart/form-data`
- Body: Form data with file field

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file` | File | Yes | Resume file (PDF, DOCX, TXT, max 10MB) |

**Example Request:**
```bash
curl -X POST \
  -H "Authorization: Bearer <token>" \
  -F "file=@resume.pdf" \
  https://api.smartresume-ai.com/api/v1/upload
```

**Response:**
```json
{
  "resume_id": "123e4567-e89b-12d3-a456-426614174000",
  "file_name": "john_doe_resume.pdf",
  "file_size": 245760,
  "processing_method": "pdfplumber",
  "confidence_score": 0.95,
  "text_length": 2847,
  "uploaded_at": "2023-11-04T10:30:00Z"
}
```

#### GET /api/v1/resumes

Get all uploaded resumes for the current user.

**Authentication:** Required

**Response:**
```json
[
  {
    "resume_id": "123e4567-e89b-12d3-a456-426614174000",
    "file_name": "john_doe_resume.pdf",
    "text_length": 2847,
    "uploaded_at": "2023-11-04T10:30:00Z"
  }
]
```

### Analysis Endpoints

#### POST /api/v1/analyze

Perform comprehensive resume analysis against a job description.

**Authentication:** Required

**Request Body:**
```json
{
  "job_description": "We are looking for a Senior Python Developer with experience in FastAPI, PostgreSQL, and machine learning...",
  "job_title": "Senior Python Developer",
  "resume_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `job_description` | string | Yes | Job posting text (50-10000 chars) |
| `job_title` | string | No | Job title for context (max 200 chars) |
| `resume_id` | UUID | No* | ID of uploaded resume |
| `resume_text` | string | No* | Direct resume text (max 50000 chars) |

*Either `resume_id` or `resume_text` must be provided.

**Response:**
```json
{
  "analysis_id": "456e7890-e89b-12d3-a456-426614174001",
  "match_score": 78.5,
  "ai_feedback": {
    "overall_assessment": "Strong technical background with good alignment to the role",
    "recommendations": [
      {
        "category": "skills",
        "priority": "high",
        "suggestion": "Add more specific experience with FastAPI framework",
        "impact": "This would increase your match score by approximately 8-12 points"
      },
      {
        "category": "experience",
        "priority": "medium", 
        "suggestion": "Highlight your machine learning project experience more prominently",
        "impact": "Better positioning for ML-related requirements"
      }
    ],
    "strengths": [
      "Strong Python programming background",
      "Solid database experience with PostgreSQL",
      "Good API development experience"
    ],
    "priority_improvements": [
      "FastAPI framework experience",
      "Docker containerization",
      "Kubernetes orchestration"
    ]
  },
  "matched_keywords": ["Python", "PostgreSQL", "API development", "machine learning"],
  "missing_keywords": ["FastAPI", "Docker", "Kubernetes", "microservices"],
  "processing_time": 12.3,
  "created_at": "2023-11-04T10:35:00Z"
}
```

### History Endpoints

#### GET /api/v1/analyses

Get analysis history for the current user.

**Authentication:** Required

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | 1 | Page number (1-based) |
| `page_size` | integer | 10 | Items per page (max 50) |
| `sort_by` | string | created_at | Sort field (created_at, match_score) |
| `sort_order` | string | desc | Sort order (asc, desc) |

**Example Request:**
```bash
curl -H "Authorization: Bearer <token>" \
     "https://api.smartresume-ai.com/api/v1/analyses?page=1&page_size=10&sort_by=match_score&sort_order=desc"
```

**Response:**
```json
{
  "analyses": [
    {
      "analysis_id": "456e7890-e89b-12d3-a456-426614174001",
      "job_title": "Senior Python Developer",
      "match_score": 78.5,
      "created_at": "2023-11-04T10:35:00Z",
      "processing_time": 12.3
    }
  ],
  "total_count": 15,
  "page": 1,
  "page_size": 10,
  "has_next": true
}
```

#### GET /api/v1/analyses/{analysis_id}

Get detailed results for a specific analysis.

**Authentication:** Required

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `analysis_id` | UUID | Yes | Analysis identifier |

**Response:**
```json
{
  "analysis_id": "456e7890-e89b-12d3-a456-426614174001",
  "job_title": "Senior Python Developer",
  "job_description": "We are looking for a Senior Python Developer...",
  "match_score": 78.5,
  "ai_feedback": { /* Full AI feedback object */ },
  "matched_keywords": ["Python", "PostgreSQL", "API development"],
  "missing_keywords": ["FastAPI", "Docker", "Kubernetes"],
  "processing_time": 12.3,
  "created_at": "2023-11-04T10:35:00Z"
}
```

### Monitoring Endpoints

#### GET /api/v1/monitoring/metrics

Get system performance metrics.

**Authentication:** Required (Admin only)

**Response:**
```json
{
  "timestamp": "2023-11-04T10:30:00Z",
  "database": {
    "status": "healthy",
    "pool_info": {
      "active_connections": 5,
      "idle_connections": 15,
      "total_connections": 20
    },
    "query_performance": {
      "avg_response_time_ms": 45,
      "slow_queries": 0
    }
  },
  "ml_models": {
    "loaded_models": ["ner_model", "embedding_model"],
    "model_health": {
      "ner_model": true,
      "embedding_model": true
    },
    "memory_usage": {
      "ner_model_mb": 512,
      "embedding_model_mb": 256
    }
  },
  "service": {
    "name": "SmartResume AI Resume Analyzer",
    "version": "1.0.0",
    "uptime_check": "healthy"
  }
}
```

## Usage Examples

### Complete Analysis Workflow

1. **Upload Resume:**
```bash
curl -X POST \
  -H "Authorization: Bearer <token>" \
  -F "file=@resume.pdf" \
  https://api.smartresume-ai.com/api/v1/upload
```

2. **Analyze Against Job Description:**
```bash
curl -X POST \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "job_description": "Senior Python Developer position...",
    "job_title": "Senior Python Developer",
    "resume_id": "123e4567-e89b-12d3-a456-426614174000"
  }' \
  https://api.smartresume-ai.com/api/v1/analyze
```

3. **View Analysis History:**
```bash
curl -H "Authorization: Bearer <token>" \
     https://api.smartresume-ai.com/api/v1/analyses
```

### Error Handling Example

```javascript
async function analyzeResume(jobDescription, resumeId) {
  try {
    const response = await fetch('/api/v1/analyze', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        job_description: jobDescription,
        resume_id: resumeId
      })
    });

    if (!response.ok) {
      const error = await response.json();
      
      switch (error.error_code) {
        case 'RATE_LIMIT_EXCEEDED':
          console.log('Rate limit exceeded, retry after:', error.details.retry_after);
          break;
        case 'NLU_PROCESSING_FAILED':
          console.log('Resume processing failed:', error.message);
          break;
        default:
          console.log('Analysis failed:', error.message);
      }
      
      return null;
    }

    return await response.json();
  } catch (error) {
    console.error('Network error:', error);
    return null;
  }
}
```

## SDK and Client Libraries

### Python Client Example

```python
import requests
from typing import Optional, Dict, Any

class SmartResumeClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip('/')
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
    
    def upload_resume(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Upload a resume file"""
        with open(file_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(
                f'{self.base_url}/api/v1/upload',
                headers={'Authorization': self.headers['Authorization']},
                files=files
            )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Upload failed: {response.json()}")
            return None
    
    def analyze_resume(self, job_description: str, resume_id: str, 
                      job_title: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Analyze resume against job description"""
        data = {
            'job_description': job_description,
            'resume_id': resume_id
        }
        if job_title:
            data['job_title'] = job_title
        
        response = requests.post(
            f'{self.base_url}/api/v1/analyze',
            headers=self.headers,
            json=data
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Analysis failed: {response.json()}")
            return None

# Usage
client = SmartResumeClient('https://api.smartresume-ai.com', 'your-jwt-token')
upload_result = client.upload_resume('resume.pdf')
if upload_result:
    analysis = client.analyze_resume(
        'Job description text...',
        upload_result['resume_id'],
        'Senior Developer'
    )
```

## Performance Considerations

### Response Times

- **File Upload**: 2-5 seconds (depends on file size and format)
- **Resume Analysis**: 8-15 seconds (includes ML processing and AI generation)
- **History Retrieval**: <1 second
- **Health Checks**: <500ms

### Optimization Tips

1. **Use resume_id instead of resume_text** for repeated analyses to avoid reprocessing
2. **Cache analysis results** on the client side when appropriate
3. **Implement retry logic** with exponential backoff for transient failures
4. **Monitor rate limits** and implement client-side throttling
5. **Use pagination** for large history requests

### Concurrent Usage

The system supports up to 50 concurrent users with the following considerations:

- ML model inference is CPU-intensive and may queue requests during peak usage
- Database connections are pooled (max 20 connections)
- AI API calls have built-in retry and circuit breaker patterns

## Changelog

### Version 1.0.0 (Current)

- Initial API release
- Document upload and processing
- Resume analysis with AI feedback
- Analysis history and retrieval
- Comprehensive health monitoring
- Rate limiting and security features

## Support

For API support and questions:

- **Documentation**: https://docs.smartresume-ai.com
- **Support Email**: support@smartresume-ai.com
- **Status Page**: https://status.smartresume-ai.com
- **GitHub Issues**: https://github.com/smartresume-ai/backend/issues

## Legal

- **Terms of Service**: https://smartresume-ai.com/terms
- **Privacy Policy**: https://smartresume-ai.com/privacy
- **License**: MIT License