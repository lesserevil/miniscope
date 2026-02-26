"""Unit tests for job router API endpoints.

This module tests the job processing API:
- POST /api/v1/process (start video processing)
- GET /api/v1/jobs/{job_id} (job status)
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import patch

from hollywood_script_generator.db.models import Video, Job, Script
from hollywood_script_generator.models.job_status import JobStatus


class TestStartProcessing:
    """Tests for POST /api/v1/process endpoint."""

    def test_start_processing_success(self, client: TestClient, sample_video: Video):
        """Test starting processing for a valid video."""
        response = client.post("/api/v1/process", json={"video_id": sample_video.id})

        assert response.status_code == 201
        data = response.json()
        assert "job_id" in data
        assert data["video_id"] == sample_video.id
        assert data["status"] == JobStatus.PENDING.value
        assert "message" in data

    def test_start_processing_video_not_found(self, client: TestClient):
        """Test starting processing for non-existent video returns 404."""
        response = client.post("/api/v1/process", json={"video_id": 999})

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    def test_start_processing_creates_job_in_db(
        self, client: TestClient, db_session: Session, sample_video: Video
    ):
        """Test that processing request creates a job record in database."""
        response = client.post("/api/v1/process", json={"video_id": sample_video.id})

        assert response.status_code == 201
        data = response.json()

        # Verify job was created in database
        job = db_session.query(Job).filter_by(id=data["job_id"]).first()
        assert job is not None
        assert job.video_id == sample_video.id
        assert job.status == JobStatus.PENDING.value
        assert job.progress == 0.0

    def test_start_processing_invalid_video_id_type(self, client: TestClient):
        """Test that invalid video_id type returns 422."""
        response = client.post("/api/v1/process", json={"video_id": "invalid"})

        assert response.status_code == 422

    def test_start_processing_missing_video_id(self, client: TestClient):
        """Test that missing video_id returns 422."""
        response = client.post("/api/v1/process", json={})

        assert response.status_code == 422


class TestGetJobStatus:
    """Tests for GET /api/v1/jobs/{job_id} endpoint."""

    def test_get_job_status_success(self, client: TestClient, sample_job: Job):
        """Test retrieving status for an existing job."""
        response = client.get(f"/api/v1/jobs/{sample_job.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_job.id
        assert data["video_id"] == sample_job.video_id
        assert data["status"] == sample_job.status
        assert data["progress"] == sample_job.progress

    def test_get_job_status_not_found(self, client: TestClient):
        """Test retrieving status for non-existent job returns 404."""
        response = client.get("/api/v1/jobs/999")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    def test_get_job_status_with_optional_fields(
        self, client: TestClient, db_session: Session, sample_job: Job
    ):
        """Test that job status includes all fields including optional ones."""
        # Update job with error message
        sample_job.status = JobStatus.FAILED.value
        sample_job.error_message = "Processing failed"
        sample_job.started_at = __import__("datetime").datetime.utcnow()
        sample_job.completed_at = __import__("datetime").datetime.utcnow()
        db_session.commit()

        response = client.get(f"/api/v1/jobs/{sample_job.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["error_message"] == "Processing failed"
        assert data["started_at"] is not None
        assert data["completed_at"] is not None

    def test_get_job_status_with_script(
        self, client: TestClient, db_session: Session, sample_job: Job
    ):
        """Test that completed job includes script information."""
        # Create script for the job
        script = Script(
            job_id=sample_job.id,
            content="# Test Script\n\nThis is a test script with content.",
        )
        db_session.add(script)
        sample_job.status = JobStatus.COMPLETED.value
        sample_job.progress = 100.0
        db_session.commit()

        response = client.get(f"/api/v1/jobs/{sample_job.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["script"] is not None
        assert "id" in data["script"]
        assert "content_preview" in data["script"]
        assert "Test Script" in data["script"]["content_preview"]

    def test_get_job_status_no_script(self, client: TestClient, sample_job: Job):
        """Test that pending job returns null for script."""
        response = client.get(f"/api/v1/jobs/{sample_job.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["script"] is None


class TestJobResponseStructure:
    """Tests for job response model structure."""

    def test_job_response_has_required_fields(
        self, client: TestClient, sample_job: Job
    ):
        """Test that job response includes all required fields."""
        response = client.get(f"/api/v1/jobs/{sample_job.id}")

        assert response.status_code == 200
        data = response.json()
        required_fields = [
            "id",
            "video_id",
            "status",
            "progress",
            "error_message",
            "created_at",
            "started_at",
            "completed_at",
            "script",
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

    def test_job_progress_range(self, client: TestClient, sample_job: Job):
        """Test that progress is returned as a float between 0 and 100."""
        response = client.get(f"/api/v1/jobs/{sample_job.id}")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["progress"], float)
        assert 0.0 <= data["progress"] <= 100.0

    def test_job_status_enum_values(
        self, client: TestClient, db_session: Session, sample_video: Video
    ):
        """Test that all job status values are correctly returned."""
        statuses = [
            JobStatus.PENDING.value,
            JobStatus.PROCESSING.value,
            JobStatus.COMPLETED.value,
            JobStatus.FAILED.value,
        ]

        for status in statuses:
            job = Job(video_id=sample_video.id, status=status, progress=0.0)
            db_session.add(job)
            db_session.commit()
            db_session.refresh(job)

            response = client.get(f"/api/v1/jobs/{job.id}")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == status


class TestJobErrorHandling:
    """Tests for job endpoint error handling."""

    def test_invalid_job_id_format(self, client: TestClient):
        """Test that invalid job_id format returns 422."""
        response = client.get("/api/v1/jobs/invalid")
        assert response.status_code == 422

    def test_negative_job_id(self, client: TestClient):
        """Test that negative job_id returns 404."""
        response = client.get("/api/v1/jobs/-1")
        assert response.status_code == 404
