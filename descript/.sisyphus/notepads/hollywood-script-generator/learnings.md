# Learning from Hollywood Script Generator

## Key Architectural Decisions

### Scene-Based Chunking
- Using **30s chunks with 5s overlap** to capture scene transitions accurately
- Overlap prevents cutting dialog in the middle
- Each chunk includes start/end timestamps for precise filtering

### Skip Section Management
- **CRUD operations** for user-defined time ranges
- Validation to prevent overlapping sections
- Persisted in database and applied during filtering

### Credits/Ads Filtering
- **Two‑pronged approach**: Heuristics + Manual
  1. **Black frame detection** (using OpenCV)
  2. **Silence detection** (using ffmpeg/whisper)
- Allows users to add manual skips for edge cases

### LLM Integration
- Using **Ollama** as local OpenAI-compatible endpoint
- Model: **llama3.1:70b** for high-quality script generation
- Prompt template enforces: sets, locations, camera movements, character descriptions, dialog

### Database Schema
- **Video** table: stores video metadata, file paths
- **Job** table: tracks processing status (pending/processing/completed/failed)
- **Script** table: stores generated markdown
- **SkipSection** table: stores time ranges

## Testing Strategy

### TDD Approach
1. Write tests first (what we want to achieve)
2. Implement minimal code to pass tests
3. Refactor while maintaining coverage

### Test Categories
- **Unit tests**: Individual functions, services, models
- **Integration tests**: API endpoints, database interactions
- **E2E tests**: Playwright for full user flows

### QA Evidence
- Every task includes Agent‑Executed QA scenarios stored in `.sisyphus/evidence/`
- Evidence includes: test results, manual verification logs, bug reports

## Known Gotchas

1. **Video processing can be slow** - Use async processing and status tracking
2. **Chunk boundaries might cut through scenes** - Overlap strategy mitigates this
3. **Whisper model size**: 70B model needs significant RAM (18GB+)
4. **Cross‑platform video paths**: Need to handle platform‑specific path formats

## Dependencies to Remember

- `whisper` for transcription
- `openai` for LLM client (compatible with Ollama)
- `sqlalchemy` + `alembic` for DB
- `fastapi`, `uvicorn` for web
- `moviepy`, `opencv-python-headless` for video processing
- `pytest`, `pytest-asyncio`, `httpx` for testing
- `playwright` for UI E2E tests
## Task 1: Project Setup Learnings

- Using src-layout for Python package structure (src/hollywood_script_generator/)
- pyproject.toml configured with [tool.setuptools.packages.find] for modern packaging
- pytest.ini uses 'asyncio_mode = auto' for automatic async fixture handling
- All dependencies pinned with minimum versions for reproducibility
- .env.example includes comprehensive documentation for each variable
- Comprehensive .gitignore covers Python, IDE, OS, and application-specific files

## Task 2: Type Definitions Learnings

- **pydantic-settings** simplifies Settings class by reading from environment variables automatically
- **pydantic BaseModel** provides built-in validation, serialization, and model_config support
- **field_validator** and **model_validator** decorators are powerful tools for custom validation logic
- **Enum from str** allows JobStatus to be compared with strings, useful for external APIs
- **Path type** from pathlib is preferred over str for file paths in modern Python
- **pytest + monkeypatch** is the standard pattern for testing environment variable loading
- **Validation constraints** (gt, ge, le, etc.) automatically create tests for edge cases
- **comprehensive docstrings** are essential for complex classes with many validators
- **Computed properties** (width, height, total_frames) are useful abstractions for metadata models

## Task 3: Database Schema + Models Learnings

### SQLAlchemy 2.0 Style

- **Use `Mapped[T]` type annotations** for all columns - enables better IDE support and type checking
- **Use `mapped_column()`** instead of `Column()` for column definitions
- **DeclarativeBase** is the modern way to create the base class (not `declarative_base()`)

### Reserved Attribute Names

- **`metadata` is reserved** in SQLAlchemy Declarative API - rename to `video_metadata` or similar
- Always check for reserved names when defining model attributes

### Alembic Configuration

