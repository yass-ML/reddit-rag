"""Retrieval placeholders for local subreddit RAG."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RetrievalResult:
    """Placeholder retrieval result contract."""

    chunk_id: str
    text: str
    score: float
    metadata: dict[str, Any]
    source_permalink: str
    source_title: str
    source_type: str


def retrieve_relevant_chunks(_question: str, _top_k: int = 5) -> list[RetrievalResult]:
    """Retrieve the most relevant chunks and source metadata for a question.

    TODO:
    - Embed the question locally.
    - Query vector store and map records into RetrievalResult.
    """
    raise NotImplementedError("Retrieval is not implemented yet.")
