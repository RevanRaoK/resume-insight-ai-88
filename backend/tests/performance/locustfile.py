"""
Performance tests for SmartResume AI Resume Analyzer using Locust

This module contains comprehensive load tests that simulate 50 concurrent users
and validate the 30-second response time requirement for 95% of requests.

Requirements: 5.5, 6.6
"""
import os
import json
import time
import random
from io import BytesIO
from typing import Dict, Any, Optional
from locust import HttpUser, task, between, events
from locust.exception import StopUser

# Test data and configuration
TEST_JOB_DESCRIPTIONS = [
    """
    Senior Software Engineer - Full Stack Development
    
    We are seeking a highly skilled Senior Software Engineer to join our dynamic team. 
    The ideal candidate will have extensive experience in both frontend and backend development,
    with a strong focus on scalable web applications.
    
    Required Skills:
    - 5+ years of experience in software development
    - Proficiency in Python, JavaScript, and TypeScript
    - Experience with React, Node.js, and FastAPI
    - Strong knowledge of databases (PostgreSQL, MongoDB)
    - Experience with cloud platforms (AWS, GCP, Azure)
    - Knowledge of containerization (Docker, Kubernetes)
    - Understanding of CI/CD pipelines
    - Experience with testing frameworks (Jest, pytest)
    
    Preferred Qualifications:
    - Bachelor's degree in Computer Science or related field
    - Experience with machine learning frameworks
    - Knowledge of microservices architecture
    - Experience with GraphQL and REST APIs
    """,
    """
    Data Scientist - Machine Learning Engineer
    
    Join our AI team to build cutting-edge machine learning solutions that drive business impact.
    We're looking for a passionate data scientist with strong engineering skills.
    
    Required Skills:
    - PhD or Master's in Computer Science, Statistics, or related field
    - 3+ years of experience in machine learning and data science
    - Proficiency in Python, R, and SQL
    - Experience with ML frameworks (TensorFlow, PyTorch, scikit-learn)
    - Strong statistical analysis and modeling skills
    - Experience with big data tools (Spark, Hadoop)
    - Knowledge of cloud ML platforms (AWS SageMaker, GCP AI Platform)
    - Experience with data visualization tools (Tableau, matplotlib, seaborn)
    
    Preferred Qualifications:
    - Experience with deep learning and neural networks
    - Knowledge of MLOps and model deployment
    - Experience with A/B testing and experimentation
    - Publications in top-tier conferences or journals
    """,
    """
    DevOps Engineer - Infrastructure Automation
    
    We are looking for a DevOps Engineer to help us scale our infrastructure and 
    improve our deployment processes. The ideal candidate will have experience 
    with cloud platforms and automation tools.
    
    Required Skills:
    - 4+ years of experience in DevOps or Site Reliability Engineering
    - Proficiency in Linux/Unix systems administration
    - Experience with cloud platforms (AWS, Azure, GCP)
    - Strong knowledge of containerization (Docker, Kubernetes)
    - Experience with Infrastructure as Code (Terraform, CloudFormation)
    - Proficiency in scripting languages (Python, Bash, PowerShell)
    - Experience with CI/CD tools (Jenkins, GitLab CI, GitHub Actions)
    - Knowledge of monitoring and logging tools (Prometheus, Grafana, ELK stack)
    
    Preferred Qualifications:
    - Bachelor's degree in Computer Science or related field
    - Experience with service mesh technologies (Istio, Linkerd)
    - Knowledge of security best practices and compliance
    - Experience with database administration and optimization
    """
]

