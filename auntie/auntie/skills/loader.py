"""Skill loader for dynamic discovery and loading of Auntie bot skills.

Provides dynamic import and initialization of skills from a directory.
"""

import importlib
import inspect
import logging
from pathlib import Path
from typing import Any

from telegram import Update

from auntie.skills.base import BaseSkill

logger = logging.getLogger(__name__)


class SkillLoader:
    """Dynamic skill loader for Auntie bot.

    Discovers skills from a directory, filters for BaseSkill subclasses,
    and handles their initialization and message dispatch.

    Attributes:
        skills_dir: Path to the directory containing skill modules
        db: SQLite database connection instance
        config: Application configuration
        skills: Dictionary of loaded skills (name -> skill instance)
    """

    def __init__(self, skills_dir: str, db: Any, config: Any) -> None:
        """Initialize the skill loader.

        Args:
            skills_dir: Path to the directory containing skill modules
            db: SQLite database connection instance
            config: Application configuration (Pydantic Settings)
        """
        self.skills_dir = Path(skills_dir)
        self.db = db
        self.config = config
        self.skills: dict[str, BaseSkill] = {}

    async def load_skills(self) -> dict[str, BaseSkill]:
        """Discover and load all skills from the skills directory.

        Scans the directory for Python files, imports them, and instantiates
        any classes that inherit from BaseSkill.

        Returns:
            Dictionary of loaded skills (skill name -> skill instance)

        Note:
            Import errors are logged as warnings and do not stop loading
            of other skills.
        """
        self.skills = {}

        if not self.skills_dir.exists():
            logger.warning(f"Skills directory does not exist: {self.skills_dir}")
            return self.skills

        # Get package name from directory path
        # Convert path like 'auntie/skills' to package 'auntie.skills'
        package_parts = self.skills_dir.parts
        package_name = ".".join(package_parts)

        # Find all Python files in the directory
        for file_path in self.skills_dir.glob("*.py"):
            # Skip __init__.py and files starting with underscore
            if file_path.name == "__init__.py" or file_path.name.startswith("_"):
                continue

            module_name = file_path.stem
            full_module_name = f"{package_name}.{module_name}"

            try:
                # Dynamically import the module
                module = importlib.import_module(full_module_name)

                # Find all skill classes in the module
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    # Check if it's a skill class (ends with 'Skill' or 'SkillPlugin')
                    if not (name.endswith("Skill") or name.endswith("SkillPlugin")):
                        continue

                    # Check if it's a subclass of BaseSkill (but not BaseSkill itself)
                    if obj is BaseSkill:
                        continue

                    if issubclass(obj, BaseSkill):
                        try:
                            # Instantiate the skill
                            skill = obj(self.db, self.config)

                            # Initialize the skill
                            await skill.initialize()

                            # Register the skill
                            self.skills[skill.name] = skill
                            logger.info(f"Loaded skill: {skill.name} ({name})")

                        except Exception as e:
                            logger.error(f"Failed to initialize skill {name} from {file_path}: {e}")

            except ImportError as e:
                logger.warning(f"Failed to import module {full_module_name}: {e}")
            except SyntaxError as e:
                logger.warning(f"Syntax error in module {full_module_name}: {e}")
            except Exception as e:
                logger.warning(f"Unexpected error loading module {full_module_name}: {e}")

        logger.info(f"Loaded {len(self.skills)} skill(s): {list(self.skills.keys())}")
        return self.skills

    async def dispatch_message(self, message: Update) -> str | None:
        """Dispatch a message to the appropriate skill.

        Iterates through loaded skills and calls handle_message() on each
        until one returns True (indicating it handled the message).

        Args:
            message: Telegram Update object containing the message

        Returns:
            Name of the skill that handled the message, or None if no skill handled it
        """
        for name, skill in self.skills.items():
            try:
                handled = await skill.handle_message(message)
                if handled:
                    logger.debug(f"Message handled by skill: {name}")
                    return name
            except Exception as e:
                logger.error(f"Error in skill {name} while handling message: {e}")
                # Continue to next skill

        return None

    async def cleanup(self) -> None:
        """Cleanup all loaded skills.

        Calls cleanup() on each skill during graceful shutdown.
        Errors are logged but do not prevent cleanup of other skills.
        """
        for name, skill in self.skills.items():
            try:
                await skill.cleanup()
                logger.debug(f"Cleaned up skill: {name}")
            except Exception as e:
                logger.error(f"Error cleaning up skill {name}: {e}")

        self.skills = {}
