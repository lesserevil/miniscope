"""Video browsing API router for Hollywood Script Generator.

This module provides endpoints for browsing and retrieving video metadata.
"""

from typing import List, Optional, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from hollywood_script_generator.db.models import Video, Job
from hollywood_script_generator.db.base import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


# Pydantic response models
class VideoResponse(BaseModel):
    """Response model for video metadata."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    path: str
    video_metadata: dict
    created_at: datetime
    updated_at: datetime


class JobSummaryResponse(BaseModel):
    """Summary of job status for video details."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    progress: float
    created_at: datetime


class VideoDetailResponse(BaseModel):
    """Detailed response model including job status."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    path: str
    video_metadata: dict
    created_at: datetime
    updated_at: datetime
    jobs: List[JobSummaryResponse]


# Database session dependency
# Note: In production, this should be imported from a central location
# For now, we define it here for simplicity
_engine = None
_SessionLocal = None


def get_engine():
    """Get or create the database engine."""
    global _engine
    if _engine is None:
        from hollywood_script_generator.core.config import get_settings

        settings = get_settings()
        _engine = create_engine(
            str(settings.DATABASE_URL),
            connect_args={"check_same_thread": False}
            if "sqlite" in str(settings.DATABASE_URL)
            else {},
        )
    return _engine


def get_session_local():
    """Get or create the session local class."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=get_engine()
        )
    return _SessionLocal


def get_db():
    """Get database session dependency."""
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Create router
video_router = APIRouter(prefix="/videos", tags=["videos"])


@video_router.get("", response_model=List[VideoResponse])
async def list_videos(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
) -> List[Video]:
    """List all videos with pagination.

    Returns a list of video metadata records from the database.

    Args:
        skip: Number of records to skip (for pagination).
        limit: Maximum number of records to return.
        db: Database session dependency.

    Returns:
        List of Video objects with metadata.

    Example:
        GET /api/v1/videos?skip=0&limit=10
    """
    query = select(Video).offset(skip).limit(limit)
    result = db.execute(query)
    videos = result.scalars().all()
    return list(videos)


@video_router.get("/{video_id}", response_model=VideoDetailResponse)
async def get_video(video_id: int, db: Session = Depends(get_db)) -> Video:
    """Get detailed information about a specific video.

    Retrieves a single video by its ID, including associated job status information.

    Args:
        video_id: The unique identifier of the video.
        db: Database session dependency.

    Returns:
        Video object with metadata and job status.

    Raises:
        HTTPException: 404 if video not found.

    Example:
        GET /api/v1/videos/1
    """
    video = db.get(Video, video_id)

    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video with ID {video_id} not found",
        )

    # Eager load jobs relationship
    db.refresh(video)

    return video
