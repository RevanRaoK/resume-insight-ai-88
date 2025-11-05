"""
Domain entity models for database operations
"""
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from datetime import datetime
from uuid import UUID


@dataclass
class BaseEntity:
    """Base entity class"""
    pass


@dataclass
class UserProfile:
    """User profile entity matching profiles table"""
    id: UUID
    email: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: Optional[datetime] = None


@dataclass
class Resume:
    """Resume entity matching resumes table"""
    id: UUID
    user_id: UUID
    file_name: str
    file_url: str
    parsed_text: Optional[str] = None
    uploaded_at: Optional[datetime] = None


@dataclass
class Analysis:
    """Analysis entity matching analyses table"""
    id: UUID
    user_id: UUID
    resume_id: UUID
    job_title: str
    job_description: str
    match_score: int
    ai_feedback: Dict[str, Any]
    matched_keywords: List[str]
    missing_keywords: List[str]
    created_at: Optional[datetime] = None


@dataclass
class ProcessedDocument:
    """Processed document data from document ingestion"""
    text: str
    file_name: str
    file_size: int
    processing_method: str  # "pdfplumber", "ocr", "docx", "text"
    confidence_score: float


@dataclass
class ResumeEntities:
    """Extracted entities from resume text"""
    skills: List[str]
    job_titles: List[str]
    companies: List[str]
    education: List[str]
    contact_info: Dict[str, str]
    experience_years: Optional[int]
    confidence_scores: Dict[str, float]


@dataclass
class CompatibilityAnalysis:
    """Semantic compatibility analysis results"""
    match_score: float  # 0-100
    matched_keywords: List[str]
    missing_keywords: List[str]
    semantic_similarity: float
    keyword_coverage: float


@dataclass
class AIFeedback:
    """AI-generated feedback and recommendations"""
    recommendations: List[Dict[str, Any]]
    overall_assessment: str
    priority_improvements: List[str]
    strengths: List[str]


@dataclass
class AnalysisResult:
    """Complete analysis result for storage"""
    user_id: UUID
    resume_id: UUID
    job_title: str
    job_description: str
    match_score: int
    ai_feedback: Dict[str, Any]
    matched_keywords: List[str]
    missing_keywords: List[str]
    processing_time: float