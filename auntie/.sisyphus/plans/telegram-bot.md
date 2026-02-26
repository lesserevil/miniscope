# Telegram Companion Bot - Phase 1

## TL;DR

> **Quick Summary**: Build a production-grade Telegram bot with extensible plugin/skill system using Python and python-telegram-bot v20+. Phase 1 delivers core conversational engine + one demo skill (bookmark tracker) with TDD, full type safety, graceful shutdown, and proper error isolation.
>
> **Deliverables**:
> - Core bot with plugin loading system
> - Bookmark skill with /bookmark, /bookmarks, /delete_bookmark commands
> - Full test suite with mocks
> - Deployment configs (systemd + docker-compose)
>
> **Estimated Effort**: Medium (4‑5 days)
> **Parallel Execution**: YES - 3 waves, max 7 concurrent tasks
> **Critical Path**: Config → Database → Base Skill → Skill Loader → Main Bot → Bookmark Skill → Tests

---

## Context

### Original Request
Create a Telegram companion bot that functions as a personal assistant, with an extensible plugin/skill system for future capabilities (image/video generation via LORA, bookmark tracking, research). Phase 1 must deliver core conversation + one demo skill.

### Interview Summary
**Key Discussions**:
- Single-user personal assistant (no multi-user auth)
- Python with python-telegram-bot (matches existing codebase conventions)
- Self-hosted on local hardware
- Data retention: 30 days live, then archive
- API key management: Environment variables (.env)
- Monitoring: Minimal logs, debug flag enables expanded logging
- Skill isolation: Separate DB schema per skill
- Cost budget: No constraints
- Test strategy: TDD (tests before implementation)

**Research Findings**:
- python-telegram-bot v20+ is production-grade with asyncio support
- Pydantic Settings pattern established from miniscope/stairtup projects
- SQLite context manager pattern from existing codebase
- No existing test infrastructure (need to set up pytest + pytest-asyncio)

### Metis Review
**Identified Gaps** (addressed):
- **Chat ID whitelist**: Implemented before processing ANY message
- **Skill error isolation**: Wrapped skill calls in try/except per skill
- **Testing strategy**: Use pytest-telegram or mocks for tests
- **Graceful shutdown**: Implemented SIGTERM/SIGINT handling
- **SQLite concurrency**: WAL mode enabled
- **Scope creep**: Explicit single-user only, no web dashboard or multi-user features

---

## Work Objectives

### Core Objective
Build a production-grade Telegram bot with extensible plugin/skill system that handles personal conversations, enforces single-user access, and supports future skill additions without modifying core bot code.

### Concrete Deliverables
- `/home/shedwards/src/auntie/` package with `auntie/` subdirectory
- `auntie/config.py` - Pydantic Settings for bot configuration
- `auntie/database.py` - SQLite connection manager with WAL mode
- `auntie/models.py` - Pydantic models for data structures
- `auntie/main.py` - Bot entry point with asyncio support
- `auntie/skills/base.py` - Abstract base skill interface
- `auntie/skills/loader.py` - Dynamic skill discovery and loading
- `auntie/skills/bookmark.py` - Demo bookmark tracker skill
- `auntie/skills/__init__.py` - Skill package exports
- Test suite with >80% coverage (pytest, pytest-asyncio)
- Deployment configs: systemd service file + docker-compose.yml
- README.md with setup instructions

### Definition of Done
- [ ] All components implement Type Hints
- [ ] All code passes `ruff check` and `ruff format`
- [ ] All tests pass with `pytest` (TDD pattern)
- [ ] Bot starts and responds to `/start`
- [ ] Chat ID whitelist enforces single-user model
- [ ] Bookmark skill handles /bookmark, /bookmarks, /delete_bookmark
- [ ] Graceful shutdown on SIGTERM with proper cleanup
- [ ] Systemd service file OR docker-compose.yml works
- [ ] README contains complete setup instructions

### Must Have
- Single-user chat ID whitelist enforcement
- Skill isolation (one crashing skill shouldn't kill bot)
- Proper async/await patterns throughout
- SQLite WAL mode for concurrency safety
- Full type safety (no `Any`, no `@ts-ignore`)
- TDD workflow with mocks (no real Telegram API in tests)
- Graceful shutdown with DB connection cleanup

### Must NOT Have (Guardrails)
- Multi-user authentication or role-based access control
- Web dashboard or HTTP endpoints
- Cloud deployment (AWS/GCP) or Kubernetes
- Hot-reloading of skills (restart required)
- Metrics collection or monitoring dashboards
- External databases (PostgreSQL, Redis) in Phase 1
- Automatic skill dependencies (manual only)
- Database migration automation (manual only)
- Real-time features (polling only, no websockets)
- Advanced AI/NLP libraries

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.
> Acceptance criteria requiring "user manually tests/confirms" are FORBIDDEN.

### Test Decision
- **Infrastructure exists**: NO (needs to be created)
- **Automated tests**: TDD (tests drive implementation)
- **Framework**: pytest + pytest-asyncio
- **If TDD**: Each task follows RED → GREEN → REFACTOR

### QA Policy
Every task MUST include agent-executed QA scenarios (see TODO template below).
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Backend**: Use Python's unittest.mock to mock telegram.Bot calls
- **Tests**: pytest with fixtures, test isolation, parametrized tests
- **Coverage**: Aim for >80% line coverage (use pytest-cov)

---

## Execution Strategy

### Parallel Execution Waves

> Maximize throughput by grouping independent tasks into parallel waves.
> Each wave completes before the next begins.
> Target: 5-8 tasks per wave. Fewer than 3 per wave (except final) = under-splitting.

```
Wave 1 (Start Immediately — No Dependencies):
├── Task 1: Project Bootstrap & Configuration [quick]
├── Task 2: Database Foundation (SQLite + WAL mode) [quick]
├── Task 3: Base Skill Interface [quick]
└── Task 4: Skill Loader (dynamic discovery) [unspecified-low]

Wave 2 (After Wave 1 — Core + Bot):
├── Task 5: Pydantic Configuration [quick]
├── Task 6: Main Bot Setup (chat ID whitelist, graceful shutdown) [unspecified-low]
└── Task 7: Bookmark Demo Skill [unspecified-low]

Wave 3 (After Wave 2 — Integration + Tests):
├── Task 8: Integration Tests (skill loader + database) [deep]
├── Task 9: Unit Tests (pytest mocks, >80% coverage) [deep]
├── Task 10: Deployment Configs (systemd + docker-compose) [quick]
└── Task 11: Documentation & README [visual-engineering]

Wave 4 (After Wave 3 — Final Verification):
├── Task F1: Plan Compliance Audit (oracle)
├── Task F2: Code Quality Review (unspecified-high)
├── Task F3: Real Manual QA (unspecified-high)
└── Task F4: Scope Fidelity Check (deep)

Critical Path: Task 1 → Task 2 → Task 3 → Task 4 → Task 5 → Task 6 → Task 7 → Task 8 → Task 9 → Task 10 → F1-F4
Parallel Speedup: ~60% faster than sequential
Max Concurrent: 4 (Waves 1, 2, 3) or 4 (Wave 4)
```

### Dependency Matrix (abbreviated — show ALL tasks in your generated plan)

- **1**: — — 2, 3, 4, 5
- **2**: 1 — — —
- **3**: 1 — — —
- **4**: 3 — — —
- **5**: 1 — — —
- **6**: 1, 3, 4, 5 — 7
- **7**: 2, 3, 4, 6 — F1, F2
- **8**: 4, 5, 7 — —
- **9**: 1, 2, 3, 4, 5, 6, 7 — —
- **10**: 1, 5 — —
- **11**: 1, 10 — —
- **F1**: 8, 9, 10, 11 — —
- **F2**: 1-11 — —
- **F3**: 8, 9, 10, 11 — —
- **F4**: 1-11 — —

### Agent Dispatch Summary

- **1**: **4** — T1-T4 → quick
- **2**: **1** — T2 → quick
- **3**: **1** — T3 → quick
- **4**: **1** — T4 → unspecified-low
- **5**: **1** — T5 → quick
- **6**: **4** — T6 → unspecified-low
- **7**: **4** — T7 → unspecified-low
- **8**: **6** — T8 → deep
- **9**: **6** — T9 → deep
- **10**: **1** — T10 → quick
- **11**: **4** — T11 → visual-engineering
- **FINAL**: **4** — F1 → oracle, F2 → unspecified-high, F3 → unspecified-high, F4 → deep

---

## TODOs

> Implementation + Test = ONE Task. Never separate.
> EVERY task MUST have: Recommended Agent Profile + Parallelization info + QA Scenarios.
> **A task WITHOUT QA Scenarios is INCOMPLETE. No exceptions.**

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 review agents run in PARALLEL. ALL must APPROVE. Rejection → fix → re-run.

- [ ] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, run command). For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in .sisyphus/evidence/. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [ ] F2. **Code Quality Review** — `unspecified-high`
  Run `python -m ruff check . && ruff format --check . && pytest --cov`. Review all changed files for: `# type: ignore`, empty catches, console.log, commented-out code, unused imports. Check AI slop: excessive comments, over-abstraction, generic names (data/result/item/temp).
  Output: `Ruff [PASS/FAIL] | Tests [N pass/N fail] | Coverage [N%] | Files [N clean/N issues] | VERDICT`

