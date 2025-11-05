# SmartResume AI Resume Analyzer - Documentation

## Overview

This directory contains comprehensive documentation for the SmartResume AI Resume Analyzer backend system. The documentation is organized to support different audiences and use cases, from API consumers to system operators.

## Documentation Structure

### 📚 API Documentation
- **[API_DOCUMENTATION.md](./API_DOCUMENTATION.md)** - Complete API reference with examples
- **[openapi.yaml](./openapi.yaml)** - OpenAPI 3.0 specification for automated tooling
- **Interactive API Docs** - Available at `/docs` (Swagger UI) and `/redoc` (ReDoc) when running

### 🚀 Deployment & Operations
- **[../DEPLOYMENT.md](../DEPLOYMENT.md)** - Comprehensive deployment guide
- **[TROUBLESHOOTING.md](./TROUBLESHOOTING.md)** - Troubleshooting guide and diagnostics
- **[OPERATIONAL_RUNBOOK.md](./OPERATIONAL_RUNBOOK.md)** - Day-to-day operational procedures

### 🏗️ Architecture & Design
- **[../README.md](../README.md)** - Project overview and setup instructions
- **[../../.kiro/specs/smart-resume-analyzer/design.md](../../.kiro/specs/smart-resume-analyzer/design.md)** - System architecture and design decisions
- **[../../.kiro/specs/smart-resume-analyzer/requirements.md](../../.kiro/specs/smart-resume-analyzer/requirements.md)** - Functional requirements specification

## Quick Start Guides

### For API Consumers

1. **Authentication Setup**
   - Obtain JWT token from Supabase Auth
   - Include in Authorization header: `Bearer <token>`

2. **Basic Workflow**
   ```bash
   # Upload resume
   curl -X POST -H "Authorization: Bearer <token>" \
        -F "file=@resume.pdf" \
        https://api.smartresume-ai.com/api/v1/upload
   
   # Analyze resume
   curl -X POST -H "Authorization: Bearer <token>" \
        -H "Content-Type: application/json" \
        -d '{"job_description": "...", "resume_id": "..."}' \
        https://api.smartresume-ai.com/api/v1/analyze
   ```

3. **Resources**
   - [Complete API Documentation](./API_DOCUMENTATION.md)
   - [OpenAPI Specification](./openapi.yaml)
   - Interactive docs at `/docs` endpoint

### For Developers

1. **Local Development Setup**
   ```bash
   # Clone and setup
   git clone <repository>
   cd backend
   cp .env.example .env
   # Edit .env with your configuration
   
   # Start services
   docker-compose up -d
   
   # Verify health
   curl http://localhost:8000/api/v1/health
   ```

2. **Key Resources**
   - [Project README](../README.md)
   - [System Design](../../.kiro/specs/smart-resume-analyzer/design.md)
   - [Requirements Specification](../../.kiro/specs/smart-resume-analyzer/requirements.md)

### For System Operators

1. **Deployment**
   - Follow [Deployment Guide](../DEPLOYMENT.md)
   - Use provided Docker Compose configurations
   - Configure monitoring and alerting

2. **Daily Operations**
   - Review [Operational Runbook](./OPERATIONAL_RUNBOOK.md)
   - Monitor health endpoints
   - Follow maintenance schedules

3. **Troubleshooting**
   - Use [Troubleshooting Guide](./TROUBLESHOOTING.md)
   - Check system health diagnostics
   - Follow incident response procedures

## API Overview

### Core Endpoints

| Endpoint | Method | Purpose | Auth Required |
|----------|--------|---------|---------------|
| `/health` | GET | Basic health check | No |
| `/health/detailed` | GET | Comprehensive health status | No |
| `/upload` | POST | Upload resume document | Yes |
| `/analyze` | POST | Analyze resume vs job description | Yes |
| `/analyses` | GET | Get analysis history | Yes |
| `/analyses/{id}` | GET | Get specific analysis | Yes |

### Key Features

