"""Demo skill for testing the skill loader.

A simple skill that responds to /start and /help commands.
"""

from telegram import Update

from auntie.skills.base import BaseSkill


class DemoSkill(BaseSkill):
    """Demo skill for testing purposes.

    Handles basic commands like /start and /help.
    """

    async def initialize(self) -> None:
        """Initialize the demo skill.

        No special initialization needed for this demo skill.
        """
        pass

    async def handle_message(self, message: Update) -> bool:
        """Handle incoming messages.

        Args:
            message: Telegram Update object

        Returns:
            True if message was handled, False otherwise
        """
        if not message.message or not message.message.text:
            return False

        text = message.message.text.strip()

        if text == "/start":
            return True

        if text == "/help":
            return True

        return False

    async def cleanup(self) -> None:
        """Cleanup resources.

        No resources to cleanup for this demo skill.
        """
        pass
