"""Unit tests for database models (TDD approach).

These tests define the expected behavior of SQLAlchemy models.
Run these first to verify the model implementation.
"""

import pytest
from datetime import datetime
from pathlib import Path
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker, Session

from hollywood_script_generator.db.base import Base
from hollywood_script_generator.db.models import (
    Video,
    Job,
    Script,
    SkipSection,
)
from hollywood_script_generator.models.job_status import JobStatus


# Use in-memory SQLite for tests
@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


class TestVideoModel:
    """Tests for Video model."""

    def test_video_model_exists(self, db_session: Session):
        """Verify Video model can be instantiated."""
        video = Video(
            path="/path/to/video.mp4",
            video_metadata={"duration": 120.5, "resolution": "1920x1080"},
        )
        assert video is not None

    def test_video_required_fields(self, db_session: Session):
        """Verify Video model has required fields."""
        video = Video(
            path="/path/to/video.mp4",
            video_metadata={"duration": 120.5},
        )
        db_session.add(video)
        db_session.commit()

        # Verify fields
        assert video.id is not None
        assert isinstance(video.id, int)
        assert video.path == "/path/to/video.mp4"
        assert video.video_metadata == {"duration": 120.5}

    def test_video_timestamps_auto_set(self, db_session: Session):
        """Verify created_at and updated_at are auto-set."""
        video = Video(path="/path/to/video.mp4", video_metadata={})
        db_session.add(video)
        db_session.commit()

        assert video.created_at is not None
        assert video.updated_at is not None
        assert isinstance(video.created_at, datetime)
        assert isinstance(video.updated_at, datetime)

    def test_video_has_jobs_relationship(self, db_session: Session):
        """Verify Video has relationship to Job model."""
        video = Video(path="/path/to/video.mp4", video_metadata={})
        db_session.add(video)
        db_session.commit()

        # Should have a jobs attribute that is a list
        assert hasattr(video, "jobs")
        assert isinstance(video.jobs, list)


class TestJobModel:
    """Tests for Job model."""

    def test_job_model_exists(self, db_session: Session):
        """Verify Job model can be instantiated."""
        job = Job(
            video_id=1,
            status=JobStatus.PENDING,
            progress=0.0,
        )
        assert job is not None

    def test_job_required_fields(self, db_session: Session):
        """Verify Job model has required fields."""
        video = Video(path="/path/to/video.mp4", video_metadata={})
        db_session.add(video)
        db_session.commit()

        job = Job(
            video_id=video.id,
            status=JobStatus.PENDING,
            progress=0.0,
        )
        db_session.add(job)
        db_session.commit()

        assert job.id is not None
        assert isinstance(job.id, int)
        assert job.video_id == video.id
        assert job.status == JobStatus.PENDING
        assert job.progress == 0.0

    def test_job_optional_fields(self, db_session: Session):
        """Verify Job model handles optional fields."""
        video = Video(path="/path/to/video.mp4", video_metadata={})
        db_session.add(video)
        db_session.commit()

        job = Job(
            video_id=video.id,
            status=JobStatus.FAILED,
            progress=50.0,
            error_message="Processing error occurred",
        )
        db_session.add(job)
        db_session.commit()

        assert job.error_message == "Processing error occurred"
        assert job.started_at is None
        assert job.completed_at is None

    def test_job_status_enum(self, db_session: Session):
        """Verify Job accepts all status enum values."""
        video = Video(path="/path/to/video.mp4", video_metadata={})
        db_session.add(video)
        db_session.commit()

        statuses = [
            JobStatus.PENDING,
            JobStatus.PROCESSING,
            JobStatus.COMPLETED,
            JobStatus.FAILED,
        ]

        for status in statuses:
            job = Job(
                video_id=video.id,
                status=status,
                progress=0.0,
            )
            db_session.add(job)

        db_session.commit()

        # Verify all jobs were created
        jobs = db_session.query(Job).filter_by(video_id=video.id).all()
        assert len(jobs) == 4

    def test_job_has_script_relationship(self, db_session: Session):
        """Verify Job has relationship to Script model."""
        video = Video(path="/path/to/video.mp4", video_metadata={})
        db_session.add(video)
        db_session.commit()

        job = Job(
            video_id=video.id,
            status=JobStatus.COMPLETED,
            progress=100.0,
        )
        db_session.add(job)
        db_session.commit()

        assert hasattr(job, "script")

    def test_job_has_skip_sections_relationship(self, db_session: Session):
        """Verify Job has relationship to SkipSection model."""
        video = Video(path="/path/to/video.mp4", video_metadata={})
        db_session.add(video)
        db_session.commit()

        job = Job(
            video_id=video.id,
            status=JobStatus.PENDING,
            progress=0.0,
        )
        db_session.add(job)
        db_session.commit()

        assert hasattr(job, "skip_sections")
        assert isinstance(job.skip_sections, list)