- **Multi-format Support**: PDF, DOCX, TXT with OCR fallback
- **AI-Powered Analysis**: NLP entity extraction + semantic similarity + AI feedback
- **Secure & Scalable**: JWT auth, rate limiting, horizontal scaling
- **Comprehensive Monitoring**: Health checks, metrics, structured logging

## System Architecture

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

## Performance Characteristics

### Service Level Objectives (SLOs)

- **Uptime**: 99.9% (8.76 hours downtime per year)
- **Response Time**: 95% of requests complete within 30 seconds
- **Error Rate**: <1% for all endpoints
- **Throughput**: Support 50 concurrent users

### Typical Response Times

- **File Upload**: 2-5 seconds
- **Resume Analysis**: 8-15 seconds
- **History Retrieval**: <1 second
- **Health Checks**: <500ms

## Security Features

### Authentication & Authorization
- JWT token validation with Supabase Auth
- User context injection for all operations
- Request ID tracking for audit trails

### Input Validation & Security
- File type validation using MIME detection
- File size limits (10MB maximum)
- Input sanitization for all text inputs
- Rate limiting per user and endpoint

### Data Protection
- Secure storage in Supabase PostgreSQL
- User data isolation and access controls
- Structured logging without sensitive data
- Temporary file cleanup

## Monitoring & Observability

### Health Monitoring
- Multi-level health checks (basic, detailed, component-specific)
- Dependency health validation (database, ML models, external APIs)
- Automated health monitoring and alerting

### Performance Monitoring
- Request latency percentiles (P50, P95, P99)
- Error rates by endpoint and error type
- ML model inference times
- Database query performance
- Resource utilization metrics

### Logging & Tracing
- Structured JSON logging with contextual data
- Request ID tracing across all components
- User activity tracking and audit trails
- Error tracking with detailed context

## Error Handling

### Comprehensive Error Responses
All errors follow a consistent format with:
- Machine-readable error codes
- Human-readable messages
- Additional context and details
- Request IDs for tracing
- Timestamps for correlation

### Error Categories
- **Client Errors (4xx)**: Invalid requests, authentication, authorization
- **Processing Errors (422)**: ML/AI processing failures with specific stages
- **Server Errors (5xx)**: System failures with appropriate retry guidance

## Rate Limiting

### Per-User Limits
- **Analysis endpoints**: 10 requests per hour
- **Upload endpoints**: 20 requests per hour
- **History endpoints**: 50 requests per hour
- **Health endpoints**: No limits

### Rate Limit Headers
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Requests remaining
- `X-RateLimit-Reset`: Reset time

## Support & Resources

### Getting Help
- **Technical Support**: support@smartresume-ai.com
- **API Issues**: Check [Troubleshooting Guide](./TROUBLESHOOTING.md)
- **System Status**: https://status.smartresume-ai.com
- **Documentation Issues**: Create GitHub issue

### Additional Resources
- **OpenAPI Specification**: [openapi.yaml](./openapi.yaml)
- **Postman Collection**: Available on request
- **SDK Examples**: See [API Documentation](./API_DOCUMENTATION.md)
- **Status Page**: https://status.smartresume-ai.com

### Community
- **GitHub Repository**: https://github.com/smartresume-ai/backend
- **Discussion Forum**: https://github.com/smartresume-ai/backend/discussions
- **Issue Tracker**: https://github.com/smartresume-ai/backend/issues

## Contributing

### Documentation Updates
1. Fork the repository
2. Make documentation changes
3. Test documentation locally
4. Submit pull request with clear description

### API Changes
1. Update OpenAPI specification
2. Update API documentation
3. Add examples and test cases
4. Update troubleshooting guide if needed

### Operational Procedures
1. Test procedures in staging environment
2. Update operational runbook
3. Review with operations team
4. Document lessons learned

---

**Last Updated**: November 4, 2023  
**Version**: 1.0.0  
**Maintained By**: SmartResume AI Development Team