"""Main entry point for Auntie Telegram bot.

Initializes the bot with chat ID whitelist protection and graceful shutdown.
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path
from types import FrameType
from typing import Any

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from auntie.config.settings import settings
from auntie.database import init_database
from auntie.skills.loader import SkillLoader

# Global variables for cleanup
skill_loader: SkillLoader | None = None
application: Application | None = None
shutdown_event: asyncio.Event | None = None

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    """Configure logging based on settings."""
    log_level = getattr(logging, settings.LOG_LEVEL)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Set debug level for telegram library if debug mode is enabled
    if settings.DEBUG:
        logging.getLogger("telegram").setLevel(logging.DEBUG)
        logging.getLogger("httpx").setLevel(logging.DEBUG)
    else:
        logging.getLogger("telegram").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)

    logger.debug(f"Logging configured with level: {settings.LOG_LEVEL}")


async def is_authorized(update: Update) -> bool:
    """Check if the chat ID is authorized.

    Args:
        update: Telegram update object

    Returns:
        True if chat ID is in whitelist, False otherwise
    """
    if not update.effective_chat:
        return False

    chat_id = update.effective_chat.id
    allowed = settings.is_chat_allowed(chat_id)

    if not allowed:
        logger.warning(f"Unauthorized access attempt from chat ID: {chat_id}")

    return allowed


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command.

    Args:
        update: Telegram update object
        context: Callback context
    """
    if not update.effective_chat:
        return

    chat_id = update.effective_chat.id

    # Check whitelist first
    if not await is_authorized(update):
        await update.message.reply_text("unauthorized") if update.message else None
        logger.warning(f"Unauthorized /start attempt from chat ID: {chat_id}")
        return

    # Authorized user - send welcome message
    welcome_message = (
        "👋 Welcome to Auntie!\n\n"
        "I'm your personal assistant bot. I can help you with:\n"
        "- Managing bookmarks\n"
        "- And more skills coming soon!\n\n"
        "Send me a message to get started."
    )

    await update.message.reply_text(welcome_message) if update.message else None
    logger.info(f"User {chat_id} started the bot")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming messages.

    Validates chat ID against whitelist before dispatching to skills.

    Args:
        update: Telegram update object
        context: Callback context
    """
    if not update.effective_chat or not update.message:
        return

    chat_id = update.effective_chat.id

    # Check whitelist first
    if not await is_authorized(update):
        await update.message.reply_text("unauthorized")
        logger.warning(f"Unauthorized message from chat ID: {chat_id}")
        return

    # Authorized user - dispatch to skill loader
    if skill_loader:
        try:
            handled_by = await skill_loader.dispatch_message(update)
            if handled_by:
                logger.debug(f"Message handled by skill: {handled_by}")
            else:
                logger.debug("No skill handled the message")
        except Exception as e:
            logger.error(f"Error dispatching message: {e}")
            await update.message.reply_text(
                "Sorry, I encountered an error processing your message."
            )
    else:
        logger.warning("Skill loader not initialized")
        await update.message.reply_text("Sorry, I'm not ready to process messages yet.")


async def shutdown() -> None:
    """Perform graceful shutdown.

    Closes database connections and cleans up resources.
    """
    logger.info("Shutting down bot...")

    global skill_loader, application

    # Cleanup skills
    if skill_loader:
        try:
            await skill_loader.cleanup()
            logger.info("Skills cleaned up")
        except Exception as e:
            logger.error(f"Error during skill cleanup: {e}")

    # Stop the application
    if application:
        try:
            await application.stop()
            await application.shutdown()
            logger.info("Application stopped")
        except Exception as e:
            logger.error(f"Error stopping application: {e}")

    logger.info("Shutdown complete")

    # Signal that shutdown is complete
    if shutdown_event:
        shutdown_event.set()


def signal_handler(signum: int, frame: FrameType | None) -> None:
    """Handle shutdown signals.

    Args:
        signum: Signal number
        frame: Current stack frame
    """
    signal_name = signal.Signals(signum).name
    logger.info(f"Received signal {signal_name} ({signum})")

    # Create task to run async shutdown
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(shutdown())
        else:
            loop.run_until_complete(shutdown())
    except Exception as e:
        logger.error(f"Error during signal handling: {e}")
        sys.exit(1)


async def init_bot() -> Application:
    """Initialize the bot application.

    Returns:
        Configured Application instance
    """
    global application, skill_loader

    logger.info("Initializing bot...")

    # Initialize database
    await init_database(settings.DATABASE_PATH)
    logger.info("Database initialized")

    # Build application
    application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()

    # Initialize skill loader
    skills_dir = Path(__file__).parent / "skills"
    skill_loader = SkillLoader(
        skills_dir=str(skills_dir),
        db=None,  # Skills will get their own DB connections
        config=settings,
    )
    await skill_loader.load_skills()

    # Register handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot initialized successfully")
    return application


async def main() -> None:
    """Main entry point for the bot."""
    global shutdown_event

    # Setup logging first
    setup_logging()

    logger.info("Starting Auntie bot...")
    logger.info(f"Allowed chat IDs: {settings.get_allowed_chat_ids()}")

    # Create shutdown event
    shutdown_event = asyncio.Event()

    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        # Initialize bot
        app = await init_bot()

        # Start the bot (polling mode)
        logger.info("Starting polling...")
        await app.initialize()
        await app.start()
        await app.updater.start_polling()

        # Wait for shutdown signal
        logger.info("Bot is running. Press Ctrl+C to stop.")
        await shutdown_event.wait()

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise
    finally:
        await shutdown()


if __name__ == "__main__":
    asyncio.run(main())