class TestScriptModel:
    """Tests for Script model."""

    def test_script_model_exists(self, db_session: Session):
        """Verify Script model can be instantiated."""
        script = Script(
            job_id=1,
            content="# Script Content\n\nScene 1...",
        )
        assert script is not None

    def test_script_required_fields(self, db_session: Session):
        """Verify Script model has required fields."""
        video = Video(path="/path/to/video.mp4", video_metadata={})
        db_session.add(video)
        db_session.commit()

        job = Job(
            video_id=video.id,
            status=JobStatus.COMPLETED,
            progress=100.0,
        )
        db_session.add(job)
        db_session.commit()

        script = Script(
            job_id=job.id,
            content="# Generated Script\n\n## Scene 1\n\nINT. OFFICE - DAY\n\nCharacter speaks.",
        )
        db_session.add(script)
        db_session.commit()

        assert script.id is not None
        assert isinstance(script.id, int)
        assert script.job_id == job.id
        assert "Generated Script" in script.content

    def test_script_created_at_auto_set(self, db_session: Session):
        """Verify created_at is auto-set."""
        video = Video(path="/path/to/video.mp4", video_metadata={})
        db_session.add(video)
        db_session.commit()

        job = Job(
            video_id=video.id,
            status=JobStatus.COMPLETED,
            progress=100.0,
        )
        db_session.add(job)
        db_session.commit()

        script = Script(
            job_id=job.id,
            content="Script content",
        )
        db_session.add(script)
        db_session.commit()

        assert script.created_at is not None
        assert isinstance(script.created_at, datetime)

    def test_script_has_job_relationship(self, db_session: Session):
        """Verify Script has relationship to Job model."""
        video = Video(path="/path/to/video.mp4", video_metadata={})
        db_session.add(video)
        db_session.commit()

        job = Job(
            video_id=video.id,
            status=JobStatus.COMPLETED,
            progress=100.0,
        )
        db_session.add(job)
        db_session.commit()

        script = Script(
            job_id=job.id,
            content="Script",
        )
        db_session.add(script)
        db_session.commit()

        # Access the relationship
        assert script.job is not None
        assert script.job.id == job.id


