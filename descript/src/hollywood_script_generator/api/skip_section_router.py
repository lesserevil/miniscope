"""Skip section management API router for Hollywood Script Generator.

This module provides endpoints for creating, reading, updating, and deleting
skip sections for video processing jobs.
"""

from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from hollywood_script_generator.db.models import SkipSection, Job
from hollywood_script_generator.services.skip_section_manager import (
    SkipSectionManager,
    InvalidTimeRangeError,
    OverlappingSectionError,
)
from hollywood_script_generator.api.video_router import get_db


# Pydantic request/response models
class SkipSectionCreateRequest(BaseModel):
    """Request model for creating a skip section."""

    job_id: int = Field(..., description="ID of the job to add the section to")
    start_seconds: float = Field(
        ..., ge=0, description="Start time in seconds (must be >= 0)"
    )
    end_seconds: float = Field(
        ..., gt=0, description="End time in seconds (must be > 0)"
    )
    reason: Optional[str] = Field(
        None, max_length=100, description="Optional reason for skipping"
    )


class SkipSectionUpdateRequest(BaseModel):
    """Request model for updating a skip section."""

    start_seconds: Optional[float] = Field(
        None, ge=0, description="Start time in seconds"
    )
    end_seconds: Optional[float] = Field(None, gt=0, description="End time in seconds")
    reason: Optional[str] = Field(
        None, max_length=100, description="Reason for skipping"
    )


class SkipSectionResponse(BaseModel):
    """Response model for skip section."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    start_seconds: float
    end_seconds: float
    reason: Optional[str]
    created_at: datetime


class SkipSectionListResponse(BaseModel):
    """Response model for list of skip sections."""

    sections: List[SkipSectionResponse]
    total_duration: float


# Create router
skip_section_router = APIRouter(prefix="/skip_sections", tags=["skip_sections"])


@skip_section_router.post(
    "", response_model=SkipSectionResponse, status_code=status.HTTP_201_CREATED
)
async def create_skip_section(
    request: SkipSectionCreateRequest, db: Session = Depends(get_db)
) -> SkipSection:
    """Create a new skip section for a job.

    Creates a time range that will be skipped during video processing.
    Validates that the time range is valid and doesn't overlap with
    existing sections.

    Args:
        request: Skip section creation request.
        db: Database session dependency.

    Returns:
        Created SkipSection object.

    Raises:
        HTTPException: 404 if job not found.
        HTTPException: 422 if time range is invalid or overlaps.

    Example:
        POST /api/v1/skip_sections
        {
            "job_id": 1,
            "start_seconds": 10.0,
            "end_seconds": 30.0,
            "reason": "credits"
        }
    """
    # Verify job exists
    job = db.get(Job, request.job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {request.job_id} not found",
        )

    manager = SkipSectionManager(db)

    try:
        section = manager.add_skip_section(
            job_id=request.job_id,
            start_seconds=request.start_seconds,
            end_seconds=request.end_seconds,
            reason=request.reason,
        )
        return section
    except InvalidTimeRangeError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except OverlappingSectionError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )


@skip_section_router.get("/job/{job_id}", response_model=SkipSectionListResponse)
async def list_skip_sections(
    job_id: int, db: Session = Depends(get_db)
) -> SkipSectionListResponse:
    """Get all skip sections for a job.

    Retrieves all skip sections associated with a specific job,
    sorted by start time.

    Args:
        job_id: ID of the job to get sections for.
        db: Database session dependency.

    Returns:
        List of skip sections and total skipped duration.

    Raises:
        HTTPException: 404 if job not found.

    Example:
        GET /api/v1/skip_sections/job/1
    """
    # Verify job exists
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found",
        )

    manager = SkipSectionManager(db)
    sections = manager.get_skip_sections(job_id)
    total_duration = manager.get_total_skipped_duration(job_id)

    return SkipSectionListResponse(
        sections=[SkipSectionResponse.model_validate(s) for s in sections],
        total_duration=total_duration,
    )


@skip_section_router.get("/{section_id}", response_model=SkipSectionResponse)
async def get_skip_section(
    section_id: int, db: Session = Depends(get_db)
) -> SkipSection:
    """Get a specific skip section by ID.

    Args:
        section_id: ID of the skip section.
        db: Database session dependency.

    Returns:
        SkipSection object.

    Raises:
        HTTPException: 404 if section not found.

    Example:
        GET /api/v1/skip_sections/1
    """
    manager = SkipSectionManager(db)
    section = manager.get_skip_section_by_id(section_id)

    if section is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skip section with ID {section_id} not found",
        )

    return section


@skip_section_router.put("/{section_id}", response_model=SkipSectionResponse)
async def update_skip_section(
    section_id: int,
    request: SkipSectionUpdateRequest,
    db: Session = Depends(get_db),
) -> SkipSection:
    """Update an existing skip section.

    Updates the time range and/or reason for a skip section.
    Validates that the new time range doesn't overlap with other sections.

    Args:
        section_id: ID of the skip section to update.
        request: Update request with optional fields.
        db: Database session dependency.

    Returns:
        Updated SkipSection object.

    Raises:
        HTTPException: 404 if section not found.
        HTTPException: 422 if time range is invalid or overlaps.

    Example:
        PUT /api/v1/skip_sections/1
        {
            "start_seconds": 15.0,
            "end_seconds": 35.0,
            "reason": "updated reason"
        }
    """
    manager = SkipSectionManager(db)

    try:
        section = manager.update_skip_section(
            section_id=section_id,
            start_seconds=request.start_seconds,
            end_seconds=request.end_seconds,
            reason=request.reason,
        )

        if section is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Skip section with ID {section_id} not found",
            )

        return section
    except InvalidTimeRangeError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except OverlappingSectionError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )


@skip_section_router.delete("/{section_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_skip_section(section_id: int, db: Session = Depends(get_db)) -> None:
    """Delete a skip section.

    Permanently removes a skip section from the database.

    Args:
        section_id: ID of the skip section to delete.
        db: Database session dependency.

    Raises:
        HTTPException: 404 if section not found.

    Example:
        DELETE /api/v1/skip_sections/1
    """
    manager = SkipSectionManager(db)
    deleted = manager.delete_skip_section(section_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skip section with ID {section_id} not found",
        )

    # Returns 204 No Content on success
    return None