- **Initialize alembic** in the db directory: `alembic init migrations`
- **Update alembic.ini** to set proper database URL (sqlite:///./hollywood_script_generator.db)
- **Update env.py** to:
  - Add project to sys.path for imports
  - Import Base and models
  - Set `target_metadata = Base.metadata` (not None)
- **Remove or comment out** the `target_metadata = None` line that alembic generates

### Relationships

- **back_populates** creates bidirectional relationships
- **cascade="all, delete-orphan"** ensures child records are deleted when parent is deleted
- **ForeignKey with ondelete="CASCADE"** ensures database-level cascading

### Indexes

- **Always add indexes** on foreign keys and frequently queried columns
- **Use `__table_args__`** to define composite indexes and constraints
- Naming convention: `ix_tablename_columnname`

### Testing

- **Use in-memory SQLite** for unit tests: `create_engine("sqlite:///:memory:")`
- **Create fresh session per test** using pytest fixtures with `scope="function"`
- **Test relationships** by actually creating related records and verifying navigation
- **Test cascading deletes** by deleting parent and verifying children are gone

### Foreign Keys and SQLite

- SQLite supports foreign keys but **they're disabled by default**
- Enable with: `PRAGMA foreign_keys = ON`
- SQLAlchemy handles this automatically in most cases

### TDD Workflow

1. Write tests defining expected model behavior
2. Run tests (they will fail - models don't exist yet)
3. Create minimal model implementation
4. Run tests again - fix until all pass
5. Refactor if needed while maintaining green tests


## Task 3: Database Models Learnings

- **SQLAlchemy 2.0** uses Mapped[T] for type annotations and mapped_column for column definitions
- **declarative_base** provides a central base class for all models (DeclarativeBase)
- **JSON column** is useful for flexible metadata storage (video_metadata)
- **relationship()** with back_populates provides bidirectional navigation
- **cascade="all, delete-orphan"** ensures cleanup of related records
- **unique constraint** enforces one-to-one relationship on Script.job_id
- **Indexes** on foreign keys improve query performance for joins
- **server_default=func.now()** sets timestamp defaults at database level
- **onupdate=func.now()** automatically updates timestamps on model updates
- **TDD for SQLAlchemy**: Test fixture with in-memory SQLite is standard pattern
- **Alembic** provides automatic migration generation and versioning
- **ForeignKey with CASCADE** on delete ensures referential integrity
- **Text type** is appropriate for large content (script content)
- **Float** type for time values (start_seconds, end_seconds)


## Task 4: FastAPI App Structure Learnings

### FastAPI App Factory Pattern
- **Use `create_app()` factory function** instead of global app instance for better testability
- **@asynccontextmanager** for lifespan events handles startup/shutdown cleanly
- **Lifespan events** are the modern replacement for @app.on_event("startup"/"shutdown")

### CORS Configuration
- **CORSMiddleware** must be added before including routers
- **Common dev origins** to allow: localhost:3000 (Next.js), localhost:5173 (Vite)
- **allow_credentials=True** requires specific origins (not "*")

### Static Files
- **StaticFiles directory** should be created on startup if it doesn't exist
- **Mount static files** using `app.mount("/static", StaticFiles(...), name="static")`
- Static directories structure: `static/templates/`, `static/css/`, `static/js/`

### Health Check Endpoint
- **Root-level health check** at `/health` for easy monitoring
- **Include app metadata** in response: name, version, timestamp, status
- **Return type annotation** should be `Dict[str, Any]` for FastAPI schema

### Directory Creation in Lifespan
- **Handle permission errors gracefully** when creating directories
- **Check if path is within project** before attempting to create system paths
- **Use `is_relative_to(Path.cwd())`** to verify paths are project-relative

### Testing FastAPI
- **TestClient** automatically triggers lifespan events
- **Test CORS** with OPTIONS preflight requests
- **Test static files** by checking for Mount objects in app.routes
- **Separate concerns**: test app factory, middleware, routes, and lifespan independently

### Router Organization
- **APIRouter with prefix** for versioning: `/api/v1`
- **Separate routers** for different domains (videos, jobs, scripts)
- **Root-level endpoints** defined in main.py (health check, docs)

### Type Annotations
- **Always use type hints** for FastAPI to generate OpenAPI schema
- **Return type** must be explicitly annotated for proper JSON response
- **Use `from typing import Dict, Any`** for flexible return types

## Task 5: LLM Client Service Learnings

### OpenAI SDK with Ollama

- **Ollama is OpenAI-compatible**: Uses the same API format, just point `base_url` to `http://localhost:11434/v1`
- **API key can be any string**: Ollama doesn't validate the API key, use `"ollama"` or similar
- **Long timeouts needed**: Script generation can take minutes, use `httpx.Timeout(300.0, connect=10.0)`
- **Model name format**: Ollama uses `model:tag` format (e.g., `llama3.1:70b`)

### Prompt Engineering for Scripts

- **System prompt is critical**: Explicitly list all required elements (sets, locations, camera, characters, dialogue)
- **Use numbered rules**: Clear constraints in system prompt improve output quality
- **Context helps**: Pass video metadata (title, duration) for better scene context
- **Template placeholders**: Use `{transcript}` and `{context}` for dynamic content

### Retry Logic Implementation

- **Exponential backoff**: Double delay on each retry (`retry_delay *= 2`)
- **Retry specific exceptions**: Only retry transient errors (RateLimitError, ConnectError, Timeout)
- **Max retries**: 3 attempts is a good balance for local LLM
- **Preserve last error**: Store the last exception to include in final error message

### Testing LLM Services

- **Mock OpenAI client**: Patch `hollywood_script_generator.services.llm_service.OpenAI`
- **Mock completion structure**: `completion.choices[0].message.content` pattern
- **Test retry logic**: Mock side_effect with multiple return values (fail, fail, success)
- **Patch time.sleep**: Prevent actual delays in retry tests
- **Mock httpx errors**: For connection error testing

### Error Handling Strategy

- **Differentiate error types**: Retry transient, fail fast on API errors
- **Empty responses**: Return empty string gracefully rather than crashing
- **Descriptive messages**: Include original error in exception message
- **Type safety**: Return type annotation ensures consistent handling

### Type Annotations for LLM

- **Optional parameters**: Use `Optional[Type] = None` for overridable settings
- **Flexible context**: `Optional[Dict[str, Any]]` allows arbitrary metadata
- **Return types**: Always annotate return types for IDE support


## Task 7: Audio Transcriber (Whisper) Learnings

### Whisper Integration

#### Model Loading
- **Use `whisper.load_model()`** to load models: `whisper.load_model("base", device="cpu")`
- **Lazy loading pattern**: Load model on first access and cache in instance variable
- **Model caching**: Prevents repeated loading overhead when transcribing multiple chunks
- **Device selection**: Pass `device="cpu"` or `device="cuda"` to control inference device

#### Audio Preprocessing
- **MoviePy for extraction**: Use `VideoFileClip` to extract audio from video files
- **Mono conversion**: Whisper expects mono audio - average stereo channels if needed
- **Resampling**: Resample to 16kHz (Whisper's expected sample rate) using interpolation
- **Float32 format**: Ensure audio is float32 numpy array before passing to Whisper

#### Timestamp Handling
- **Absolute timestamps**: Adjust Whisper's relative timestamps by adding chunk start time
- **Segment structure**: Each segment has text, start_time, end_time
- **Chunk boundaries**: Track both chunk-level and segment-level timestamps

#### Testing Strategy
- **Mock Whisper library**: Patch `whisper.load_model()` to avoid actual model downloads
- **Mock MoviePy**: Patch `VideoFileClip` to avoid file I/O in tests
- **Test timestamp math**: Verify relative timestamps are correctly offset to absolute times
- **Test audio preprocessing**: Verify stereo→mono conversion and resampling logic

#### Error Handling
- **Model loading errors**: Wrap in RuntimeError with descriptive message
- **Video file errors**: Handle file not found, unsupported formats gracefully
- **Transcription errors**: Catch and re-raise with context about which chunk failed

#### API Design
- **Two entry points**: 
  - `transcribe()` for raw audio arrays
  - `transcribe_chunk()` for video file + time range
- **Batch processing**: `batch_transcribe()` handles multiple chunks efficiently
- **Language option**: Optional language parameter for non-English content
- **Result dataclass**: `TranscriptionResult` encapsulates text, segments, and timing



## Task 8: Skip Section Manager Learnings

### Overlap Detection Logic
- **Mathematical approach**: Two sections overlap when: start1 < end2 AND end1 > start2
- **Adjacent sections allowed**: (10-30) and (30-50) don't overlap - useful for back-to-back skip ranges
- **Complete containment**: Handled automatically by the same logic
- **Direction independent**: Logic works regardless of order of comparison

### CRUD Service Pattern
- **Session injection**: Pass SQLAlchemy session to service constructor
- **Immediate commit**: Call session.commit() after modifications
- **Refresh after commit**: Call session.refresh() to get DB-generated fields (like ID)
- **Return instances**: Return model instances, not just IDs

### Validation Strategy
- **Two-phase validation**:
  1. Time range validity (start < end, no negatives)
  2. Overlap check with existing sections
- **Separate error types**: Different exceptions for different validation failures
- **Partial updates**: Only validate when relevant fields change

### Testing CRUD Services
- **In-memory SQLite**: Fast, isolated tests with real database behavior
- **Fixture pattern**: Create base fixtures (session, video, job) for reuse
- **Test categories**: Group tests by operation type (Add, Get, Delete, Update)
- **Edge cases**: Test boundaries (adjacent sections, exact overlaps)
- **Error cases**: Verify proper exceptions raised with pytest.raises()

### SQLAlchemy 2.0 Best Practices
- **session.get(Model, id)**: New method for primary key lookup (replaces query.get())
- **select() syntax**: Modern query style with select(Model) instead of session.query()
- **scalars().all()**: Get list of model instances from results
- **order_by()**: Sort in query rather than in Python for efficiency


## Task 9: Credits/Ads Filter (Heuristics) Learnings

### Black Frame Detection

#### OpenCV Frame Processing
- **VideoCapture properties**: Use `cv2.CAP_PROP_FPS` (5) and `cv2.CAP_PROP_FRAME_COUNT` (7) for timing
- **Frame seeking**: `cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)` to jump to specific frames
- **Brightness calculation**: Average of grayscale pixels gives reliable brightness metric
- **Threshold approach**: Default threshold of 20 (0-255 scale) works well for detecting black frames

#### Detection Logic
- Track consecutive black frames to form sections
- Require minimum duration (default 1.0s) to filter out brief transitions
- Calculate confidence based on proportion of black frames in section

### Silence Detection

#### Audio Processing with MoviePy
- **Subclip extraction**: Use `clip.audio.subclipped(start, end).to_soundarray()` for chunks
- **Chunk size**: 500ms chunks provide good balance between precision and performance
- **Mono conversion**: Average stereo channels for consistent analysis
- **dB calculation**: RMS to dB conversion: `20 * log10(rms)`

#### Threshold Approach
- Default -40 dB threshold captures typical silent sections
- Credits often have very low or no audio
- Advertisements may have variable audio levels

### Section Combination Strategy

#### Merging Logic
- Sort all sections by start time first
- Check for overlap: `section1.start < section2.end AND section1.end > section2.start`
- When merging, extend to maximum end time of overlapping sections
- Manual sections take precedence in method assignment

#### Adjacent vs Overlapping
- Adjacent sections (end1 == start2) remain separate
- Only truly overlapping sections are merged
- This preserves distinct credits/ad breaks

### Testing Challenges

#### Mock Complexity
- Video frame mocks need sufficient frames to exceed min_section_duration
- Audio mocking requires chain: `subclipped().to_soundarray()`
- Frame counts must align with FPS and duration expectations

#### TDD Benefits
- Writing tests first forced clear API design
- Mock setup revealed implementation requirements early
- Edge cases (no video, no audio) were considered upfront

### Integration Points

#### With VideoChunker
- Can be run on full video or per-chunk basis
- Chunks provide natural boundaries for analysis
- Scene changes help identify likely credit boundaries

#### With SkipSectionManager
- Heuristic detections combine with user-specified skips
- Same FilteredSection format allows seamless integration
- Manual skips take precedence when merging overlaps

### Configuration Best Practices

#### Threshold Validation
- Validate thresholds in constructor (fail fast)
- Black frame: 1-255 range
- Silence: negative dB values
- Duration: positive seconds

#### Default Values
- Conservative defaults prevent false positives
- Users can adjust based on content type
- Document thresholds clearly for end users


## Task 9: Credits/Ads Filter Learnings

### Black Frame Detection with OpenCV

**Implementation Details:**
- Use `cv2.VideoCapture` for reading video frames
- Convert to grayscale with `cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)`
- Calculate mean brightness with `np.mean(gray)`
- Track consecutive frames below threshold using state machine pattern
- Consider FPS when calculating durations: `duration = frame_count / fps`

**Threshold Considerations:**
- Default threshold of 20 works for most content (0-255 scale)
- Typical video has brightness > 50, black frames < 10
- Should be configurable per video type

### Silence Detection with Audio Processing

**Implementation Details:**
- Use MoviePy's `VideoFileClip` for audio extraction
- Convert stereo to mono: `np.mean(audio_chunk, axis=1)`
- Calculate RMS: `np.sqrt(np.mean(audio_chunk**2))`
- Convert to dB: `20 * np.log10(rms)`
- Protect against log(0) with epsilon check

**Chunk Processing:**
- Process in 500ms chunks for reasonable granularity
- Track consecutive silent chunks
- Minimum duration filtering to exclude brief pauses

### Test Mocking Strategy

**Video Frame Mocking:**
```python
mock_cap.get.side_effect = lambda prop: {
    5: 10.0,  # FPS (cv2.CAP_PROP_FPS = 5)
    7: 100,   # Total frames (cv2.CAP_PROP_FRAME_COUNT = 7)
}.get(prop, 0)
```

**Audio Chain Mocking:**
```python
mock_clip.audio.subclipped(start, end).to_soundarray()
```
Requires mocking the full chain of calls.

**Key Lesson:** Ensure enough mock frames to exceed `min_section_duration`:
- At 10 FPS, need at least 10 frames for 1 second
- Add buffer: use 20+ frames to be safe

### Section Merging Logic

**Overlap Detection:**
Two sections overlap if: `start1 < end2 AND end1 > start2`
Adjacent sections (end1 == start2) do NOT overlap.

**Merge Priority:**
- Manual sections take precedence over detected
- When merging, preserve MANUAL method and confidence=1.0
- Extend end time to max of both sections

### Integration Points

**With SkipSectionManager:**
- CreditsFilter works independently (no DB)
- Can convert FilteredSection to SkipSection for persistence
- Combines detected + manual before storage

**With VideoChunker:**
- Filter video before chunking for efficiency
- Or filter per-chunk for more granular control
- Skip sections reduce chunk count

