"""
Document upload endpoints for resume file processing
"""
import time
from uuid import uuid4, UUID
from typing import List, Dict, Any
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse

from app.utils.logger import get_logger
from app.models.responses import UploadResponse, ErrorResponse
from app.models.entities import Resume
from app.services.document_service import DocumentService
from app.services.database_service import db_service
from app.middleware.auth import get_current_user
from app.core.exceptions import (
    DocumentProcessingError, 
    UnsupportedFormatError, 
    FileSizeError,
    DatabaseError
)

logger = get_logger(__name__)
router = APIRouter()

# Initialize document service
document_service = DocumentService()

@router.post("/upload", response_model=UploadResponse)
async def upload_resume(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Resume file (PDF, DOCX, or TXT)"),
    current_user: dict = Depends(get_current_user)
) -> UploadResponse:
    """
    Upload and process a resume document
    
    This endpoint accepts resume files in PDF, DOCX, or TXT format,
    extracts text content, and stores the processed resume in the database.
    
    - **file**: Resume file to upload (max 10MB)
    - **Returns**: Upload confirmation with processing metadata
    
    Requirements: 1.1, 1.2, 1.3, 1.4, 1.5
    """
    start_time = time.time()
    request_id = str(uuid4())
    user_id = current_user["user_id"]
    
    print(f"DEBUG: Upload started - file: {file.filename}, content_type: {file.content_type}")
    logger.info(
        "resume_upload_started",
        request_id=request_id,
        user_id=user_id,
        filename=file.filename,
        content_type=file.content_type
    )
    
    try:
        # Process the document
        print("DEBUG: About to process document...")
        processed_doc = await document_service.process_document(file)
        print(f"DEBUG: Document processed successfully, text length: {len(processed_doc.text)}")
        
        logger.info(
            "document_processing_completed",
            request_id=request_id,
            user_id=user_id,
            filename=processed_doc.file_name,
            processing_method=processed_doc.processing_method,
            text_length=len(processed_doc.text),
            confidence_score=processed_doc.confidence_score
        )
        
        # Create user directly in auth.users table for testing
        print("DEBUG: Creating user in auth.users table...")
        try:
            async with db_service.connection_manager.get_connection() as conn:
                # First, try to insert into auth.users table
                await conn.execute(
                    """
                    INSERT INTO auth.users (id, email, created_at, updated_at, email_confirmed_at)
                    VALUES ($1, $2, NOW(), NOW(), NOW())
                    ON CONFLICT (id) DO NOTHING
                    """,
                    UUID(user_id),
                    "test@example.com"
                )
                print("DEBUG: User created in auth.users")
                
                # Then create profile
                await conn.execute(
                    """
                    INSERT INTO profiles (id, email, full_name, avatar_url)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    UUID(user_id),
                    "test@example.com",
                    "Test User",
                    ""
                )
                print("DEBUG: Profile created")
        except Exception as e:
            print(f"DEBUG: User/profile creation failed: {e}")
            # Continue anyway
        
        # Create resume record in database
        resume_id = uuid4()
        print(f"DEBUG: Creating resume with ID: {resume_id}")
        resume = Resume(
            id=resume_id,
            user_id=UUID(user_id),
            file_name=processed_doc.file_name,
            file_url="",  # We're storing text directly, not file URL
            parsed_text=processed_doc.text
        )
        
        # Store in database
        print("DEBUG: About to store resume in database...")
        created_resume = await db_service.resumes.create_resume(resume)
        print(f"DEBUG: Resume stored successfully with ID: {created_resume.id}")
        
        processing_time = time.time() - start_time
        
        logger.info(
            "resume_upload_completed",
            request_id=request_id,
            user_id=user_id,
            resume_id=str(created_resume.id),
            processing_time=processing_time
        )
        
        print(f"DEBUG: Creating response with resume_id: {created_resume.id}")
        try:
            from fastapi.responses import JSONResponse
            
            response_data = {
                "resume_id": str(created_resume.id),
                "file_name": processed_doc.file_name,
                "file_size": getattr(processed_doc, 'file_size', 0),
                "processing_method": processed_doc.processing_method,
                "confidence_score": processed_doc.confidence_score,
                "text_length": len(processed_doc.text),
                "uploaded_at": created_resume.uploaded_at.isoformat() if created_resume.uploaded_at else None
            }
            
            print("DEBUG: Response data created successfully")
            
            # Create JSONResponse with explicit CORS headers
            response = JSONResponse(
                content=response_data,
                status_code=200,
                headers={
                    "Access-Control-Allow-Origin": "http://localhost:5173",
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Allow-Credentials": "true"
                }
            )
            print("DEBUG: JSONResponse created with CORS headers")
            return response
            
        except Exception as e:
            print(f"DEBUG: Error creating response: {e}")
            raise
        
    except UnsupportedFormatError as e:
        logger.warning(
            "unsupported_file_format",
            request_id=request_id,
            user_id=user_id,
            filename=file.filename,
            detected_type=e.file_type,
            supported_types=e.supported_types
        )
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "UNSUPPORTED_FORMAT",
                "message": f"File format '{e.file_type}' is not supported",
                "details": {
                    "supported_formats": e.supported_types,
                    "detected_format": e.file_type
                },
                "request_id": request_id
            }
        )
        
    except FileSizeError as e:
        logger.warning(
            "file_size_exceeded",
            request_id=request_id,
            user_id=user_id,
            filename=file.filename,
            file_size=e.file_size,
            max_size=e.max_size
        )
        raise HTTPException(
            status_code=413,
            detail={
                "error_code": "FILE_TOO_LARGE",
                "message": f"File size ({e.file_size} bytes) exceeds maximum allowed size ({e.max_size} bytes)",
                "details": {
                    "file_size": e.file_size,
                    "max_size": e.max_size
                },
                "request_id": request_id
            }
        )
        
    except DocumentProcessingError as e:
        logger.error(
            "document_processing_failed",
            request_id=request_id,
            user_id=user_id,
            filename=file.filename,
            error=str(e),
            processing_stage=e.processing_stage
        )
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": "PROCESSING_FAILED",
                "message": f"Failed to process document: {e.message}",
                "details": {
                    "processing_stage": e.processing_stage,
                    "file_name": e.file_name
                },
                "request_id": request_id
            }
        )
        
    except DatabaseError as e:
        logger.error(
            "database_error_during_upload",
            request_id=request_id,
            user_id=user_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "DATABASE_ERROR",
                "message": "Failed to store resume in database",
                "details": {"error": str(e)},
                "request_id": request_id
            }
        )
        
    except Exception as e:
        logger.error(
            "unexpected_error_during_upload",
            request_id=request_id,
            user_id=user_id,
            filename=file.filename,
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred during file processing",
                "details": {"error_type": type(e).__name__},
                "request_id": request_id
            }
        )

@router.get("/resumes", response_model=List[Dict[str, Any]])
async def get_user_resumes(
    current_user: dict = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """
    Get all uploaded resumes for the current user
    
    Returns a list of all resumes uploaded by the authenticated user,
    including metadata but not the full text content.
    
    - **Returns**: List of user's uploaded resumes
    """
    user_id = current_user["user_id"]
    
    logger.info("user_resumes_requested", user_id=user_id)
    
    try:
        resumes = await db_service.resumes.get_user_resumes(user_id)
        
        resume_list = [
            {
                "resume_id": str(resume.id),
                "file_name": resume.file_name,
                "text_length": len(resume.parsed_text) if resume.parsed_text else 0,
                "uploaded_at": resume.uploaded_at.isoformat()
            }
            for resume in resumes
        ]
        
        logger.info(
            "user_resumes_retrieved",
            user_id=user_id,
            resume_count=len(resume_list)
        )
        
        return resume_list
        
    except DatabaseError as e:
        logger.error(
            "failed_to_retrieve_user_resumes",
            user_id=user_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "DATABASE_ERROR",
                "message": "Failed to retrieve user resumes",
                "details": {"error": str(e)}
            }
        )