class TestSkipSectionModel:
    """Tests for SkipSection model."""

    def test_skip_section_model_exists(self, db_session: Session):
        """Verify SkipSection model can be instantiated."""
        skip = SkipSection(
            job_id=1,
            start_seconds=10.0,
            end_seconds=20.0,
            reason="credits",
        )
        assert skip is not None

    def test_skip_section_required_fields(self, db_session: Session):
        """Verify SkipSection model has required fields."""
        video = Video(path="/path/to/video.mp4", video_metadata={})
        db_session.add(video)
        db_session.commit()

        job = Job(
            video_id=video.id,
            status=JobStatus.PENDING,
            progress=0.0,
        )
        db_session.add(job)
        db_session.commit()

        skip = SkipSection(
            job_id=job.id,
            start_seconds=30.0,
            end_seconds=45.5,
            reason="advertisement",
        )
        db_session.add(skip)
        db_session.commit()

        assert skip.id is not None
        assert isinstance(skip.id, int)
        assert skip.job_id == job.id
        assert skip.start_seconds == 30.0
        assert skip.end_seconds == 45.5
        assert skip.reason == "advertisement"

    def test_skip_section_optional_reason(self, db_session: Session):
        """Verify SkipSection allows optional reason."""
        video = Video(path="/path/to/video.mp4", video_metadata={})
        db_session.add(video)
        db_session.commit()

        job = Job(
            video_id=video.id,
            status=JobStatus.PENDING,
            progress=0.0,
        )
        db_session.add(job)
        db_session.commit()

        skip = SkipSection(
            job_id=job.id,
            start_seconds=60.0,
            end_seconds=90.0,
        )
        db_session.add(skip)
        db_session.commit()

        assert skip.reason is None

    def test_skip_section_created_at_auto_set(self, db_session: Session):
        """Verify created_at is auto-set."""
        video = Video(path="/path/to/video.mp4", video_metadata={})
        db_session.add(video)
        db_session.commit()

        job = Job(
            video_id=video.id,
            status=JobStatus.PENDING,
            progress=0.0,
        )
        db_session.add(job)
        db_session.commit()

        skip = SkipSection(
            job_id=job.id,
            start_seconds=0.0,
            end_seconds=5.0,
        )
        db_session.add(skip)
        db_session.commit()

        assert skip.created_at is not None
        assert isinstance(skip.created_at, datetime)

    def test_skip_section_has_job_relationship(self, db_session: Session):
        """Verify SkipSection has relationship to Job model."""
        video = Video(path="/path/to/video.mp4", video_metadata={})
        db_session.add(video)
        db_session.commit()

        job = Job(
            video_id=video.id,
            status=JobStatus.PENDING,
            progress=0.0,
        )
        db_session.add(job)
        db_session.commit()

        skip = SkipSection(
            job_id=job.id,
            start_seconds=10.0,
            end_seconds=20.0,
            reason="test",
        )
        db_session.add(skip)
        db_session.commit()

        # Access the relationship
        assert skip.job is not None
        assert skip.job.id == job.id


class TestModelRelationships:
    """Tests for relationships between models."""

    def test_video_to_jobs_relationship(self, db_session: Session):
        """Verify Video can have multiple Jobs."""
        video = Video(path="/path/to/video.mp4", video_metadata={})
        db_session.add(video)
        db_session.commit()

        job1 = Job(video_id=video.id, status=JobStatus.COMPLETED, progress=100.0)
        job2 = Job(video_id=video.id, status=JobStatus.FAILED, progress=50.0)
        db_session.add(job1)
        db_session.add(job2)
        db_session.commit()

        # Refresh video to load relationships
        db_session.refresh(video)

        assert len(video.jobs) == 2
        assert job1 in video.jobs
        assert job2 in video.jobs

    def test_job_to_script_relationship(self, db_session: Session):
        """Verify Job can have one Script."""
        video = Video(path="/path/to/video.mp4", video_metadata={})
        db_session.add(video)
        db_session.commit()

        job = Job(video_id=video.id, status=JobStatus.COMPLETED, progress=100.0)
        db_session.add(job)
        db_session.commit()

        script = Script(job_id=job.id, content="Script content")
        db_session.add(script)
        db_session.commit()

        # Refresh job to load relationships
        db_session.refresh(job)

        assert job.script is not None
        assert job.script.content == "Script content"

    def test_job_to_skip_sections_relationship(self, db_session: Session):
        """Verify Job can have multiple SkipSections."""
        video = Video(path="/path/to/video.mp4", video_metadata={})
        db_session.add(video)
        db_session.commit()

        job = Job(video_id=video.id, status=JobStatus.PROCESSING, progress=50.0)
        db_session.add(job)
        db_session.commit()

        skip1 = SkipSection(
            job_id=job.id, start_seconds=10.0, end_seconds=20.0, reason="credits"
        )
        skip2 = SkipSection(
            job_id=job.id, start_seconds=100.0, end_seconds=110.0, reason="ad"
        )
        db_session.add(skip1)
        db_session.add(skip2)
        db_session.commit()

        # Refresh job to load relationships
        db_session.refresh(job)

        assert len(job.skip_sections) == 2
        assert skip1 in job.skip_sections
        assert skip2 in job.skip_sections


