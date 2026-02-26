# Hollywood Script Generator

## TL;DR
Build a Python FastAPI web app that processes local MP4 videos through scene-based chunking, Whisper transcription, and local LLM script generation, filtering out credits/ads via heuristics and manual skip sections. Output Markdown scripts.

## Tech Stack
- **Language**: Python
- **Web Framework**: FastAPI
- **Database**: SQLite
- **LLM**: Local OpenAI-compatible (Ollama, Llama 3.1 70B)
- **Audio**: Whisper (local transcription)
- **Video**: MoviePy, OpenCV
- **Testing**: pytest (TDD)
- **Output**: Markdown

## Key Features
- Local video file browser UI
- Scene-based chunking (30s segments)
- Skip section management (user marks time ranges)
- Credits/ads filtering (black frame + silence heuristics)
- Async job processing
- LLM script generation

## Scope Boundaries (MUST NOT)
- No video uploads from web
- No video player/viewer
- No script editor UI
- No output formats other than Markdown
- No user auth
- No cloud storage

## Execution Strategy: 5 Waves

### Wave 1 (Foundation - 5 tasks)
1. **Project setup + dependencies**: pyproject.toml with all deps, project structure, pytest config
2. **Type definitions + config**: VideoMetadata, JobStatus, Settings class, .env.example
3. **Database schema + models**: SQLAlchemy models (Video, Job, Script, SkipSection), Alembic migrations
4. **FastAPI app structure**: app factory, CORS, health check, static files
5. **LLM client service**: OpenAI SDK integration with local LLM, prompt templates

### Wave 2 (Processing Core - 5 tasks)
6. **Video chunker + scene detection**: MoviePy/OpenCV scene detection, 30s chunks with overlap
7. **Audio transcriber (Whisper)**: Load model, transcribe chunks, store timestamps
8. **Skip sections manager**: CRUD for time ranges, validate no overlaps
9. **Credits/ads filter (heuristics)**: Black frame detection, silence detection
10. **Script assembler**: Combine chunks → LLM generation → final Markdown

### Wave 3 (API Endpoints - 4 tasks)
11. **Video browsing API**: GET /api/videos (list MP4), GET /api/videos/{path}
12. **Job processing API**: POST /api/process, GET /api/jobs/{job_id}
13. **Script retrieval API**: GET /api/scripts/{video_id}, download Markdown
14. **Skip section management API**: POST/PUT/DELETE /api/skip_sections/{id}

### Wave 4 (UI Layer - 3 tasks)
15. **Video browser UI**: List videos, click to view details
16. **Skip sections management UI**: Time range picker, list skip sections, CRUD
17. **Status monitoring UI**: Real-time job status, progress bar

### Wave 5 (Integration - 3 tasks)
18. **Integration tests**: Complete pipeline test with real video files
19. **UI end-to-end tests**: Playwright test full user flow
20. **E2E processing test**: Sample video → process → verify script content

## Final Verification Wave
- [ ] F1. Plan Compliance Audit (oracle) - Verify MUST HAVE and MUST NOT
- [ ] F2. Code Quality Review - Lint, test, check for AI slop
- [ ] F3. Real Manual QA - Execute all QA scenarios
- [ ] F4. Scope Fidelity Check - Verify nothing beyond spec

## Success Criteria
- All pytest tests pass
- App runs on localhost:8000
- Video browser shows MP4 files
- Processing creates job and script
- Script includes: sets, locations, camera, characters, dialog
- Skip sections UI works
- Local processing only (no cloud APIs)

## To Begin
Run: `/start-work hollywood-script-generator`
