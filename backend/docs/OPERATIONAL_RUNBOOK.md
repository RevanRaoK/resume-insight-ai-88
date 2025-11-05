# SmartResume AI Resume Analyzer - Operational Runbook

## Table of Contents

1. [Daily Operations](#daily-operations)
2. [Monitoring and Alerting](#monitoring-and-alerting)
3. [Backup Procedures](#backup-procedures)
4. [Maintenance Tasks](#maintenance-tasks)
5. [Incident Response](#incident-response)
6. [Performance Monitoring](#performance-monitoring)
7. [Security Operations](#security-operations)
8. [Capacity Planning](#capacity-planning)
9. [Emergency Procedures](#emergency-procedures)
10. [Runbook Checklists](#runbook-checklists)

## Daily Operations

### Morning Health Check (Start of Business Day)

**Frequency:** Daily at 8:00 AM

**Checklist:**
- [ ] Verify all services are running
- [ ] Check system health endpoints
- [ ] Review overnight error logs
- [ ] Validate database connectivity
- [ ] Confirm ML models are loaded
- [ ] Test external API connectivity
- [ ] Review resource utilization
- [ ] Check backup completion status

**Commands:**
```bash
# Quick health check
curl -s http://localhost:8000/api/v1/health | jq '.status'

# Detailed system status
curl -s http://localhost:8000/api/v1/health/detailed | jq '.checks'

# Check container status
docker-compose ps

# Review overnight errors
docker-compose logs smartresume-api --since 24h | grep -i error | wc -l

# Check resource usage
docker stats --no-stream | grep smartresume
```

**Expected Results:**
- All health checks return "healthy"
- No critical errors in logs
- Resource usage within normal ranges (<80% CPU, <75% memory)
- Response times <2 seconds for health checks

**Escalation:** If any check fails, follow [Incident Response](#incident-response) procedures.

### End of Day Review

**Frequency:** Daily at 6:00 PM

**Checklist:**
- [ ] Review daily metrics and performance
- [ ] Check error rates and patterns
- [ ] Validate backup completion
- [ ] Review user activity and usage patterns
- [ ] Check for any pending alerts
- [ ] Verify log rotation is working
- [ ] Update operational notes

**Commands:**
```bash
# Daily metrics summary
docker-compose exec smartresume-api python -c "
import asyncio
from datetime import datetime, timedelta
from app.utils.metrics import get_daily_metrics

metrics = asyncio.run(get_daily_metrics())
print(f'Total requests: {metrics.get(\"total_requests\", 0)}')
print(f'Error rate: {metrics.get(\"error_rate\", 0):.2%}')
print(f'Avg response time: {metrics.get(\"avg_response_time\", 0):.2f}s')
print(f'Active users: {metrics.get(\"active_users\", 0)}')
"

# Check backup status
ls -la ./backups/ | tail -5

# Review error patterns
docker-compose logs smartresume-api --since 24h | grep -i error | cut -d' ' -f5- | sort | uniq -c | sort -nr
```

## Monitoring and Alerting

### Key Metrics to Monitor

**System Health Metrics:**
- Service availability (uptime)
- Response time percentiles (P50, P95, P99)
- Error rates by endpoint
- Database connection pool status
- ML model inference times

**Business Metrics:**
- Daily active users
- Resume uploads per day
- Analysis requests per day
- Success/failure rates
- User retention metrics

**Infrastructure Metrics:**
- CPU utilization
- Memory usage
- Disk I/O
- Network latency
- Container health

### Alert Thresholds

| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| Service Availability | <99% | <95% | Immediate investigation |
| Response Time P95 | >15s | >30s | Performance investigation |
| Error Rate | >5% | >10% | Incident response |
| CPU Usage | >80% | >90% | Scale resources |
| Memory Usage | >75% | >85% | Memory investigation |
| Database Connections | >80% pool | >95% pool | Connection tuning |
| Disk Usage | >80% | >90% | Cleanup/expansion |

### Monitoring Setup

**Prometheus Configuration:**
```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'smartresume-api'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/api/v1/monitoring/metrics'
    scrape_interval: 30s
```

**Grafana Dashboard Queries:**
```promql
# Request rate
rate(http_requests_total[5m])

# Error rate
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])

# Response time percentiles
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Active users
increase(user_sessions_total[1h])
```

**Alert Rules:**
```yaml
# alerting_rules.yml
groups:
  - name: smartresume_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }}"
      
      - alert: HighResponseTime
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 30
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High response time detected"
          description: "95th percentile response time is {{ $value }}s"
      
      - alert: ServiceDown
        expr: up{job="smartresume-api"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "SmartResume API is down"
          description: "The SmartResume API service is not responding"
```

## Backup Procedures

### Database Backup

**Frequency:** Daily at 2:00 AM

**Automated Backup Script:**
```bash
#!/bin/bash
# backup_database.sh

set -e

BACKUP_DIR="/backups/database"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="smartresume_backup_${DATE}.sql"
RETENTION_DAYS=30

# Create backup directory
mkdir -p $BACKUP_DIR

# Create database backup
echo "Starting database backup at $(date)"
pg_dump $DATABASE_URL > "${BACKUP_DIR}/${BACKUP_FILE}"

# Compress backup
gzip "${BACKUP_DIR}/${BACKUP_FILE}"

# Verify backup
if [ -f "${BACKUP_DIR}/${BACKUP_FILE}.gz" ]; then
    echo "Backup completed successfully: ${BACKUP_FILE}.gz"
    
    # Test backup integrity
    gunzip -t "${BACKUP_DIR}/${BACKUP_FILE}.gz"
    echo "Backup integrity verified"
else
    echo "ERROR: Backup failed"
    exit 1
fi

# Cleanup old backups
find $BACKUP_DIR -name "smartresume_backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete
echo "Cleaned up backups older than $RETENTION_DAYS days"

# Upload to cloud storage (optional)
# aws s3 cp "${BACKUP_DIR}/${BACKUP_FILE}.gz" s3://your-backup-bucket/database/

echo "Database backup completed at $(date)"
```

**Backup Verification:**
```bash
# Weekly backup verification (Sundays at 3:00 AM)
#!/bin/bash
# verify_backup.sh

LATEST_BACKUP=$(ls -t /backups/database/smartresume_backup_*.sql.gz | head -1)

if [ -z "$LATEST_BACKUP" ]; then
    echo "ERROR: No backup files found"
    exit 1
fi

echo "Verifying backup: $LATEST_BACKUP"

# Test backup integrity
gunzip -t "$LATEST_BACKUP"
if [ $? -eq 0 ]; then
    echo "Backup integrity check passed"
else
    echo "ERROR: Backup integrity check failed"
    exit 1
fi

# Test restore to temporary database (optional)
# This requires a test database environment
echo "Backup verification completed successfully"
```

### Application Configuration Backup

**Frequency:** Daily at 2:30 AM

```bash
#!/bin/bash
# backup_config.sh

BACKUP_DIR="/backups/config"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="config_backup_${DATE}.tar.gz"

mkdir -p $BACKUP_DIR

# Backup configuration files (excluding secrets)
tar -czf "${BACKUP_DIR}/${BACKUP_FILE}" \
    --exclude='.env' \
    --exclude='*.key' \
    --exclude='*.pem' \
    docker-compose.yml \
    docker-compose.prod.yml \
    nginx/ \
    monitoring/ \
    docs/ \
    README.md \
    DEPLOYMENT.md

echo "Configuration backup completed: ${BACKUP_FILE}"

# Cleanup old config backups (keep 14 days)
find $BACKUP_DIR -name "config_backup_*.tar.gz" -mtime +14 -delete
```

### Log Backup and Rotation

**Frequency:** Daily at 1:00 AM

```bash
#!/bin/bash
# rotate_logs.sh

LOG_DIR="./logs"
ARCHIVE_DIR="/backups/logs"
DATE=$(date +%Y%m%d)

mkdir -p $ARCHIVE_DIR

# Rotate application logs
if [ -f "${LOG_DIR}/app.log" ]; then
    cp "${LOG_DIR}/app.log" "${ARCHIVE_DIR}/app_${DATE}.log"
    > "${LOG_DIR}/app.log"  # Truncate current log
fi

# Rotate nginx logs
if [ -f "${LOG_DIR}/nginx/access.log" ]; then
    cp "${LOG_DIR}/nginx/access.log" "${ARCHIVE_DIR}/nginx_access_${DATE}.log"
    > "${LOG_DIR}/nginx/access.log"
fi

if [ -f "${LOG_DIR}/nginx/error.log" ]; then
    cp "${LOG_DIR}/nginx/error.log" "${ARCHIVE_DIR}/nginx_error_${DATE}.log"
    > "${LOG_DIR}/nginx/error.log"
fi

# Compress archived logs
gzip "${ARCHIVE_DIR}"/*_${DATE}.log

# Cleanup old log archives (keep 90 days)
find $ARCHIVE_DIR -name "*.log.gz" -mtime +90 -delete

# Restart nginx to reopen log files
docker-compose exec nginx nginx -s reopen

echo "Log rotation completed"
```

## Maintenance Tasks

### Weekly Maintenance (Sundays at 4:00 AM)

**System Cleanup:**
```bash
#!/bin/bash
# weekly_maintenance.sh

echo "Starting weekly maintenance at $(date)"

# Clean up Docker resources
docker system prune -f
docker volume prune -f

# Clean up temporary files
find /tmp -name "smartresume_*" -mtime +7 -delete

# Update system packages (if needed)
# apt-get update && apt-get upgrade -y

# Restart services for fresh start
docker-compose restart

# Verify services after restart
sleep 30
curl -f http://localhost:8000/api/v1/health || echo "WARNING: Health check failed after restart"

echo "Weekly maintenance completed at $(date)"
```

**Database Maintenance:**
```bash
#!/bin/bash
# database_maintenance.sh

echo "Starting database maintenance"

# Update table statistics
psql $DATABASE_URL -c "ANALYZE;"

# Vacuum tables
psql $DATABASE_URL -c "VACUUM ANALYZE analyses;"
psql $DATABASE_URL -c "VACUUM ANALYZE resumes;"

# Check for unused indexes
psql $DATABASE_URL -c "
SELECT schemaname, tablename, attname, n_distinct, correlation 
FROM pg_stats 
WHERE schemaname = 'public' 
ORDER BY n_distinct DESC;
"

# Check table sizes
psql $DATABASE_URL -c "
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname = 'public' 
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"

echo "Database maintenance completed"
```

### Monthly Maintenance (First Sunday of month)

**Performance Review:**
```bash
#!/bin/bash
# monthly_performance_review.sh

echo "=== Monthly Performance Review ===" > monthly_report.txt
echo "Date: $(date)" >> monthly_report.txt
echo >> monthly_report.txt

# System uptime
echo "System Uptime:" >> monthly_report.txt
docker-compose exec smartresume-api uptime >> monthly_report.txt
echo >> monthly_report.txt

# Resource usage trends
echo "Resource Usage Summary:" >> monthly_report.txt
docker stats --no-stream >> monthly_report.txt
echo >> monthly_report.txt

# Database size growth
echo "Database Size:" >> monthly_report.txt
psql $DATABASE_URL -c "
SELECT 
    pg_size_pretty(pg_database_size(current_database())) as database_size,
    (SELECT COUNT(*) FROM analyses) as total_analyses,
    (SELECT COUNT(*) FROM resumes) as total_resumes;
" >> monthly_report.txt
echo >> monthly_report.txt

# Top error patterns
echo "Top Error Patterns (Last 30 days):" >> monthly_report.txt
docker-compose logs smartresume-api --since 720h | grep -i error | cut -d' ' -f5- | sort | uniq -c | sort -nr | head -10 >> monthly_report.txt

echo "Monthly performance review completed"
```

**Security Audit:**
```bash
#!/bin/bash
# security_audit.sh

echo "=== Monthly Security Audit ===" > security_audit.txt
echo "Date: $(date)" >> security_audit.txt
echo >> security_audit.txt

# Check for security updates
echo "Security Updates Available:" >> security_audit.txt
apt list --upgradable 2>/dev/null | grep -i security >> security_audit.txt
echo >> security_audit.txt

# Review access logs for suspicious activity
echo "Suspicious Access Patterns:" >> security_audit.txt
grep -E "(40[1-4]|50[0-9])" ./logs/nginx/access.log | tail -20 >> security_audit.txt
echo >> security_audit.txt

# Check SSL certificate expiry
echo "SSL Certificate Status:" >> security_audit.txt
openssl x509 -in nginx/ssl/cert.pem -noout -dates 2>/dev/null >> security_audit.txt || echo "No SSL certificate found" >> security_audit.txt
echo >> security_audit.txt

# Review user activity
echo "User Activity Summary:" >> security_audit.txt
docker-compose logs smartresume-api --since 720h | grep "user_id" | cut -d'"' -f4 | sort | uniq -c | sort -nr | head -10 >> security_audit.txt

echo "Security audit completed"
```

## Incident Response

### Incident Classification

**Severity Levels:**

| Level | Description | Response Time | Examples |
|-------|-------------|---------------|----------|
| P1 - Critical | Service completely down | 15 minutes | Complete outage, data loss |
| P2 - High | Major functionality impacted | 1 hour | Analysis failures, slow performance |
| P3 - Medium | Minor functionality impacted | 4 hours | Non-critical feature issues |
| P4 - Low | Cosmetic or documentation issues | 24 hours | UI glitches, typos |

### Incident Response Procedures

**P1 - Critical Incident Response:**

1. **Immediate Actions (0-15 minutes):**
   ```bash
   # Check service status
   curl -f http://localhost:8000/api/v1/health
   
   # Check container status
   docker-compose ps
   
   # Check recent logs for errors
   docker-compose logs smartresume-api --tail=50 | grep -i error
   
   # Check system resources
   docker stats --no-stream
   ```

2. **Assessment (15-30 minutes):**
   - Determine root cause
   - Estimate impact and affected users
   - Decide on immediate mitigation steps

3. **Mitigation (30-60 minutes):**
   ```bash
   # Quick restart if needed
   docker-compose restart smartresume-api
   
   # Scale resources if needed
   docker-compose up -d --scale smartresume-api=2
   
   # Rollback if recent deployment
   docker-compose down
   docker pull smartresume-api:previous-stable
   docker-compose up -d
   ```

4. **Communication:**
   - Update status page
   - Notify stakeholders
   - Provide regular updates

**P2 - High Priority Response:**

1. **Investigation (0-1 hour):**
   ```bash
   # Detailed health check
   curl -s http://localhost:8000/api/v1/health/detailed | jq '.'
   
   # Check specific components
   curl -s http://localhost:8000/api/v1/health/database
   curl -s http://localhost:8000/api/v1/health/models
   curl -s http://localhost:8000/api/v1/health/apis
   
   # Analyze performance metrics
   docker-compose exec smartresume-api python -c "
   from app.utils.metrics import get_current_metrics
   print(get_current_metrics())
   "
   ```

2. **Targeted Fix:**
   - Address specific component issues
   - Apply configuration changes
   - Restart affected services only

### Incident Documentation Template

```markdown
# Incident Report: [INCIDENT-ID]

## Summary
- **Date/Time**: [Start time] - [End time]
- **Severity**: P[1-4]
- **Status**: [Open/Resolved/Closed]
- **Affected Services**: [List services]
- **Impact**: [Description of user impact]

## Timeline
- **[Time]**: Issue first detected
- **[Time]**: Investigation started
- **[Time]**: Root cause identified
- **[Time]**: Mitigation applied
- **[Time]**: Service restored
- **[Time]**: Incident closed

## Root Cause
[Detailed description of what caused the incident]

## Resolution
[Description of how the incident was resolved]

## Action Items
- [ ] [Action item 1] - [Owner] - [Due date]
- [ ] [Action item 2] - [Owner] - [Due date]

## Lessons Learned
[What we learned and how to prevent similar incidents]
```

## Performance Monitoring

### Key Performance Indicators (KPIs)

**Service Level Objectives (SLOs):**
- 99.9% uptime (8.76 hours downtime per year)
- 95% of requests complete within 30 seconds
- 99% of requests complete within 60 seconds
- Error rate <1% for all endpoints

**Performance Baselines:**
- Average analysis time: 8-15 seconds
- File upload processing: 2-5 seconds
- Database query response: <100ms
- Health check response: <500ms

### Performance Monitoring Script

```python
#!/usr/bin/env python3
# performance_monitor.py

import asyncio
import aiohttp
import time
import json
from datetime import datetime, timedelta
import statistics

class PerformanceMonitor:
    def __init__(self, base_url):
        self.base_url = base_url
        self.metrics = {
            'response_times': [],
            'error_count': 0,
            'total_requests': 0,
            'start_time': time.time()
        }
    
    async def test_endpoint(self, session, endpoint, method='GET', **kwargs):
        """Test a single endpoint and record metrics"""
        start_time = time.time()
        
        try:
            async with session.request(method, f"{self.base_url}{endpoint}", **kwargs) as response:
                response_time = time.time() - start_time
                self.metrics['response_times'].append(response_time)
                self.metrics['total_requests'] += 1
                
                if response.status >= 400:
                    self.metrics['error_count'] += 1
                
                return {
                    'endpoint': endpoint,
                    'status': response.status,
                    'response_time': response_time,
                    'success': response.status < 400
                }
        except Exception as e:
            self.metrics['error_count'] += 1
            self.metrics['total_requests'] += 1
            return {
                'endpoint': endpoint,
                'status': 0,
                'response_time': time.time() - start_time,
                'success': False,
                'error': str(e)
            }
    
    async def run_performance_test(self, duration_minutes=10):
        """Run continuous performance monitoring"""
        end_time = time.time() + (duration_minutes * 60)
        
        async with aiohttp.ClientSession() as session:
            while time.time() < end_time:
                # Test various endpoints
                tasks = [
                    self.test_endpoint(session, '/api/v1/health'),
                    self.test_endpoint(session, '/api/v1/health/detailed'),
                    self.test_endpoint(session, '/api/v1/health/database'),
                ]
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Log results
                for result in results:
                    if isinstance(result, dict):
                        print(f"[{datetime.now()}] {result['endpoint']}: {result['status']} ({result['response_time']:.3f}s)")
                
                await asyncio.sleep(30)  # Test every 30 seconds
        
        return self.generate_report()
    
    def generate_report(self):
        """Generate performance report"""
        if not self.metrics['response_times']:
            return "No data collected"
        
        response_times = self.metrics['response_times']
        total_time = time.time() - self.metrics['start_time']
        
        report = {
            'duration_minutes': total_time / 60,
            'total_requests': self.metrics['total_requests'],
            'error_count': self.metrics['error_count'],
            'error_rate': self.metrics['error_count'] / self.metrics['total_requests'],
            'avg_response_time': statistics.mean(response_times),
            'median_response_time': statistics.median(response_times),
            'p95_response_time': statistics.quantiles(response_times, n=20)[18] if len(response_times) > 20 else max(response_times),
            'min_response_time': min(response_times),
            'max_response_time': max(response_times),
            'requests_per_minute': self.metrics['total_requests'] / (total_time / 60)
        }
        
        return report

# Usage
if __name__ == "__main__":
    monitor = PerformanceMonitor("http://localhost:8000")
    report = asyncio.run(monitor.run_performance_test(10))  # 10 minute test
    print(json.dumps(report, indent=2))
```

## Security Operations

### Security Monitoring

**Daily Security Checks:**
```bash
#!/bin/bash
# daily_security_check.sh

echo "=== Daily Security Check ===" > security_check.txt
echo "Date: $(date)" >> security_check.txt
echo >> security_check.txt

# Check for failed authentication attempts
echo "Failed Authentication Attempts (Last 24h):" >> security_check.txt
docker-compose logs smartresume-api --since 24h | grep -i "authentication.*failed" | wc -l >> security_check.txt
echo >> security_check.txt

# Check for suspicious IP addresses
echo "Top IP Addresses (Last 24h):" >> security_check.txt
grep -o '[0-9]\{1,3\}\.[0-9]\{1,3\}\.[0-9]\{1,3\}\.[0-9]\{1,3\}' ./logs/nginx/access.log | sort | uniq -c | sort -nr | head -10 >> security_check.txt
echo >> security_check.txt

# Check for rate limit violations
echo "Rate Limit Violations:" >> security_check.txt
docker-compose logs smartresume-api --since 24h | grep -i "rate.*limit" | wc -l >> security_check.txt
echo >> security_check.txt

# Check file upload attempts
echo "File Upload Activity:" >> security_check.txt
docker-compose logs smartresume-api --since 24h | grep "resume_upload_started" | wc -l >> security_check.txt

echo "Security check completed"
```

### SSL Certificate Management

**Certificate Renewal (Monthly):**
```bash
#!/bin/bash
# renew_ssl_cert.sh

# Check certificate expiry
CERT_FILE="nginx/ssl/cert.pem"
DAYS_UNTIL_EXPIRY=$(openssl x509 -in $CERT_FILE -noout -checkend $((30*24*3600)) && echo "OK" || echo "EXPIRING")

if [ "$DAYS_UNTIL_EXPIRY" = "EXPIRING" ]; then
    echo "Certificate expiring soon, renewing..."
    
    # Renew Let's Encrypt certificate
    certbot renew --quiet
    
    # Copy new certificates
    cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem nginx/ssl/cert.pem
    cp /etc/letsencrypt/live/yourdomain.com/privkey.pem nginx/ssl/key.pem
    
    # Reload nginx
    docker-compose exec nginx nginx -s reload
    
    echo "Certificate renewed successfully"
else
    echo "Certificate is still valid"
fi
```

## Capacity Planning

### Resource Monitoring

**Weekly Capacity Report:**
```bash
#!/bin/bash
# capacity_report.sh

echo "=== Weekly Capacity Report ===" > capacity_report.txt
echo "Date: $(date)" >> capacity_report.txt
echo >> capacity_report.txt

# CPU usage trends
echo "CPU Usage (Last 7 days average):" >> capacity_report.txt
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}" | grep smartresume >> capacity_report.txt
echo >> capacity_report.txt

# Memory usage trends
echo "Memory Usage (Last 7 days average):" >> capacity_report.txt
docker stats --no-stream --format "table {{.Container}}\t{{.MemUsage}}\t{{.MemPerc}}" | grep smartresume >> capacity_report.txt
echo >> capacity_report.txt

# Database growth
echo "Database Growth:" >> capacity_report.txt
psql $DATABASE_URL -c "
SELECT 
    'analyses' as table_name,
    COUNT(*) as row_count,
    pg_size_pretty(pg_total_relation_size('analyses')) as size
FROM analyses
UNION ALL
SELECT 
    'resumes' as table_name,
    COUNT(*) as row_count,
    pg_size_pretty(pg_total_relation_size('resumes')) as size
FROM resumes;
" >> capacity_report.txt
echo >> capacity_report.txt

# Request volume trends
echo "Request Volume (Last 7 days):" >> capacity_report.txt
docker-compose logs smartresume-api --since 168h | grep "request_id" | wc -l >> capacity_report.txt

echo "Capacity report completed"
```

### Scaling Triggers

**Horizontal Scaling Triggers:**
- CPU usage >80% for 10 minutes
- Memory usage >75% for 10 minutes
- Request queue depth >50
- Response time P95 >20 seconds

**Vertical Scaling Triggers:**
- Consistent high resource usage
- ML model memory requirements increase
- Database connection pool exhaustion

**Scaling Commands:**
```bash
# Horizontal scaling (add more containers)
docker-compose up -d --scale smartresume-api=3

# Vertical scaling (increase resources)
# Update docker-compose.yml with higher resource limits
docker-compose down
docker-compose up -d
```

## Emergency Procedures

### Complete System Failure

**Emergency Response Checklist:**

1. **Immediate Assessment (0-5 minutes):**
   - [ ] Check if issue is infrastructure-wide
   - [ ] Verify external dependencies (Supabase, Gemini API)
   - [ ] Check system resources and disk space
   - [ ] Review recent changes or deployments

2. **Quick Recovery Attempts (5-15 minutes):**
   ```bash
   # Try service restart
   docker-compose restart
   
   # If restart fails, try full rebuild
   docker-compose down
   docker-compose up -d --build
   
   # Check for resource issues
   df -h  # Check disk space
   free -h  # Check memory
   ```

3. **Rollback Procedures (15-30 minutes):**
   ```bash
   # Rollback to last known good version
   docker-compose down
   git checkout last-stable-tag
   docker-compose up -d
   ```

4. **Communication (Immediate):**
   - Update status page
   - Notify key stakeholders
   - Prepare user communication

### Data Recovery Procedures

**Database Recovery:**
```bash
#!/bin/bash
# emergency_db_recovery.sh

echo "Starting emergency database recovery"

# Stop application to prevent further writes
docker-compose stop smartresume-api

# Create current state backup (if possible)
pg_dump $DATABASE_URL > emergency_backup_$(date +%Y%m%d_%H%M%S).sql 2>/dev/null || echo "Current backup failed"

# Find latest good backup
LATEST_BACKUP=$(ls -t /backups/database/smartresume_backup_*.sql.gz | head -1)

if [ -z "$LATEST_BACKUP" ]; then
    echo "ERROR: No backup files found"
    exit 1
fi

echo "Restoring from: $LATEST_BACKUP"

# Restore database
gunzip -c "$LATEST_BACKUP" | psql $DATABASE_URL

# Verify restoration
psql $DATABASE_URL -c "SELECT COUNT(*) FROM analyses;" > /dev/null

if [ $? -eq 0 ]; then
    echo "Database restoration successful"
    
    # Restart application
    docker-compose start smartresume-api
    
    # Verify application health
    sleep 30
    curl -f http://localhost:8000/api/v1/health || echo "WARNING: Health check failed"
else
    echo "ERROR: Database restoration failed"
    exit 1
fi
```

## Runbook Checklists

### New Deployment Checklist

- [ ] Review deployment plan and rollback procedures
- [ ] Backup current database and configuration
- [ ] Test deployment in staging environment
- [ ] Schedule maintenance window
- [ ] Deploy new version
- [ ] Run smoke tests
- [ ] Monitor for 30 minutes post-deployment
- [ ] Update documentation if needed
- [ ] Notify stakeholders of completion

### Incident Response Checklist

- [ ] Acknowledge incident within SLA timeframe
- [ ] Assess severity and impact
- [ ] Form incident response team if needed
- [ ] Begin investigation and mitigation
- [ ] Communicate status to stakeholders
- [ ] Document timeline and actions taken
- [ ] Implement fix and verify resolution
- [ ] Conduct post-incident review
- [ ] Update runbooks based on lessons learned

### Monthly Maintenance Checklist

- [ ] Review and update backup procedures
- [ ] Perform security audit
- [ ] Review capacity and performance trends
- [ ] Update system documentation
- [ ] Review and test disaster recovery procedures
- [ ] Update monitoring and alerting rules
- [ ] Review access controls and permissions
- [ ] Plan for upcoming capacity needs

### Quarterly Review Checklist

- [ ] Review SLA performance and adjust targets
- [ ] Assess infrastructure costs and optimization opportunities
- [ ] Review security policies and procedures
- [ ] Update disaster recovery and business continuity plans
- [ ] Conduct tabletop exercises for major incident scenarios
- [ ] Review and update operational procedures
- [ ] Plan infrastructure upgrades and improvements
- [ ] Review team training and knowledge gaps

---

**Document Version:** 1.0  
**Last Updated:** November 4, 2023  
**Next Review:** December 4, 2023  
**Owner:** DevOps Team  
**Approved By:** Technical Lead