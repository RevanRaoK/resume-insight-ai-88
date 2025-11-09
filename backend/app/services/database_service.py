"""
Database operations service with async connection management and repositories
"""
import asyncio
import asyncpg
import socket
import urllib.parse
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from contextlib import asynccontextmanager

from app.config import settings
from app.models.entities import UserProfile, Resume, Analysis, AnalysisResult
from app.utils.logger import get_logger
from app.utils.async_utils import connection_optimizer, async_timer
from app.core.exceptions import DatabaseError

logger = get_logger(__name__)


class DatabaseConnectionManager:
    """Manages async database connections with connection pooling"""
    
    def __init__(self):
        self._pool: Optional[asyncpg.Pool] = None
        self._lock = asyncio.Lock()
    
    async def initialize(self) -> None:
        """Initialize database connection pool"""
        async with self._lock:
            if self._pool is None:
                try:
                    logger.info("Initializing database connection pool")
                    logger.info(f"Attempting to connect to: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'unknown'}")
                    
                    # Parse URL to handle IPv4 resolution for Supabase
                    parsed = urllib.parse.urlparse(settings.DATABASE_URL)
                    
                    # For Supabase db subdomain, use direct IPv4 to avoid DNS issues
                    if parsed.hostname == 'db.deeomgotpmynipwwbkuf.supabase.co':
                        # Use known IPv4 addresses for this Supabase instance
                        ipv4_addresses = ['104.18.38.10', '172.64.149.246']
                        
                        for ipv4_addr in ipv4_addresses:
                            try:
                                logger.info(f"Attempting connection to {parsed.hostname} via IPv4: {ipv4_addr}")
                                
                                # Create connection with IPv4 address
                                self._pool = await asyncio.wait_for(
                                    asyncpg.create_pool(
                                        host=ipv4_addr,
                                        port=parsed.port or 5432,
                                        user=parsed.username,
                                        password=parsed.password,
                                        database=parsed.path.lstrip('/'),
                                        ssl='require',
                                        min_size=3,
                                        max_size=10,
                                        command_timeout=15,
                                        server_settings={'jit': 'off'}
                                    ),
                                    timeout=10.0
                                )
                                logger.info(f"Database connection pool initialized successfully with IPv4: {ipv4_addr}")
                                break
                            except (asyncio.TimeoutError, Exception) as e:
                                logger.warning(f"Failed to connect via {ipv4_addr}: {e}")
                                if ipv4_addr == ipv4_addresses[-1]:  # Last attempt
                                    raise
                    else:
                        # Standard connection for other hosts
                        self._pool = await asyncpg.create_pool(
                            settings.DATABASE_URL,
                            min_size=5,
                            max_size=20,
                            command_timeout=30,
                            ssl='require' if 'supabase.co' in settings.DATABASE_URL else None,
                            server_settings={'jit': 'off'}
                        )
                        logger.info("Database connection pool initialized successfully")
                except Exception as e:
                    logger.error("Failed to initialize database connection pool", error=str(e))
                    logger.error(f"Connection URL format: {settings.DATABASE_URL[:20]}...{settings.DATABASE_URL[-20:] if len(settings.DATABASE_URL) > 40 else settings.DATABASE_URL[20:]}")
                    
                    # Try alternative connection methods
                    try:
                        logger.info("Attempting alternative connection method...")
                        import urllib.parse
                        parsed = urllib.parse.urlparse(settings.DATABASE_URL)
                        
                        # Try with explicit IPv4 preference
                        self._pool = await asyncpg.create_pool(
                            host=parsed.hostname,
                            port=parsed.port or 5432,
                            user=parsed.username,
                            password=parsed.password,
                            database=parsed.path.lstrip('/'),
                            ssl='require',
                            min_size=3,
                            max_size=10,
                            command_timeout=30
                        )
                        logger.info("Alternative connection method successful")
                    except Exception as e2:
                        logger.error("Alternative connection method failed", error=str(e2))
                        
                        # Try with pooler connection as final fallback
                        try:
                            logger.info("Attempting pooler connection...")
                            pooler_url = settings.DATABASE_URL.replace(
                                "db.deeomgotpmynipwwbkuf.supabase.co:5432",
                                "aws-0-ap-south-1.pooler.supabase.com:6543"
                            )
                            
                            self._pool = await asyncpg.create_pool(
                                pooler_url,
                                min_size=3,
                                max_size=10,
                                command_timeout=30,
                                ssl='require'
                            )
                            logger.info("Pooler connection successful")
                        except Exception as e3:
                            logger.error("All connection methods failed", error=str(e3))
                            raise DatabaseError(f"Failed to initialize database connection pool: {e}")
    
    async def close(self) -> None:
        """Close database connection pool"""
        async with self._lock:
            if self._pool:
                logger.info("Closing database connection pool")
                await self._pool.close()
                self._pool = None
    
    @asynccontextmanager
    async def get_connection(self):
        """Get optimized database connection from pool with performance monitoring"""
        if not self._pool:
            await self.initialize()
        
        async with connection_optimizer.get_optimized_connection(self._pool) as connection:
            yield connection
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive database health check with performance metrics"""
        try:
            async with self.get_connection() as conn:
                # Test basic connectivity
                result = await conn.fetchval("SELECT 1")
                
                # Get comprehensive pool metrics
                pool_metrics = await connection_optimizer.get_pool_metrics(self._pool)
                
                return {
                    "status": "healthy" if result == 1 else "unhealthy",
                    "pool_metrics": pool_metrics,
                    "timestamp": datetime.utcnow().isoformat()
                }
        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "error": str(e),
                "pool_metrics": await connection_optimizer.get_pool_metrics(self._pool),
                "timestamp": datetime.utcnow().isoformat()
            }


class UserRepository:
    """Repository for user profile operations"""
    
    def __init__(self, connection_manager: DatabaseConnectionManager):
        self.connection_manager = connection_manager
    
    @async_timer
    async def get_user_by_id(self, user_id: UUID) -> Optional[UserProfile]:
        """Get user profile by ID"""
        try:
            async with self.connection_manager.get_connection() as conn:
                row = await conn.fetchrow(
                    "SELECT id, email, full_name, avatar_url, created_at FROM profiles WHERE id = $1",
                    user_id
                )
                
                if row:
                    return UserProfile(
                        id=row['id'],
                        email=row['email'],
                        full_name=row['full_name'],
                        avatar_url=row['avatar_url'],
                        created_at=row['created_at']
                    )
                return None
        except Exception as e:
            logger.error("Failed to get user by ID", user_id=str(user_id), error=str(e))
            raise DatabaseError(f"Failed to get user: {e}")
    
    @async_timer
    async def create_user_profile(self, user_profile: UserProfile) -> UserProfile:
        """Create new user profile"""
        try:
            async with self.connection_manager.get_connection() as conn:
                await conn.execute(
                    """
                    INSERT INTO profiles (id, email, full_name, avatar_url)
                    VALUES ($1, $2, $3, $4)
                    """,
                    user_profile.id,
                    user_profile.email,
                    user_profile.full_name,
                    user_profile.avatar_url
                )
                
                logger.info("User profile created", user_id=str(user_profile.id))
                return user_profile
        except Exception as e:
            logger.error("Failed to create user profile", user_id=str(user_profile.id), error=str(e))
            raise DatabaseError(f"Failed to create user profile: {e}")


class ResumeRepository:
    """Repository for resume operations"""
    
    def __init__(self, connection_manager: DatabaseConnectionManager):
        self.connection_manager = connection_manager
    
    @async_timer
    async def create_resume(self, resume: Resume) -> Resume:
        """Create new resume record"""
        try:
            async with self.connection_manager.get_connection() as conn:
                row = await conn.fetchrow(
                    """
                    INSERT INTO resumes (user_id, file_name, file_url, parsed_text)
                    VALUES ($1, $2, $3, $4)
                    RETURNING id, uploaded_at
                    """,
                    resume.user_id,
                    resume.file_name,
                    resume.file_url,
                    resume.parsed_text
                )
                
                resume.id = row['id']
                resume.uploaded_at = row['uploaded_at']
                
                logger.info("Resume created", resume_id=str(resume.id), user_id=str(resume.user_id))
                return resume
        except Exception as e:
            logger.error("Failed to create resume", user_id=str(resume.user_id), error=str(e))
            raise DatabaseError(f"Failed to create resume: {e}")
    
    async def get_resume_by_id(self, resume_id: UUID) -> Optional[Resume]:
        """Get resume by ID"""
        try:
            async with self.connection_manager.get_connection() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT id, user_id, file_name, file_url, parsed_text, uploaded_at
                    FROM resumes WHERE id = $1
                    """,
                    resume_id
                )
                
                if row:
                    return Resume(
                        id=row['id'],
                        user_id=row['user_id'],
                        file_name=row['file_name'],
                        file_url=row['file_url'],
                        parsed_text=row['parsed_text'],
                        uploaded_at=row['uploaded_at']
                    )
                return None
        except Exception as e:
            logger.error("Failed to get resume by ID", resume_id=str(resume_id), error=str(e))
            raise DatabaseError(f"Failed to get resume: {e}")
    
    async def get_user_resumes(self, user_id: UUID) -> List[Resume]:
        """Get all resumes for a user"""
        try:
            async with self.connection_manager.get_connection() as conn:
                rows = await conn.fetch(
                    """
                    SELECT id, user_id, file_name, file_url, parsed_text, uploaded_at
                    FROM resumes WHERE user_id = $1
                    ORDER BY uploaded_at DESC
                    """,
                    user_id
                )
                
                return [
                    Resume(
                        id=row['id'],
                        user_id=row['user_id'],
                        file_name=row['file_name'],
                        file_url=row['file_url'],
                        parsed_text=row['parsed_text'],
                        uploaded_at=row['uploaded_at']
                    )
                    for row in rows
                ]
        except Exception as e:
            logger.error("Failed to get user resumes", user_id=str(user_id), error=str(e))
            raise DatabaseError(f"Failed to get user resumes: {e}")
    
    async def update_resume_text(self, resume_id: UUID, parsed_text: str) -> None:
        """Update parsed text for a resume"""
        try:
            async with self.connection_manager.get_connection() as conn:
                await conn.execute(
                    "UPDATE resumes SET parsed_text = $1 WHERE id = $2",
                    parsed_text,
                    resume_id
                )
                
                logger.info("Resume text updated", resume_id=str(resume_id))
        except Exception as e:
            logger.error("Failed to update resume text", resume_id=str(resume_id), error=str(e))
            raise DatabaseError(f"Failed to update resume text: {e}")


