"""
app/jobs/history.py
===================
SQLite-backed persistent publishing history tracking.
Stores records of each published video short:
- date: YYYY-MM-DD
- topic: video headline/topic
- clip_id: stock clip ID or cartoon asset identifier
- provider: source provider (pexels, pixabay, local, cartoon)
- video_id: uploaded platform video ID (YouTube ID)
- status: publishing status (PUBLISHED, FAILED, etc.)
- error: error message if any
"""

import os
import sqlite3
from typing import Dict, Any, List, Optional
from datetime import datetime
from app.utils.logging import logger


class PublishingHistoryManager:
    """Manages SQLite-backed local history of published videos."""

    DEFAULT_DB_PATH = "output/publishing_history.db"

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or self.DEFAULT_DB_PATH
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS publishing_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    topic TEXT,
                    clip_id TEXT,
                    provider TEXT,
                    video_id TEXT,
                    status TEXT NOT NULL,
                    error TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_pub_date ON publishing_history(date)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_pub_video_id ON publishing_history(video_id)
                """
            )

    def record_publication(
        self,
        date: str,
        topic: Optional[str],
        clip_id: Optional[str],
        provider: Optional[str],
        video_id: Optional[str],
        status: str,
        error: Optional[str] = None,
    ) -> int:
        """Inserts a publishing history record into SQLite."""
        created_at = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO publishing_history (
                    date, topic, clip_id, provider, video_id, status, error, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (date, topic, clip_id, provider, video_id, status, error, created_at),
            )
            record_id = cursor.lastrowid
            logger.info(
                f"Recorded publishing history to SQLite (ID: {record_id}): "
                f"date={date}, video_id={video_id}, status={status}"
            )
            return record_id

    def get_records_by_date(self, date: str) -> List[Dict[str, Any]]:
        """Retrieves all publication records for a given date."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM publishing_history WHERE date = ? ORDER BY id DESC",
                (date,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_latest_record(self) -> Optional[Dict[str, Any]]:
        """Returns the most recent publishing history entry."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM publishing_history ORDER BY id DESC LIMIT 1"
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_records(self) -> List[Dict[str, Any]]:
        """Returns all publishing history entries."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM publishing_history ORDER BY id DESC")
            return [dict(row) for row in cursor.fetchall()]
