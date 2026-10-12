"""SQLite connection and database table setup for the library system."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

DATABASE_FILE = Path(__file__).resolve().parent.parent / "library.db"
PHILIPPINES_TZ = ZoneInfo("Asia/Manila")


def current_date() -> str:
    """Return the current date in Philippine time as YYYY-MM-DD."""
    return datetime.now(PHILIPPINES_TZ).date().isoformat()

@contextmanager
def database_connection() -> Iterator[sqlite3.Connection]:
    """Open a database connection, commit on success, roll back on error, then close."""
    connection = sqlite3.connect(DATABASE_FILE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database() -> None:
    """Create the library tables if they do not already exist."""
    with database_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS borrowers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                borrower_id TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                borrower_type TEXT NOT NULL
                    CHECK (borrower_type IN ('Student', 'Professor', 'Staff')),
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                isbn TEXT UNIQUE,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                total_copies INTEGER NOT NULL CHECK (total_copies >= 1),
                available_copies INTEGER NOT NULL CHECK (
                    available_copies >= 0 AND available_copies <= total_copies
                ),
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS borrow_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                borrower_record_id INTEGER NOT NULL,
                book_id INTEGER NOT NULL,
                borrowed_at TEXT NOT NULL,
                due_date TEXT NOT NULL,
                returned_at TEXT,
                status TEXT NOT NULL DEFAULT 'Borrowed'
                    CHECK (status IN ('Borrowed', 'Returned')),
                FOREIGN KEY (borrower_record_id) REFERENCES borrowers(id),
                FOREIGN KEY (book_id) REFERENCES books(id)
            );

            CREATE INDEX IF NOT EXISTS idx_borrow_records_status
                ON borrow_records(status);
            CREATE INDEX IF NOT EXISTS idx_borrow_records_due_date
                ON borrow_records(due_date);
            """
        )
