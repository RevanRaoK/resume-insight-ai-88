# SmartResume AI Resume Analyzer - Troubleshooting Guide

## Table of Contents

1. [Common Issues](#common-issues)
2. [System Health Diagnostics](#system-health-diagnostics)
3. [Performance Issues](#performance-issues)
4. [Error Code Reference](#error-code-reference)
5. [Log Analysis](#log-analysis)
6. [Database Issues](#database-issues)
7. [ML Model Issues](#ml-model-issues)
8. [External API Issues](#external-api-issues)
9. [File Processing Issues](#file-processing-issues)
10. [Authentication Issues](#authentication-issues)
11. [Monitoring and Alerting](#monitoring-and-alerting)
12. [Recovery Procedures](#recovery-procedures)

## Common Issues

### Application Won't Start

**Symptoms:**
- Container fails to start
- Application exits immediately
- Health checks fail

**Diagnostic Steps:**

1. **Check Environment Variables:**
```bash
# Verify all required environment variables are set
docker-compose exec smartresume-api env | grep -E "(DATABASE_URL|GOOGLE_GEMINI_API_KEY|SECRET_KEY)"

# Check for missing variables
python -c "
from app.config import settings
print('Config loaded successfully')
print(f'Database URL: {settings.DATABASE_URL[:20]}...')
print(f'Debug mode: {settings.DEBUG}')
"
```

2. **Check Logs:**
```bash
# View application logs
docker-compose logs smartresume-api

# View startup logs specifically
docker-compose logs smartresume-api | grep -E "(startup|error|failed)"
```

3. **Verify Dependencies:**
```bash
# Check if all system dependencies are available
docker-compose exec smartresume-api python -c "
import pdfplumber, pytesseract, docx, magic
print('All dependencies available')
"
```

**Common Solutions:**

- **Missing Environment Variables**: Copy `.env.example` to `.env` and configure all required values
- **Database Connection**: Verify Supabase URL and credentials
- **Port Conflicts**: Change port in `docker-compose.yml` if 8000 is in use
- **Memory Issues**: Increase Docker memory allocation to at least 4GB

### Health Check Failures

**Symptoms:**
- `/health` endpoint returns 503
- Load balancer marks service as unhealthy
- Monitoring alerts triggered

**Diagnostic Commands:**

```bash
# Test basic health endpoint
curl -v http://localhost:8000/api/v1/health

# Test detailed health check
curl -v http://localhost:8000/api/v1/health/detailed

# Check specific components
curl -v http://localhost:8000/api/v1/health/database
curl -v http://localhost:8000/api/v1/health/models
curl -v http://localhost:8000/api/v1/health/apis
```

**Component-Specific Checks:**

1. **Database Health:**
```bash
# Test database connection manually
docker-compose exec smartresume-api python -c "
import asyncio
from app.services.database_service import db_service
result = asyncio.run(db_service.health_check())
print(result)
"
```

2. **ML Models Health:**
```bash
# Check model loading status
docker-compose exec smartresume-api python -c "
from app.utils.ml_utils import model_cache
info = model_cache.get_model_info()
print(info)
"
```

3. **External APIs Health:**
```bash
# Test Gemini API connectivity
docker-compose exec smartresume-api python -c "
import asyncio
from app.services.ai_service import ai_service
result = asyncio.run(ai_service.health_check())
print(result)
"
```

### High Response Times

**Symptoms:**
- API responses taking >30 seconds
- Timeout errors
- Poor user experience

**Investigation Steps:**

1. **Check System Resources:**
```bash
# Monitor CPU and memory usage
docker stats

# Check disk I/O
iostat -x 1

# Monitor network latency
ping -c 5 db.your-project-id.supabase.co
```

2. **Analyze Request Patterns:**
```bash
# Check for concurrent requests
docker-compose logs smartresume-api | grep "analysis_started" | tail -20

# Monitor processing times
docker-compose logs smartresume-api | grep "processing_time" | tail -10
```

3. **Database Performance:**
```bash
# Check slow queries
docker-compose exec smartresume-api python -c "
import asyncio
from app.services.database_service import db_service
# Check connection pool status
pool_info = asyncio.run(db_service.get_pool_info())
print(pool_info)
"
```

**Optimization Actions:**

- **Scale Workers**: Increase worker count in production
- **Database Optimization**: Add indexes, optimize queries
- **Model Caching**: Ensure ML models are properly cached
- **Connection Pooling**: Tune database connection pool settings

## System Health Diagnostics

### Comprehensive Health Check Script

Create a diagnostic script to check all system components:

```bash
#!/bin/bash
# health_check.sh

echo "=== SmartResume AI Health Diagnostics ==="
echo "Timestamp: $(date)"
echo

# Basic connectivity
echo "1. Basic Health Check:"
curl -s http://localhost:8000/api/v1/health | jq '.' || echo "FAILED: Basic health check"
echo

# Detailed health
echo "2. Detailed Health Check:"
curl -s http://localhost:8000/api/v1/health/detailed | jq '.checks' || echo "FAILED: Detailed health check"
echo

# Container status
echo "3. Container Status:"
docker-compose ps
echo

# Resource usage
echo "4. Resource Usage:"
docker stats --no-stream
echo

# Log errors
echo "5. Recent Errors:"
docker-compose logs smartresume-api --tail=50 | grep -i error | tail -10
echo

# Database connectivity
echo "6. Database Test:"
docker-compose exec -T smartresume-api python -c "
import asyncio
from app.services.database_service import db_service
try:
    result = asyncio.run(db_service.health_check())
    print('Database Status:', result['status'])
except Exception as e:
    print('Database Error:', str(e))
"
echo

# ML Models status
echo "7. ML Models Test:"
docker-compose exec -T smartresume-api python -c "
from app.utils.ml_utils import model_cache
try:
    info = model_cache.get_model_info()
    print('Loaded Models:', info.get('loaded_models', []))
except Exception as e:
    print('ML Models Error:', str(e))
"
echo

echo "=== Health Check Complete ==="
```

### Automated Monitoring Setup

```python
# monitoring_script.py
import asyncio
import aiohttp
import json
from datetime import datetime
import smtplib
from email.mime.text import MimeText

class HealthMonitor:
    def __init__(self, base_url, alert_email=None):
        self.base_url = base_url
        self.alert_email = alert_email
        self.last_status = {}
    
    async def check_health(self):
        """Perform comprehensive health check"""
        results = {
            'timestamp': datetime.utcnow().isoformat(),
            'overall_status': 'healthy',
            'checks': {}
        }
        
        async with aiohttp.ClientSession() as session:
            # Basic health
            try:
                async with session.get(f'{self.base_url}/api/v1/health') as resp:
                    if resp.status == 200:
                        results['checks']['basic'] = 'healthy'
                    else:
                        results['checks']['basic'] = 'unhealthy'
                        results['overall_status'] = 'unhealthy'
            except Exception as e:
                results['checks']['basic'] = f'error: {str(e)}'
                results['overall_status'] = 'unhealthy'
            
            # Detailed health
            try:
                async with session.get(f'{self.base_url}/api/v1/health/detailed') as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        results['checks']['detailed'] = data['status']
                        results['checks']['components'] = data['checks']
                    else:
                        results['checks']['detailed'] = 'unhealthy'
                        if results['overall_status'] == 'healthy':
                            results['overall_status'] = 'degraded'
            except Exception as e:
                results['checks']['detailed'] = f'error: {str(e)}'
                if results['overall_status'] == 'healthy':
                    results['overall_status'] = 'degraded'
        
        return results
    
    async def send_alert(self, status_change):
        """Send alert email for status changes"""
        if not self.alert_email:
            return
        
        subject = f"SmartResume AI Health Alert: {status_change['new_status']}"
        body = f"""
        Health status changed from {status_change['old_status']} to {status_change['new_status']}
        
        Timestamp: {status_change['timestamp']}
        Details: {json.dumps(status_change['details'], indent=2)}
        """
        
        # Configure your SMTP settings
        # This is a placeholder - implement according to your email provider
        print(f"ALERT: {subject}")
        print(body)
    
    async def monitor_loop(self, interval=60):
        """Continuous monitoring loop"""
        while True:
            try:
                results = await self.check_health()
                current_status = results['overall_status']
                
                # Check for status changes
                if self.last_status.get('overall_status') != current_status:
                    await self.send_alert({
                        'old_status': self.last_status.get('overall_status', 'unknown'),
                        'new_status': current_status,
                        'timestamp': results['timestamp'],
                        'details': results['checks']
                    })
                
                self.last_status = results
                
                # Log current status
                print(f"[{results['timestamp']}] Status: {current_status}")
                
                await asyncio.sleep(interval)
                
            except Exception as e:
                print(f"Monitoring error: {str(e)}")
                await asyncio.sleep(interval)

# Usage
if __name__ == "__main__":
    monitor = HealthMonitor("http://localhost:8000", "admin@yourcompany.com")
    asyncio.run(monitor.monitor_loop(60))  # Check every minute
```

## Performance Issues

### Slow Analysis Processing

**Symptoms:**
- Analysis takes >30 seconds
- Timeout errors during analysis
- High CPU usage during processing

**Investigation:**

1. **Profile Analysis Pipeline:**
```bash
# Enable detailed timing logs
docker-compose exec smartresume-api python -c "
import asyncio
import time
from app.services.nlu_service import nlu_service
from app.services.semantic_service import semantic_service

async def profile_analysis():
    sample_text = 'Sample resume text for testing...'
    
    # Time NLU processing
    start = time.time()
    entities = await nlu_service.extract_entities(sample_text)
    nlu_time = time.time() - start
    print(f'NLU Processing: {nlu_time:.2f}s')
    
    # Time semantic analysis
    start = time.time()
    analysis = await semantic_service.analyze_compatibility(sample_text, 'Sample job description')
    semantic_time = time.time() - start
    print(f'Semantic Analysis: {semantic_time:.2f}s')

asyncio.run(profile_analysis())
"
```

2. **Check Model Loading:**
```bash
# Verify models are cached properly
docker-compose exec smartresume-api python -c "
from app.utils.ml_utils import model_cache
import time

start = time.time()
model_info = model_cache.get_model_info()
load_time = time.time() - start

print(f'Model info retrieval: {load_time:.2f}s')
print('Loaded models:', model_info.get('loaded_models', []))
print('Memory usage:', model_info.get('memory_usage', {}))
"
```

**Optimization Steps:**

1. **Increase Worker Count:**
```yaml
# docker-compose.yml
services:
  smartresume-api:
    command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

2. **Optimize Model Loading:**
```python
# In app/utils/ml_utils.py - ensure models are loaded at startup
class ModelCache:
    def __init__(self):
        self._models = {}
        self._load_at_startup = True  # Ensure this is True
```

3. **Database Connection Tuning:**
```python
# In app/config.py
DATABASE_POOL_SIZE = 20
DATABASE_MAX_OVERFLOW = 30
DATABASE_POOL_TIMEOUT = 30
```

### Memory Issues

**Symptoms:**
- Out of memory errors
- Container restarts
- Slow garbage collection

**Investigation:**

```bash
# Monitor memory usage
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"

# Check Python memory usage
docker-compose exec smartresume-api python -c "
import psutil
import os

process = psutil.Process(os.getpid())
memory_info = process.memory_info()
print(f'RSS: {memory_info.rss / 1024 / 1024:.2f} MB')
print(f'VMS: {memory_info.vms / 1024 / 1024:.2f} MB')
"
```

**Solutions:**

1. **Increase Container Memory:**
```yaml
# docker-compose.yml
services:
  smartresume-api:
    deploy:
      resources:
        limits:
          memory: 8G
        reservations:
          memory: 4G
```

2. **Optimize Model Memory Usage:**
```python
# Clear model cache periodically if needed
from app.utils.ml_utils import model_cache
model_cache.clear_cache()  # Implement this method if memory issues persist
```

## Error Code Reference

### Document Processing Errors

| Error Code | Cause | Solution |
|------------|-------|----------|
| `UNSUPPORTED_FORMAT` | File format not supported | Use PDF, DOCX, or TXT files |
| `FILE_TOO_LARGE` | File exceeds 10MB limit | Compress or split the file |
| `PROCESSING_FAILED` | Document corruption or OCR failure | Try different file format or manual text input |
| `INSUFFICIENT_TEXT` | Extracted text too short | Ensure document has sufficient content |

### Analysis Errors

| Error Code | Cause | Solution |
|------------|-------|----------|
| `NLU_PROCESSING_FAILED` | NER model failure | Check model availability, retry request |
| `SEMANTIC_ANALYSIS_FAILED` | Embedding generation failure | Verify text content, check model status |
| `AI_FEEDBACK_FAILED` | Gemini API error | Check API key, verify connectivity |
| `MISSING_RESUME_DATA` | No resume provided | Provide either resume_id or resume_text |

### System Errors

| Error Code | Cause | Solution |
|------------|-------|----------|
| `DATABASE_ERROR` | Database connectivity issues | Check Supabase connection, verify credentials |
| `RATE_LIMIT_EXCEEDED` | Too many requests | Wait for rate limit reset, implement client throttling |
| `INTERNAL_ERROR` | Unexpected system error | Check logs, contact support if persistent |
| `SERVICE_UNAVAILABLE` | System overloaded | Retry with exponential backoff |

## Log Analysis

### Log Locations

- **Application Logs**: `./logs/app.log`
- **Container Logs**: `docker-compose logs smartresume-api`
- **Nginx Logs**: `./logs/nginx/access.log`, `./logs/nginx/error.log`

### Log Analysis Commands

```bash
# Find errors in the last hour
docker-compose logs smartresume-api --since 1h | grep -i error

# Analyze processing times
docker-compose logs smartresume-api | grep "processing_time" | awk '{print $NF}' | sort -n

# Find failed requests
docker-compose logs smartresume-api | grep -E "(failed|error)" | tail -20

# Monitor real-time logs
docker-compose logs -f smartresume-api | grep -E "(error|warning|failed)"

# Analyze user activity
docker-compose logs smartresume-api | grep "user_id" | cut -d'"' -f4 | sort | uniq -c

# Find slow requests (>10 seconds)
docker-compose logs smartresume-api | grep "processing_time" | awk '$NF > 10.0 {print}'
```

### Log Parsing Script

```python
# log_analyzer.py
import json
import re
from datetime import datetime, timedelta
from collections import defaultdict

class LogAnalyzer:
    def __init__(self, log_file):
        self.log_file = log_file
        
    def parse_logs(self, hours_back=24):
        """Parse logs from the last N hours"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
        
        stats = {
            'total_requests': 0,
            'errors': defaultdict(int),
            'processing_times': [],
            'user_activity': defaultdict(int),
            'endpoints': defaultdict(int)
        }
        
        with open(self.log_file, 'r') as f:
            for line in f:
                try:
                    log_entry = json.loads(line)
                    timestamp = datetime.fromisoformat(log_entry['timestamp'].replace('Z', '+00:00'))
                    
                    if timestamp < cutoff_time:
                        continue
                    
                    # Count requests
                    if 'request_id' in log_entry:
                        stats['total_requests'] += 1
                    
                    # Track errors
                    if log_entry.get('level') == 'ERROR':
                        error_type = log_entry.get('message', 'unknown_error')
                        stats['errors'][error_type] += 1
                    
                    # Track processing times
                    if 'processing_time' in log_entry:
                        stats['processing_times'].append(float(log_entry['processing_time']))
                    
                    # Track user activity
                    if 'user_id' in log_entry:
                        stats['user_activity'][log_entry['user_id']] += 1
                    
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue
        
        return stats
    
    def generate_report(self, stats):
        """Generate a summary report"""
        report = []
        report.append("=== Log Analysis Report ===")
        report.append(f"Total Requests: {stats['total_requests']}")
        
        if stats['processing_times']:
            avg_time = sum(stats['processing_times']) / len(stats['processing_times'])
            max_time = max(stats['processing_times'])
            report.append(f"Average Processing Time: {avg_time:.2f}s")
            report.append(f"Max Processing Time: {max_time:.2f}s")
        
        if stats['errors']:
            report.append("\nTop Errors:")
            for error, count in sorted(stats['errors'].items(), key=lambda x: x[1], reverse=True)[:5]:
                report.append(f"  {error}: {count}")
        
        report.append(f"\nActive Users: {len(stats['user_activity'])}")
        
        return "\n".join(report)

# Usage
analyzer = LogAnalyzer('./logs/app.log')
stats = analyzer.parse_logs(24)  # Last 24 hours
print(analyzer.generate_report(stats))
```

## Database Issues

### Connection Problems

**Symptoms:**
- Database connection timeouts
- Pool exhaustion errors
- Slow query performance

**Diagnostic Commands:**

```bash
# Test direct database connection
psql $DATABASE_URL -c "SELECT version();"

# Check connection pool status
docker-compose exec smartresume-api python -c "
import asyncio
from app.services.database_service import db_service
pool_info = asyncio.run(db_service.get_pool_info())
print('Active connections:', pool_info.get('active_connections'))
print('Idle connections:', pool_info.get('idle_connections'))
"

# Monitor slow queries
psql $DATABASE_URL -c "
SELECT query, mean_exec_time, calls 
FROM pg_stat_statements 
WHERE mean_exec_time > 1000 
ORDER BY mean_exec_time DESC 
LIMIT 10;
"
```

**Solutions:**

1. **Optimize Connection Pool:**
```python
# In app/config.py
DATABASE_POOL_SIZE = 20
DATABASE_MAX_OVERFLOW = 30
DATABASE_POOL_TIMEOUT = 30
DATABASE_POOL_RECYCLE = 3600
```

2. **Add Database Indexes:**
```sql
-- Add indexes for common queries
CREATE INDEX IF NOT EXISTS idx_analyses_user_id ON analyses(user_id);
CREATE INDEX IF NOT EXISTS idx_analyses_created_at ON analyses(created_at);
CREATE INDEX IF NOT EXISTS idx_resumes_user_id ON resumes(user_id);
```

### Data Integrity Issues

**Symptoms:**
- Foreign key constraint violations
- Orphaned records
- Inconsistent data

**Investigation:**

```sql
-- Check for orphaned analyses
SELECT COUNT(*) FROM analyses a 
LEFT JOIN resumes r ON a.resume_id = r.id 
WHERE a.resume_id IS NOT NULL AND r.id IS NULL;

-- Check for analyses without users
SELECT COUNT(*) FROM analyses a 
LEFT JOIN auth.users u ON a.user_id = u.id 
WHERE u.id IS NULL;

-- Verify data consistency
SELECT 
  COUNT(*) as total_analyses,
  COUNT(DISTINCT user_id) as unique_users,
  AVG(match_score) as avg_match_score
FROM analyses 
WHERE created_at > NOW() - INTERVAL '7 days';
```

## ML Model Issues

### Model Loading Failures

**Symptoms:**
- NER processing fails
- Embedding generation errors
- Model not found errors

**Diagnostic Steps:**

```bash
# Check model files
docker-compose exec smartresume-api ls -la /app/models/

# Test model loading manually
docker-compose exec smartresume-api python -c "
from transformers import AutoTokenizer, AutoModelForTokenClassification
from sentence_transformers import SentenceTransformer

try:
    # Test NER model
    tokenizer = AutoTokenizer.from_pretrained('yashpwr/resume-ner-bert-v2')
    model = AutoModelForTokenClassification.from_pretrained('yashpwr/resume-ner-bert-v2')
    print('NER model loaded successfully')
    
    # Test embedding model
    embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    print('Embedding model loaded successfully')
    
except Exception as e:
    print(f'Model loading failed: {e}')
"
```

**Solutions:**

1. **Clear Model Cache:**
```bash
# Remove cached models and reload
docker-compose exec smartresume-api rm -rf ~/.cache/huggingface/
docker-compose restart smartresume-api
```

2. **Manual Model Download:**
```bash
# Pre-download models
docker-compose exec smartresume-api python -c "
from transformers import AutoTokenizer, AutoModelForTokenClassification
from sentence_transformers import SentenceTransformer

# Download NER model
AutoTokenizer.from_pretrained('yashpwr/resume-ner-bert-v2')
AutoModelForTokenClassification.from_pretrained('yashpwr/resume-ner-bert-v2')

# Download embedding model
SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
print('Models downloaded successfully')
"
```

### Model Performance Issues

**Symptoms:**
- Slow inference times
- High memory usage
- Poor accuracy

**Optimization:**

```python
# Model optimization settings
import torch

# Enable optimizations if using GPU
if torch.cuda.is_available():
    torch.backends.cudnn.benchmark = True
    torch.backends.cudnn.deterministic = False

# Use half precision for inference (if supported)
model = model.half()  # For GPU inference

# Batch processing for multiple texts
def batch_process_texts(texts, batch_size=8):
    results = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        batch_results = model(batch)
        results.extend(batch_results)
    return results
```

## External API Issues

### Gemini API Problems

**Symptoms:**
- AI feedback generation fails
- API timeout errors
- Rate limit exceeded

**Diagnostic Commands:**

```bash
# Test API connectivity
curl -H "Authorization: Bearer $GOOGLE_GEMINI_API_KEY" \
     "https://generativelanguage.googleapis.com/v1/models"

# Test from application
docker-compose exec smartresume-api python -c "
import asyncio
from app.services.ai_service import ai_service

async def test_api():
    try:
        health = await ai_service.health_check()
        print('API Health:', health)
    except Exception as e:
        print('API Error:', str(e))

asyncio.run(test_api())
"
```

**Solutions:**

1. **Implement Retry Logic:**
```python
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def call_gemini_api(prompt):
    # API call implementation
    pass
```

2. **Circuit Breaker Pattern:**
```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
    
    async def call(self, func, *args, **kwargs):
        if self.state == 'OPEN':
            if time.time() - self.last_failure_time > self.timeout:
                self.state = 'HALF_OPEN'
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            self.failure_count = 0
            self.state = 'CLOSED'
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = 'OPEN'
            
            raise e
```

## Recovery Procedures

### Service Recovery

**Complete Service Restart:**
```bash
# Stop all services
docker-compose down

# Clear any stuck containers
docker system prune -f

# Restart services
docker-compose up -d --build

# Verify health
curl http://localhost:8000/api/v1/health
```

**Database Recovery:**
```bash
# Backup current database
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore from backup (if needed)
psql $DATABASE_URL < backup_YYYYMMDD_HHMMSS.sql

# Verify data integrity
psql $DATABASE_URL -c "SELECT COUNT(*) FROM analyses;"
```

**Model Cache Recovery:**
```bash
# Clear model cache
docker-compose exec smartresume-api rm -rf ~/.cache/huggingface/

# Restart to reload models
docker-compose restart smartresume-api

# Verify model loading
docker-compose logs smartresume-api | grep "model.*loaded"
```

### Disaster Recovery

**Full System Recovery:**

1. **Stop Services:**
```bash
docker-compose down
```

2. **Restore Configuration:**
```bash
# Restore from backup
tar -xzf backup_YYYYMMDD_HHMMSS.tar.gz
```

3. **Restore Database:**
```bash
# If using database backup
psql $DATABASE_URL < database_backup.sql
```

4. **Restart Services:**
```bash
docker-compose up -d --build
```

5. **Verify Recovery:**
```bash
# Run health checks
./health_check.sh

# Test critical functionality
curl -X POST -H "Authorization: Bearer $TEST_TOKEN" \
     -F "file=@test_resume.pdf" \
     http://localhost:8000/api/v1/upload
```

### Rollback Procedures

**Application Rollback:**
```bash
# Tag current version
docker tag smartresume-api:latest smartresume-api:backup-$(date +%Y%m%d)

# Pull previous version
docker pull smartresume-api:previous-version

# Update docker-compose.yml to use previous version
# Then restart
docker-compose up -d
```

**Database Rollback:**
```bash
# Create current backup
pg_dump $DATABASE_URL > current_backup.sql

# Restore previous backup
psql $DATABASE_URL < previous_backup.sql

# Verify rollback
psql $DATABASE_URL -c "SELECT version, created_at FROM schema_migrations ORDER BY created_at DESC LIMIT 5;"
```

## Support Escalation

### When to Escalate

- System down for >15 minutes
- Data corruption detected
- Security breach suspected
- Performance degradation >50%
- Multiple component failures

### Escalation Information to Collect

```bash
# System information
echo "=== System Information ===" > escalation_report.txt
date >> escalation_report.txt
docker-compose ps >> escalation_report.txt
docker stats --no-stream >> escalation_report.txt

# Recent logs
echo "=== Recent Errors ===" >> escalation_report.txt
docker-compose logs smartresume-api --tail=100 | grep -i error >> escalation_report.txt

# Health status
echo "=== Health Status ===" >> escalation_report.txt
curl -s http://localhost:8000/api/v1/health/detailed >> escalation_report.txt

# Configuration (sanitized)
echo "=== Configuration ===" >> escalation_report.txt
docker-compose exec smartresume-api env | grep -v -E "(SECRET|KEY|PASSWORD)" >> escalation_report.txt
```

### Contact Information

- **Emergency**: [Emergency contact]
- **Technical Support**: support@smartresume-ai.com
- **DevOps Team**: devops@smartresume-ai.com
- **Status Page**: https://status.smartresume-ai.com

Remember to include the escalation report and any relevant error messages when contacting support.