class TestDatabaseIndexes:
    """Tests for database indexes and performance optimizations."""

    def test_video_path_index_exists(self, db_session: Session):
        """Verify Video has an index on path column."""
        inspector = inspect(db_session.bind)
        indexes = inspector.get_indexes("videos")
        index_names = [idx["name"] for idx in indexes]
        assert "ix_videos_path" in index_names or any(
            "path" in str(idx["column_names"]) for idx in indexes
        )

    def test_job_status_index_exists(self, db_session: Session):
        """Verify Job has an index on status column."""
        inspector = inspect(db_session.bind)
        indexes = inspector.get_indexes("jobs")
        index_names = [idx["name"] for idx in indexes]
        assert "ix_jobs_status" in index_names or any(
            "status" in str(idx["column_names"]) for idx in indexes
        )

    def test_job_video_id_index_exists(self, db_session: Session):
        """Verify Job has an index on video_id column."""
        inspector = inspect(db_session.bind)
        indexes = inspector.get_indexes("jobs")
        index_names = [idx["name"] for idx in indexes]
        assert "ix_jobs_video_id" in index_names or any(
            "video_id" in str(idx["column_names"]) for idx in indexes
        )


class TestModelCascadingDelete:
    """Tests for cascading delete behavior."""

    def test_delete_video_cascades_to_jobs(self, db_session: Session):
        """Verify deleting a Video cascades delete to related Jobs."""
        video = Video(path="/path/to/video.mp4", video_metadata={})
        db_session.add(video)
        db_session.commit()

        job = Job(video_id=video.id, status=JobStatus.PENDING, progress=0.0)
        db_session.add(job)
        db_session.commit()

        # Delete video
        db_session.delete(video)
        db_session.commit()

        # Job should also be deleted
        assert db_session.query(Job).filter_by(id=job.id).first() is None

    def test_delete_job_cascades_to_script(self, db_session: Session):
        """Verify deleting a Job cascades delete to related Script."""
        video = Video(path="/path/to/video.mp4", video_metadata={})
        db_session.add(video)
        db_session.commit()

        job = Job(video_id=video.id, status=JobStatus.COMPLETED, progress=100.0)
        db_session.add(job)
        db_session.commit()

        script = Script(job_id=job.id, content="Script")
        db_session.add(script)
        db_session.commit()

        # Delete job
        db_session.delete(job)
        db_session.commit()

        # Script should also be deleted
        assert db_session.query(Script).filter_by(id=script.id).first() is None

    def test_delete_job_cascades_to_skip_sections(self, db_session: Session):
        """Verify deleting a Job cascades delete to related SkipSections."""
        video = Video(path="/path/to/video.mp4", video_metadata={})
        db_session.add(video)
        db_session.commit()

        job = Job(video_id=video.id, status=JobStatus.PENDING, progress=0.0)
        db_session.add(job)
        db_session.commit()

        skip = SkipSection(job_id=job.id, start_seconds=10.0, end_seconds=20.0)
        db_session.add(skip)
        db_session.commit()

        # Delete job
        db_session.delete(job)
        db_session.commit()

        # SkipSection should also be deleted
        assert db_session.query(SkipSection).filter_by(id=skip.id).first() is None
