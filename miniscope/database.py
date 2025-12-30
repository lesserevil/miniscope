import sqlite3
import os
from contextlib import contextmanager

DB_PATH = "miniscope.db"

def init_db():
    """Initialize the database with the schema."""
    with get_db_cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS miniatures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                line TEXT,
                set_name TEXT,
                number TEXT,
                rarity TEXT,
                size TEXT,
                image_url TEXT,
                image_path TEXT,
                vision_description TEXT,
                embedding JSON
            )
        """)
        # We can store embedding as a JSON list for now, or blob.
        # JSON is easier for simple retrieval and manual parsing if needed.

@contextmanager
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.commit()
        conn.close()

@contextmanager
def get_db_cursor():
    with get_db_connection() as conn:
        yield conn.cursor()