SAMPLE_RESUME_TEXT = """
John Doe
Senior Software Engineer
Email: john.doe@email.com
Phone: (555) 123-4567
LinkedIn: linkedin.com/in/johndoe

PROFESSIONAL SUMMARY
Experienced Senior Software Engineer with 6+ years of expertise in full-stack development, 
specializing in Python, JavaScript, and cloud technologies. Proven track record of building 
scalable web applications and leading development teams.

TECHNICAL SKILLS
Programming Languages: Python, JavaScript, TypeScript, Java, Go
Frontend Technologies: React, Vue.js, HTML5, CSS3, Redux
Backend Technologies: FastAPI, Django, Node.js, Express.js
Databases: PostgreSQL, MongoDB, Redis, MySQL
Cloud Platforms: AWS (EC2, S3, Lambda, RDS), Google Cloud Platform
DevOps Tools: Docker, Kubernetes, Jenkins, GitLab CI/CD
Testing: pytest, Jest, Selenium, Unit Testing, Integration Testing

PROFESSIONAL EXPERIENCE

Senior Software Engineer | TechCorp Inc. | 2020 - Present
• Led development of microservices architecture serving 1M+ daily active users
• Implemented CI/CD pipelines reducing deployment time by 60%
• Mentored junior developers and conducted code reviews
• Built RESTful APIs using FastAPI and PostgreSQL
• Developed React-based frontend applications with TypeScript

Software Engineer | StartupXYZ | 2018 - 2020
• Developed full-stack web applications using Python Django and React
• Implemented automated testing suites achieving 95% code coverage
• Optimized database queries improving application performance by 40%
• Collaborated with cross-functional teams in Agile environment

Junior Developer | WebSolutions LLC | 2017 - 2018
• Built responsive web applications using HTML, CSS, and JavaScript
• Participated in code reviews and pair programming sessions
• Learned best practices in software development and testing

EDUCATION
Bachelor of Science in Computer Science
University of Technology | 2013 - 2017
GPA: 3.8/4.0

CERTIFICATIONS
• AWS Certified Solutions Architect - Associate
• Google Cloud Professional Developer
• Certified Kubernetes Administrator (CKA)

PROJECTS
E-commerce Platform (2021)
• Built scalable e-commerce platform using FastAPI, React, and PostgreSQL
• Implemented payment processing with Stripe API
• Deployed on AWS using Docker and Kubernetes

Machine Learning Pipeline (2020)
• Developed ML pipeline for customer churn prediction
• Used Python, scikit-learn, and Apache Airflow
• Achieved 92% accuracy in production environment
"""

class PerformanceMetrics:
    """Track performance metrics during load testing"""
    
    def __init__(self):
        self.response_times = []
        self.error_count = 0
        self.success_count = 0
        self.start_time = time.time()
    
    def record_response(self, response_time: float, success: bool):
        """Record a response time and success status"""
        self.response_times.append(response_time)
        if success:
            self.success_count += 1
        else:
            self.error_count += 1
    
    def get_percentile(self, percentile: float) -> float:
        """Calculate response time percentile"""
        if not self.response_times:
            return 0.0
        
        sorted_times = sorted(self.response_times)
        index = int(len(sorted_times) * percentile / 100)
        return sorted_times[min(index, len(sorted_times) - 1)]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics"""
        if not self.response_times:
            return {"error": "No response times recorded"}
        
        return {
            "total_requests": len(self.response_times),
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": self.success_count / len(self.response_times) * 100,
            "avg_response_time": sum(self.response_times) / len(self.response_times),
            "min_response_time": min(self.response_times),
            "max_response_time": max(self.response_times),
            "p50_response_time": self.get_percentile(50),
            "p95_response_time": self.get_percentile(95),
            "p99_response_time": self.get_percentile(99),
            "test_duration": time.time() - self.start_time
        }

# Global metrics instance
metrics = PerformanceMetrics()

@events.request.add_listener
def record_request(request_type, name, response_time, response_length, response, context, exception, **kwargs):
    """Record all requests for performance analysis"""
    success = exception is None and response.status_code < 400
    metrics.record_response(response_time, success)

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Print performance statistics when test stops"""
    stats = metrics.get_stats()
    
    print("\n" + "="*60)
    print("PERFORMANCE TEST RESULTS")
    print("="*60)
    
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"{key}: {value:.2f}")
        else:
            print(f"{key}: {value}")
    
    # Check 30-second requirement for 95% of requests
    p95_time = stats.get("p95_response_time", 0)
    requirement_met = p95_time <= 30000  # 30 seconds in milliseconds
    
    print(f"\n30-second requirement (95% of requests): {'✓ PASSED' if requirement_met else '✗ FAILED'}")
    print(f"P95 response time: {p95_time/1000:.2f} seconds")
    print("="*60)

