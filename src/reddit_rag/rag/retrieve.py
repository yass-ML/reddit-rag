"""Semantic retrieval over embedded chunks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from reddit_rag.embeddings.ollama_client import OllamaEmbeddingClient
from reddit_rag.storage.vector_store import VectorStore


@dataclass(frozen=True)
class RetrievalResult:
    """One retrieved chunk with similarity score and source metadata."""

    chunk_id: str
    text: str
    score: float
    metadata: dict[str, Any]
    source_permalink: str
    source_title: str
    source_type: str


def chroma_cosine_distance_to_score(distance: float | None) -> float:
    """Map Chroma cosine *distance* to a higher-is-better similarity *score*.

    With ``hnsw:space: cosine``, Chroma uses distance = 1 - cosine_similarity
    in ``[0, 2]``. The score ``1.0 - distance`` equals cosine similarity
    in ``[-1, 1]`` (higher is better). ``None`` maps to 0.0.
    """
    if distance is None:
        return 0.0
    try:
        return 1.0 - float(distance)
    except (TypeError, ValueError):
        return 0.0


def _str_from_metadata(meta: dict[str, Any], key: str) -> str:
    v = meta.get(key)
    if isinstance(v, str):
        return v.strip()
    return ""


def _coerce_chroma_distance(dist: object) -> float | None:
    if dist is None:
        return None
    if isinstance(dist, (int, float)) and not isinstance(dist, bool):
        return float(dist)
    try:
        return float(dist)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _hit_to_result(hit: dict[str, Any]) -> RetrievalResult:
    mid = hit.get("id")
    chunk_id = str(mid) if mid is not None else ""
    doc = hit.get("document")
    text = str(doc) if doc is not None else ""
    raw_meta = hit.get("metadata")
    meta: dict[str, Any] = raw_meta if isinstance(raw_meta, dict) else {}
    d_raw = _coerce_chroma_distance(hit.get("distance"))
    score = chroma_cosine_distance_to_score(d_raw)

    return RetrievalResult(
        chunk_id=chunk_id,
        text=text,
        score=score,
        metadata=dict(meta),
        source_permalink=_str_from_metadata(meta, "permalink"),
        source_title=_str_from_metadata(meta, "title"),
        source_type=_str_from_metadata(meta, "source_type"),
    )


def retrieve_relevant_chunks(
    question: str,
    *,
    embedding_client: OllamaEmbeddingClient,
    vector_store: VectorStore,
    top_k: int = 5,
    subreddit: str | None = None,
) -> list[RetrievalResult]:
    """Embed ``question`` and return the top ``top_k`` chunks with metadata.

    When ``subreddit`` is set, only chunks tagged with that subreddit in
    Chroma metadata are considered (exact string match, case-sensitive).
    """
    cleaned = question.strip()
    if not cleaned:
        raise ValueError("question must be a non-empty string")

    if top_k <= 0:
        raise ValueError("top_k must be > 0")

    sub: str | None = None
    if subreddit is not None and str(subreddit).strip():
        sub = str(subreddit).strip()
    where: dict[str, Any] | None = None
    if sub is not None:
        where = {"subreddit": sub}

    vec = embedding_client.embed_text(cleaned)
    hits = vector_store.query(vec, top_k, where=where)
    return [_hit_to_result(h) for h in hits]
