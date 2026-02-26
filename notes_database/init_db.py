#!/usr/bin/env python3
"""
SQLite schema initializer for the Personal Notes Organizer.

This script creates the SQLite database file (notes.db) and all required tables
and indexes to support:
- notes (CRUD)
- tags (CRUD)
- note_tags (many-to-many relationship for filtering/search)

It is designed to be safe to run multiple times (uses IF NOT EXISTS).

Usage:
  python init_db.py
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path


DB_FILENAME = "notes.db"


def _db_path() -> Path:
    """Return the absolute path of the SQLite DB file in this directory."""
    return Path(__file__).resolve().parent / DB_FILENAME


def _connect(db_file: Path) -> sqlite3.Connection:
    """Create a SQLite connection with sane defaults."""
    conn = sqlite3.connect(str(db_file))
    # Enable FK constraints (off by default in sqlite).
    conn.execute("PRAGMA foreign_keys = ON;")
    # Better concurrency characteristics for typical app usage.
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn


def _apply_schema(conn: sqlite3.Connection) -> None:
    """Create tables + indexes required by the application."""
    # Notes table
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
            updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
        );
        """
    )

    # Tags table
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
        );
        """
    )

    # Many-to-many note<->tag mapping
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS note_tags (
            note_id INTEGER NOT NULL,
            tag_id INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
            PRIMARY KEY (note_id, tag_id),
            FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
        );
        """
    )

    # Helpful indexes for common queries (filter/search)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_notes_updated_at ON notes(updated_at);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_notes_created_at ON notes(created_at);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_note_tags_tag_id ON note_tags(tag_id);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_note_tags_note_id ON note_tags(note_id);")


def _install_updated_at_trigger(conn: sqlite3.Connection) -> None:
    """
    Keep notes.updated_at in sync automatically on UPDATE.

    SQLite cannot modify NEW.* directly in a BEFORE UPDATE trigger reliably the way some
    other DBs do; using an AFTER UPDATE trigger that performs a second UPDATE is common.
    The WHEN clause prevents infinite recursion.
    """
    conn.execute(
        """
        CREATE TRIGGER IF NOT EXISTS trg_notes_updated_at
        AFTER UPDATE ON notes
        FOR EACH ROW
        WHEN NEW.updated_at = OLD.updated_at
        BEGIN
            UPDATE notes
            SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            WHERE id = NEW.id;
        END;
        """
    )


def main() -> None:
    """Create/upgrade the local notes.db schema."""
    db_file = _db_path()
    db_file.parent.mkdir(parents=True, exist_ok=True)

    # Touch the file path so it's obvious where it is on disk.
    if not db_file.exists():
        os.close(os.open(str(db_file), os.O_CREAT | os.O_WRONLY))

    conn = _connect(db_file)
    try:
        with conn:
            _apply_schema(conn)
            _install_updated_at_trigger(conn)
    finally:
        conn.close()

    print(f"Initialized SQLite database schema at: {db_file}")


if __name__ == "__main__":
    main()
