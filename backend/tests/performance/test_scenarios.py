"""
Specific performance test scenarios for SmartResume AI Resume Analyzer

This module contains specialized test scenarios that focus on different
aspects of system performance under various load conditions.

Requirements: 5.5, 6.6
"""
import time
import json
import random
from typing import Dict, Any, List
from locust import HttpUser, task, between, events
from locust.exception import StopUser

from config import ENDPOINT_THRESHOLDS, validate_performance_requirements

class AnalysisHeavyUser(HttpUser):
    """
    User focused on analysis endpoints - tests the core functionality
    that must meet the 30-second response time requirement
    """
    
    wait_time = between(2, 5)
    weight = 3  # Higher weight for more analysis-focused users
    
    def on_start(self):
        """Initialize with mock authentication"""
        self.client.headers.update({
            "Authorization": f"Bearer mock_token_{random.randint(1000, 9999)}",
            "Content-Type": "application/json"
        })
    
    @task(10)
    def analyze_software_engineer_resume(self):
        """Test analysis for software engineer positions"""
        payload = {
            "job_description": """
            Senior Software Engineer position requiring Python, JavaScript, React, 
            FastAPI, PostgreSQL, AWS, Docker, and Kubernetes experience. 
            Must have 5+ years of full-stack development experience.
            """,
            "job_title": "Senior Software Engineer",
            "resume_text": """
            John Smith - Senior Software Engineer
            6 years experience in Python, JavaScript, React, FastAPI, PostgreSQL.
            Worked with AWS, Docker, Kubernetes. Led development teams.
            Built scalable microservices and web applications.
            """
        }
        
        start_time = time.time()
        with self.client.post("/api/v1/analyze", json=payload, catch_response=True) as response:
            response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            if response.status_code == 200:
                if response_time <= 30000:  # 30-second requirement
                    response.success()
                else:
                    response.failure(f"Response time {response_time:.0f}ms exceeds 30s requirement")
            else:
                response.failure(f"Analysis failed: {response.status_code}")
    
    @task(8)
    def analyze_data_scientist_resume(self):
        """Test analysis for data scientist positions"""
        payload = {
            "job_description": """
            Data Scientist role requiring Python, R, machine learning, TensorFlow,
            scikit-learn, pandas, SQL, and statistical analysis experience.
            PhD or Master's degree preferred.
            """,
            "job_title": "Data Scientist",
            "resume_text": """
            Dr. Jane Doe - Data Scientist
            PhD in Statistics, 4 years ML experience. Expert in Python, R, TensorFlow,
            scikit-learn, pandas, SQL. Published research in machine learning.
            Built predictive models and data pipelines.
            """
        }
        
        start_time = time.time()
        with self.client.post("/api/v1/analyze", json=payload, catch_response=True) as response:
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                if response_time <= 30000:
                    response.success()
                else:
                    response.failure(f"Response time {response_time:.0f}ms exceeds 30s requirement")
            else:
                response.failure(f"Analysis failed: {response.status_code}")
    
    @task(5)
    def analyze_devops_resume(self):
        """Test analysis for DevOps positions"""
        payload = {
            "job_description": """
            DevOps Engineer position requiring AWS, Kubernetes, Docker, Terraform,
            Jenkins, Python scripting, and Linux administration experience.
            Experience with monitoring tools and CI/CD pipelines required.
            """,
            "job_title": "DevOps Engineer",
            "resume_text": """
            Mike Johnson - DevOps Engineer
            5 years DevOps experience. Expert in AWS, Kubernetes, Docker, Terraform.
            Built CI/CD pipelines with Jenkins. Python scripting and Linux admin.
            Implemented monitoring with Prometheus and Grafana.
            """
        }
        
        start_time = time.time()
        with self.client.post("/api/v1/analyze", json=payload, catch_response=True) as response:
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                if response_time <= 30000:
                    response.success()
                else:
                    response.failure(f"Response time {response_time:.0f}ms exceeds 30s requirement")
            else:
                response.failure(f"Analysis failed: {response.status_code}")

class UploadHeavyUser(HttpUser):
    """
    User focused on document upload functionality
    Tests file processing performance under load
    """
    
    wait_time = between(3, 8)
    weight = 2
    
    def on_start(self):
        """Initialize with mock authentication"""
        self.client.headers.update({
            "Authorization": f"Bearer mock_token_{random.randint(1000, 9999)}"
        })
    
    @task(5)
    def upload_pdf_resume(self):
        """Test PDF resume upload performance"""
        # Create mock PDF content
        pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
