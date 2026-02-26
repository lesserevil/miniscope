# Learnings

## 2026-02-26 - Initial Setup
- Telegram bot project will use Python with python-telegram-bot v20+
- Follow existing codebase conventions: Pydantic Settings, SQLite WAL mode, no barrel exports
- Single-user access enforced via chat ID whitelist in .env
- Skill system must be extensible: BaseSkill abstract class + SkillLoader
- TDD approach required: tests before implementation
- No real Telegram API in tests - use mocks

## 2026-02-26 - Architecture Decisions
- Python 3.12+ required (matches existing projects)
- No web dashboard, no multi-user auth, no cloud deployment
- Manual skill dependencies only (no auto-discovery)
- Data retention: 30 days live, then archive (per interview summary)
- Graceful shutdown required (SIGTERM/SIGINT handling)