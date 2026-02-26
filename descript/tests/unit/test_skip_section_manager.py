"""Tests for SkipSectionManager service.

This module tests the SkipSectionManager class for managing skip sections
with CRUD operations and overlap validation.

Tests follow TDD principles:
- Write tests first defining expected behavior
- Run tests (they fail initially)
- Implement code to make tests pass
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from hollywood_script_generator.db.base import Base
from hollywood_script_generator.db.models import Video, Job, SkipSection
from hollywood_script_generator.models.job_status import JobStatus
from hollywood_script_generator.services.skip_section_manager import (
    SkipSectionManager,
    OverlappingSectionError,
    InvalidTimeRangeError,
)


@pytest.fixture
def db_session():
    """Create a fresh in-memory database session for each test."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    yield session

    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def sample_video(db_session: Session):
    """Create a sample video record."""
    video = Video(
        path="/test/video.mp4",
        video_metadata={"duration": 3600.0, "width": 1920, "height": 1080},
    )
    db_session.add(video)
    db_session.commit()
    db_session.refresh(video)
    return video


@pytest.fixture
def sample_job(db_session: Session, sample_video: Video):
    """Create a sample job record."""
    job = Job(video_id=sample_video.id, status=JobStatus.PENDING.value, progress=0.0)
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


@pytest.fixture
def manager(db_session: Session):
    """Create a SkipSectionManager instance."""
    return SkipSectionManager(db_session)


class TestSkipSectionManagerInit:
    """Tests for SkipSectionManager initialization."""

    def test_manager_initializes_with_session(self, db_session: Session):
        """Test that manager can be initialized with a database session."""
        manager = SkipSectionManager(db_session)
        assert manager.session is db_session


class TestAddSkipSection:
    """Tests for adding skip sections."""

    def test_add_skip_section_success(
        self, manager: SkipSectionManager, sample_job: Job
    ):
        """Test successfully adding a skip section."""
        section = manager.add_skip_section(
            job_id=sample_job.id, start_seconds=10.0, end_seconds=30.0, reason="credits"
        )

        assert section.job_id == sample_job.id
        assert section.start_seconds == 10.0
        assert section.end_seconds == 30.0
        assert section.reason == "credits"
        assert section.id is not None

    def test_add_skip_section_without_reason(
        self, manager: SkipSectionManager, sample_job: Job
    ):
        """Test adding a skip section without a reason."""
        section = manager.add_skip_section(
            job_id=sample_job.id, start_seconds=10.0, end_seconds=30.0
        )

        assert section.reason is None

    def test_add_skip_section_invalid_time_range(
        self, manager: SkipSectionManager, sample_job: Job
    ):
        """Test that adding with start >= end raises InvalidTimeRangeError."""
        with pytest.raises(InvalidTimeRangeError):
            manager.add_skip_section(
                job_id=sample_job.id, start_seconds=30.0, end_seconds=10.0
            )

        with pytest.raises(InvalidTimeRangeError):
            manager.add_skip_section(
                job_id=sample_job.id, start_seconds=30.0, end_seconds=30.0
            )

    def test_add_skip_section_negative_start(
        self, manager: SkipSectionManager, sample_job: Job
    ):
        """Test that adding with negative start time raises InvalidTimeRangeError."""
        with pytest.raises(InvalidTimeRangeError):
            manager.add_skip_section(
                job_id=sample_job.id, start_seconds=-1.0, end_seconds=10.0
            )

    def test_add_skip_section_overlap_detected(
        self, manager: SkipSectionManager, sample_job: Job
    ):
        """Test that overlapping sections raise OverlappingSectionError."""
        # First section: 10-30 seconds
        manager.add_skip_section(
            job_id=sample_job.id, start_seconds=10.0, end_seconds=30.0
        )

        # Try to add overlapping section: 20-40 seconds
        with pytest.raises(OverlappingSectionError):
            manager.add_skip_section(
                job_id=sample_job.id, start_seconds=20.0, end_seconds=40.0
            )

    def test_add_skip_section_overlap_at_boundary(
        self, manager: SkipSectionManager, sample_job: Job
    ):
        """Test that sections touching at boundaries don't overlap."""
        # First section: 10-30 seconds
        manager.add_skip_section(
            job_id=sample_job.id, start_seconds=10.0, end_seconds=30.0
        )

        # Adjacent section: 30-50 seconds (should be allowed)
        section = manager.add_skip_section(
            job_id=sample_job.id, start_seconds=30.0, end_seconds=50.0
        )

        assert section.start_seconds == 30.0
        assert section.end_seconds == 50.0

    def test_add_skip_section_complete_overlap(
        self, manager: SkipSectionManager, sample_job: Job
    ):
        """Test detecting complete overlap."""
        # First section: 10-50 seconds
        manager.add_skip_section(
            job_id=sample_job.id, start_seconds=10.0, end_seconds=50.0
        )

        # Inner section: 20-30 seconds
        with pytest.raises(OverlappingSectionError):
            manager.add_skip_section(
                job_id=sample_job.id, start_seconds=20.0, end_seconds=30.0
            )

    def test_add_skip_section_contained_within(
        self, manager: SkipSectionManager, sample_job: Job
    ):
        """Test detecting when new section contains existing section."""
        # First section: 20-30 seconds
        manager.add_skip_section(
            job_id=sample_job.id, start_seconds=20.0, end_seconds=30.0
        )

        # Outer section: 10-50 seconds
        with pytest.raises(OverlappingSectionError):
            manager.add_skip_section(
                job_id=sample_job.id, start_seconds=10.0, end_seconds=50.0
            )


