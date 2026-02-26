"""Script retrieval API router for Hollywood Script Generator.

This module provides endpoints for retrieving generated scripts.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from hollywood_script_generator.db.models import Script, Job, Video
from hollywood_script_generator.api.video_router import get_db


# Pydantic response models
class ScriptResponse(BaseModel):
    """Response model for script content."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    content: str


class ScriptDownloadResponse(BaseModel):
    """Response model for script download."""

    content: str
    filename: str
    content_type: str = "text/markdown"


# Create router
script_router = APIRouter(prefix="/scripts", tags=["scripts"])


def _find_script_by_video_id(db: Session, video_id: int) -> Optional[Script]:
    """Find the most recent completed script for a video.

    Args:
        db: Database session.
        video_id: ID of the video.

    Returns:
        The most recent Script if found, None otherwise.
    """
    # Find the most recent completed job for this video
    query = (
        select(Script)
        .join(Job, Script.job_id == Job.id)
        .where(Job.video_id == video_id)
        .where(Job.status == "completed")
        .order_by(Job.completed_at.desc())
        .limit(1)
    )

    result = db.execute(query)
    return result.scalar_one_or_none()
    query = (
        select(Script)
        .join(Job, Script.job_id == Job.id)
        .where(Job.video_id == video_id)
        .where(Job.status == "completed")
        .order_by(Job.completed_at.desc())
    )

    result = db.execute(query)
    return result.scalar_one_or_none()


@script_router.get("/{video_id}", response_model=ScriptResponse)
async def get_script(video_id: int, db: Session = Depends(get_db)) -> Script:
    """Retrieve the generated script for a video.

    Gets the most recent completed script for the specified video.

    Args:
        video_id: ID of the video to get the script for.
        db: Database session dependency.

    Returns:
        Script object with markdown content.

    Raises:
        HTTPException: 404 if video not found.
        HTTPException: 404 if no completed script found for video.

    Example:
        GET /api/v1/scripts/1
    """
    # First verify the video exists
    video = db.get(Video, video_id)
    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video with ID {video_id} not found",
        )

    # Find the most recent completed script
    script = _find_script_by_video_id(db, video_id)

    if script is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Not found: No completed script found for video {video_id}. "
            "The video may still be processing or no jobs exist.",
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No completed script found for video {video_id}. "
            "The video may still be processing or no jobs exist.",
        )

    return script


@script_router.get("/{video_id}/download")
async def download_script(video_id: int, db: Session = Depends(get_db)):
    """Download the generated script as a Markdown file.

    Returns the script content with appropriate headers for file download.

    Args:
        video_id: ID of the video to download the script for.
        db: Database session dependency.

    Returns:
        Script content with Content-Disposition header.

    Raises:
        HTTPException: 404 if video or script not found.

    Example:
        GET /api/v1/scripts/1/download
    """
    from fastapi.responses import PlainTextResponse

    # First verify the video exists
    video = db.get(Video, video_id)
    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video with ID {video_id} not found",
        )

    # Find the most recent completed script
    script = _find_script_by_video_id(db, video_id)

    if script is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Not found: No completed script found for video {video_id}. "
            "The video may still be processing or no jobs exist.",
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No completed script found for video {video_id}. "
            "The video may still be processing or no jobs exist.",
        )

    # Generate filename from video path
    from pathlib import Path

    video_path = Path(video.path)
    filename = f"{video_path.stem}_script.md"

    return PlainTextResponse(
        content=script.content,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
