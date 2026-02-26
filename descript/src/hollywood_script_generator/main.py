"""FastAPI application factory for Hollywood Script Generator.

This module provides the main FastAPI application instance with CORS middleware,
static file serving, health check endpoint, and lifespan events.
"""

from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator, Dict, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from hollywood_script_generator.api.routers import api_router
from hollywood_script_generator.core.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan events (startup/shutdown).

    This context manager handles:
    - Startup: Initialize services, create directories, load models
    - Shutdown: Cleanup resources, close connections

    Args:
        app: The FastAPI application instance.

    Yields:
        None: Control to the application during its lifetime.
    """
    settings = get_settings()

    # Startup: Create necessary directories
    # Only create directories that are within the project (not system paths)
    try:
        # Create output directory
        if (
            settings.OUTPUT_DIR.is_relative_to(Path.cwd())
            or not settings.OUTPUT_DIR.is_absolute()
        ):
            settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        # Create video directory only if it's a relative path or in the project
        if (
            settings.VIDEO_DIR.is_relative_to(Path.cwd())
            or not settings.VIDEO_DIR.is_absolute()
        ):
            settings.VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    except (PermissionError, OSError):
        # If we can't create directories, log but don't fail
        # (the app can still work with existing directories)
        pass

    # Create static directories
    static_dir = Path(__file__).parent.parent / "static"
    templates_dir = static_dir / "templates"
    css_dir = static_dir / "css"
    js_dir = static_dir / "js"

    for dir_path in [static_dir, templates_dir, css_dir, js_dir]:
        dir_path.mkdir(parents=True, exist_ok=True)

    yield

    # Shutdown: Cleanup resources
    # Add any cleanup logic here (close DB connections, etc.)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    This factory function creates a fully configured FastAPI application
    with all middleware, routers, and static file serving.

    Returns:
        FastAPI: The configured FastAPI application instance.
    """
    settings = get_settings()

    app = FastAPI(
        title="Hollywood Script Generator",
        description="A FastAPI web app that processes local MP4 videos through scene-based chunking, Whisper transcription, and local LLM script generation",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Configure CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount static files (create directory if it doesn't exist)
    static_dir = Path(__file__).parent.parent / "static"
    static_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Include API router
    app.include_router(api_router)

    # Add root-level health check endpoint
    @app.get("/health")
    async def health_check() -> Dict[str, Any]:
        """Health check endpoint.

        Returns the current health status of the application.

        Returns:
            Dict containing health status information:
            - status: "healthy" if the app is running
            - app_name: The application name
            - version: The application version
            - timestamp: ISO format timestamp of the check
        """
        settings = get_settings()

        return {
            "status": "healthy",
            "app_name": settings.APP_NAME,
            "version": "0.1.0",
            "timestamp": datetime.utcnow().isoformat(),
        }

    return app


# Global app instance for uvicorn
app = create_app()
