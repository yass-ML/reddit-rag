"""Index chunk JSONL rows into the persistent Chroma vector store."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from reddit_rag.embeddings.ollama_client import OllamaEmbeddingClient
from reddit_rag.processing.chunks_io import load_records_from_jsonl
from reddit_rag.storage.vector_store import VectorStore, chunk_jsonl_row_to_chroma_metadata


class EmbeddingClient(Protocol):
    def embed_texts(self, texts: list[str], *, batch_size: int | None = None) -> list[list[float]]:
        """Embed texts in input order."""


class ChunkVectorStore(Protocol):
    def upsert_chunks(
        self,
        chunk_ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict[str, object]],
    ) -> None:
        """Persist embedded chunk rows."""

    def count(self) -> int:
        """Return indexed record count."""


@dataclass(frozen=True)
class ChunkIndexSummary:
    chunks_path: Path
    rows_seen: int
    indexed: int
    skipped_empty_text: int
    vector_count: int


def index_chunk_rows(
    rows: list[dict[str, object]],
    *,
    embedding_client: EmbeddingClient,
    vector_store: ChunkVectorStore,
    batch_size: int | None = None,
) -> ChunkIndexSummary:
    """Embed valid chunk rows and upsert them into Chroma-compatible storage."""
    if batch_size is not None and batch_size <= 0:
        raise ValueError("batch_size must be > 0 when set")

    ids: list[str] = []
    texts: list[str] = []
    metadatas: list[dict[str, object]] = []
    skipped = 0

    for row in rows:
        chunk_id = row.get("id")
        text = row.get("text")
        if not isinstance(chunk_id, str) or not chunk_id.strip():
            raise ValueError("chunk row missing non-empty id")
        if not isinstance(text, str) or not text.strip():
            skipped += 1
            continue
        ids.append(chunk_id.strip())
        texts.append(text.strip())
        metadatas.append(chunk_jsonl_row_to_chroma_metadata(row))

    if ids:
        embeddings = embedding_client.embed_texts(texts, batch_size=batch_size)
        vector_store.upsert_chunks(ids, embeddings, texts, metadatas)

    return ChunkIndexSummary(
        chunks_path=Path(""),
        rows_seen=len(rows),
        indexed=len(ids),
        skipped_empty_text=skipped,
        vector_count=vector_store.count(),
    )


def index_chunks_jsonl(
    chunks_path: Path,
    *,
    embedding_client: OllamaEmbeddingClient,
    vector_store: VectorStore,
    batch_size: int | None = None,
) -> ChunkIndexSummary:
    """Load chunk rows from JSONL, embed their text, and persist vectors."""
    resolved = chunks_path.expanduser().resolve()
    rows = load_records_from_jsonl(resolved)
    summary = index_chunk_rows(
        rows,
        embedding_client=embedding_client,
        vector_store=vector_store,
        batch_size=batch_size,
    )
    return ChunkIndexSummary(
        chunks_path=resolved,
        rows_seen=summary.rows_seen,
        indexed=summary.indexed,
        skipped_empty_text=summary.skipped_empty_text,
        vector_count=summary.vector_count,
    )