class TestGetSkipSections:
    """Tests for retrieving skip sections."""

    def test_get_skip_sections_empty(
        self, manager: SkipSectionManager, sample_job: Job
    ):
        """Test getting sections when none exist."""
        sections = manager.get_skip_sections(sample_job.id)
        assert sections == []

    def test_get_skip_sections_returns_sorted(
        self, manager: SkipSectionManager, sample_job: Job
    ):
        """Test that sections are returned sorted by start time."""
        # Add sections out of order
        manager.add_skip_section(
            job_id=sample_job.id, start_seconds=100.0, end_seconds=120.0
        )
        manager.add_skip_section(
            job_id=sample_job.id, start_seconds=10.0, end_seconds=30.0
        )
        manager.add_skip_section(
            job_id=sample_job.id, start_seconds=50.0, end_seconds=60.0
        )

        sections = manager.get_skip_sections(sample_job.id)

        assert len(sections) == 3
        assert sections[0].start_seconds == 10.0
        assert sections[1].start_seconds == 50.0
        assert sections[2].start_seconds == 100.0

    def test_get_skip_sections_only_for_job(
        self,
        manager: SkipSectionManager,
        db_session: Session,
        sample_job: Job,
        sample_video: Video,
    ):
        """Test that only sections for the specified job are returned."""
        # Create another job
        job2 = Job(video_id=sample_video.id, status=JobStatus.PENDING.value)
        db_session.add(job2)
        db_session.commit()

        # Add sections to both jobs
        manager.add_skip_section(
            job_id=sample_job.id, start_seconds=10.0, end_seconds=30.0
        )
        manager.add_skip_section(job_id=job2.id, start_seconds=100.0, end_seconds=120.0)

        sections = manager.get_skip_sections(sample_job.id)

        assert len(sections) == 1
        assert sections[0].start_seconds == 10.0


class TestDeleteSkipSection:
    """Tests for deleting skip sections."""

    def test_delete_skip_section_success(
        self, manager: SkipSectionManager, sample_job: Job
    ):
        """Test successfully deleting a skip section."""
        section = manager.add_skip_section(
            job_id=sample_job.id, start_seconds=10.0, end_seconds=30.0
        )

        result = manager.delete_skip_section(section.id)

        assert result is True
        sections = manager.get_skip_sections(sample_job.id)
        assert len(sections) == 0

    def test_delete_skip_section_not_found(self, manager: SkipSectionManager):
        """Test deleting a non-existent section returns False."""
        result = manager.delete_skip_section(999)
        assert result is False

    def test_delete_skip_section_wrong_job(
        self, manager: SkipSectionManager, db_session: Session, sample_video: Video
    ):
        """Test deleting a section from another job is still allowed by ID."""
        # Create two jobs
        job1 = Job(video_id=sample_video.id, status=JobStatus.PENDING.value)
        job2 = Job(video_id=sample_video.id, status=JobStatus.PENDING.value)
        db_session.add_all([job1, job2])
        db_session.commit()

        # Add section to job1
        section = manager.add_skip_section(
            job_id=job1.id, start_seconds=10.0, end_seconds=30.0
        )

        # Delete by ID (should work regardless of job)
        result = manager.delete_skip_section(section.id)
        assert result is True


