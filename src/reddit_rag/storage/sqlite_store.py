"""SQLite metadata and checkpoint store placeholders."""

from __future__ import annotations

from pathlib import Path
from typing import Any


class SqliteStore:
    """Placeholder interface for local SQLite-backed metadata storage."""

    def __init__(self, _db_path: Path) -> None:
        """Initialize the store with a local sqlite path."""
        raise NotImplementedError("SQLite store initialization is not implemented yet.")

    def upsert_records(self, _records: list[dict[str, Any]]) -> None:
        """Persist normalized records and associated metadata.

        TODO:
        - Add tables for posts, comments, chunks, and checkpoints.
        """
        raise NotImplementedError("Record upsert is not implemented yet.")

    def save_checkpoint(self, _subreddit: str, _payload: dict[str, Any]) -> None:
        """Persist ingestion checkpoint state for safe resumability."""
        raise NotImplementedError("Checkpoint persistence is not implemented yet.")
