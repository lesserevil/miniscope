"""Database models for Hollywood Script Generator.

This module defines SQLAlchemy ORM models for:
- Video: Stores video file metadata
- Job: Tracks processing jobs
- Script: Stores generated script content
- SkipSection: Stores user-defined time ranges to skip
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hollywood_script_generator.db.base import Base
from hollywood_script_generator.models.job_status import JobStatus


class Video(Base):
    """Video model for storing video file metadata.

    Attributes:
        id: Primary key
        path: Absolute path to the video file
        video_metadata: JSON blob with video metadata (duration, resolution, etc.)
        created_at: Timestamp when record was created
        updated_at: Timestamp when record was last updated
        jobs: Relationship to associated processing jobs
    """

    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    path: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    video_metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    jobs: Mapped[List["Job"]] = relationship(
        "Job", back_populates="video", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("ix_videos_path", "path"),
        Index("ix_videos_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Video(id={self.id}, path={self.path!r})>"


class Job(Base):
    """Job model for tracking video processing jobs.

    Attributes:
        id: Primary key
        video_id: Foreign key to videos table
        status: Current job status (pending/processing/completed/failed)
        progress: Progress percentage (0.0 to 100.0)
        error_message: Error message if job failed
        created_at: Timestamp when job was created
        started_at: Timestamp when job started processing
        completed_at: Timestamp when job completed or failed
        video: Relationship to associated video
        script: Relationship to generated script
        skip_sections: Relationship to skip sections for this job
    """

    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    video_id: Mapped[int] = mapped_column(
        ForeignKey("videos.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=JobStatus.PENDING.value
    )
    progress: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    video: Mapped["Video"] = relationship("Video", back_populates="jobs")
    script: Mapped[Optional["Script"]] = relationship(
        "Script", back_populates="job", uselist=False, cascade="all, delete-orphan"
    )
    skip_sections: Mapped[List["SkipSection"]] = relationship(
        "SkipSection", back_populates="job", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("ix_jobs_video_id", "video_id"),
        Index("ix_jobs_status", "status"),
        Index("ix_jobs_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Job(id={self.id}, video_id={self.video_id}, status={self.status!r})>"


class Script(Base):
    """Script model for storing generated script content.

    Attributes:
        id: Primary key
        job_id: Foreign key to jobs table (one-to-one relationship)
        content: Generated script content in Markdown format
        created_at: Timestamp when script was generated
        job: Relationship to associated job
    """

    __tablename__ = "scripts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # Enforce one-to-one relationship
    )
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="script")

    # Indexes
    __table_args__ = (
        Index("ix_scripts_job_id", "job_id"),
        Index("ix_scripts_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        content_preview = self.content[:50] if self.content else ""
        return f"<Script(id={self.id}, job_id={self.job_id}, content={content_preview!r}...)>"


class SkipSection(Base):
    """SkipSection model for storing user-defined time ranges to skip.

    Attributes:
        id: Primary key
        job_id: Foreign key to jobs table
        start_seconds: Start time in seconds
        end_seconds: End time in seconds
        reason: Optional reason for skipping (e.g., 'credits', 'ad')
        created_at: Timestamp when skip section was created
        job: Relationship to associated job
    """

    __tablename__ = "skip_sections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    start_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    end_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="skip_sections")

    # Indexes
    __table_args__ = (
        Index("ix_skip_sections_job_id", "job_id"),
        Index("ix_skip_sections_start_seconds", "start_seconds"),
        Index("ix_skip_sections_end_seconds", "end_seconds"),
    )

    def __repr__(self) -> str:
        return (
            f"<SkipSection(id={self.id}, job_id={self.job_id}, "
            f"start={self.start_seconds}s, end={self.end_seconds}s)>"
        )