class SmartResumeUser(HttpUser):
    """
    Simulated user for SmartResume AI Resume Analyzer performance testing
    
    This class simulates realistic user behavior including:
    - Authentication
    - Resume uploads
    - Analysis requests
    - History retrieval
    """
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between requests
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.auth_token: Optional[str] = None
        self.resume_id: Optional[str] = None
        self.user_id: str = f"test_user_{random.randint(1000, 9999)}"
    
    def on_start(self):
        """Initialize user session with authentication"""
        self.authenticate()
    
    def authenticate(self):
        """
        Simulate user authentication
        In a real scenario, this would use Supabase auth
        For testing, we'll use a mock JWT token
        """
        # Mock JWT token for testing (in real scenario, get from Supabase)
        mock_token = f"mock_jwt_token_for_{self.user_id}"
        self.auth_token = mock_token
        
        # Set authorization header for all requests
        self.client.headers.update({
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json"
        })
    
    @task(1)
    def health_check(self):
        """Test basic health check endpoint"""
        with self.client.get("/api/v1/health", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")
    
    @task(2)
    def detailed_health_check(self):
        """Test detailed health check endpoint"""
        with self.client.get("/api/v1/health/detailed", catch_response=True) as response:
            if response.status_code in [200, 503]:  # 503 is acceptable for degraded state
                response.success()
            else:
                response.failure(f"Detailed health check failed: {response.status_code}")
    
    @task(3)
    def upload_resume(self):
        """Test resume upload functionality"""
        # Create a mock PDF file for upload
        pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"
        
        files = {
            'file': ('test_resume.pdf', BytesIO(pdf_content), 'application/pdf')
        }
        
        # Remove Content-Type header for multipart upload
        headers = {k: v for k, v in self.client.headers.items() if k != "Content-Type"}
        
        with self.client.post(
            "/api/v1/upload", 
            files=files, 
            headers=headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    self.resume_id = data.get("resume_id")
                    response.success()
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"Upload failed: {response.status_code}")
    
    @task(5)
    def analyze_resume_with_text(self):
        """Test resume analysis with direct text input (most common scenario)"""
        job_description = random.choice(TEST_JOB_DESCRIPTIONS)
        
        payload = {
            "job_description": job_description,
            "job_title": "Software Engineer",
            "resume_text": SAMPLE_RESUME_TEXT
        }
        
        with self.client.post(
            "/api/v1/analyze", 
            json=payload,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    # Validate response structure
                    required_fields = ["analysis_id", "match_score", "ai_feedback", "processing_time"]
                    if all(field in data for field in required_fields):
                        response.success()
                    else:
                        response.failure("Missing required fields in response")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"Analysis failed: {response.status_code}")
    
    @task(3)
    def analyze_resume_with_id(self):
        """Test resume analysis with uploaded resume ID"""
        if not self.resume_id:
            # Skip if no resume uploaded yet
            return
        
        job_description = random.choice(TEST_JOB_DESCRIPTIONS)
        
        payload = {
            "job_description": job_description,
            "job_title": "Data Scientist",
            "resume_id": self.resume_id
        }
        
        with self.client.post(
            "/api/v1/analyze", 
            json=payload,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                # Resume not found is acceptable in test environment
                response.success()
            else:
                response.failure(f"Analysis with resume ID failed: {response.status_code}")
    
    @task(2)
    def get_user_resumes(self):
        """Test retrieving user's uploaded resumes"""
        with self.client.get("/api/v1/resumes", catch_response=True) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, list):
                        response.success()
                    else:
                        response.failure("Response is not a list")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"Get resumes failed: {response.status_code}")
    
    @task(2)
    def get_analysis_history(self):
        """Test retrieving user's analysis history"""
        with self.client.get("/api/v1/analyses", catch_response=True) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, list):
                        response.success()
                    else:
                        response.failure("Response is not a list")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"Get analysis history failed: {response.status_code}")
    
    @task(1)
    def system_metrics(self):
        """Test system metrics endpoint"""
        with self.client.get("/api/v1/metrics", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"System metrics failed: {response.status_code}")

class HighLoadUser(SmartResumeUser):
    """
    High-intensity user for stress testing
    Performs more frequent analysis requests to test system limits
    """
    
    wait_time = between(0.5, 1.5)  # Shorter wait time for stress testing
    
    @task(10)
    def intensive_analysis(self):
        """Perform intensive analysis requests"""
        self.analyze_resume_with_text()
    
    @task(5)
    def rapid_health_checks(self):
        """Rapid health check requests"""
        self.health_check()

class LightUser(SmartResumeUser):
    """
    Light user for baseline testing
    Performs fewer requests to simulate casual users
    """
    
    wait_time = between(5, 10)  # Longer wait time for light usage
    
    @task(1)
    def occasional_analysis(self):
        """Occasional analysis requests"""
        self.analyze_resume_with_text()
    
    @task(2)
    def browse_history(self):
        """Browse analysis history"""
        self.get_analysis_history()