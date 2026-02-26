"""Job status enumeration for async processing."""

from enum import Enum


class JobStatus(str, Enum):
    """Enumeration of possible job processing statuses.

    Attributes:
        PENDING: Job is queued and waiting to start.
        PROCESSING: Job is currently being processed.
        COMPLETED: Job finished successfully.
        FAILED: Job encountered an error and did not complete.
    """

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
