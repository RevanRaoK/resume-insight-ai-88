# Performance Tests for SmartResume AI Resume Analyzer

This directory contains comprehensive performance tests designed to validate system performance under various load conditions and ensure compliance with the 30-second response time requirement for 95% of requests.

## Requirements Tested

- **5.5**: System shall handle at least 50 concurrent users without performance degradation
- **6.6**: System shall complete end-to-end analysis in under 30 seconds for 95% of requests

## Test Structure

### Core Test Files

- `locustfile.py` - Main Locust test file with realistic user simulation
- `test_scenarios.py` - Specialized test scenarios with different user types
- `config.py` - Configuration settings for different test types
- `run_tests.py` - Test runner script with multiple test configurations
- `validate_requirements.py` - Requirements validation script

### Test Types

1. **Load Test** - Normal expected load (50 users, 10 minutes)
2. **Stress Test** - Beyond normal capacity (100 users, 5 minutes)
3. **Spike Test** - Sudden load increase (200 users, 2 minutes)
4. **Endurance Test** - Sustained load (30 users, 30 minutes)
5. **Scenario Test** - Specialized user behavior patterns

## Prerequisites

### Install Dependencies

```bash
# Install performance testing dependencies
pip install locust pandas requests

# Or install from requirements.txt (already includes locust)
pip install -r requirements.txt
```

### Start the Application

Ensure the SmartResume backend is running:

```bash
cd backend
python -m app.main
```

The application should be accessible at `http://localhost:8000`

## Running Performance Tests

### Quick Requirements Validation

To quickly validate that the system meets performance requirements:

```bash
cd backend/tests/performance
python validate_requirements.py
```

This runs a comprehensive 10-minute test with 50 concurrent users and validates all requirements.

### Individual Test Types

Run specific test types using the test runner:

```bash
# Load test (recommended for regular validation)
python run_tests.py --test-type load

# Stress test (find system limits)
python run_tests.py --test-type stress

# Spike test (sudden load increase)
python run_tests.py --test-type spike

# Scenario-based tests (different user patterns)
python run_tests.py --test-type scenario

# Run all tests
python run_tests.py --test-type all
```

### Custom Configuration

Override default settings:

```bash
# Custom user count and duration
python run_tests.py --test-type load --users 75 --spawn-rate 10 --run-time 15m

# Test against different host
python run_tests.py --host http://staging.example.com --test-type load
```

### Direct Locust Usage

For more control, run Locust directly:

```bash
# Basic load test
locust -f locustfile.py --host http://localhost:8000 --users 50 --spawn-rate 5 --run-time 10m --headless

# With web UI for real-time monitoring
locust -f locustfile.py --host http://localhost:8000

# Scenario-based tests
locust -f test_scenarios.py --host http://localhost:8000 --users 50 --spawn-rate 5 --run-time 5m --headless
```

## Test Results

### Output Files

Test results are saved in the `results/` directory:

- `*_report.html` - Detailed HTML reports with charts and statistics
- `*_stats.csv` - Raw statistics in CSV format
- `*_failures.csv` - Failure details (if any)
- `*_results.json` - Structured test results and configuration
- `validation_report.json` - Requirements validation results

### Key Metrics

The tests track and validate:

1. **Response Time Percentiles**
   - P50 (median)
   - P95 (95th percentile) - **Must be ≤ 30 seconds**
   - P99 (99th percentile)

2. **Success Rates**
   - Overall success rate - **Must be ≥ 95%**
   - Endpoint-specific success rates

3. **Throughput**
   - Requests per second
   - Concurrent user handling

4. **Endpoint-Specific Performance**
   - `/api/v1/analyze` - Core analysis endpoint (30s requirement)
   - `/api/v1/upload` - File upload performance
   - `/api/v1/health` - Health check responsiveness

## Test Scenarios

### User Types in Scenario Tests

1. **AnalysisHeavyUser** (Weight: 3)
   - Focuses on resume analysis requests
   - Tests core 30-second requirement
   - Simulates job seekers performing analyses

2. **UploadHeavyUser** (Weight: 2)
   - Focuses on document upload functionality
   - Tests file processing performance
   - Simulates users uploading resumes

3. **HealthCheckUser** (Weight: 1)
   - Monitors system health endpoints
   - Tests monitoring infrastructure
   - Simulates monitoring systems

4. **BrowsingUser** (Weight: 2)
   - Focuses on data retrieval operations
   - Tests history and resume listing
   - Simulates users browsing past analyses

### Realistic Test Data

Tests use realistic data including:
- Multiple job description templates
- Sample resume content
- Various file formats (PDF, DOCX, TXT)
- Authentic user interaction patterns

## Performance Thresholds

### Core Requirements

- **30-Second Rule**: 95% of analysis requests must complete within 30 seconds
- **Concurrent Users**: Handle 50+ concurrent users without degradation
- **Success Rate**: Maintain 95%+ success rate under load

### Endpoint-Specific Thresholds

| Endpoint | P95 Response Time | Success Rate |
|----------|------------------|--------------|
| `/api/v1/health` | 1 second | 99% |
| `/api/v1/health/detailed` | 5 seconds | 95% |
| `/api/v1/upload` | 15 seconds | 90% |
| `/api/v1/analyze` | **30 seconds** | **95%** |
| `/api/v1/resumes` | 3 seconds | 98% |
| `/api/v1/analyses` | 5 seconds | 98% |

## Troubleshooting

### Common Issues

1. **Connection Refused**
   ```
   Error: Connection refused
   ```
   - Ensure the backend application is running
   - Check the host URL and port

2. **High Response Times**
   ```
   P95 response time exceeds threshold
   ```
   - Check system resources (CPU, memory)
   - Verify ML models are loaded properly
   - Check database connection performance

3. **Authentication Errors**
   ```
   401 Unauthorized responses
   ```
   - Tests use mock authentication tokens
   - Ensure auth middleware handles test tokens properly

### Performance Optimization

If tests fail performance requirements:

1. **Check System Resources**
   ```bash
   # Monitor during tests
   htop
   nvidia-smi  # If using GPU for ML models
   ```

2. **Database Performance**
   - Check connection pool settings
   - Monitor query performance
   - Verify indexes are in place

3. **ML Model Performance**
   - Ensure models are cached in memory
   - Check GPU utilization if available
   - Monitor model inference times

4. **Application Configuration**
   - Verify async/await usage
   - Check for blocking operations
   - Monitor garbage collection

## Continuous Integration

### GitHub Actions Example

```yaml
name: Performance Tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  performance:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.9
    
    - name: Install dependencies
      run: |
        pip install -r backend/requirements.txt
    
    - name: Start application
      run: |
        cd backend
        python -m app.main &
        sleep 30  # Wait for startup
    
    - name: Run performance validation
      run: |
        cd backend/tests/performance
        python validate_requirements.py
```

## Reporting

### Automated Reports

The validation script generates:
- Console output with pass/fail status
- JSON report with detailed metrics
- HTML reports with visualizations
- CSV data for further analysis

### Manual Analysis

For deeper analysis:
1. Open HTML reports in browser
2. Import CSV data into spreadsheet tools
3. Use JSON results for custom analysis
4. Monitor real-time metrics during tests

## Best Practices

1. **Run tests regularly** - Include in CI/CD pipeline
2. **Monitor trends** - Track performance over time
3. **Test realistic scenarios** - Use production-like data
4. **Validate requirements** - Always check against 30-second rule
5. **Document results** - Keep performance baselines
6. **Optimize iteratively** - Address bottlenecks systematically