"""Unit tests for script router API endpoints.

This module tests the script retrieval API:
- GET /api/v1/scripts/{video_id} (get script)
- GET /api/v1/scripts/{video_id}/download (download script)
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from hollywood_script_generator.db.models import Video, Job, Script
from hollywood_script_generator.models.job_status import JobStatus


class TestGetScript:
    """Tests for GET /api/v1/scripts/{video_id} endpoint."""

    def test_get_script_success(
        self, client: TestClient, db_session: Session, sample_video: Video
    ):
        """Test retrieving script for a video with completed job."""
        # Create completed job with script
        job = Job(
            video_id=sample_video.id, status=JobStatus.COMPLETED.value, progress=100.0
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)

        script = Script(
            job_id=job.id,
            content="# Generated Script\n\n## Scene 1\n\nINT. OFFICE - DAY",
        )
        db_session.add(script)
        db_session.commit()

        response = client.get(f"/api/v1/scripts/{sample_video.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job.id
        assert "content" in data
        assert "Generated Script" in data["content"]

    def test_get_script_video_not_found(self, client: TestClient):
        """Test retrieving script for non-existent video returns 404."""
        response = client.get("/api/v1/scripts/999")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    def test_get_script_no_completed_job(self, client: TestClient, sample_video: Video):
        """Test retrieving script when no completed job exists."""
        response = client.get(f"/api/v1/scripts/{sample_video.id}")

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
        assert "processing" in data["detail"].lower()

    def test_get_script_pending_job(
        self, client: TestClient, db_session: Session, sample_video: Video
    ):
        """Test retrieving script when job is still pending."""
        job = Job(
            video_id=sample_video.id, status=JobStatus.PENDING.value, progress=0.0
        )
        db_session.add(job)
        db_session.commit()

        response = client.get(f"/api/v1/scripts/{sample_video.id}")

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_get_script_processing_job(
        self, client: TestClient, db_session: Session, sample_video: Video
    ):
        """Test retrieving script when job is processing."""
        job = Job(
            video_id=sample_video.id, status=JobStatus.PROCESSING.value, progress=50.0
        )
        db_session.add(job)
        db_session.commit()

        response = client.get(f"/api/v1/scripts/{sample_video.id}")

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_get_script_failed_job(
        self, client: TestClient, db_session: Session, sample_video: Video
    ):
        """Test retrieving script when job has failed."""
        job = Job(
            video_id=sample_video.id, status=JobStatus.FAILED.value, progress=50.0
        )
        db_session.add(job)
        db_session.commit()

        response = client.get(f"/api/v1/scripts/{sample_video.id}")

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_get_script_returns_most_recent(
        self, client: TestClient, db_session: Session, sample_video: Video
    ):
        """Test that the most recent completed script is returned."""
        from datetime import datetime, timedelta

        # Create older completed job
        old_job = Job(
            video_id=sample_video.id,
            status=JobStatus.COMPLETED.value,
            progress=100.0,
            completed_at=datetime.utcnow() - timedelta(days=1),
        )
        db_session.add(old_job)
        db_session.commit()
        db_session.refresh(old_job)

        old_script = Script(job_id=old_job.id, content="# Old Script")
        db_session.add(old_script)

        # Create newer completed job
        new_job = Job(
            video_id=sample_video.id,
            status=JobStatus.COMPLETED.value,
            progress=100.0,
            completed_at=datetime.utcnow(),
        )
        db_session.add(new_job)
        db_session.commit()
        db_session.refresh(new_job)

        new_script = Script(job_id=new_job.id, content="# New Script")
        db_session.add(new_script)
        db_session.commit()

        response = client.get(f"/api/v1/scripts/{sample_video.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == new_job.id
        assert "New Script" in data["content"]


class TestDownloadScript:
    """Tests for GET /api/v1/scripts/{video_id}/download endpoint."""

    def test_download_script_success(
        self, client: TestClient, db_session: Session, sample_video: Video
    ):
        """Test downloading script as markdown file."""
        # Create completed job with script
        job = Job(
            video_id=sample_video.id, status=JobStatus.COMPLETED.value, progress=100.0
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)

        script = Script(
            job_id=job.id,
            content="# Generated Script\n\n## Scene 1\n\nINT. OFFICE - DAY",
        )
        db_session.add(script)
        db_session.commit()

        response = client.get(f"/api/v1/scripts/{sample_video.id}/download")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/markdown; charset=utf-8"
        assert "attachment" in response.headers["content-disposition"]
        assert ".md" in response.headers["content-disposition"]
        content = response.text
        assert "Generated Script" in content

    def test_download_script_video_not_found(self, client: TestClient):
        """Test downloading script for non-existent video returns 404."""
        response = client.get("/api/v1/scripts/999/download")

        assert response.status_code == 404

    def test_download_script_no_script(self, client: TestClient, sample_video: Video):
        """Test downloading when no script exists."""
        response = client.get(f"/api/v1/scripts/{sample_video.id}/download")

        assert response.status_code == 404

    def test_download_script_filename(self, client: TestClient, db_session: Session):
        """Test that downloaded filename is based on video name."""
        # Create video with specific path
        video = Video(
            path="/path/to/my_video_file.mp4", video_metadata={"duration": 120.0}
        )
        db_session.add(video)
        db_session.commit()
        db_session.refresh(video)

        # Create completed job with script
        job = Job(video_id=video.id, status=JobStatus.COMPLETED.value, progress=100.0)
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)

        script = Script(job_id=job.id, content="# Test")
        db_session.add(script)
        db_session.commit()

        response = client.get(f"/api/v1/scripts/{video.id}/download")

        assert response.status_code == 200
        disposition = response.headers["content-disposition"]
        assert "my_video_file_script.md" in disposition


class TestScriptResponseStructure:
    """Tests for script response model structure."""

    def test_script_response_has_required_fields(
        self, client: TestClient, db_session: Session, sample_video: Video
    ):
        """Test that script response includes all required fields."""
        job = Job(
            video_id=sample_video.id, status=JobStatus.COMPLETED.value, progress=100.0
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)

        script = Script(job_id=job.id, content="# Test Script")
        db_session.add(script)
        db_session.commit()

        response = client.get(f"/api/v1/scripts/{sample_video.id}")

        assert response.status_code == 200
        data = response.json()
        required_fields = ["id", "job_id", "content"]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

    def test_script_content_type(
        self, client: TestClient, db_session: Session, sample_video: Video
    ):
        """Test that script content is returned as string."""
        job = Job(
            video_id=sample_video.id, status=JobStatus.COMPLETED.value, progress=100.0
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)

        script = Script(job_id=job.id, content="# Test\n\nContent")
        db_session.add(script)
        db_session.commit()

        response = client.get(f"/api/v1/scripts/{sample_video.id}")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["content"], str)
        assert "# Test" in data["content"]


class TestScriptErrorHandling:
    """Tests for script endpoint error handling."""

    def test_invalid_video_id_format(self, client: TestClient):
        """Test that invalid video_id format returns 422."""
        response = client.get("/api/v1/scripts/invalid")
        assert response.status_code == 422

    def test_negative_video_id(self, client: TestClient):
        """Test that negative video_id returns 404."""
        response = client.get("/api/v1/scripts/-1")
        assert response.status_code == 404