- [ ] F3. **Real Manual QA** — `unspecified-high` (+ `playwright` if UI)
  Start from clean state. Execute EVERY QA scenario from EVERY task — follow exact steps, capture evidence. Test cross-task integration (features working together, not isolation). Test edge cases: unauthorized chat ID, skill crash, graceful shutdown, long messages.
  Output: `Scenarios [N/N pass] | Integration [N/N] | Edge Cases [N tested] | VERDICT`

- [ ] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff (git log/diff). Verify 1:1 — everything in spec was built (no missing), nothing beyond spec was built (no creep). Check "Must NOT do" compliance. Detect cross-task contamination: Task N touching Task M's files. Flag unaccounted changes.
  Output: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

- **1-4**: `chore: add project scaffolding, dependencies, config` — pyproject.toml, .env.example, .gitignore
- **5-7**: `feat: implement core bot, skills, database` — config.py, database.py, skills/, main.py
- **8-9**: `test: add integration and unit tests` — tests/, pytest.ini, pytest-cov
- **10-11**: `docs: add deployment configs and README` — systemd/, docker-compose.yml, README.md
- **FINAL**: `chore: complete Phase 1 telegram bot` — git tag v1.0.0-telegram-bot

---

## Success Criteria

### Verification Commands
```bash
# 1. Project setup
uv sync                          # Expected: all dependencies installed
python -c "from auntie.config import BotSettings; print(BotSettings())"  # Expected: loads config without error

# 2. Tests
pytest -v                       # Expected: 100% pass rate
pytest --cov=auntie              # Expected: >80% coverage
pytest -m integration            # Expected: all integration tests pass

# 3. Bot functionality
# Start bot, send /start           # Expected: "Welcome! I'm your personal assistant..."
# Send /bookmark https://example.com Test # Expected: "Added bookmark: https://example.com Test"
# Send /bookmarks                  # Expected: "No bookmarks yet."
# Send /delete_bookmark 1         # Expected: bookmark deleted

# 4. Security
# Bot token from .env              # Expected: no hardcoded secrets
# Chat ID whitelist check          # Expected: non-whitelisted IDs blocked

# 5. Graceful shutdown
# SIGTERM signal                   # Expected: bot exits cleanly, DB connections closed

# 6. Deployment
# systemctl start auntie          # Expected: unit file valid
# docker-compose up               # Expected: container starts, logs show "Bot started"
```

