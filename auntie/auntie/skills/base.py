"""Base skill interface for Auntie bot.

All skills must inherit from BaseSkill and implement the required abstract methods.
"""

from abc import ABC, abstractmethod
from typing import Any

from telegram import Update


class BaseSkill(ABC):
    """Abstract base class for all Auntie bot skills.

    Skills are modular components that handle specific functionality.
    Each skill must implement initialize(), handle_message(), and cleanup().

    Attributes:
        db: SQLite database connection instance
        config: Application configuration (Pydantic Settings)
        _name: Derived skill name from class name
    """

    def __init__(self, db: Any, config: Any) -> None:
        """Initialize the base skill.

        Args:
            db: SQLite database connection instance
            config: Application configuration (Pydantic Settings)
        """
        self.db = db
        self.config = config
        self._name = self._derive_name()

    def _derive_name(self) -> str:
        """Derive skill name from class name.

        Removes 'Skill' suffix if present and converts to lowercase.
        Example: BookmarkSkill -> bookmark
        """
        class_name = self.__class__.__name__
        if class_name.endswith("Skill"):
            return class_name[:-5].lower()
        return class_name.lower()

    @property
    def name(self) -> str:
        """Return the skill name derived from class name."""
        return self._name

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the skill.

        Called once when the skill is loaded. Use this for:
        - Setting up database tables
        - Loading external resources
        - Establishing connections

        Raises:
            Exception: If initialization fails (skill will be disabled)
        """
        pass

    @abstractmethod
    async def handle_message(self, message: Update) -> bool:
        """Handle an incoming Telegram message.

        Args:
            message: Telegram Update object containing the message

        Returns:
            True if the message was handled by this skill, False otherwise.
            Return False to allow other skills to process the message.

        Raises:
            Exception: If processing fails (error will be logged, other skills continue)
        """
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Cleanup resources when the bot shuts down.

        Called during graceful shutdown. Use this for:
        - Closing database connections
        - Flushing buffers
        - Releasing external resources

        Raises:
            Exception: Errors are logged but don't prevent shutdown
        """
        pass
