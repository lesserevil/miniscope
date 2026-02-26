"""Skip section manager service for managing video skip sections.

This module provides the SkipSectionManager class for:
- Creating skip sections with overlap validation
- Retrieving skip sections for a job
- Updating skip sections
- Deleting skip sections
- Checking for overlapping time ranges

Example:
    >>> from sqlalchemy.orm import Session
    >>> session = Session(engine)
    >>> manager = SkipSectionManager(session)
    >>> section = manager.add_skip_section(
    ...     job_id=1,
    ...     start_seconds=10.0,
    ...     end_seconds=30.0,
    ...     reason="credits"
    ... )
    >>> sections = manager.get_skip_sections(job_id=1)
"""

from typing import List, Optional
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from hollywood_script_generator.db.models import SkipSection

logger = logging.getLogger(__name__)


class OverlappingSectionError(Exception):
    """Raised when attempting to create or update a skip section that overlaps with existing sections."""

    def __init__(self, message: str = "Skip section overlaps with an existing section"):
        self.message = message
        super().__init__(self.message)


class InvalidTimeRangeError(Exception):
    """Raised when a time range is invalid (e.g., start >= end, negative times)."""

    def __init__(self, message: str = "Invalid time range"):
        self.message = message
        super().__init__(self.message)


class SkipSectionManager:
    """Service for managing skip sections with CRUD operations and overlap validation.

    This service provides methods to create, read, update, and delete skip sections
    for video processing jobs. It includes validation to prevent overlapping time ranges.

    Attributes:
        session: SQLAlchemy database session for database operations.

    Example:
        >>> manager = SkipSectionManager(session)
        >>> section = manager.add_skip_section(
        ...     job_id=1,
        ...     start_seconds=10.0,
        ...     end_seconds=30.0,
        ...     reason="credits"
        ... )
        >>> sections = manager.get_skip_sections(job_id=1)
    """

    def __init__(self, session: Session):
        """Initialize the SkipSectionManager.

        Args:
            session: SQLAlchemy database session for database operations.
        """
        self.session = session
        logger.debug("SkipSectionManager initialized")

    def _validate_time_range(self, start_seconds: float, end_seconds: float) -> None:
        """Validate a time range.

        Args:
            start_seconds: Start time in seconds.
            end_seconds: End time in seconds.

        Raises:
            InvalidTimeRangeError: If start_seconds >= end_seconds or if start_seconds < 0.
        """
        if start_seconds < 0:
            raise InvalidTimeRangeError("Start time cannot be negative")

        if start_seconds >= end_seconds:
            raise InvalidTimeRangeError("Start time must be less than end time")

    def _sections_overlap(
        self, start1: float, end1: float, start2: float, end2: float
    ) -> bool:
        """Check if two time ranges overlap.

        Two sections overlap if they share any time period.
        Adjacent sections (where end1 == start2 or end2 == start1) do NOT overlap.

        Args:
            start1: Start time of first section.
            end1: End time of first section.
            start2: Start time of second section.
            end2: End time of second section.

        Returns:
            True if the sections overlap, False otherwise.
        """
        # Sections overlap if one starts before the other ends
        # AND ends after the other starts
        # But they don't overlap if they just touch at boundaries
        return start1 < end2 and end1 > start2

    def _check_for_overlap(
        self,
        job_id: int,
        start_seconds: float,
        end_seconds: float,
        exclude_id: Optional[int] = None,
    ) -> bool:
        """Check if a time range would overlap with existing skip sections.

        Args:
            job_id: ID of the job to check.
            start_seconds: Start time of the new section.
            end_seconds: End time of the new section.
            exclude_id: Optional section ID to exclude from check (for updates).

        Returns:
            True if there's an overlap, False otherwise.
        """
        query = select(SkipSection).where(SkipSection.job_id == job_id)

        if exclude_id is not None:
            query = query.where(SkipSection.id != exclude_id)

        existing_sections = self.session.execute(query).scalars().all()

        for section in existing_sections:
            if self._sections_overlap(
                start_seconds, end_seconds, section.start_seconds, section.end_seconds
            ):
                return True

        return False

    def add_skip_section(
        self,
        job_id: int,
        start_seconds: float,
        end_seconds: float,
        reason: Optional[str] = None,
    ) -> SkipSection:
        """Add a new skip section for a job.

        Args:
            job_id: ID of the job to add the section to.
            start_seconds: Start time in seconds.
            end_seconds: End time in seconds.
            reason: Optional reason for skipping (e.g., 'credits', 'ad').

        Returns:
            The created SkipSection instance.

        Raises:
            InvalidTimeRangeError: If the time range is invalid.
            OverlappingSectionError: If the section overlaps with an existing section.
        """
        logger.debug(
            f"Adding skip section for job {job_id}: {start_seconds}s - {end_seconds}s"
        )

        # Validate time range
        self._validate_time_range(start_seconds, end_seconds)

        # Check for overlaps
        if self._check_for_overlap(job_id, start_seconds, end_seconds):
            raise OverlappingSectionError(
                f"Skip section ({start_seconds}s - {end_seconds}s) overlaps with an existing section"
            )

        # Create the section
        section = SkipSection(
            job_id=job_id,
            start_seconds=start_seconds,
            end_seconds=end_seconds,
            reason=reason,
        )

        self.session.add(section)
        self.session.commit()
        self.session.refresh(section)

        logger.info(
            f"Created skip section {section.id} for job {job_id}: "
            f"{start_seconds}s - {end_seconds}s"
        )

        return section

    def get_skip_sections(self, job_id: int) -> List[SkipSection]:
        """Get all skip sections for a job, sorted by start time.

        Args:
            job_id: ID of the job to get sections for.

        Returns:
            List of SkipSection instances sorted by start_seconds.
        """
        query = (
            select(SkipSection)
            .where(SkipSection.job_id == job_id)
            .order_by(SkipSection.start_seconds)
        )

        sections = self.session.execute(query).scalars().all()

        logger.debug(f"Retrieved {len(sections)} skip sections for job {job_id}")

        return list(sections)

    def get_skip_section_by_id(self, section_id: int) -> Optional[SkipSection]:
        """Get a skip section by its ID.

        Args:
            section_id: ID of the section to retrieve.

        Returns:
            The SkipSection instance if found, None otherwise.
        """
        section = self.session.get(SkipSection, section_id)

        if section:
            logger.debug(f"Retrieved skip section {section_id}")
        else:
            logger.debug(f"Skip section {section_id} not found")

        return section

    def update_skip_section(
        self,
        section_id: int,
        start_seconds: Optional[float] = None,
        end_seconds: Optional[float] = None,
        reason: Optional[str] = None,
    ) -> Optional[SkipSection]:
        """Update an existing skip section.

        Args:
            section_id: ID of the section to update.
            start_seconds: New start time (or None to keep current).
            end_seconds: New end time (or None to keep current).
            reason: New reason (or None to keep current).

        Returns:
            The updated SkipSection instance if found, None otherwise.

        Raises:
            InvalidTimeRangeError: If the new time range is invalid.
            OverlappingSectionError: If the updated section would overlap with another.
        """
        section = self.get_skip_section_by_id(section_id)

        if section is None:
            logger.warning(f"Cannot update: skip section {section_id} not found")
            return None

        # Determine new values (use existing if not provided)
        new_start = (
            start_seconds if start_seconds is not None else section.start_seconds
        )
        new_end = end_seconds if end_seconds is not None else section.end_seconds

        logger.debug(f"Updating skip section {section_id}: {new_start}s - {new_end}s")

        # Validate time range if either value changed
        if start_seconds is not None or end_seconds is not None:
            self._validate_time_range(new_start, new_end)

        # Check for overlaps (excluding this section)
        if self._check_for_overlap(
            section.job_id, new_start, new_end, exclude_id=section_id
        ):
            raise OverlappingSectionError(
                f"Updated section ({new_start}s - {new_end}s) would overlap with an existing section"
            )

        # Update fields
        section.start_seconds = new_start
        section.end_seconds = new_end
        if reason is not None:
            section.reason = reason

        self.session.commit()
        self.session.refresh(section)

        logger.info(f"Updated skip section {section_id}")

        return section

    def delete_skip_section(self, section_id: int) -> bool:
        """Delete a skip section by its ID.

        Args:
            section_id: ID of the section to delete.

        Returns:
            True if the section was deleted, False if not found.
        """
        section = self.get_skip_section_by_id(section_id)

        if section is None:
            logger.warning(f"Cannot delete: skip section {section_id} not found")
            return False

        self.session.delete(section)
        self.session.commit()

        logger.info(f"Deleted skip section {section_id}")

        return True

    def clear_skip_sections(self, job_id: int) -> int:
        """Delete all skip sections for a job.

        Args:
            job_id: ID of the job to clear sections for.

        Returns:
            Number of sections deleted.
        """
        sections = self.get_skip_sections(job_id)
        count = len(sections)

        for section in sections:
            self.session.delete(section)

        self.session.commit()

        logger.info(f"Cleared {count} skip sections for job {job_id}")

        return count

    def get_total_skipped_duration(self, job_id: int) -> float:
        """Calculate the total duration of all skip sections for a job.

        Args:
            job_id: ID of the job to calculate duration for.

        Returns:
            Total duration in seconds of all skip sections.
        """
        sections = self.get_skip_sections(job_id)
        total = sum(section.end_seconds - section.start_seconds for section in sections)

        logger.debug(f"Total skipped duration for job {job_id}: {total}s")

        return total
