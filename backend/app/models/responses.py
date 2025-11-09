"""
Pydantic response models for API endpoints
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID

class ErrorResponse(BaseModel):
    """Standard error response format"""
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime
    request_id: str

class UploadResponse(BaseModel):
    """Response model for document upload"""
    resume_id: UUID = Field(..., description="Unique identifier for the uploaded resume")
    file_name: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    processing_method: str = Field(..., description="Method used to extract text (pdfplumber, ocr, docx, text)")
    confidence_score: float = Field(..., description="Confidence score of text extraction (0.0-1.0)")
    text_length: int = Field(..., description="Length of extracted text")
    uploaded_at: datetime = Field(..., description="Upload timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "resume_id": "123e4567-e89b-12d3-a456-426614174000",
                "file_name": "john_doe_resume.pdf",
                "file_size": 245760,
                "processing_method": "pdfplumber",
                "confidence_score": 0.95,
                "text_length": 2847,
                "uploaded_at": "2023-11-04T10:30:00Z"
            }
        }

class AnalysisResponse(BaseModel):
    """Response model for resume analysis"""
    analysis_id: UUID = Field(..., description="Unique identifier for the analysis")
    match_score: float = Field(..., description="Compatibility score (0-100)")
    ai_feedback: Dict[str, Any] = Field(..., description="AI-generated feedback and recommendations")
    matched_keywords: List[str] = Field(..., description="Keywords found in both resume and job description")
    missing_keywords: List[str] = Field(..., description="Important keywords missing from resume")
    processing_time: float = Field(..., description="Analysis processing time in seconds")
    created_at: datetime = Field(..., description="Analysis timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "analysis_id": "456e7890-e89b-12d3-a456-426614174001",
                "match_score": 78.5,
                "ai_feedback": {
                    "overall_assessment": "Strong technical background with good alignment to the role",
                    "recommendations": [
                        {
                            "category": "skills",
                            "priority": "high",
                            "suggestion": "Add more specific experience with FastAPI framework"
                        }
                    ]
                },
                "matched_keywords": ["Python", "PostgreSQL", "API development"],
                "missing_keywords": ["FastAPI", "Docker", "Kubernetes"],
                "processing_time": 12.3,
                "created_at": "2023-11-04T10:35:00Z"
            }
        }

class AnalysisListResponse(BaseModel):
    """Response model for analysis history list"""
    analyses: List[Dict[str, Any]] = Field(..., description="List of user analyses")
    total_count: int = Field(..., description="Total number of analyses for the user")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    has_next: bool = Field(..., description="Whether there are more pages")
    
    class Config:
        json_schema_extra = {
            "example": {
                "analyses": [
                    {
                        "analysis_id": "456e7890-e89b-12d3-a456-426614174001",
                        "job_title": "Senior Python Developer",
                        "match_score": 78.5,
                        "created_at": "2023-11-04T10:35:00Z"
                    }
                ],
                "total_count": 15,
                "page": 1,
                "page_size": 10,
                "has_next": True
            }
        }