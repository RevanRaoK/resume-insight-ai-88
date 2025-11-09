"""
Configuration management with environment variables
"""
import os
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application settings
    DEBUG: bool = Field(default=False, env="DEBUG")
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    JWT_SECRET_KEY: str = Field(..., env="JWT_SECRET_KEY")
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:3000"], 
        env="ALLOWED_ORIGINS"
    )
    
    # Database settings
    SUPABASE_URL: str = Field(..., env="SUPABASE_URL")
    SUPABASE_ANON_KEY: str = Field(..., env="SUPABASE_ANON_KEY")
    SUPABASE_SERVICE_ROLE_KEY: str = Field(..., env="SUPABASE_SERVICE_ROLE_KEY")
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    
    # External API keys
    GOOGLE_GEMINI_API_KEY: str = Field(..., env="GOOGLE_GEMINI_API_KEY")
    GOOGLE_GEMINI_MODEL: str = Field(default="gemini-2.0-flash-exp", env="GOOGLE_GEMINI_MODEL")
    
    # File upload settings
    MAX_FILE_SIZE: int = Field(default=10 * 1024 * 1024, env="MAX_FILE_SIZE")  # 10MB
    ALLOWED_FILE_TYPES: List[str] = Field(
        default=["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "text/plain"],
        env="ALLOWED_FILE_TYPES"
    )
    
    # Rate limiting settings
    RATE_LIMIT_REQUESTS: int = Field(default=10, env="RATE_LIMIT_REQUESTS")
    RATE_LIMIT_WINDOW: int = Field(default=3600, env="RATE_LIMIT_WINDOW")  # 1 hour
    
    # ML Model settings
    NER_MODEL_NAME: str = Field(default="yashpwr/resume-ner-bert-v2", env="NER_MODEL_NAME")
    EMBEDDING_MODEL_NAME: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2", 
        env="EMBEDDING_MODEL_NAME"
    )
    NER_CONFIDENCE_THRESHOLD: float = Field(default=0.80, env="NER_CONFIDENCE_THRESHOLD")
    
    # Performance settings
    MAX_CONCURRENT_USERS: int = Field(default=50, env="MAX_CONCURRENT_USERS")
    REQUEST_TIMEOUT: int = Field(default=30, env="REQUEST_TIMEOUT")
    
    # Logging settings
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field(default="json", env="LOG_FORMAT")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()