### Final Checklist
- [ ] All "Must Have" present
- [ ] All "Must NOT Have" absent
- [ ] All tests pass (>80% coverage)
- [ ] Chat ID whitelist enforced
\n- [ ] 8. Integration Tests (skill loader + database)

  **What to do**:
  - Create `tests/test_integration.py` with pytest tests:
    - Test skill discovery and loading:
      - Create mock skill files in `tests/fixtures/skills/`
      - Verify loader discovers them
      - Verify instantiation works
      - Verify errors are handled
    - Test database operations:
      - Test CRUD operations (create, read, update, delete)
      - Test concurrent writes (WAL mode)
      - Test SQL injection prevention
    - Test skill loading with errors:
      - Create broken skill
      - Verify loader skips it
      - Verify other skills still load
  - Use `pytest fixtures` for test setup/teardown
  - Use `tmp_path` for temporary database files

  **Must NOT do**:
  - Do NOT create tests that hit real Telegram API
  - Do NOT test handler logic (that's in task 9)
  - Do NOT test UI or user interactions

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []
    - pytest fixtures, mocking
  - **Skills Evaluated but Omitted**: `ultrabrain` (test patterns are straightforward)

  **Parallelization**:
  - **Can Run In Parallel**: YES (depends on 4, 5, 6, 7)
  - **Parallel Group**: Wave 3 (tasks 8-9, 10-11 split into 2 groups)
  - **Blocks**: Tasks 9, 10, 11
  - **Blocked By**: Tasks 4, 5, 6, 7 (skill loader, database, bot, skill implemented)

  **References**:
  - `tests/` from miniscope: pytest patterns
  - `auntie/skills/base.py`: BaseSkill interface to test against
  - `auntie/database.py`: DB operations to test

  **WHY Each Reference Matters**:
  - miniscope tests: Pytest pattern for integration tests
  - base.py/skills/loader.py/database.py: Implementation to test

  **Acceptance Criteria**:
  - [ ] All integration tests pass
  - [ ] Tests cover skill loading edge cases
  - [ ] Tests cover database operations
  - [ ] Tests use fixtures for setup/teardown

  **QA Scenarios**:

  Scenario: Skill loader discovers valid skills
    Tool: Bash (pytest)
    Preconditions: 3 valid mock skills in fixtures
    Steps:
      1. Run `pytest tests/test_integration.py::test_skill_discovery`
      2. Verify all 3 skills discovered
      3. Verify all initialized without errors
    Expected Result: All tests pass, skills discovered
    Failure Indicators: Tests fail, skills not discovered
    Evidence: .sisyphus/evidence/task-8-skill-discovery-pass.log

  Scenario: Loader handles broken skill gracefully
    Tool: Bash (pytest)
    Preconditions: 1 broken skill + 2 valid skills
    Steps:
      1. Run `pytest tests/test_integration.py::test_error_handling`
      2. Verify 2 valid skills still loaded
      3. Verify broken skill skipped
      4. Verify error logged
    Expected Result: Graceful error handling, valid skills loaded
    Failure Indicators: Loader crashes, all skills skipped
    Evidence: .sisyphus/evidence/task-8-error-handling-pass.log

  Scenario: Database operations work concurrently
    Tool: Bash (pytest)
    Preconditions: Database initialized
    Steps:
      1. Run multiple concurrent inserts (pytest-xdist or ThreadPool)
      2. Query database after all inserts
      3. Verify all records present (WAL mode)
      4. Verify no "database is locked" errors
    Expected Result: All inserts succeed, no locks
    Failure Indicators: Some inserts fail with lock error
    Evidence: .sisyphus/evidence/task-8-concurrent-db-pass.log

  Scenario: SQL injection blocked
    Tool: Bash (pytest)
    Preconditions: Database initialized
    Steps:
      1. Inject SQL via URL parameter
      2. Try to create table or drop table
      3. Verify actual tables unchanged
      4. Verify query handled safely
    Expected Result: Tables not affected, error handled
    Failure Indicators: Table dropped or database error
    Evidence: .sisyphus/evidence/task-8-sql-injection-blocked.log

  **Commit**: YES (group 8-9)
  - Message: `test: add integration tests for skills and database`
  - Files: `tests/test_integration.py`, `tests/fixtures/skills/`
  - Pre-commit: `pytest tests/test_integration.py -v`

- [ ] 9. Unit Tests (pytest mocks, >80% coverage)

  **What to do**:
  - Create `tests/` directory structure:
    - `tests/test_config.py`
    - `tests/test_database.py`
    - `tests/test_skills_base.py`
    - `tests/test_skills_loader.py`
    - `tests/test_skills_bookmark.py`
    - `tests/test_main.py`
  - Write tests using `unittest.mock` to mock telegram API:
    - Mock `Application.builder()` and `Application.run_polling()`
    - Mock `telegram.Update` and `telegram.Message`
    - Mock database connections
  - Use pytest fixtures for:
    - Test config with valid/invalid values
    - Mocked database connection
    - Sample messages for testing
  - Aim for >80% line coverage (use `pytest-cov`)
  - Test all paths: happy path, error paths, edge cases

  **Must NOT do**:
  - Do NOT create tests that require real Telegram API
  - Do NOT test system integration (that's task 8)

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []
    - pytest, unittest.mock
  - **Skills Evaluated but Omitted**: `ultrabrain` (test patterns are standard)

  **Parallelization**:
  - **Can Run In Parallel**: YES (depends on 1-7)
  - **Parallel Group**: Wave 3 (tasks 8-9)
  - **Blocks**: Tasks 10, 11
  - **Blocked By**: Tasks 1-7 (all implementation complete)

  **References**:
  - pytest docs: https://docs.pytest.org/
  - unittest.mock docs: https://docs.python.org/3/library/unittest.mock.html
  - `tests/` from miniscope: Pytest patterns

  **WHY Each Reference Matters**:
  - pytest/unittest.mock: Official testing frameworks
  - miniscope tests: Pytest patterns for Python code

  **Acceptance Criteria**:
  - [ ] All unit tests pass
  - [ ] Coverage >80%
  - [ ] All mocks used (no real API calls)
  - [ ] Fixtures for test isolation

  **QA Scenarios**:

  Scenario: Config validation tests pass
    Tool: Bash (pytest)
    Preconditions: Valid and invalid config values in fixtures
    Steps:
      1. Run `pytest tests/test_config.py -v`
      2. Verify all config tests pass
      3. Verify no real .env file read
    Expected Result: All config tests pass without file
    Failure Indicators: ImportError, file read errors
    Evidence: .sisyphus/evidence/task-9-config-tests-pass.log

  Scenario: Base skill abstractness tests pass
    Tool: Bash (pytest)
    Preconditions: BaseSkill class implemented
    Steps:
      1. Run `pytest tests/test_skills_base.py -v`
      2. Verify all abstract method tests pass
      3. Verify abstract class checks work
    Expected Result: All base skill tests pass
    Failure Indicators: Tests fail on instantiation
    Evidence: .sisyphus/evidence/task-9-base-tests-pass.log

  Scenario: Coverage >80%
    Tool: Bash (pytest-cov)
    Preconditions: All tests written
    Steps:
      1. Run `pytest tests/ --cov=auntie --cov-report=term-missing`
      2. Verify coverage report shows >80%
      3. Note any <80% files
    Expected Result: Coverage threshold met
    Failure Indicators: Coverage <80%, specific files failing
    Evidence: .sisyphus/evidence/task-9-coverage-80pct.log

  Scenario: No real Telegram API calls in tests
    Tool: Bash (grep)
    Preconditions: Tests directory exists
    Steps:
      1. Run `grep -r 'telegram.Bot' tests/` (should be empty or mocks only)
      2. Run `grep -r 'requests.get' tests/` (should be empty)
      3. Verify all API calls are mocked
    Expected Result: No real API calls found
    Failure Indicators: Real API calls detected
    Evidence: .sisyphus/evidence/task-9-no-real-api.log

  **Commit**: YES (group 8-9)
  - Message: `test: add unit tests with >80% coverage`
  - Files: `tests/*.py`
  - Pre-commit: `pytest tests/ --cov=auntie --cov-report=term-missing`

- [ ] 10. Deployment Configs (systemd + docker-compose)

  **What to do**:
  - Create `deployment/systemd/auntie.service`:
    - Description: "Telegram Companion Bot"
    - User: `auntie` (or `root` if deploying as sudo)
    - Working directory: `/opt/auntie`
    - Environment file: `/opt/auntie/.env`
    - ExecStart: `/usr/bin/python3 -m auntie`
    - Restart: always
    - Auto restart on failure
  - Create `deployment/docker-compose.yml`:
    - Service: `auntie`
    - Image: `python:3.12-slim`
    - Volumes: `./auntie:/app/auntie`, `./auntie.db:/app/auntie.db`
    - Environment: Load from `.env`
    - Command: `python -m auntie`
  - Create `deployment/setup.sh`:
    - Install dependencies
    - Copy .env file
    - Create data directory
    - Set permissions

  **Must NOT do**:
  - Do NOT include Kubernetes manifests
  - Do NOT add health check HTTP endpoints
  - Do NOT configure auto-scaling

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: [`git-master`]
    - git-master: Commit service files with proper metadata
  - **Skills Evaluated but Omitted**: `visual-engineering` (configs are code, not UI)

  **Parallelization**:
  - **Can Run In Parallel**: YES (depends on 1, 5 only)
  - **Parallel Group**: Wave 3 (task 10 only)
  - **Blocks**: Task 11
  - **Blocked By**: Tasks 1, 5 (config file exists)

  **References**:
  - systemd docs: https://www.freedesktop.org/software/systemd/man/systemd.service.html
  - docker-compose docs: https://docs.docker.com/compose/
  - miniscope deployment patterns: Check for any service files there

  **WHY Each Reference Matters**:
  - systemd/docker-compose: Standard deployment tools for local services

  **Acceptance Criteria**:
  - [ ] systemd service file is valid
  - [ ] docker-compose.yml is valid
  - [ ] setup.sh script exists

  **QA Scenarios**:

  Scenario: systemd service file validates
    Tool: Bash (systemctl)
    Preconditions: Systemd service file created
    Steps:
      1. Run `systemctl daemon-reload`
      2. Run `systemctl status auntie`
      3. Verify no errors
    Expected Result: Service file valid, no errors
    Failure Indicators: Invalid service error
    Evidence: .sisyphus/evidence/task-10-systemd-valid.log

  Scenario: docker-compose file validates
    Tool: Bash (docker)
    Preconditions: docker-compose.yml exists
    Steps:
      1. Run `docker-compose config`
      2. Verify no errors
      3. Run `docker-compose up --dry-run`
      4. Verify no errors
    Expected Result: Config valid, no syntax errors
    Failure Indicators: Configuration error
    Evidence: .sisyphus/evidence/task-10-docker-compose-valid.log

  Scenario: setup.sh script exists and is executable
    Tool: Bash (bash)
    Preconditions: setup.sh created
    Steps:
      1. Run `bash deployment/setup.sh --help`
      2. Verify output shows usage
    Expected Result: Script runs without errors
    Failure Indicators: Script not executable or doesn't run
    Evidence: .sisyphus/evidence/task-10-setup-script-okay.log

  **Commit**: YES (group 10-11)
  - Message: `chore: add deployment configs (systemd + docker-compose)`
  - Files: `deployment/systemd/auntie.service`, `deployment/docker-compose.yml`, `deployment/setup.sh`
  - Pre-commit: `systemctl status auntie` (if available)

- [ ] 11. Documentation & README

  **What to do**:
  - Create comprehensive `README.md`:
    - Project overview (Telegram companion bot)
    - Architecture description (plugin system, skills)
    - Features list (Phase 1 deliverables)
    - Prerequisites: Python 3.12+, uv, git
    - Setup instructions:
      - Clone repository
      - Install dependencies (`uv sync`)
      - Configure `.env` (copy from `.env.example`)
      - Run bot (`python -m auntie` or `make run`)
    - Configuration options:
      - `TELEGRAM_BOT_TOKEN` (required)
      - `CHAT_ID_WHITELIST` (required)
      - `DEBUG` (optional)
      - `LOG_LEVEL` (optional)
    - Using the bot:
      - `/start` - Start the bot
      - `/bookmark <url> <title>` - Add bookmark
      - `/bookmarks` - List bookmarks
      - `/delete_bookmark <id>` - Delete bookmark
    - Deployment options:
      - Manual run: `python -m auntie`
      - systemd: `systemctl enable auntie && systemctl start auntie`
      - Docker: `docker-compose up -d`
    - Development:
      - Running tests: `pytest`
      - Code style: `ruff check . && ruff format .`
    - Contributing: (future, optional)
    - License: MIT
  - Update `.env.example` with comments explaining each variable

  **Must NOT do**:
  - Do NOT include screenshots or UI mockups
  - Do NOT add API documentation (code is self-documenting)
  - Do NOT include advanced deployment guides (keep simple)

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: [`git-master`]
    - git-master: Commit README with proper attribution
  - **Skills Evaluated but Omitted**: `writing` (markdown is basic)

  **Parallelization**:
  - **Can Run In Parallel**: YES (depends on 1, 10 only)
  - **Parallel Group**: Wave 3 (task 11 only)
  - **Blocks**: None (final task)
  - **Blocked By**: Tasks 1, 10 (config file, deployment configs)

  **References**:
  - `README.md` from miniscope: Project overview pattern
  - `AGENTS.md`: Follow agent workflow conventions

  **WHY Each Reference Matters**:
  - miniscope README: Standard project documentation structure
  - AGENTS.md: Consistent workflow documentation

  **Acceptance Criteria**:
  - [ ] README has complete setup instructions
  - [ ] All commands in README work on fresh clone
  - [ ] `.env.example` has all comments
  - [ ] README includes both manual and automated deployment

  **QA Scenarios**:

  Scenario: README setup instructions work
    Tool: Bash (bash)
    Preconditions: Fresh clone of repository
    Steps:
      1. Follow README instructions: `uv sync`, configure .env, `python -m auntie`
      2. Verify each step completes without errors
      3. Note any commands that don't work
    Expected Result: All setup commands succeed
    Failure Indicators: Command fails, missing step
    Evidence: .sisyphus/evidence/task-11-readme-instructions-work.log

  Scenario: .env.example has all explanations
    Tool: Bash (bash)
    Preconditions: .env.example exists
    Steps:
      1. Read each variable in .env.example
      2. Verify each has a comment
      3. Verify comment explains the variable
    Expected Result: All variables have clear comments
    Failure Indicators: Variable without comment or unclear comment
    Evidence: .sisyphus/evidence/task-11-env-explanation-complete.log

  **Commit**: YES (group 10-11)
  - Message: `docs: add comprehensive README and deployment docs`
  - Files: `README.md`, `.env.example`
  - Pre-commit: `bash setup.sh --help` (verify scripts work)

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 review agents run in PARALLEL. ALL must APPROVE. Rejection → fix → re-run.

- [ ] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, run command). For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in .sisyphus/evidence/. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [ ] F2. **Code Quality Review** — `unspecified-high`
  Run `python -m ruff check . && ruff format --check . && pytest --cov`. Review all changed files for: `# type: ignore`, empty catches, console.log, commented-out code, unused imports. Check AI slop: excessive comments, over-abstraction, generic names (data/result/item/temp).
  Output: `Ruff [PASS/FAIL] | Tests [N pass/N fail] | Coverage [N%] | Files [N clean/N issues] | VERDICT`

- [ ] F3. **Real Manual QA** — `unspecified-high` (+ `playwright` if UI)
  Start from clean state. Execute EVERY QA scenario from EVERY task — follow exact steps, capture evidence. Test cross-task integration (features working together, not isolation). Test edge cases: unauthorized chat ID, skill crash, graceful shutdown, long messages.
  Output: `Scenarios [N/N pass] | Integration [N/N] | Edge Cases [N tested] | VERDICT`

- [ ] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff (git log/diff). Verify 1:1 — everything in spec was built (no missing), nothing beyond spec was built (no creep). Check "Must NOT do" compliance. Detect cross-task contamination: Task N touching Task M's files. Flag unaccounted changes.
  Output: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | Unaccounted [CLEAN/N files] | VERDICT`
\n- [ ] 5. Pydantic Configuration

  **What to do**:
  - Create `auntie/config.py` with `BotSettings` Pydantic class:
    - Inherit from `BaseSettings`
    - Fields:
      - `TELEGRAM_BOT_TOKEN: str` (required)
      - `CHAT_ID_WHITELIST: str` (required, single user ID)
      - `DEBUG: bool = False`
      - `LOG_LEVEL: str = "INFO"`
      - `CONVERSATION_RETENTION_DAYS: int = 30`
      - `ENABLE_BOOKMARK_SKILL: bool = True`
    - Load from `.env` file (set in Config)
  - Add validation:
    - Ensure `TELEGRAM_BOT_TOKEN` is not empty
    - Ensure `CHAT_ID_WHITELIST` is valid telegram chat ID
  - Export `settings` singleton instance

  **Must NOT do**:
  - Do NOT add fields beyond what's specified
  - Do NOT implement secrets management (use environment variables)
  - Do NOT add any business logic

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []
    - Pydantic Settings pattern from miniscope
  - **Skills Evaluated but Omitted**: `git-master` (no git changes)

  **Parallelization**:
  - **Can Run In Parallel**: YES (depends on Task 1 only, not others)
  - **Parallel Group**: Wave 2 (task 5 only)
  - **Blocks**: Tasks 6, 7
  - **Blocked By**: Task 1 (pyproject.toml created .env.example)

  **References**:
  - `auntie/config.py` from miniscope: Pydantic Settings pattern

  **WHY Each Reference Matters**:
  - miniscope config pattern: Show how to set up Pydantic Settings correctly

  **Acceptance Criteria**:
  - [ ] `BotSettings` inherits from `BaseSettings`
  - [ ] All required fields are defined with correct types
  - [ ] `.env` file is read by `Config`
  - [ ] Setting values are accessible as instance attributes

  **QA Scenarios**:

  Scenario: Config loads without errors
    Tool: Bash (python)
    Preconditions: `.env` file exists with all required fields
    Steps:
      1. Run `python -c "from auntie.config import BotSettings; s = BotSettings(); print(s)``
      2. Verify no errors, settings printed
    Expected Result: Config loads and prints all settings
    Failure Indicators: ValidationError, Missing env var error
    Evidence: .sisyphus/evidence/task-5-config-load-okay.log

  Scenario: Debug flag controls logging
    Tool: Bash (python)
    Preconditions: `.env` has `DEBUG=true`
    Steps:
      1. Run python and check log output
      2. Verify DEBUG enabled messages
      3. Reset `DEBUG=false`
      4. Run again, verify less verbose output
    Expected Result: DEBUG=true shows debug messages, false suppresses
    Failure Indicators: No difference in output
    Evidence: .sisyphus/evidence/task-5-debug-flag-okay.log

  **Commit**: YES (group 5-7)
  - Message: `feat: add Pydantic configuration`
  - Files: `auntie/config.py`
  - Pre-commit: `python -c "from auntie.config import BotSettings; BotSettings()"`

- [ ] 6. Main Bot Setup (chat ID whitelist, graceful shutdown)

  **What to do**:
  - Create `auntie/main.py` with bot entry point:
    - Import `Application` from `python-telegram-bot`
    - Load config: `from auntie.config import settings`
    - Initialize bot: `Application.builder().token(settings.telegram_bot_token).build()`
    - Add `/start` command handler:
      - Validate chat ID against `settings.chat_id_whitelist`
      - If unauthorized, reply "unauthorized"
      - If authorized, reply welcome message
    - Add message handler:
      - Validate chat ID first (whitelist check)
      - If unauthorized, reply "unauthorized"
      - If authorized, dispatch to skill loader
    - Implement graceful shutdown handler:
      - Subscribe to SIGTERM/SIGINT
      - Close DB connections on shutdown
      - Log shutdown completion
  - Add logging configuration:
    - Set level based on `settings.debug`
    - Format: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`

  **Must NOT do**:
  - Do NOT implement webhooks (use polling only)
  - Do NOT add any business logic (just dispatch to skills)
  - Do NOT create skill-specific handlers

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
  - **Skills**: []
    - python-telegram-bot patterns
  - **Skills Evaluated but Omitted**: `playwright` (no UI)

  **Parallelization**:
  - **Can Run In Parallel**: YES (depends on 1, 3, 4, 5)
  - **Parallel Group**: Wave 2 (tasks 5-7)
  - **Blocks**: Task 7
  - **Blocked By**: Tasks 1, 3, 4, 5 (config, base skill, loader, database)

  **References**:
  - `auntie/config.py`: Settings to get bot token and chat IDs
  - `auntie/database.py`: Database for cleanup on shutdown
  - `auntie/skills/loader.py`: Skill loader to dispatch messages
  - python-telegram-bot docs: https://docs.python-telegram-bot.org/

  **WHY Each Reference Matters**:
  - `config.py`: Bot token and whitelist from settings
  - `database.py`: Need database connection to close on shutdown
  - `loader.py`: Dispatch messages to skills

  **Acceptance Criteria**:
  - [ ] Bot starts with provided token
  - [ ] `/start` responds to authorized chat ID
  - [ ] `/start` rejects unauthorized chat ID
  - [ ] Graceful shutdown handler installed
  - [ ] DB connections closed on shutdown

  **QA Scenarios**:

  Scenario: Bot starts successfully
    Tool: Bash (python)
    Preconditions: `.env` has valid `TELEGRAM_BOT_TOKEN`
    Steps:
      1. Run `python -c "from auntie.main import main; import asyncio; asyncio.run(main())"`
      2. Verify no errors, bot initialized
    Expected Result: Bot starts without errors
    Failure Indicators: 401 authentication error, token not found
    Evidence: .sisyphus/evidence/task-6-bot-start-okay.log

  Scenario: Chat ID whitelist enforced
    Tool: Bash (python)
    Preconditions: Bot running, `.env` has `CHAT_ID_WHITELIST`
    Steps:
      1. Send `/start` to whitelisted chat ID
      2. Send `/start` to non-whitelisted chat ID
      3. Verify first gets welcome, second gets "unauthorized"
    Expected Result: Whitelisted chat ID succeeds, non-whitelisted blocked
    Failure Indicators: No blocking or wrong message
    Evidence: .sisyphus/evidence/task-6-whitelist-enforced.log

  Scenario: Graceful shutdown
    Tool: Bash (python)
    Preconditions: Bot running
    Steps:
      1. Send `SIGTERM` signal to process
      2. Verify log shows "shutdown complete"
      3. Verify DB connections are closed (check process list)
    Expected Result: Bot exits cleanly with proper cleanup
    Failure Indicators: Bot hangs or exits with error
    Evidence: .sisyphus/evidence/task-6-shutdown-okay.log

  **Commit**: YES (group 5-7)
  - Message: `feat: implement main bot with chat ID whitelist`
  - Files: `auntie/main.py`
  - Pre-commit: `python -c "from auntie.main import main"` (no execution)

- [ ] 7. Bookmark Demo Skill

  **What to do**:
  - Create `auntie/skills/bookmark.py` implementing `BaseSkill`:
    - `name`: "bookmark"
    - `initialize()`: Create `bookmarks` table if not exists
    - `handle_message(message)`: Handle bookmark commands
      - `/bookmark <url> <title>` - Parse url and title, store in database
      - `/bookmarks` - List all bookmarks (limit 10, paginated)
      - `/delete_bookmark <id>` - Remove bookmark by ID
    - `cleanup()`: Close DB connection
  - Implement command parsing:
    - Extract command word
    - Parse arguments with split()
    - Validate URLs (basic regex)
  - Implement database operations:
    - Use parameterized queries
    - Handle duplicates (skip if URL exists)
    - Delete logic
  - Add logging for all operations

  **Must NOT do**:
  - Do NOT implement pagination UI (text list only)
  - Do NOT add more than these 3 commands
  - Do NOT implement bookmark sharing or tagging

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
  - **Skills**: []
    - Python async patterns, database operations
  - **Skills Evaluated but Omitted**: `artistry` (skill is utility, not UI)

  **Parallelization**:
  - **Can Run In Parallel**: YES (depends on 2, 3, 4, 5, 6)
  - **Parallel Group**: Wave 2 (tasks 5-7)
  - **Blocks**: Tasks 8, 9
  - **Blocked By**: Tasks 2, 3, 4, 5, 6 (database, base skill, loader, config, main bot)

  **References**:
  - `auntie/skills/base.py`: BaseSkill interface to implement
  - `auntie/database.py`: Database context manager pattern
  - `auntie/config.py`: Settings for debug flag

  **WHY Each Reference Matters**:
  - `base.py`: Interface contract for all skills
  - `database.py`: Async DB operations pattern

  **Acceptance Criteria**:
  - [ ] Skill is loaded by loader
  - [ ] `/bookmark` stores URL and title in database
  - [ ] `/bookmarks` lists bookmarks (up to 10)
  - [ ] `/delete_bookmark` removes bookmark by ID
  - [ ] Validations work (URL format, required args)

  **QA Scenarios**:

  Scenario: /bookmark stores data
    Tool: Bash (python)
    Preconditions: Skill loaded, database initialized
    Steps:
      1. Call `handle_message` with `/bookmark https://example.com Test Title`
      2. Verify no error
      3. Query database for the bookmark
      4. Verify URL and title match
    Expected Result: Bookmark stored correctly
    Failure Indicators: Error thrown, data not stored
    Evidence: .sisyphus/evidence/task-7-bookmark-store-okay.log

  Scenario: /bookmarks lists bookmarks
    Tool: Bash (python)
    Preconditions: Two bookmarks exist in database
    Steps:
      1. Call `handle_message` with `/bookmarks`
      2. Verify response contains both bookmarks
      3. Verify limit of 10 bookmarks
    Expected Result: Both bookmarks listed, no more than 10
    Failure Indicators: Missing bookmarks, more than 10 listed
    Evidence: .sisyphus/evidence/task-7-bookmarks-list-okay.log

  Scenario: /delete_bookmark removes bookmark
    Tool: Bash (python)
    Preconditions: One bookmark exists with ID=1
    Steps:
      1. Call `handle_message` with `/delete_bookmark 1`
      2. Verify no error
      3. Query database for ID=1
      4. Verify bookmark is deleted
    Expected Result: Bookmark deleted successfully
    Failure Indicators: Error thrown, bookmark still exists
    Evidence: .sisyphus/evidence/task-7-delete-bookmark-okay.log

  **Commit**: YES (group 5-7)
  - Message: `feat: add bookmark demo skill`
  - Files: `auntie/skills/bookmark.py`
  - Pre-commit: Create test bookmark and verify it persists
\n- [ ] 2. Database Foundation (SQLite + WAL mode)

  **What to do**:
  - Create `auntie/database.py` with SQLite connection manager:
    - Context manager pattern (`get_db_connection()`)
    - Enable WAL mode: `PRAGMA journal_mode=WAL`
    - Return async context manager with asyncpg-style interface (or use async context vars)
  - Implement database initialization function that creates tables:
    - `conversations` table (id, user_id, message_id, text, is_command, created_at)
    - `bookmarks` table (id, url, title, description, created_at)
    - Use parameterized queries (prevent SQL injection)
  - Create `auntie/database.py` with `init_database()` function
  - Add basic error handling and logging

  **Must NOT do**:
  - Do NOT create table migration system yet (manual only)
  - Do NOT implement connection pooling (keep simple)
  - Do NOT add any business logic or CRUD operations

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []
    - No external skills needed - standard async database patterns
  - **Skills Evaluated but Omitted**: `ultrabrain` (standard async patterns)

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on Task 1)
  - **Parallel Group**: Wave 1 (task 2 only, tasks 1-4 run sequentially)
  - **Blocks**: Tasks 3, 4, 5, 6, 7
  - **Blocked By**: Task 1 (config.py, .env)

  **References**:
  - `auntie/config.py` from miniscope: Pydantic Settings pattern
  - `database.py` from miniscope: SQLite context manager pattern

  **WHY Each Reference Matters**:
  - `auntie/config.py`: Need settings to get database path
  - `database.py` from miniscope: Async context manager pattern for connections

  **Acceptance Criteria**:
  - [ ] `database.py` has `get_db_connection()` context manager
  - [ ] WAL mode is enabled in init
  - [ ] `init_database()` creates tables without errors
  - [ ] All queries use parameterized SQL (no string concatenation)

  **QA Scenarios**:

  Scenario: Database connection manager works
    Tool: Bash (python)
    Preconditions: Database file `auntie.db` doesn't exist
    Steps:
      1. Run `python -c "from auntie.database import get_db_connection; import asyncio; asyncio.run(get_db_connection())"`
      2. Check if `auntie.db` file was created
    Expected Result: Database file created, connection opened successfully
    Failure Indicators: FileNotFoundError, PermissionError
    Evidence: .sisyphus/evidence/task-2-db-connection-okay.log

  Scenario: WAL mode is enabled
    Tool: Bash (python)
    Preconditions: Database file exists
    Steps:
      1. Connect to database
      2. Run `PRAGMA journal_mode;`
    Expected Result: Returns "wal"
    Failure Indicators: Returns "delete" or other mode
    Evidence: .sisyphus/evidence/task-2-wal-mode-enabled.log

  Scenario: Tables are created successfully
    Tool: Bash (python)
    Preconditions: Database initialized
    Steps:
      1. Run `python -c "from auntie.database import init_database; init_database();"`
      2. Run `PRAGMA table_info(bookmarks);`
      3. Verify columns exist (id, url, title, description, created_at)
    Expected Result: Tables created with correct columns
    Failure Indicators: Table doesn't exist or missing columns
    Evidence: .sisyphus/evidence/task-2-tables-created.log

  Scenario: Parameterized queries prevent SQL injection
    Tool: Bash (python)
    Preconditions: Database initialized
    Steps:
      1. Try to inject SQL via INSERT: `"INSERT INTO bookmarks (url) VALUES (''); DROP TABLE bookmarks;--"`
      2. Verify no error (or catch and validate)
      3. Verify actual table still exists
    Expected Result: Table not dropped, query handled safely
    Failure Indicators: Table dropped, database error
    Evidence: .sisyphus/evidence/task-2-sql-injection-prevented.log

  **Commit**: YES (group 1-4)
  - Message: `chore: add database foundation (SQLite + WAL)`
  - Files: `auntie/database.py`
  - Pre-commit: `python -c "from auntie.database import init_database; init_database();"`

