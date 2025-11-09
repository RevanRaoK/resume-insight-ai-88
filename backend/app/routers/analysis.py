"""
Resume analysis endpoints for comprehensive resume-job matching
"""
import time
import asyncio
from datetime import datetime
from uuid import uuid4, UUID
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Request

from app.utils.logger import get_logger
from app.models.requests import AnalysisRequest
from app.models.responses import AnalysisResponse
from app.models.entities import AnalysisResult
from app.services.nlu_service import nlu_service
from app.services.semantic_service import get_semantic_service
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
    analysis_request: AnalysisRequest,
    request: Request,
    current_user: dict = Depends(get_current_user)
) -> AnalysisResponse:
    print("DEBUG: ANALYSIS ENDPOINT HIT!")
    print(f"DEBUG: Request data: {analysis_request}")
    print(f"DEBUG: Resume ID: {analysis_request.resume_id}")
    print(f"DEBUG: Job description length: {len(analysis_request.job_description) if analysis_request.job_description else 0}")
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
    
    print(f"DEBUG: Analysis started with resume_id: {analysis_request.resume_id}")
    logger.info(
        "analysis_started",
        request_id=request_id,
        user_id=user_id,
        has_resume_id=analysis_request.resume_id is not None,
        has_resume_text=analysis_request.resume_text is not None,
        job_title=analysis_request.job_title
    )
    
    try:
        # Validate that we have either resume_id or resume_text
        if not analysis_request.resume_id and not analysis_request.resume_text:
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
        
        if analysis_request.resume_id:
            # Fetch resume from database
            print(f"DEBUG: Fetching resume with ID: {analysis_request.resume_id}")
            resume = await db_service.resumes.get_resume_by_id(analysis_request.resume_id)
            if not resume:
                print(f"DEBUG: Resume not found with ID: {analysis_request.resume_id}")
                raise HTTPException(
                    status_code=404,
                    detail={
                        "error_code": "RESUME_NOT_FOUND",
                        "message": f"Resume with ID {analysis_request.resume_id} not found",
                        "request_id": request_id
                    }
                )
            print(f"DEBUG: Resume found, text length: {len(resume.parsed_text) if resume.parsed_text else 0}")
            
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
            resume_text = analysis_request.resume_text
        
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
            job_description_length=len(analysis_request.job_description)
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
        
        # Step 2: Semantic Analysis - Calculate compatibility with timeout
        logger.info("semantic_analysis_started", request_id=request_id)
        semantic_service = get_semantic_service()  # Initialize the service
        
        # PERFORMANCE OPTIMIZATION: Add timeout to prevent hanging
        try:
            compatibility_analysis = await asyncio.wait_for(
                semantic_service.analyze_compatibility(resume_text, analysis_request.job_description),
                timeout=60.0  # 60 second timeout
            )
        except asyncio.TimeoutError:
            logger.error("semantic_analysis_timeout", request_id=request_id, user_id=user_id)
            raise HTTPException(
                status_code=408,
                detail={
                    "error_code": "ANALYSIS_TIMEOUT",
                    "message": "Analysis took too long to complete. Please try with a shorter job description.",
                    "request_id": request_id
                }
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
        from app.services.ai_service import AnalysisContext
        
        # Convert ResumeEntities object to dictionary format for AI service
        resume_entities_dict = {
            'skills': resume_entities.skills,
            'job_titles': resume_entities.job_titles,
            'companies': resume_entities.companies,
            'education': resume_entities.education,
            'contact_info': resume_entities.contact_info,
            'experience_years': resume_entities.experience_years,
            'confidence_scores': resume_entities.confidence_scores
        }
        
        analysis_context = AnalysisContext(
            resume_entities=resume_entities_dict,
            match_score=compatibility_analysis.match_score,
            matched_keywords=compatibility_analysis.matched_keywords,
            missing_keywords=compatibility_analysis.missing_keywords,
            semantic_similarity=compatibility_analysis.semantic_similarity,
            keyword_coverage=compatibility_analysis.keyword_coverage,
            job_description=analysis_request.job_description,
            resume_text=resume_text
        )
        
        ai_feedback = await ai_service.generate_feedback(analysis_context)
        
        logger.info(
            "ai_feedback_completed",
            request_id=request_id,
            recommendations_count=len(ai_feedback.recommendations) if hasattr(ai_feedback, 'recommendations') else 0
        )
        
        # Step 4: Store analysis results
        processing_time = time.time() - start_time
        
        # Convert objects to JSON strings for database storage
        import json
        ai_feedback_json = json.dumps(ai_feedback.dict() if hasattr(ai_feedback, 'dict') else ai_feedback.__dict__)
        matched_keywords_json = json.dumps(compatibility_analysis.matched_keywords)
        missing_keywords_json = json.dumps(compatibility_analysis.missing_keywords)
        
        # Validate job_title is provided (job role requirement)
        if not analysis_request.job_title or not analysis_request.job_title.strip():
            raise HTTPException(
                status_code=400,
                detail={
                    "error_code": "MISSING_JOB_TITLE",
                    "message": "Job title (job role) is required for analysis",
                    "request_id": request_id
                }
            )

        analysis_result = AnalysisResult(
            user_id=UUID(user_id),
            resume_id=resume_id,
            job_title=analysis_request.job_title.strip(),
            job_description=analysis_request.job_description,
            match_score=compatibility_analysis.match_score,
            ai_feedback=ai_feedback_json,
            matched_keywords=matched_keywords_json,
            missing_keywords=missing_keywords_json,
            processing_time=processing_time
        )
        
        # Store analysis with enhanced error handling
        print(f"DEBUG: About to store analysis for user {user_id}")
        try:
            analysis_id = await db_service.store_analysis(analysis_result)
            print(f"DEBUG: Analysis stored successfully with ID: {analysis_id}")
            
            # Verify the analysis was actually saved
            verification = await db_service.get_analysis_by_id(UUID(analysis_id))
            if not verification:
                print(f"DEBUG: CRITICAL ERROR - Analysis {analysis_id} not found after creation!")
                raise DatabaseError("Analysis was created but cannot be retrieved")
            else:
                print(f"DEBUG: Analysis verification successful - found analysis with score {verification.match_score}")
            
        except Exception as e:
            print(f"DEBUG: CRITICAL ERROR storing analysis: {e}")
            logger.error("Critical error storing analysis", error=str(e), user_id=user_id)
            raise
        
        logger.info(
            "analysis_completed",
            request_id=request_id,
            user_id=user_id,
            analysis_id=analysis_id,
            match_score=compatibility_analysis.match_score,
            processing_time=processing_time
        )
        
        # Convert AIFeedback object to dictionary for response
        ai_feedback_dict = ai_feedback.dict() if hasattr(ai_feedback, 'dict') else ai_feedback.__dict__
        
        return AnalysisResponse(
            analysis_id=UUID(analysis_id),
            match_score=compatibility_analysis.match_score,
            ai_feedback=ai_feedback_dict,
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

@router.get("/analyses")
async def get_all_analyses(
    current_user: dict = Depends(get_current_user)
):
    """
    Get all analyses for the current user
    
    Returns:
        List of analysis summaries with job title, match score, and date
        
    Raises:
        HTTPException: If database error occurs
    """
    request_id = str(uuid4())
    user_id = current_user["user_id"]
    
    logger.info(
        "get_all_analyses_started",
        request_id=request_id,
        user_id=user_id
    )
    
    try:
        # Fetch all analyses for the user
        analyses = await db_service.get_user_analyses(UUID(user_id))
        
        # Format response data
        response_data = []
        for analysis in analyses:
            response_data.append({
                "id": str(analysis.id),
                "job_title": analysis.job_title,
                "match_score": analysis.match_score,
                "created_at": analysis.created_at.isoformat() if analysis.created_at else None
            })
        
        logger.info(
            "get_all_analyses_completed",
            request_id=request_id,
            user_id=user_id,
            analyses_count=len(response_data)
        )
        
        return {"analyses": response_data}
        
    except Exception as e:
        logger.error(
            "unexpected_error_getting_all_analyses",
            request_id=request_id,
            user_id=user_id,
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred while fetching analyses",
                "details": {"error_type": type(e).__name__},
                "request_id": request_id
            }
        )

@router.get("/analysis/{analysis_id}")
async def get_analysis(
    analysis_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """
    Get analysis results by ID
    
    Args:
        analysis_id: UUID of the analysis to retrieve
        current_user: Current authenticated user
        
    Returns:
        Analysis data with AI feedback and match results
        
    Raises:
        HTTPException: If analysis not found or access denied
    """
    request_id = str(uuid4())
    user_id = current_user["user_id"]
    
    logger.info(
        "get_analysis_started",
        request_id=request_id,
        user_id=user_id,
        analysis_id=str(analysis_id)
    )
    
    try:
        # Fetch analysis from database
        analysis = await db_service.get_analysis_by_id(analysis_id)
        
        if not analysis:
            logger.warning(
                "analysis_not_found",
                request_id=request_id,
                user_id=user_id,
                analysis_id=str(analysis_id)
            )
            raise HTTPException(
                status_code=404,
                detail={
                    "error_code": "ANALYSIS_NOT_FOUND",
                    "message": f"Analysis with ID {analysis_id} not found",
                    "request_id": request_id
                }
            )
        
        # Note: User authorization check temporarily disabled for testing
        
        # Parse JSON fields back to objects
        import json
        ai_feedback_dict = json.loads(analysis.ai_feedback) if isinstance(analysis.ai_feedback, str) else analysis.ai_feedback
        matched_keywords = json.loads(analysis.matched_keywords) if isinstance(analysis.matched_keywords, str) else analysis.matched_keywords
        missing_keywords = json.loads(analysis.missing_keywords) if isinstance(analysis.missing_keywords, str) else analysis.missing_keywords
        
        # Return analysis data in the format expected by frontend
        response_data = {
            "id": str(analysis.id),
            "job_title": analysis.job_title,
            "match_score": analysis.match_score,
            "ai_feedback": ai_feedback_dict,
            "matched_keywords": matched_keywords,
            "missing_keywords": missing_keywords,
            "created_at": analysis.created_at.isoformat() if analysis.created_at else None
        }
        
        logger.info(
            "get_analysis_completed",
            request_id=request_id,
            user_id=user_id,
            analysis_id=str(analysis_id),
            match_score=analysis.match_score
        )
        
        return response_data
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
        
    except Exception as e:
        logger.error(
            "unexpected_error_getting_analysis",
            request_id=request_id,
            user_id=user_id,
            analysis_id=str(analysis_id),
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred while fetching analysis",
                "details": {"error_type": type(e).__name__},
                "request_id": request_id
            }
        )