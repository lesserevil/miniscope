"""Pytest configuration and fixtures for API router tests.

This module provides shared fixtures for testing API endpoints
with in-memory database.
"""

import os
import sys

# Set test database URL BEFORE any imports
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["TESTING"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

from hollywood_script_generator.db.base import Base
from hollywood_script_generator.db.models import Video, Job, Script, SkipSection
from hollywood_script_generator.models.job_status import JobStatus


@pytest.fixture(scope="function")
def db_engine():
    """Create a fresh database engine for each test."""
    # Use a file-based SQLite database for testing to avoid connection isolation issues
    db_path = "/tmp/test_hollywood.db"
    # Remove old test database if it exists
    if os.path.exists(db_path):
        os.remove(db_path)
    
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        echo=False,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create a fresh database session for each test."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db_session, db_engine):
    """Create a test client with overridden database dependency."""
    
    # Step 1: First, clear any cached modules to ensure fresh imports
    modules_to_remove = [
        'hollywood_script_generator.api.video_router',
        'hollywood_script_generator.api.job_router',
        'hollywood_script_generator.api.script_router',
        'hollywood_script_generator.api.skip_section_router',
        'hollywood_script_generator.api.routers',
        'hollywood_script_generator.api',
        'hollywood_script_generator.main',
    ]
    for mod in modules_to_remove:
        if mod in sys.modules:
            del sys.modules[mod]
    
    # Step 2: Import video_router and patch it BEFORE anything else imports it
    import hollywood_script_generator.api.video_router as vr
    
    # Create test session factory
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    
    # Patch the engine and session at module level
    vr._engine = db_engine
    vr._SessionLocal = TestSessionLocal
    
    # Create a new get_db function that uses our test session
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    # Replace the get_db function in video_router
    vr.get_db = override_get_db
    
    # Step 3: Now import everything else (they'll get the patched get_db)
    from hollywood_script_generator.main import create_app
    from hollywood_script_generator.api import (
        video_router,
        job_router,
        script_router,
        skip_section_router,
        routers,
    )
    
    # Step 4: Double-check all get_db references are patched
    video_router.get_db = override_get_db
    job_router.get_db = override_get_db
    script_router.get_db = override_get_db
    skip_section_router.get_db = override_get_db
    routers.get_db = override_get_db
    
    app = create_app()
    
    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture(scope="function")
def sample_video(db_session):
    """Create a sample video record."""
    video = Video(
        path="/path/to/video.mp4",
        video_metadata={"duration": 120.5, "resolution": "1920x1080"},
    )
    db_session.add(video)
    db_session.commit()
    db_session.refresh(video)
    return video


@pytest.fixture(scope="function")
def sample_job(db_session, sample_video):
    """Create a sample job record."""
    job = Job(
        video_id=sample_video.id,
        status=JobStatus.PENDING.value,
        progress=0.0,
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


@pytest.fixture(scope="function")
def sample_script(db_session, sample_job):
    """Create a sample script record."""
    script = Script(
        job_id=sample_job.id,
        content="# Generated Script\n\n## Scene 1\n\nINT. OFFICE - DAY\n\nCharacter speaks.",
    )
    db_session.add(script)
    db_session.commit()
    db_session.refresh(script)
    return script


@pytest.fixture(scope="function")
def sample_skip_section(db_session, sample_job):
    """Create a sample skip section record."""
    skip = SkipSection(
        job_id=sample_job.id,
        start_seconds=10.0,
        end_seconds=30.0,
        reason="credits",
    )
    db_session.add(skip)
    db_session.commit()
    db_session.refresh(skip)
    return skip


@pytest.fixture(scope="function")
def multiple_videos(db_session):
    """Create multiple video records for pagination tests."""
    videos = []
    for i in range(5):
        video = Video(
            path=f"/path/to/video_{i}.mp4",
            video_metadata={"duration": 100.0 + i, "resolution": "1920x1080"},
        )
        db_session.add(video)
        videos.append(video)
    db_session.commit()
    for video in videos:
        db_session.refresh(video)
    return videos
