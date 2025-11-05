"""
Analysis history endpoints for retrieving past analyses
"""
from uuid import UUID
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query

from app.utils.logger import get_logger
from app.models.responses import AnalysisListResponse
from app.services.database_service import db_service
from app.middleware.auth import get_current_user
from app.core.exceptions import DatabaseError

logger = get_logger(__name__)
router = APIRouter()

@router.get("/analyses", response_model=AnalysisListResponse)
async def get_user_analyses(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(10, ge=1, le=100, description="Number of items per page"),
    current_user: dict = Depends(get_current_user)
) -> AnalysisListResponse:
    """
    Get paginated list of user's past analyses
    
    Returns a paginated list of all analyses performed by the authenticated user,
    including basic metadata and summary information.
    
    - **page**: Page number (starting from 1)
    - **page_size**: Number of analyses per page (1-100)
    - **Returns**: Paginated list of user analyses
    
    Requirements: 7.2, 7.3
    """
    user_id = current_user["user_id"]
    
    logger.info(
        "user_analyses_requested",
        user_id=user_id,
        page=page,
        page_size=page_size
    )
    
    try:
        # Calculate offset for pagination
        offset = (page - 1) * page_size
        
        # Get analyses and total count
        analyses = await db_service.get_user_analyses(
            user_id=UUID(user_id),
            limit=page_size,
            offset=offset
        )
        
        total_count = await db_service.analyses.get_user_analyses_count(UUID(user_id))
        
        # Format analyses for response
        analysis_list = [
            {
                "analysis_id": str(analysis.id),
                "job_title": analysis.job_title,
                "match_score": analysis.match_score,
                "created_at": analysis.created_at.isoformat(),
                "matched_keywords_count": len(analysis.matched_keywords) if analysis.matched_keywords else 0,
                "missing_keywords_count": len(analysis.missing_keywords) if analysis.missing_keywords else 0
            }
            for analysis in analyses
        ]
        
        # Calculate pagination info
        has_next = (offset + page_size) < total_count
        
        logger.info(
            "user_analyses_retrieved",
            user_id=user_id,
            page=page,
            page_size=page_size,
            total_count=total_count,
            returned_count=len(analysis_list),
            has_next=has_next
        )
        
        return AnalysisListResponse(
            analyses=analysis_list,
            total_count=total_count,
            page=page,
            page_size=page_size,
            has_next=has_next
        )
        
    except DatabaseError as e:
        logger.error(
            "failed_to_retrieve_user_analyses",
            user_id=user_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "DATABASE_ERROR",
                "message": "Failed to retrieve user analyses",
                "details": {"error": str(e)}
            }
        )

@router.get("/analyses/{analysis_id}")
async def get_analysis_by_id(
    analysis_id: UUID,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get detailed analysis by ID
    
    Returns complete analysis details including AI feedback,
    keyword analysis, and all metadata for a specific analysis.
    
    - **analysis_id**: Unique identifier of the analysis
    - **Returns**: Complete analysis details
    
    Requirements: 7.2, 7.3
    """
    user_id = current_user["user_id"]
    
    logger.info(
        "analysis_details_requested",
        user_id=user_id,
        analysis_id=str(analysis_id)
    )
    
    try:
        # Get analysis from database
        analysis = await db_service.get_analysis_by_id(analysis_id)
        
        if not analysis:
            logger.warning(
                "analysis_not_found",
                user_id=user_id,
                analysis_id=str(analysis_id)
            )
            raise HTTPException(
                status_code=404,
                detail={
                    "error_code": "ANALYSIS_NOT_FOUND",
                    "message": f"Analysis with ID {analysis_id} not found"
                }
            )
        
        # Verify analysis belongs to current user
        if str(analysis.user_id) != user_id:
            logger.warning(
                "unauthorized_analysis_access",
                user_id=user_id,
                analysis_id=str(analysis_id),
                analysis_owner=str(analysis.user_id)
            )
            raise HTTPException(
                status_code=403,
                detail={
                    "error_code": "UNAUTHORIZED_ACCESS",
                    "message": "You don't have permission to access this analysis"
                }
            )
        
        # Format complete analysis response
        analysis_details = {
            "analysis_id": str(analysis.id),
            "job_title": analysis.job_title,
            "job_description": analysis.job_description,
            "match_score": analysis.match_score,
            "ai_feedback": analysis.ai_feedback,
            "matched_keywords": analysis.matched_keywords,
            "missing_keywords": analysis.missing_keywords,
            "created_at": analysis.created_at.isoformat(),
            "resume_id": str(analysis.resume_id) if analysis.resume_id else None
        }
        
        logger.info(
            "analysis_details_retrieved",
            user_id=user_id,
            analysis_id=str(analysis_id),
            match_score=analysis.match_score
        )
        
        return analysis_details
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
        
    except DatabaseError as e:
        logger.error(
            "failed_to_retrieve_analysis",
            user_id=user_id,
            analysis_id=str(analysis_id),
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "DATABASE_ERROR",
                "message": "Failed to retrieve analysis",
                "details": {"error": str(e)}
            }
        )

@router.delete("/analyses/{analysis_id}")
async def delete_analysis(
    analysis_id: UUID,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, str]:
    """
    Delete an analysis by ID
    
    Permanently removes an analysis from the user's history.
    This action cannot be undone.
    
    - **analysis_id**: Unique identifier of the analysis to delete
    - **Returns**: Deletion confirmation
    """
    user_id = current_user["user_id"]
    
    logger.info(
        "analysis_deletion_requested",
        user_id=user_id,
        analysis_id=str(analysis_id)
    )
    
    try:
        # First verify the analysis exists and belongs to the user
        analysis = await db_service.get_analysis_by_id(analysis_id)
        
        if not analysis:
            raise HTTPException(
                status_code=404,
                detail={
                    "error_code": "ANALYSIS_NOT_FOUND",
                    "message": f"Analysis with ID {analysis_id} not found"
                }
            )
        
        # Verify analysis belongs to current user
        if str(analysis.user_id) != user_id:
            raise HTTPException(
                status_code=403,
                detail={
                    "error_code": "UNAUTHORIZED_ACCESS",
                    "message": "You don't have permission to delete this analysis"
                }
            )
        
        # Delete the analysis
        async with db_service.connection_manager.get_connection() as conn:
            await conn.execute(
                "DELETE FROM analyses WHERE id = $1",
                analysis_id
            )
        
        logger.info(
            "analysis_deleted",
            user_id=user_id,
            analysis_id=str(analysis_id)
        )
        
        return {
            "message": "Analysis deleted successfully",
            "analysis_id": str(analysis_id)
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
        
    except DatabaseError as e:
        logger.error(
            "failed_to_delete_analysis",
            user_id=user_id,
            analysis_id=str(analysis_id),
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "DATABASE_ERROR",
                "message": "Failed to delete analysis",
                "details": {"error": str(e)}
            }
        )