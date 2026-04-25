"""Chunk normalized records while preserving source metadata.

Post and comment bodies are expected to be cleaned already via
``reddit_rag.processing.text_clean.clean_reddit_text`` during normalization.
Assemble chunk text from normalized fields without re-running the full cleaner
unless a future pipeline adds a minimal defensive step (e.g. null-byte strip).
"""

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

    Input records should already carry cleaned ``body`` (and titles as produced
    by the normalizer). See module docstring.

    TODO:
    - Support post and comment records with stable chunk IDs.
    - Preserve citation metadata needed for final answers.
    """
    raise NotImplementedError("Chunking is not implemented yet.")
