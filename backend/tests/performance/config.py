"""
Configuration for performance tests

This module contains configuration settings for different performance test scenarios
including load testing, stress testing, and endurance testing.

Requirements: 5.5, 6.6
"""
import os
from typing import Dict, Any

# Base configuration
BASE_CONFIG = {
    "host": os.getenv("PERFORMANCE_TEST_HOST", "http://localhost:8000"),
    "users": 50,
    "spawn_rate": 5,  # Users spawned per second
    "run_time": "5m",  # 5 minutes
    "response_time_threshold": 30.0,  # 30 seconds
    "success_rate_threshold": 95.0,  # 95% success rate
}

# Load test configuration (normal expected load)
LOAD_TEST_CONFIG = {
    **BASE_CONFIG,
    "users": 50,
    "spawn_rate": 5,
    "run_time": "10m",
    "test_name": "load_test",
    "description": "Normal expected load with 50 concurrent users"
}

# Stress test configuration (beyond normal capacity)
STRESS_TEST_CONFIG = {
    **BASE_CONFIG,
    "users": 100,
    "spawn_rate": 10,
    "run_time": "5m",
    "test_name": "stress_test",
    "description": "Stress test with 100 concurrent users to find breaking point"
}

# Spike test configuration (sudden load increase)
SPIKE_TEST_CONFIG = {
    **BASE_CONFIG,
    "users": 200,
    "spawn_rate": 50,  # Rapid spawn rate for spike
    "run_time": "2m",
    "test_name": "spike_test",
    "description": "Spike test with rapid user increase to 200 users"
}

# Endurance test configuration (sustained load)
ENDURANCE_TEST_CONFIG = {
    **BASE_CONFIG,
    "users": 30,
    "spawn_rate": 2,
    "run_time": "30m",
    "test_name": "endurance_test",
    "description": "Endurance test with sustained load for 30 minutes"
}

# Performance thresholds for different endpoints
ENDPOINT_THRESHOLDS = {
    "/api/v1/health": {
        "p95_response_time": 1000,  # 1 second
        "success_rate": 99.0
    },
    "/api/v1/health/detailed": {
        "p95_response_time": 5000,  # 5 seconds
        "success_rate": 95.0
    },
    "/api/v1/upload": {
        "p95_response_time": 15000,  # 15 seconds
        "success_rate": 90.0
    },
    "/api/v1/analyze": {
        "p95_response_time": 30000,  # 30 seconds (main requirement)
        "success_rate": 95.0
    },
    "/api/v1/resumes": {
        "p95_response_time": 3000,  # 3 seconds
        "success_rate": 98.0
    },
    "/api/v1/analyses": {
        "p95_response_time": 5000,  # 5 seconds
        "success_rate": 98.0
    }
}

def get_test_config(test_type: str) -> Dict[str, Any]:
    """Get configuration for specific test type"""
    configs = {
        "load": LOAD_TEST_CONFIG,
        "stress": STRESS_TEST_CONFIG,
        "spike": SPIKE_TEST_CONFIG,
        "endurance": ENDURANCE_TEST_CONFIG
    }
    
    return configs.get(test_type, LOAD_TEST_CONFIG)

def validate_performance_requirements(stats: Dict[str, Any], endpoint: str = None) -> Dict[str, bool]:
    """
    Validate performance requirements against test results
    
    Args:
        stats: Performance statistics from test run
        endpoint: Specific endpoint to validate (optional)
    
    Returns:
        Dictionary with validation results
    """
    results = {}
    
    # Overall 30-second requirement for 95% of requests
    p95_time = stats.get("p95_response_time", 0)
    results["30_second_requirement"] = p95_time <= 30000
    
    # Success rate requirement
    success_rate = stats.get("success_rate", 0)
    results["success_rate_requirement"] = success_rate >= 95.0
    
    # Endpoint-specific thresholds
    if endpoint and endpoint in ENDPOINT_THRESHOLDS:
        threshold = ENDPOINT_THRESHOLDS[endpoint]
        results[f"{endpoint}_response_time"] = p95_time <= threshold["p95_response_time"]
        results[f"{endpoint}_success_rate"] = success_rate >= threshold["success_rate"]
    
    return results