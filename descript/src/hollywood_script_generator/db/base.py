"""Database base configuration.

This module defines the declarative base for all SQLAlchemy models.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for all database models."""

    pass
