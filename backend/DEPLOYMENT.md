# SmartResume AI Resume Analyzer - Deployment Guide

This document provides comprehensive instructions for deploying the SmartResume AI Resume Analyzer in production environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Docker Deployment](#docker-deployment)
4. [Manual Deployment](#manual-deployment)
5. [Configuration](#configuration)
6. [Monitoring](#monitoring)
7. [Security](#security)
8. [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

- **Operating System**: Linux (Ubuntu 20.04+ recommended), macOS, or Windows 10/11
- **CPU**: 2+ cores (4+ cores recommended for production)
- **Memory**: 4GB RAM minimum (8GB+ recommended for production)
- **Storage**: 20GB available space (SSD recommended)
- **Network**: Stable internet connection for API dependencies

### Software Dependencies

- **Docker**: Version 20.10+
- **Docker Compose**: Version 2.0+
- **Git**: For cloning the repository
- **curl**: For health checks and testing

### External Services

- **Supabase Account**: For database and authentication
- **Google Cloud Account**: For Gemini AI API access
- **Domain Name**: For production deployment (optional but recommended)
- **SSL Certificate**: For HTTPS (Let's Encrypt recommended)

## Environment Setup

### 1. Clone Repository

```bash
git clone https://github.com/your-org/smartresume-ai.git
cd smartresume-ai/backend
```

### 2. Environment Configuration

Copy the production environment template:

```bash
cp .env.production .env
```

Edit the `.env` file with your production values:

```bash
# Required: Update these values
SECRET_KEY=your-super-secure-secret-key-here
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.your-project-id.supabase.co:5432/postgres
GOOGLE_GEMINI_API_KEY=your-google-gemini-api-key
ALLOWED_ORIGINS=["https://yourdomain.com"]
```

### 3. SSL Certificate Setup (Production)

For HTTPS deployment, place your SSL certificates in the `nginx/ssl/` directory:

```bash
mkdir -p nginx/ssl
# Copy your certificate files
cp /path/to/your/cert.pem nginx/ssl/
cp /path/to/your/key.pem nginx/ssl/
```

For Let's Encrypt certificates:

```bash
# Install certbot
sudo apt-get install certbot

# Generate certificate
sudo certbot certonly --standalone -d yourdomain.com

# Copy certificates
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem nginx/ssl/cert.pem
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem nginx/ssl/key.pem
```

## Docker Deployment

### Quick Start (Recommended)

Use the automated deployment script:

**Linux/macOS:**
```bash
chmod +x deploy.sh
./deploy.sh
```

**Windows:**
```cmd
deploy.bat
```

### Manual Docker Deployment

1. **Build and start services:**
```bash
docker-compose up -d --build
```

2. **Verify deployment:**
```bash
# Check container status
docker-compose ps

# Check logs
docker-compose logs -f

# Test health endpoint
curl http://localhost:8000/api/v1/health
```

3. **Stop services:**
```bash
docker-compose down
```

### Development Deployment

For development environments:

```bash
docker-compose -f docker-compose.dev.yml up -d --build
```

## Manual Deployment

### 1. Python Environment Setup

```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y poppler-utils tesseract-ocr tesseract-ocr-eng libmagic1
```

**macOS:**
```bash
brew install poppler tesseract libmagic
```

**Windows:**
```powershell
# Install using chocolatey
choco install poppler tesseract
```

### 3. Start Application

```bash
# Development
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `DEBUG` | Enable debug mode | No | `false` |
| `SECRET_KEY` | Application secret key | Yes | - |
| `SUPABASE_URL` | Supabase project URL | Yes | - |
| `SUPABASE_ANON_KEY` | Supabase anonymous key | Yes | - |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key | Yes | - |
| `DATABASE_URL` | PostgreSQL connection string | Yes | - |
| `GOOGLE_GEMINI_API_KEY` | Google Gemini API key | Yes | - |
| `ALLOWED_ORIGINS` | CORS allowed origins | No | `["http://localhost:3000"]` |
| `MAX_FILE_SIZE` | Maximum upload file size (bytes) | No | `10485760` |
| `RATE_LIMIT_REQUESTS` | Rate limit per window | No | `10` |
| `RATE_LIMIT_WINDOW` | Rate limit window (seconds) | No | `3600` |
| `MAX_CONCURRENT_USERS` | Maximum concurrent users | No | `50` |
| `REQUEST_TIMEOUT` | Request timeout (seconds) | No | `30` |
| `LOG_LEVEL` | Logging level | No | `INFO` |

### Nginx Configuration

Update `nginx/nginx.conf` for your domain:

```nginx
server_name your-domain.com;
ssl_certificate /etc/nginx/ssl/cert.pem;
ssl_certificate_key /etc/nginx/ssl/key.pem;
```

### Database Setup

The application uses Supabase PostgreSQL. Ensure your database has the required tables:

```sql
-- Users table (managed by Supabase Auth)
-- Resumes table
CREATE TABLE resumes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    file_name TEXT NOT NULL,
    file_url TEXT,
    parsed_text TEXT,
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Analyses table
CREATE TABLE analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    resume_id UUID REFERENCES resumes(id),
    job_title TEXT,
    job_description TEXT,
    match_score FLOAT,
    ai_feedback JSONB,
    matched_keywords TEXT[],
    missing_keywords TEXT[],
    processing_time FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## Monitoring

### Health Checks

The application provides several health check endpoints:

- **Basic Health**: `GET /api/v1/health`
- **Detailed Health**: `GET /api/v1/health/detailed`
- **Database Health**: `GET /api/v1/health/database`

### Prometheus Metrics

If monitoring is enabled, metrics are available at:
- **Metrics Endpoint**: `GET /api/v1/monitoring/metrics`
- **Prometheus UI**: `http://localhost:9090` (if deployed)

### Logging

Logs are written to:
- **Application Logs**: `./logs/app.log`
- **Access Logs**: `./logs/nginx/access.log`
- **Error Logs**: `./logs/nginx/error.log`

Log format is JSON for structured logging:

```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "level": "INFO",
  "logger": "app.services.analysis",
  "message": "analysis_completed",
  "user_id": "uuid",
  "processing_time": 2.5
}
```

## Security

### Security Headers

The Nginx configuration includes security headers:

- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security` (HSTS)
- `Content-Security-Policy`

### Rate Limiting

Rate limiting is configured at multiple levels:

- **Nginx Level**: Per-IP rate limiting
- **Application Level**: Per-user rate limiting
- **API Level**: Endpoint-specific limits

### File Upload Security

- File type validation using MIME type detection
- File size limits (10MB default)
- Temporary file cleanup
- Virus scanning (recommended for production)

### Authentication

- JWT token validation with Supabase
- User context injection
- Request ID tracking for audit trails

## Troubleshooting

### Common Issues

#### 1. Container Won't Start

```bash
# Check logs
docker-compose logs smartresume-api

# Common causes:
# - Missing environment variables
# - Port conflicts
# - Insufficient resources
```

#### 2. Health Check Fails

```bash
# Test manually
curl -v http://localhost:8000/api/v1/health

# Check if services are running
docker-compose ps

# Check application logs
docker-compose logs -f smartresume-api
```

#### 3. Database Connection Issues

```bash
# Verify database URL
echo $DATABASE_URL

# Test connection
docker-compose exec smartresume-api python -c "
from app.services.database_service import db_service
import asyncio
asyncio.run(db_service.health_check())
"
```

#### 4. ML Model Loading Issues

```bash
# Check model cache
docker-compose exec smartresume-api python -c "
from app.utils.ml_utils import model_cache
print(model_cache.get_model_info())
"

# Clear model cache
docker-compose exec smartresume-api rm -rf /app/models/
docker-compose restart smartresume-api
```

#### 5. High Memory Usage

```bash
# Monitor resource usage
docker stats

# Adjust memory limits in docker-compose.yml
# Reduce worker count if needed
```

### Performance Tuning

#### 1. Optimize Worker Count

```bash
# Calculate optimal workers: (2 x CPU cores) + 1
# Update in docker-compose.yml or Dockerfile
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

#### 2. Database Connection Pooling

Update database configuration:

```python
# In app/config.py
DATABASE_POOL_SIZE = 20
DATABASE_MAX_OVERFLOW = 30
```

#### 3. Redis Caching

Enable Redis for caching:

```bash
# Uncomment Redis service in docker-compose.yml
# Update application configuration
REDIS_URL=redis://redis:6379/0
ENABLE_CACHING=true
```

### Backup and Recovery

#### 1. Database Backup

```bash
# Backup Supabase database
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql
```

#### 2. Application Backup

```bash
# Backup configuration and logs
tar -czf backup_$(date +%Y%m%d_%H%M%S).tar.gz .env logs/ nginx/ssl/
```

#### 3. Restore Procedure

```bash
# Stop services
docker-compose down

# Restore configuration
tar -xzf backup_YYYYMMDD_HHMMSS.tar.gz

# Restore database (if needed)
psql $DATABASE_URL < backup_YYYYMMDD_HHMMSS.sql

# Start services
docker-compose up -d
```

### Support

For additional support:

1. Check the [GitHub Issues](https://github.com/your-org/smartresume-ai/issues)
2. Review application logs for error details
3. Consult the API documentation at `/docs`
4. Contact the development team

## Production Checklist

Before deploying to production:

- [ ] Environment variables configured
- [ ] SSL certificates installed
- [ ] Domain name configured
- [ ] Database migrations applied
- [ ] Health checks passing
- [ ] Monitoring configured
- [ ] Backup procedures tested
- [ ] Security headers verified
- [ ] Rate limiting configured
- [ ] Log rotation configured
- [ ] Performance testing completed
- [ ] Disaster recovery plan documented