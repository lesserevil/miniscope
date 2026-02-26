"""API routers for Hollywood Script Generator.

This module defines all API endpoints including health check and
future API routes for video processing, job management, etc.
"""

from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from hollywood_script_generator.core.config import get_settings
from hollywood_script_generator.db.models import Video, Job
from hollywood_script_generator.models.job_status import JobStatus
from hollywood_script_generator.api.video_router import get_db
from hollywood_script_generator.api.job_router import (
    ProcessRequest,
    ProcessResponse,
    process_video_job,
)

api_router = APIRouter(prefix="/api/v1", tags=["api"])


@api_router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint.

    Returns the current health status of the application including
    app name, version, and current timestamp.

    Returns:
        Dict containing health status information:
        - status: "healthy" if the app is running
        - app_name: The application name
        - version: The application version
        - timestamp: ISO format timestamp of the check
    """
    settings = get_settings()

    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": "0.1.0",
        "timestamp": datetime.utcnow().isoformat(),
    }


@api_router.post(
    "/process", response_model=ProcessResponse, status_code=status.HTTP_201_CREATED
)
async def start_processing(
    request: ProcessRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> ProcessResponse:
    """Start processing a video at /api/v1/process.

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
    background_tasks.add_task(process_video_job, job.id, request.video_id)

    return ProcessResponse(
        job_id=job.id,
        video_id=request.video_id,
        status=JobStatus.PENDING.value,
        message="Video processing job created successfully",
    )


from hollywood_script_generator.api.video_router import video_router
from hollywood_script_generator.api.job_router import job_router
from hollywood_script_generator.api.script_router import script_router
from hollywood_script_generator.api.skip_section_router import skip_section_router

# Include all domain routers
api_router.include_router(video_router)
api_router.include_router(job_router)
api_router.include_router(script_router)
api_router.include_router(skip_section_router)
