"""
Pydantic request models for API endpoints
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from uuid import UUID

class BaseRequest(BaseModel):
    """Base request model with common fields"""
    pass

class AnalysisRequest(BaseModel):
    """Request model for resume analysis"""
    job_description: str = Field(
        ..., 
        min_length=50, 
        max_length=10000,
        description="Job description text to analyze against"
    )
    job_title: Optional[str] = Field(
        None,
        max_length=200,
        description="Optional job title for context"
    )
    resume_id: Optional[UUID] = Field(
        None,
        description="ID of previously uploaded resume"
    )
    resume_text: Optional[str] = Field(
        None,
        max_length=50000,
        description="Direct resume text input (alternative to resume_id)"
    )
    
    @validator('job_description')
    def validate_job_description(cls, v):
        if not v or not v.strip():
            raise ValueError('Job description cannot be empty')
        return v.strip()
    
    @validator('job_title')
    def validate_job_title(cls, v):
        if v is not None:
            return v.strip()
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "job_description": "We are looking for a Senior Python Developer with experience in FastAPI, PostgreSQL, and machine learning. The ideal candidate should have 5+ years of experience...",
                "job_title": "Senior Python Developer",
                "resume_id": "123e4567-e89b-12d3-a456-426614174000"
            }
        }