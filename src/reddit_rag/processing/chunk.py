"""Chunk normalized records while preserving source metadata."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Chunk:
    """Placeholder chunk contract for retrieval."""

    id: str
    source_type: str
    source_id: str
    subreddit: str
    text: str
    metadata: dict[str, Any]


def chunk_records(_records: list[dict[str, Any]], _chunk_size: int, _chunk_overlap: int) -> list[Chunk]:
    """Create chunked text units from normalized post/comment records.

    TODO:
    - Support post and comment records with stable chunk IDs.
    - Preserve citation metadata needed for final answers.
    """
    raise NotImplementedError("Chunking is not implemented yet.")