- [ ] 3. Base Skill Interface

  **What to do**:
  - Create `auntie/skills/base.py` with abstract base class `BaseSkill`
  - Define abstract methods:
    - `initialize()` - async setup (e.g., create tables)
    - `handle_message(message)` - async message handler
    - `cleanup()` - async cleanup (close connections)
  - Define skill metadata:
    - `name` property (derived from class name)
    - `description` docstring
  - Define constructor signature:
    - `__init__(self, db, config)` - database and global config
  - Add type hints for all methods

  **Must NOT do**:
  - Do NOT implement any concrete skills yet
  - Do NOT add business logic in base class
  - Do NOT include async/await if not using python-telegram-bot (this IS using it)

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []
    - Standard Python ABC pattern
  - **Skills Evaluated but Omitted**: `artistry` (abstract classes are standard)

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on Task 1 for package structure)
  - **Parallel Group**: Wave 1 (task 3 only, tasks 1-4 run sequentially)
  - **Blocks**: Tasks 4, 5, 6, 7
  - **Blocked By**: Task 1 (package structure created)

  **References**:
  - `auntie/skills/base.py`: Your implementation (to be created)

  **WHY Each Reference Matters**:
  - This file itself - need to create the interface to guide all skill implementations

  **Acceptance Criteria**:
  - [ ] `BaseSkill` is abstract (subclassing raises TypeError)
  - [ ] `BaseSkill.initialize()` is abstract method
  - [ ] `BaseSkill.handle_message()` is abstract method
  - [ ] `BaseSkill.cleanup()` is abstract method
  - [ ] All methods have type hints

  **QA Scenarios**:

  Scenario: BaseSkill is abstract
    Tool: Bash (python)
    Preconditions: `auntie/skills/base.py` created
    Steps:
      1. Run `python -c "from auntie.skills.base import BaseSkill; import inspect; print(inspect.isabstract(BaseSkill))"`
    Expected Result: Returns `True`
    Failure Indicators: Returns `False`
    Evidence: .sisyphus/evidence/task-3-abstract-okay.log

  Scenario: Abstract methods can't be called on instance
    Tool: Bash (python)
    Preconditions: `BaseSkill` class exists
    Steps:
      1. Try to instantiate: `BaseSkill(...)`
      2. Try to call `initialize()` on instance
    Expected Result: TypeError on instantiation or method call
    Failure Indicators: No error, method runs
    Evidence: .sisyphus/evidence/task-3-abstract-not-callable.log

  Scenario: Subclass can be created
    Tool: Bash (python)
    Preconditions: `BaseSkill` abstract class
    Steps:
      1. Create mock subclass with all required methods
      2. Try to instantiate
    Expected Result: Subclass can be instantiated
    Failure Indicators: Cannot subclass
    Evidence: .sisyphus/evidence/task-3-subclass-created.log

  **Commit**: YES (group 1-4)
  - Message: `feat: add BaseSkill interface`
  - Files: `auntie/skills/base.py`
  - Pre-commit: `python -c "from auntie.skills.base import BaseSkill; import inspect; print(inspect.isabstract(BaseSkill))"`

