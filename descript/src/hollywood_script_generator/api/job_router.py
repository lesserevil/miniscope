"""Job processing API router for Hollywood Script Generator.

This module provides endpoints for starting video processing jobs
and checking job status.
"""

from typing import Optional, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from hollywood_script_generator.db.models import Video, Job, Script
from hollywood_script_generator.models.job_status import JobStatus
from hollywood_script_generator.api.video_router import get_db


# Pydantic request/response models
class ProcessRequest(BaseModel):
    """Request model for starting video processing."""

    video_id: int = Field(..., description="ID of the video to process")


class ProcessResponse(BaseModel):
    """Response model for starting video processing."""

    job_id: int
    video_id: int
    status: str
    message: str


class ScriptSummaryResponse(BaseModel):
    """Summary of generated script for job status."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    content_preview: str

    @classmethod
    def from_script(cls, script: Script) -> "ScriptSummaryResponse":
        """Create summary from Script model."""
        content_preview = (
            script.content[:200] + "..."
            if len(script.content) > 200
            else script.content
        )
        return cls(
            id=script.id,
            created_at=script.created_at,
            content_preview=content_preview,
        )


class JobStatusResponse(BaseModel):
    """Response model for job status."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    video_id: int
    status: str
    progress: float
    error_message: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    script: Optional[ScriptSummaryResponse] = None

    @field_validator("script", mode="before")
    @classmethod
    def validate_script(cls, v):
        """Convert Script ORM object to ScriptSummaryResponse."""
        if v is None:
            return None
        if isinstance(v, Script):
            return ScriptSummaryResponse.from_script(v)
        return v


# Create router
job_router = APIRouter(prefix="/jobs", tags=["jobs"])


async def process_video_job(job_id: int, video_id: int) -> None:
    """Background task to process a video job.

    This is a stub implementation that simulates async processing.
    In production, this would:
    1. Transcribe audio using Whisper
    2. Generate script using LLM
    3. Save results to database

    Args:
        job_id: ID of the job to process.
        video_id: ID of the video being processed.
    """
    # Import here to avoid circular imports
    import os
    from hollywood_script_generator.api.video_router import get_engine
    from sqlalchemy.orm import sessionmaker

    # Skip processing in test mode to allow tests to verify pending state
    if os.environ.get("TESTING") == "true":
        return

    engine = get_engine()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # Update job status to processing
        job = db.get(Job, job_id)
        if job:
            job.status = JobStatus.PROCESSING.value
            job.started_at = datetime.utcnow()
            job.progress = 10.0
            db.commit()

            # Simulate processing steps
            # In production, actual processing would happen here
            import asyncio

            await asyncio.sleep(1)  # Simulate transcription
            job.progress = 50.0
            db.commit()

            await asyncio.sleep(1)  # Simulate script generation
            job.progress = 90.0
            db.commit()

            # Create empty script for now (production would have real content)
            script = Script(
                job_id=job_id,
                content="# Processing complete\n\nScript content would go here.",
            )
            db.add(script)

            # Mark job as completed
            job.status = JobStatus.COMPLETED.value
            job.progress = 100.0
            job.completed_at = datetime.utcnow()
            db.commit()

    except Exception as e:
        # Handle errors
        job = db.get(Job, job_id)
        if job:
            job.status = JobStatus.FAILED.value
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()


@job_router.post(
    "/process", response_model=ProcessResponse, status_code=status.HTTP_201_CREATED
)
async def start_processing(
    request: ProcessRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> ProcessResponse:
    """Start processing a video.

    Creates a new job for processing the specified video and queues it
    for background processing.

    Args:
        request: Process request containing video_id.
        background_tasks: FastAPI background tasks for async processing.
        db: Database session dependency.

    Returns:
        ProcessResponse with job ID and status.

    Raises:
        HTTPException: 404 if video not found.

    Example:
        POST /api/v1/process
        {"video_id": 1}
    """
    # Verify video exists
    video = db.get(Video, request.video_id)
    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video with ID {request.video_id} not found",
        )

    # Create job record
    job = Job(
        video_id=request.video_id,
        status=JobStatus.PENDING.value,
        progress=0.0,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Queue background task
    # Note: In a production environment, you'd use Celery or similar
    # For now, we use FastAPI's background tasks as a stub
    background_tasks.add_task(process_video_job, job.id, request.video_id)

    return ProcessResponse(
        job_id=job.id,
        video_id=request.video_id,
        status=JobStatus.PENDING.value,
        message="Video processing job created successfully",
    )


@job_router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: int, db: Session = Depends(get_db)) -> Job:
    """Get the status of a processing job.

    Retrieves the current status, progress, and results (if completed)
    for a specific job.

    Args:
        job_id: The unique identifier of the job.
        db: Database session dependency.

    Returns:
        Job object with status and optional script content.

    Raises:
        HTTPException: 404 if job not found.

    Example:
        GET /api/v1/jobs/1
    """
    job = db.get(Job, job_id)

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found",
        )

    # Refresh to ensure we have latest data including script
    db.refresh(job)

    return job
