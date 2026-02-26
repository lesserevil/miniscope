# Decisions

## 2026-02-26 - Project Structure
- Main package: `auntie/` (consistent with existing miniscope/stairtup)
- Test suite in `tests/` (pytest + pytest-asyncio)
- Deployment configs in `deployment/` (systemd + docker-compose)
- Skills directory: `auntie/skills/*.py` (dynamically loaded)

## 2026-02-26 - Database Schema
- Single SQLite database (`auntie.db`) in project root
- WAL mode enabled for concurrency safety
- Tables per skill: `bookmarks` table for demo skill
- Conversations table (id, user_id, message_id, text, is_command, created_at)

## 2026-02-26 - Error Handling
- Skill errors isolated (try/except per skill)
- Import errors in skills handled gracefully (log warning, continue loading)
- DB connection errors logged but don't crash bot
- Graceful shutdown with proper connection cleanup

## 2026-02-26 - Configuration
- All config via .env file (no external config files)
- Pydantic Settings for validation
- Required fields: TELEGRAM_BOT_TOKEN, CHAT_ID_WHITELIST
- Optional: DEBUG, LOG_LEVEL, CONVERSATION_RETENTION_DAYS, ENABLE_BOOKMARK_SKILL