72 720 Td
(Sample Resume Content) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000206 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
299
%%EOF"""
        
        files = {
            'file': (f'resume_{random.randint(1000, 9999)}.pdf', pdf_content, 'application/pdf')
        }
        
        # Remove Content-Type header for multipart upload
        headers = {k: v for k, v in self.client.headers.items() if k != "Content-Type"}
        
        start_time = time.time()
        with self.client.post("/api/v1/upload", files=files, headers=headers, catch_response=True) as response:
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                if response_time <= 15000:  # 15-second threshold for uploads
                    response.success()
                else:
                    response.failure(f"Upload time {response_time:.0f}ms exceeds 15s threshold")
            else:
                response.failure(f"Upload failed: {response.status_code}")
    
    @task(3)
    def upload_text_resume(self):
        """Test text resume upload performance"""
        text_content = f"""
        Resume Content {random.randint(1000, 9999)}
        
        Name: Test User
        Email: test@example.com
        
        Experience:
        - Software Engineer at TechCorp (2020-2023)
        - Junior Developer at StartupXYZ (2018-2020)
        
        Skills:
        - Python, JavaScript, React, FastAPI
        - PostgreSQL, MongoDB, Redis
        - AWS, Docker, Kubernetes
        """.encode('utf-8')
        
        files = {
            'file': (f'resume_{random.randint(1000, 9999)}.txt', text_content, 'text/plain')
        }
        
        headers = {k: v for k, v in self.client.headers.items() if k != "Content-Type"}
        
        start_time = time.time()
        with self.client.post("/api/v1/upload", files=files, headers=headers, catch_response=True) as response:
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                if response_time <= 10000:  # 10-second threshold for text uploads
                    response.success()
                else:
                    response.failure(f"Upload time {response_time:.0f}ms exceeds 10s threshold")
            else:
                response.failure(f"Upload failed: {response.status_code}")

class HealthCheckUser(HttpUser):
    """
    User focused on health check and monitoring endpoints
    Tests system monitoring performance
    """
    
    wait_time = between(1, 3)
    weight = 1
    
    @task(10)
    def basic_health_check(self):
        """Test basic health check performance"""
        start_time = time.time()
        with self.client.get("/api/v1/health", catch_response=True) as response:
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                if response_time <= 1000:  # 1-second threshold for health checks
                    response.success()
                else:
                    response.failure(f"Health check time {response_time:.0f}ms exceeds 1s threshold")
            else:
                response.failure(f"Health check failed: {response.status_code}")
    
    @task(5)
    def detailed_health_check(self):
        """Test detailed health check performance"""
        start_time = time.time()
        with self.client.get("/api/v1/health/detailed", catch_response=True) as response:
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code in [200, 503]:  # 503 acceptable for degraded state
                if response_time <= 5000:  # 5-second threshold for detailed checks
                    response.success()
                else:
                    response.failure(f"Detailed health check time {response_time:.0f}ms exceeds 5s threshold")
            else:
                response.failure(f"Detailed health check failed: {response.status_code}")
    
    @task(3)
    def system_metrics(self):
        """Test system metrics endpoint performance"""
        start_time = time.time()
        with self.client.get("/api/v1/metrics", catch_response=True) as response:
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                if response_time <= 3000:  # 3-second threshold for metrics
                    response.success()
                else:
                    response.failure(f"Metrics time {response_time:.0f}ms exceeds 3s threshold")
            else:
                response.failure(f"Metrics failed: {response.status_code}")

class BrowsingUser(HttpUser):
    """
    User focused on browsing and retrieval operations
    Tests data retrieval performance
    """
    
    wait_time = between(2, 6)
    weight = 2
    
    def on_start(self):
        """Initialize with mock authentication"""
        self.client.headers.update({
            "Authorization": f"Bearer mock_token_{random.randint(1000, 9999)}",
            "Content-Type": "application/json"
        })
    
    @task(5)
    def get_user_resumes(self):
        """Test resume listing performance"""
        start_time = time.time()
        with self.client.get("/api/v1/resumes", catch_response=True) as response:
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                if response_time <= 3000:  # 3-second threshold for resume listing
                    response.success()
                else:
                    response.failure(f"Resume listing time {response_time:.0f}ms exceeds 3s threshold")
            else:
                response.failure(f"Resume listing failed: {response.status_code}")
    
    @task(5)
    def get_analysis_history(self):
        """Test analysis history retrieval performance"""
        start_time = time.time()
        with self.client.get("/api/v1/analyses", catch_response=True) as response:
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                if response_time <= 5000:  # 5-second threshold for analysis history
                    response.success()
                else:
                    response.failure(f"Analysis history time {response_time:.0f}ms exceeds 5s threshold")
            else:
                response.failure(f"Analysis history failed: {response.status_code}")
    
    @task(2)
    def get_specific_analysis(self):
        """Test specific analysis retrieval performance"""
        # Use a mock analysis ID
        analysis_id = f"mock-analysis-{random.randint(1000, 9999)}"
        
        start_time = time.time()
        with self.client.get(f"/api/v1/analyses/{analysis_id}", catch_response=True) as response:
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code in [200, 404]:  # 404 acceptable for non-existent analysis
                if response_time <= 2000:  # 2-second threshold for specific analysis
                    response.success()
                else:
                    response.failure(f"Specific analysis time {response_time:.0f}ms exceeds 2s threshold")
            else:
                response.failure(f"Specific analysis failed: {response.status_code}")

# Performance validation events
performance_stats = {
    "total_requests": 0,
    "failed_requests": 0,
    "response_times": [],
    "endpoint_stats": {}
}

@events.request.add_listener
def track_performance(request_type, name, response_time, response_length, response, context, exception, **kwargs):
    """Track detailed performance statistics"""
    global performance_stats
    
    performance_stats["total_requests"] += 1
    performance_stats["response_times"].append(response_time)
    
    if exception or (response and response.status_code >= 400):
        performance_stats["failed_requests"] += 1
    
    # Track endpoint-specific stats
    if name not in performance_stats["endpoint_stats"]:
        performance_stats["endpoint_stats"][name] = {
            "requests": 0,
            "failures": 0,
            "response_times": []
        }
    
    endpoint_stats = performance_stats["endpoint_stats"][name]
    endpoint_stats["requests"] += 1
    endpoint_stats["response_times"].append(response_time)
    
    if exception or (response and response.status_code >= 400):
        endpoint_stats["failures"] += 1

@events.test_stop.add_listener
def validate_performance_requirements_on_stop(environment, **kwargs):
    """Validate performance requirements when test completes"""
    global performance_stats
    
    print("\n" + "="*80)
    print("PERFORMANCE REQUIREMENTS VALIDATION")
    print("="*80)
    
    if not performance_stats["response_times"]:
        print("No performance data collected!")
        return
    
    # Calculate overall statistics
    response_times = sorted(performance_stats["response_times"])
    total_requests = performance_stats["total_requests"]
    failed_requests = performance_stats["failed_requests"]
    
    p95_index = int(len(response_times) * 0.95)
    p95_time = response_times[p95_index] if p95_index < len(response_times) else response_times[-1]
    
    success_rate = ((total_requests - failed_requests) / total_requests) * 100 if total_requests > 0 else 0
    
    overall_stats = {
        "p95_response_time": p95_time,
        "success_rate": success_rate,
        "total_requests": total_requests,
        "failed_requests": failed_requests
    }
    
    # Validate overall requirements
    validation_results = validate_performance_requirements(overall_stats)
    
    print(f"Total Requests: {total_requests}")
    print(f"Failed Requests: {failed_requests}")
    print(f"Success Rate: {success_rate:.2f}%")
    print(f"P95 Response Time: {p95_time:.0f}ms ({p95_time/1000:.2f}s)")
    print()
    
    # Check main requirements
    print("REQUIREMENT VALIDATION:")
    print(f"✓ 30-second requirement (95% of requests): {'PASSED' if validation_results['30_second_requirement'] else 'FAILED'}")
    print(f"✓ 95% success rate requirement: {'PASSED' if validation_results['success_rate_requirement'] else 'FAILED'}")
    print()
    
    # Endpoint-specific validation
    print("ENDPOINT-SPECIFIC PERFORMANCE:")
    for endpoint, stats in performance_stats["endpoint_stats"].items():
        if stats["response_times"]:
            endpoint_times = sorted(stats["response_times"])
            endpoint_p95 = endpoint_times[int(len(endpoint_times) * 0.95)]
            endpoint_success_rate = ((stats["requests"] - stats["failures"]) / stats["requests"]) * 100
            
            threshold = ENDPOINT_THRESHOLDS.get(endpoint, {"p95_response_time": 30000, "success_rate": 95.0})
            
            time_ok = endpoint_p95 <= threshold["p95_response_time"]
            success_ok = endpoint_success_rate >= threshold["success_rate"]
            
            print(f"{endpoint}:")
            print(f"  Requests: {stats['requests']}, Failures: {stats['failures']}")
            print(f"  P95 Time: {endpoint_p95:.0f}ms ({'✓' if time_ok else '✗'})")
            print(f"  Success Rate: {endpoint_success_rate:.1f}% ({'✓' if success_ok else '✗'})")
    
    print("="*80)