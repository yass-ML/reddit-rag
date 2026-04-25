"""Vector storage placeholders for local embeddings."""

from __future__ import annotations

from pathlib import Path
from typing import Any


class VectorStore:
    """Placeholder interface for local vector index operations."""

    def __init__(self, _persist_dir: Path, _collection_name: str = "reddit_chunks") -> None:
        """Initialize a persistent local vector store.

        TODO:
        - Back this with Chroma in a later phase.
        """
        raise NotImplementedError("Vector store initialization is not implemented yet.")

    def upsert_chunks(self, _chunk_ids: list[str], _embeddings: list[list[float]], _metadatas: list[dict[str, Any]]) -> None:
        """Insert or update chunk embeddings and metadata."""
        raise NotImplementedError("Vector upsert is not implemented yet.")

    def query(self, _query_embedding: list[float], _top_k: int) -> list[dict[str, Any]]:
        """Return nearest chunk matches with metadata for retrieval."""
        raise NotImplementedError("Vector query is not implemented yet.")
