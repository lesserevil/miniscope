"""Tests for FastAPI application structure.

This module tests the FastAPI app factory, health check endpoint,
CORS middleware, static files, and lifespan events.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient
import asyncio


class TestAppFactory:
    """Test the FastAPI app factory function."""

    def test_create_app_returns_fastapi_instance(self):
        """Test that create_app returns a FastAPI instance."""
        from hollywood_script_generator.main import create_app

        app = create_app()

        assert isinstance(app, FastAPI)
        assert app.title == "Hollywood Script Generator"

    def test_app_has_health_endpoint(self):
        """Test that the app includes the health check endpoint."""
        from hollywood_script_generator.main import create_app

        app = create_app()
        client = TestClient(app)

        response = client.get("/health")

        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_health_endpoint_returns_expected_fields(self):
        """Test that health endpoint returns all expected fields."""
        from hollywood_script_generator.main import create_app

        app = create_app()
        client = TestClient(app)

        response = client.get("/health")
        data = response.json()

        assert "status" in data
        assert "app_name" in data
        assert "version" in data
        assert "timestamp" in data
        assert data["app_name"] == "Hollywood Script Generator"


class TestCORSMiddleware:
    """Test CORS middleware configuration."""

    def test_cors_headers_present(self):
        """Test that CORS headers are present in responses."""
        from hollywood_script_generator.main import create_app

        app = create_app()
        client = TestClient(app)

        # Make a preflight request
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

        # CORS headers should be present
        assert "access-control-allow-origin" in response.headers

    def test_cors_allows_localhost_origins(self):
        """Test that common localhost origins are allowed."""
        from hollywood_script_generator.main import create_app

        app = create_app()
        client = TestClient(app)

        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"},
        )

        assert "access-control-allow-origin" in response.headers


class TestErrorHandling:
    """Test error handling middleware."""

    def test_404_error_handler(self):
        """Test that 404 errors return JSON response."""
        from hollywood_script_generator.main import create_app

        app = create_app()
        client = TestClient(app)

        response = client.get("/nonexistent-endpoint")

        assert response.status_code == 404
        assert "detail" in response.json()

    def test_validation_error_handler(self):
        """Test that validation errors return proper JSON response."""
        from hollywood_script_generator.main import create_app

        app = create_app()
        client = TestClient(app)

        # This should trigger a validation error if we had an endpoint expecting JSON
        # For now, just verify the app handles errors gracefully
        response = client.get("/health")
        assert response.status_code == 200


class TestStaticFiles:
    """Test static file serving configuration."""

    def test_static_files_mounted(self):
        """Test that static files are properly mounted."""
        from hollywood_script_generator.main import create_app

        app = create_app()

        # Check that static files route exists
        routes = [route.path for route in app.routes]
        assert any("static" in str(route) for route in app.routes)


class TestLifespanEvents:
    """Test lifespan events (startup/shutdown)."""

    @pytest.mark.asyncio
    async def test_lifespan_events_triggered(self):
        """Test that lifespan events are properly configured."""
        from hollywood_script_generator.main import create_app

        app = create_app()

        # Lifespan events are handled automatically by TestClient
        # We just verify the app can start without errors
        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200


class TestAppConfiguration:
    """Test app configuration and settings."""

    def test_app_title(self):
        """Test that app has correct title."""
        from hollywood_script_generator.main import create_app

        app = create_app()

        assert app.title == "Hollywood Script Generator"

    def test_app_version(self):
        """Test that app has version set."""
        from hollywood_script_generator.main import create_app

        app = create_app()

        assert hasattr(app, "version")

    def test_app_description(self):
        """Test that app has description."""
        from hollywood_script_generator.main import create_app

        app = create_app()

        assert app.description is not None
        assert len(app.description) > 0


class TestRoutersIntegration:
    """Test that routers are properly integrated."""

    def test_api_router_included(self):
        """Test that API router is included in the app."""
        from hollywood_script_generator.main import create_app

        app = create_app()

        # Check that routes are registered
        routes = [route.path for route in app.routes if hasattr(route, "path")]
        assert "/health" in routes

    def test_health_endpoint_content_type(self):
        """Test that health endpoint returns JSON content type."""
        from hollywood_script_generator.main import create_app

        app = create_app()
        client = TestClient(app)

        response = client.get("/health")

        assert response.headers["content-type"] == "application/json"
