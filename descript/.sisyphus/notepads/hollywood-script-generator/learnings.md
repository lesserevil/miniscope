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