- [ ] 4. Skill Loader (dynamic discovery)

  **What to do**:
  - Create `auntie/skills/loader.py` with `SkillLoader` class
  - Implement `load_skills()` method:
    - Scan `auntie/skills/` directory for `.py` files
    - Exclude `__init__.py` and files starting with `_`
    - Use `importlib` to dynamically import modules
    - Find classes ending with "Skill" or "SkillPlugin"
    - Filter for subclasses of `BaseSkill`
    - Instantiate each skill with `db` and `config`
    - Collect skills in dictionary: `{skill_name: skill_instance}`
    - Call `await skill.initialize()` for each skill
    - Handle import errors gracefully, log warnings, continue
  - Implement `dispatch_message(message)` method:
    - Loop through loaded skills
    - Call `await skill.handle_message(message)`
    - Return response if skill handles message (not None)
    - If no skill handles message, return None

  **Must NOT do**:
  - Do NOT implement hot-reloading (restart required)
  - Do NOT implement skill versioning or dependency management
  - Do NOT add complex error recovery logic

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
  - **Skills**: []
    - Standard Python `importlib` patterns
  - **Skills Evaluated but Omitted**: `ultrabrain` (importlib is straightforward)

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on Task 3 - BaseSkill)
  - **Parallel Group**: Wave 1 (task 4 only, tasks 1-4 run sequentially)
  - **Blocks**: Tasks 5, 6, 7
  - **Blocked By**: Task 3 (BaseSkill class exists)

  **References**:
  - `auntie/skills/base.py`: BaseSkill class for inheritance checks
  - Python `importlib` docs: https://docs.python.org/3/library/importlib.html

  **WHY Each Reference Matters**:
  - `auntie/skills/base.py`: Need to filter for subclasses of this
  - Python importlib: Official API for dynamic imports

  **Acceptance Criteria**:
  - [ ] `SkillLoader.load_skills()` discovers skills from directory
  - [ ] Only filters subclasses of `BaseSkill`
  - [ ] `load_skills()` handles import errors gracefully
  - [ ] `dispatch_message()` returns correct response or None

  **QA Scenarios**:

  Scenario: Loader discovers skills
    Tool: Bash (python)
    Preconditions: `auntie/skills/demo.py` exists with a `DemoSkill` class
    Steps:
      1. Run `python -c "from auntie.skills.loader import SkillLoader; import asyncio; asyncio.run(SkillLoader('auntie/skills', None, {}).load_skills())"`
      2. Verify skill is discovered and instantiated
    Expected Result: Skill found in returned dictionary
    Failure Indicators: Skill not found, import error
    Evidence: .sisyphus/evidence/task-4-discover-skills-okay.log

  Scenario: Non-BaseSkill subclasses are filtered out
    Tool: Bash (python)
    Preconditions: Create a non-skill class in skills directory
    Steps:
      1. Create `DummyClass` that doesn't inherit from `BaseSkill`
      2. Run skill loader
      3. Verify `DummyClass` is NOT loaded
    Expected Result: DummyClass not in skills dictionary
    Failure Indicators: DummyClass is loaded
    Evidence: .sisyphus/evidence/task-4-filtered-out-okay.log

  Scenario: Import errors are handled gracefully
    Tool: Bash (python)
    Preconditions: Create skills directory with a file containing syntax error
    Steps:
      1. Add broken code to a skill file
      2. Run skill loader
      3. Verify loader continues and loads other skills
      4. Check logs for error message
    Expected Result: Loader skips broken file, loads remaining skills
    Failure Indicators: Import error causes loader to crash
    Evidence: .sisyphus/evidence/task-4-error-handling-okay.log

  Scenario: Dispatch returns correct response
    Tool: Bash (python)
    Preconditions: Loader has one skill that handles `/start`
    Steps:
      1. Call `dispatch_message` with text `/start`
      2. Verify returned response is not None
      3. Call `dispatch_message` with unknown command
      4. Verify returned response is None
    Expected Result: Skill handles known commands, returns response
    Failure Indicators: Wrong response type or None for known command
    Evidence: .sisyphus/evidence/task-4-dispatch-okay.log

  **Commit**: YES (group 1-4)
  - Message: `feat: add SkillLoader for dynamic skill discovery`
  - Files: `auntie/skills/loader.py`
  - Pre-commit: Create test skill and verify loader works