class AnalysisRepository:
    """Repository for analysis operations"""
    
    def __init__(self, connection_manager: DatabaseConnectionManager):
        self.connection_manager = connection_manager
    
    @async_timer
    async def create_analysis(self, analysis_result: AnalysisResult) -> str:
        """Create new analysis record and return analysis ID"""
        try:
            async with self.connection_manager.get_connection() as conn:
                # Start explicit transaction to ensure data is committed
                async with conn.transaction():
                    analysis_id = await conn.fetchval(
                        """
                        INSERT INTO analyses (
                            user_id, resume_id, job_title, job_description,
                            match_score, ai_feedback, matched_keywords, missing_keywords
                        )
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        RETURNING id
                        """,
                        analysis_result.user_id,
                        analysis_result.resume_id,
                        analysis_result.job_title,
                        analysis_result.job_description,
                        analysis_result.match_score,
                        analysis_result.ai_feedback,
                        analysis_result.matched_keywords,
                        analysis_result.missing_keywords
                    )
                    
                    # Verify the record was actually inserted
                    verification = await conn.fetchval(
                        "SELECT id FROM analyses WHERE id = $1",
                        analysis_id
                    )
                    
                    if not verification:
                        raise DatabaseError("Analysis was not properly saved to database")
                    
                    logger.info(
                        "Analysis created and verified",
                        analysis_id=str(analysis_id),
                        user_id=str(analysis_result.user_id),
                        match_score=analysis_result.match_score,
                        processing_time=analysis_result.processing_time
                    )
                    
                    return str(analysis_id)
        except Exception as e:
            logger.error("Failed to create analysis", user_id=str(analysis_result.user_id), error=str(e))
            raise DatabaseError(f"Failed to create analysis: {e}")
    
    async def get_analysis_by_id(self, analysis_id: UUID) -> Optional[Analysis]:
        """Get analysis by ID"""
        try:
            async with self.connection_manager.get_connection() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT id, user_id, resume_id, job_title, job_description,
                           match_score, ai_feedback, matched_keywords, missing_keywords, created_at
                    FROM analyses WHERE id = $1
                    """,
                    analysis_id
                )
                
                if row:
                    return Analysis(
                        id=row['id'],
                        user_id=row['user_id'],
                        resume_id=row['resume_id'],
                        job_title=row['job_title'],
                        job_description=row['job_description'],
                        match_score=row['match_score'],
                        ai_feedback=row['ai_feedback'],
                        matched_keywords=row['matched_keywords'],
                        missing_keywords=row['missing_keywords'],
                        created_at=row['created_at']
                    )
                return None
        except Exception as e:
            logger.error("Failed to get analysis by ID", analysis_id=str(analysis_id), error=str(e))
            raise DatabaseError(f"Failed to get analysis: {e}")
    
    async def get_user_analyses(
        self, 
        user_id: UUID, 
        limit: int = 50, 
        offset: int = 0
    ) -> List[Analysis]:
        """Get all analyses for a user with pagination"""
        try:
            async with self.connection_manager.get_connection() as conn:
                rows = await conn.fetch(
                    """
                    SELECT id, user_id, resume_id, job_title, job_description,
                           match_score, ai_feedback, matched_keywords, missing_keywords, created_at
                    FROM analyses 
                    WHERE user_id = $1
                    ORDER BY created_at DESC
                    LIMIT $2 OFFSET $3
                    """,
                    user_id,
                    limit,
                    offset
                )
                
                return [
                    Analysis(
                        id=row['id'],
                        user_id=row['user_id'],
                        resume_id=row['resume_id'],
                        job_title=row['job_title'],
                        job_description=row['job_description'],
                        match_score=row['match_score'],
                        ai_feedback=row['ai_feedback'],
                        matched_keywords=row['matched_keywords'],
                        missing_keywords=row['missing_keywords'],
                        created_at=row['created_at']
                    )
                    for row in rows
                ]
        except Exception as e:
            logger.error("Failed to get user analyses", user_id=str(user_id), error=str(e))
            raise DatabaseError(f"Failed to get user analyses: {e}")
    
    async def get_user_analyses_count(self, user_id: UUID) -> int:
        """Get total count of analyses for a user"""
        try:
            async with self.connection_manager.get_connection() as conn:
                count = await conn.fetchval(
                    "SELECT COUNT(*) FROM analyses WHERE user_id = $1",
                    user_id
                )
                return count
        except Exception as e:
            logger.error("Failed to get user analyses count", user_id=str(user_id), error=str(e))
            raise DatabaseError(f"Failed to get user analyses count: {e}")


class DatabaseService:
    """Main database service orchestrating all repositories"""
    
    def __init__(self):
        self.connection_manager = DatabaseConnectionManager()
        self.users = UserRepository(self.connection_manager)
        self.resumes = ResumeRepository(self.connection_manager)
        self.analyses = AnalysisRepository(self.connection_manager)
    
    async def initialize(self) -> None:
        """Initialize database service"""
        await self.connection_manager.initialize()
        logger.info("Database service initialized")
    
    async def close(self) -> None:
        """Close database service"""
        await self.connection_manager.close()
        logger.info("Database service closed")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive database health check"""
        return await self.connection_manager.health_check()
    
    async def store_analysis(self, analysis_result: AnalysisResult) -> str:
        """Store complete analysis results and return analysis_id"""
        return await self.analyses.create_analysis(analysis_result)
    
    async def get_user_analyses(
        self, 
        user_id: UUID, 
        limit: int = 50, 
        offset: int = 0
    ) -> List[Analysis]:
        """Retrieve all analyses for a specific user with pagination"""
        return await self.analyses.get_user_analyses(user_id, limit, offset)
    
    async def get_analysis_by_id(self, analysis_id: UUID) -> Optional[Analysis]:
        """Get specific analysis by ID"""
        return await self.analyses.get_analysis_by_id(analysis_id)


# Global database service instance
db_service = DatabaseService()