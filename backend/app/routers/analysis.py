"""
Resume analysis endpoints for comprehensive resume-job matching
"""
import time
from datetime import datetime
from uuid import uuid4, UUID
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends

from app.utils.logger import get_logger
from app.models.requests import AnalysisRequest
from app.models.responses import AnalysisResponse
from app.models.entities import AnalysisResult
from app.services.nlu_service import nlu_service
from app.services.semantic_service import semantic_service
from app.services.ai_service import ai_service
from app.services.database_service import db_service
from app.middleware.auth import get_current_user
from app.core.exceptions import (
    NLUProcessingError,
    SemanticAnalysisError, 
    AIServiceError,
    DatabaseError
)

logger = get_logger(__name__)
router = APIRouter()

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_resume(
    request: AnalysisRequest,
    current_user: dict = Depends(get_current_user)
) -> AnalysisResponse:
    """
    Perform comprehensive resume analysis against a job description
    
    This endpoint orchestrates the complete analysis pipeline:
    1. NLU processing for entity extraction
    2. Semantic analysis for compatibility scoring
    3. AI feedback generation for personalized recommendations
    
    - **job_description**: Job posting text to analyze against
    - **job_title**: Optional job title for context
    - **resume_id**: ID of previously uploaded resume (OR)
    - **resume_text**: Direct resume text input
    - **Returns**: Complete analysis with scores, keywords, and AI feedback
    
    Requirements: 2.1, 3.1, 4.1, 7.1
    """
    start_time = time.time()
    request_id = str(uuid4())
    user_id = current_user["user_id"]
    
    logger.info(
        "analysis_started",
        request_id=request_id,
        user_id=user_id,
        has_resume_id=request.resume_id is not None,
        has_resume_text=request.resume_text is not None,
        job_title=request.job_title
    )
    
    try:
        # Validate that we have either resume_id or resume_text
        if not request.resume_id and not request.resume_text:
            raise HTTPException(
                status_code=400,
                detail={
                    "error_code": "MISSING_RESUME_DATA",
                    "message": "Either resume_id or resume_text must be provided",
                    "request_id": request_id
                }
            )
        
        # Get resume text
        resume_text = ""
        resume_id = None
        
        if request.resume_id:
            # Fetch resume from database
            resume = await db_service.resumes.get_resume_by_id(request.resume_id)
            if not resume:
                raise HTTPException(
                    status_code=404,
                    detail={
                        "error_code": "RESUME_NOT_FOUND",
                        "message": f"Resume with ID {request.resume_id} not found",
                        "request_id": request_id
                    }
                )
            
            # Verify resume belongs to current user
            if str(resume.user_id) != user_id:
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error_code": "UNAUTHORIZED_RESUME_ACCESS",
                        "message": "You don't have permission to access this resume",
                        "request_id": request_id
                    }
                )
            
            resume_text = resume.parsed_text
            resume_id = resume.id
            
        else:
            # Use provided resume text
            resume_text = request.resume_text
        
        if not resume_text or len(resume_text.strip()) < 50:
            raise HTTPException(
                status_code=400,
                detail={
                    "error_code": "INSUFFICIENT_RESUME_TEXT",
                    "message": "Resume text is too short for meaningful analysis (minimum 50 characters)",
                    "request_id": request_id
                }
            )
        
        logger.info(
            "analysis_pipeline_starting",
            request_id=request_id,
            user_id=user_id,
            resume_text_length=len(resume_text),
            job_description_length=len(request.job_description)
        )
        
        # Step 1: NLU Processing - Extract entities from resume
        logger.info("nlu_processing_started", request_id=request_id)
        resume_entities = await nlu_service.extract_entities(resume_text)
        
        logger.info(
            "nlu_processing_completed",
            request_id=request_id,
            skills_count=len(resume_entities.skills),
            job_titles_count=len(resume_entities.job_titles),
            companies_count=len(resume_entities.companies)
        )
        
        # Step 2: Semantic Analysis - Calculate compatibility
        logger.info("semantic_analysis_started", request_id=request_id)
        compatibility_analysis = await semantic_service.analyze_compatibility(
            resume_text, 
            request.job_description
        )
        
        logger.info(
            "semantic_analysis_completed",
            request_id=request_id,
            match_score=compatibility_analysis.match_score,
            matched_keywords_count=len(compatibility_analysis.matched_keywords),
            missing_keywords_count=len(compatibility_analysis.missing_keywords)
        )
        
        # Step 3: AI Feedback Generation
        logger.info("ai_feedback_started", request_id=request_id)
        
        # Prepare context for AI service
        analysis_context = {
            "resume_entities": resume_entities,
            "compatibility_analysis": compatibility_analysis,
            "job_description": request.job_description,
            "job_title": request.job_title,
            "resume_text": resume_text
        }
        
        ai_feedback = await ai_service.generate_feedback(analysis_context)
        
        logger.info(
            "ai_feedback_completed",
            request_id=request_id,
            recommendations_count=len(ai_feedback.recommendations) if hasattr(ai_feedback, 'recommendations') else 0
        )
        
        # Step 4: Store analysis results
        processing_time = time.time() - start_time
        
        analysis_result = AnalysisResult(
            user_id=UUID(user_id),
            resume_id=resume_id,
            job_title=request.job_title or "Untitled Position",
            job_description=request.job_description,
            match_score=compatibility_analysis.match_score,
            ai_feedback=ai_feedback.dict() if hasattr(ai_feedback, 'dict') else ai_feedback,
            matched_keywords=compatibility_analysis.matched_keywords,
            missing_keywords=compatibility_analysis.missing_keywords,
            processing_time=processing_time
        )
        
        analysis_id = await db_service.store_analysis(analysis_result)
        
        logger.info(
            "analysis_completed",
            request_id=request_id,
            user_id=user_id,
            analysis_id=analysis_id,
            match_score=compatibility_analysis.match_score,
            processing_time=processing_time
        )
        
        return AnalysisResponse(
            analysis_id=UUID(analysis_id),
            match_score=compatibility_analysis.match_score,
            ai_feedback=ai_feedback.dict() if hasattr(ai_feedback, 'dict') else ai_feedback,
            matched_keywords=compatibility_analysis.matched_keywords,
            missing_keywords=compatibility_analysis.missing_keywords,
            processing_time=processing_time,
            created_at=datetime.utcnow()
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
        
    except NLUProcessingError as e:
        logger.error(
            "nlu_processing_failed",
            request_id=request_id,
            user_id=user_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": "NLU_PROCESSING_FAILED",
                "message": f"Failed to extract entities from resume: {str(e)}",
                "details": {"processing_stage": "entity_extraction"},
                "request_id": request_id
            }
        )
        
    except SemanticAnalysisError as e:
        logger.error(
            "semantic_analysis_failed",
            request_id=request_id,
            user_id=user_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": "SEMANTIC_ANALYSIS_FAILED",
                "message": f"Failed to perform semantic analysis: {str(e)}",
                "details": {"processing_stage": "semantic_analysis"},
                "request_id": request_id
            }
        )
        
    except AIServiceError as e:
        logger.error(
            "ai_feedback_failed",
            request_id=request_id,
            user_id=user_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": "AI_FEEDBACK_FAILED",
                "message": f"Failed to generate AI feedback: {str(e)}",
                "details": {"processing_stage": "ai_feedback"},
                "request_id": request_id
            }
        )
        
    except DatabaseError as e:
        logger.error(
            "database_error_during_analysis",
            request_id=request_id,
            user_id=user_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "DATABASE_ERROR",
                "message": "Failed to store analysis results",
                "details": {"error": str(e)},
                "request_id": request_id
            }
        )
        
    except Exception as e:
        logger.error(
            "unexpected_error_during_analysis",
            request_id=request_id,
            user_id=user_id,
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred during analysis",
                "details": {"error_type": type(e).__name__},
                "request_id": request_id
            }
        )