class TestUpdateSkipSection:
    """Tests for updating skip sections."""

    def test_update_skip_section_success(
        self, manager: SkipSectionManager, sample_job: Job
    ):
        """Test successfully updating a skip section."""
        section = manager.add_skip_section(
            job_id=sample_job.id, start_seconds=10.0, end_seconds=30.0, reason="credits"
        )

        updated = manager.update_skip_section(
            section_id=section.id,
            start_seconds=15.0,
            end_seconds=35.0,
            reason="advertisement",
        )

        assert updated is not None
        assert updated.start_seconds == 15.0
        assert updated.end_seconds == 35.0
        assert updated.reason == "advertisement"

    def test_update_skip_section_partial(
        self, manager: SkipSectionManager, sample_job: Job
    ):
        """Test updating only some fields."""
        section = manager.add_skip_section(
            job_id=sample_job.id, start_seconds=10.0, end_seconds=30.0, reason="credits"
        )

        updated = manager.update_skip_section(
            section_id=section.id, reason="advertisement"
        )

        assert updated.start_seconds == 10.0  # Unchanged
        assert updated.end_seconds == 30.0  # Unchanged
        assert updated.reason == "advertisement"

    def test_update_skip_section_not_found(self, manager: SkipSectionManager):
        """Test updating a non-existent section returns None."""
        result = manager.update_skip_section(
            section_id=999, start_seconds=10.0, end_seconds=30.0
        )
        assert result is None

    def test_update_skip_section_overlap(
        self, manager: SkipSectionManager, sample_job: Job
    ):
        """Test that updating to create overlap raises error."""
        section1 = manager.add_skip_section(
            job_id=sample_job.id, start_seconds=10.0, end_seconds=30.0
        )
        manager.add_skip_section(
            job_id=sample_job.id, start_seconds=40.0, end_seconds=60.0
        )

        # Try to update section1 to overlap with section2
        with pytest.raises(OverlappingSectionError):
            manager.update_skip_section(section_id=section1.id, end_seconds=50.0)

    def test_update_skip_section_invalid_time_range(
        self, manager: SkipSectionManager, sample_job: Job
    ):
        """Test that updating to invalid time range raises error."""
        section = manager.add_skip_section(
            job_id=sample_job.id, start_seconds=10.0, end_seconds=30.0
        )

        with pytest.raises(InvalidTimeRangeError):
            manager.update_skip_section(
                section_id=section.id, start_seconds=50.0, end_seconds=30.0
            )


class TestOverlapDetection:
    """Tests for the overlap detection logic."""

    def test_sections_overlap_partial(self, manager: SkipSectionManager):
        """Test detecting partial overlap."""
        assert manager._sections_overlap(10.0, 30.0, 20.0, 40.0) is True
        assert manager._sections_overlap(20.0, 40.0, 10.0, 30.0) is True

    def test_sections_overlap_complete(self, manager: SkipSectionManager):
        """Test detecting complete containment."""
        assert manager._sections_overlap(10.0, 50.0, 20.0, 30.0) is True
        assert manager._sections_overlap(20.0, 30.0, 10.0, 50.0) is True

    def test_sections_no_overlap(self, manager: SkipSectionManager):
        """Test non-overlapping sections."""
        assert manager._sections_overlap(10.0, 30.0, 40.0, 60.0) is False
        assert manager._sections_overlap(40.0, 60.0, 10.0, 30.0) is False

    def test_sections_adjacent_no_overlap(self, manager: SkipSectionManager):
        """Test that adjacent sections don't overlap."""
        assert manager._sections_overlap(10.0, 30.0, 30.0, 50.0) is False
        assert manager._sections_overlap(30.0, 50.0, 10.0, 30.0) is False


class TestGetSkipSectionById:
    """Tests for retrieving a single skip section by ID."""

    def test_get_skip_section_by_id_success(
        self, manager: SkipSectionManager, sample_job: Job
    ):
        """Test successfully retrieving a section by ID."""
        created = manager.add_skip_section(
            job_id=sample_job.id, start_seconds=10.0, end_seconds=30.0, reason="credits"
        )

        retrieved = manager.get_skip_section_by_id(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.start_seconds == 10.0
        assert retrieved.end_seconds == 30.0
        assert retrieved.reason == "credits"

    def test_get_skip_section_by_id_not_found(self, manager: SkipSectionManager):
        """Test retrieving non-existent section returns None."""
        result = manager.get_skip_section_by_id(999)
        assert result is None


class TestClearSkipSections:
    """Tests for clearing all skip sections from a job."""

    def test_clear_skip_sections_success(
        self, manager: SkipSectionManager, sample_job: Job
    ):
        """Test clearing all sections from a job."""
        # Add multiple sections
        manager.add_skip_section(
            job_id=sample_job.id, start_seconds=10.0, end_seconds=30.0
        )
        manager.add_skip_section(
            job_id=sample_job.id, start_seconds=40.0, end_seconds=60.0
        )

        count = manager.clear_skip_sections(sample_job.id)

        assert count == 2
        sections = manager.get_skip_sections(sample_job.id)
        assert len(sections) == 0

    def test_clear_skip_sections_empty(
        self, manager: SkipSectionManager, sample_job: Job
    ):
        """Test clearing sections when none exist."""
        count = manager.clear_skip_sections(sample_job.id)
        assert count == 0


class TestTotalSkippedDuration:
    """Tests for calculating total skipped duration."""

    def test_total_skipped_duration(self, manager: SkipSectionManager, sample_job: Job):
        """Test calculating total duration of all skip sections."""
        manager.add_skip_section(
            job_id=sample_job.id,
            start_seconds=10.0,
            end_seconds=30.0,  # 20 seconds
        )
        manager.add_skip_section(
            job_id=sample_job.id,
            start_seconds=50.0,
            end_seconds=100.0,  # 50 seconds
        )

        total = manager.get_total_skipped_duration(sample_job.id)

        assert total == 70.0  # 20 + 50

    def test_total_skipped_duration_empty(
        self, manager: SkipSectionManager, sample_job: Job
    ):
        """Test calculating duration when no sections exist."""
        total = manager.get_total_skipped_duration(sample_job.id)
        assert total == 0.0
