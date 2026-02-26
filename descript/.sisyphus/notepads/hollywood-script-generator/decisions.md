# Decisions from Hollywood Script Generator

## Decision 1: Tech Stack Rationale
- **FastAPI**: Modern async web framework, excellent JSON handling, auto‑generated docs
- **SQLite**: Single‑user, local disk, sufficient for MVP, no external dependencies
- **Whisper**: State‑of‑the‑art transcription, can run locally via Ollama
- **Llama 3.1 70B**: High‑quality script generation for Hollywood format

## Decision 2: Scene Chunking Strategy
- **30s chunks** with **5s overlap**
- Chosen because:
  - 30s is long enough to capture complete scenes
  - 5s overlap prevents cutting dialog at chunk boundaries
  - Easy to process sequentially

## Decision 3: Skip Section Implementation
- **CRUD API** for management
- Validation prevents overlaps
- Stored in database and applied during filtering
- Allows users to mark credits/ads manually

## Decision 4: Credits/Ads Filtering Approach
- **Heuristics** + **Manual** (two‑pronged)
- Black frame detection: OpenCV to detect darkness
- Silence detection: Whisper VAD (voice activity detection)
- Manual skips as fallback for edge cases

## Decision 5: Prompt Engineering
- Structured prompt enforces:
  - Scene headings (set descriptions)
  - Location names
  - Camera movements
  - Character descriptions
  - Dialog with speaker attribution
  - Action lines

## Decision 6: Database Schema
- **Video**: stores file path, metadata
- **Job**: tracks processing status
- **Script**: stores generated markdown
- **SkipSection**: time ranges for filtering

## Decision 7: Testing Approach
- **TDD**: Write tests first
- **pytest**: Core test framework
- **httpx**: Async API testing
- **playwright**: UI E2E tests
- **Evidence files**: Store QA results in `.sisyphus/evidence/`

## Decision 8: API Design
- RESTful endpoints:
  - Videos: GET /api/videos
  - Process: POST /api/process
  - Script: GET /api/scripts/{video_id}
  - Skip sections: CRUD /api/skip_sections/{id}
- JSON responses with proper status codes
- Background job processing with status polling