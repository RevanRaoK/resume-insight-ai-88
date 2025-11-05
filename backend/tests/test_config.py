"""
Test configuration to override settings for testing
"""
import os
from unittest.mock import patch

# Set test environment variables
test_env_vars = {
    "SECRET_KEY": "test-secret-key-for-testing-only",
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_ANON_KEY": "test-anon-key",
    "SUPABASE_SERVICE_ROLE_KEY": "test-service-role-key",
    "DATABASE_URL": "postgresql://test:test@localhost:5432/test_db",
    "GOOGLE_GEMINI_API_KEY": "test-gemini-api-key",
    "DEBUG": "true",
    "LOG_LEVEL": "DEBUG"
}

def setup_test_environment():
    """Setup test environment variables"""
    for key, value in test_env_vars.items():
        os.environ[key] = value

def cleanup_test_environment():
    """Cleanup test environment variables"""
    for key in test_env_vars.keys():
        if key in os.environ:
            del os.environ[key]