\n- [ ] 1. Project Bootstrap & Configuration

  **What to do**:
  - Create project directory structure (`auntie/` package, `tests/`, `deployment/`)
  - Create `pyproject.toml` with dependencies:
    - `python-telegram-bot[v20] >= 20.0.0`
    - `pydantic >= 2.0.0`
    - `pydantic-settings >= 2.0.0`
    - `pytest >= 7.4.0`
    - `pytest-asyncio >= 0.21.0`
    - `pytest-cov >= 4.1.0`
    - `ruff >= 0.1.0`
  - Create `.env.example` with required variables:
    - `TELEGRAM_BOT_TOKEN`
    - `CHAT_ID_WHITELIST` (single user ID)
    - `DEBUG=false`
  - Create `.gitignore` (Python patterns)
  - Create `README.md` with initial placeholder
  - Create `Makefile` with commands: `setup`, `test`, `run`

  **Must NOT do**:
  - Do NOT create any source code files yet
  - Do NOT create tests or deployment configs
  - Do NOT implement any business logic

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: [`git-master`]
    - git-master: Handle atomic git operations, commit with proper messages
  - **Skills Evaluated but Omitted**: `writing` (markdown is basic), `playwright` (no UI)

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (tasks 1-4)
  - **Blocks**: Tasks 2, 3, 4, 5
  - **Blocked By**: None (can start immediately)

  **References**:
  - `pyproject.toml` from miniscope: Use uv + pydantic-settings pattern
  - `AGENTS.md`: Follow bd workflow conventions
  - `.env.example` from miniscope: Use environment variable templates

  **WHY Each Reference Matters**:
  - `pyproject.toml` from miniscope: Pydantic Settings dependency pattern is established
  - `AGENTS.md`: Consistent workflow with `bd` issue tracking
  - `.env.example` from miniscope: Shows standard environment variable structure

  **Acceptance Criteria**:
  - [ ] `uv sync` installs all dependencies without error
  - [ ] `pyproject.toml` contains all required dependencies with correct versions
  - [ ] `.env.example` includes TELEGRAM_BOT_TOKEN, CHAT_ID_WHITELIST, DEBUG
  - [ ] `.gitignore` includes Python patterns (`__pycache__`, `.env`, `.pytest_cache`)
  - [ ] `Makefile` has `setup`, `test`, `run` targets

  **QA Scenarios**:

  Scenario: Project setup command succeeds
    Tool: Bash (shell)
    Preconditions: `uv` not installed, fresh clone of repository
    Steps:
      1. Run `uv sync`
      2. Verify no errors during installation
    Expected Result: All dependencies installed successfully
    Failure Indicators: Installation errors, missing dependencies
    Evidence: .sisyphus/evidence/task-1-project-setup-succeeds.log

  Scenario: Config validation
    Tool: Bash (python)
    Preconditions: .env.example exists
    Steps:
      1. Copy .env.example to .env
      2. Fill in minimal values
      3. Run `python -c "from auntie.config import BotSettings; Settings()`
    Expected Result: Configuration loads without errors
    Failure Indicators: ImportError, ValidationError
    Evidence: .sisyphus/evidence/task-1-config-validation-success.log

  Scenario: Git repository initialized correctly
    Tool: Bash (git)
    Preconditions: Fresh clone or no git history
    Steps:
      1. Run `git status`
      2. Verify `.gitignore` includes all Python artifacts
    Expected Result: Git recognizes files but shows no untracked changes
    Failure Indicators: Unignored files, .env tracked
    Evidence: .sisyphus/evidence/task-1-git-init-okay.log

  **Commit**: YES (group 1-4)
  - Message: `chore: add project scaffolding, dependencies, config`
  - Files: `pyproject.toml`, `.env.example`, `.gitignore`, `Makefile`, `README.md`
  - Pre-commit: `uv sync`
- [ ] Skill isolation working
- [ ] Graceful shutdown functional
- [ ] README instructions complete