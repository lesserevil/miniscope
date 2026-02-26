"""Unit tests for video router API endpoints.

This module tests the video browsing API:
- GET /api/v1/videos (list videos)
- GET /api/v1/videos/{video_id} (video details)
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from hollywood_script_generator.db.models import Video, Job
from hollywood_script_generator.models.job_status import JobStatus


class TestListVideos:
    """Tests for GET /api/v1/videos endpoint."""

    def test_list_videos_empty(self, client: TestClient, db_session: Session):
        """Test listing videos when database is empty."""
        response = client.get("/api/v1/videos")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_list_videos_returns_video_data(
        self, client: TestClient, sample_video: Video
    ):
        """Test that listing videos returns correct video metadata."""
        response = client.get("/api/v1/videos")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == sample_video.id
        assert data[0]["path"] == sample_video.path
        assert "video_metadata" in data[0]
        assert "created_at" in data[0]
        assert "updated_at" in data[0]

    def test_list_videos_with_pagination(
        self, client: TestClient, multiple_videos: list
    ):
        """Test pagination with skip and limit parameters."""
        # Test with limit
        response = client.get("/api/v1/videos?limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

        # Test with skip
        response = client.get("/api/v1/videos?skip=2&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

        # Test with skip exceeding count
        response = client.get("/api/v1/videos?skip=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

    def test_list_videos_default_limit(self, client: TestClient, multiple_videos: list):
        """Test that default limit of 100 is applied."""
        response = client.get("/api/v1/videos")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5  # All 5 videos returned


class TestGetVideo:
    """Tests for GET /api/v1/videos/{video_id} endpoint."""

    def test_get_video_success(self, client: TestClient, sample_video: Video):
        """Test retrieving a specific video by ID."""
        response = client.get(f"/api/v1/videos/{sample_video.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_video.id
        assert data["path"] == sample_video.path
        assert "video_metadata" in data
        assert "jobs" in data
        assert isinstance(data["jobs"], list)

    def test_get_video_not_found(self, client: TestClient):
        """Test retrieving non-existent video returns 404."""
        response = client.get("/api/v1/videos/999")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    def test_get_video_with_jobs(
        self, client: TestClient, db_session: Session, sample_video: Video
    ):
        """Test that video details include associated jobs."""
        # Create jobs for the video
        job1 = Job(
            video_id=sample_video.id, status=JobStatus.COMPLETED.value, progress=100.0
        )
        job2 = Job(
            video_id=sample_video.id, status=JobStatus.PENDING.value, progress=0.0
        )
        db_session.add(job1)
        db_session.add(job2)
        db_session.commit()

        response = client.get(f"/api/v1/videos/{sample_video.id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data["jobs"]) == 2
        job_ids = [j["id"] for j in data["jobs"]]
        assert job1.id in job_ids
        assert job2.id in job_ids

    def test_get_video_job_summary_fields(
        self, client: TestClient, db_session: Session, sample_video: Video
    ):
        """Test that job summaries contain expected fields."""
        job = Job(
            video_id=sample_video.id, status=JobStatus.PROCESSING.value, progress=50.0
        )
        db_session.add(job)
        db_session.commit()

        response = client.get(f"/api/v1/videos/{sample_video.id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data["jobs"]) == 1
        job_data = data["jobs"][0]
        assert "id" in job_data
        assert "status" in job_data
        assert "progress" in job_data
        assert "created_at" in job_data


class TestVideoResponseStructure:
    """Tests for video response model structure."""

    def test_video_response_has_required_fields(
        self, client: TestClient, sample_video: Video
    ):
        """Test that video response includes all required fields."""
        response = client.get(f"/api/v1/videos/{sample_video.id}")

        assert response.status_code == 200
        data = response.json()
        required_fields = [
            "id",
            "path",
            "video_metadata",
            "created_at",
            "updated_at",
            "jobs",
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

    def test_video_metadata_type(self, client: TestClient, sample_video: Video):
        """Test that video_metadata is returned as an object/dict."""
        response = client.get("/api/v1/videos")

        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert isinstance(data[0]["video_metadata"], dict)

    def test_video_datetime_format(self, client: TestClient, sample_video: Video):
        """Test that datetime fields are properly formatted."""
        response = client.get(f"/api/v1/videos/{sample_video.id}")

        assert response.status_code == 200
        data = response.json()
        # Datetime should be ISO format string in JSON
        assert isinstance(data["created_at"], str)
        assert isinstance(data["updated_at"], str)
        assert "T" in data["created_at"]  # ISO format indicator


class TestVideoErrorHandling:
    """Tests for video endpoint error handling."""

    def test_invalid_video_id_format(self, client: TestClient):
        """Test that invalid video_id format returns appropriate error."""
        # FastAPI will return 422 for type validation errors
        response = client.get("/api/v1/videos/invalid")
        assert response.status_code == 422

    def test_negative_video_id(self, client: TestClient):
        """Test that negative video_id returns 404."""
        response = client.get("/api/v1/videos/-1")
        assert response.status_code == 404
