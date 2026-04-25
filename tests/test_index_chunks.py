from __future__ import annotations

import json
from pathlib import Path

import pytest

from reddit_rag.embeddings.index_chunks import index_chunk_rows, index_chunks_jsonl


def _row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "id": "chunk_1",
        "source_type": "post",
        "source_id": "post_abc",
        "subreddit": "ClaudeAI",
        "text": "Useful chunk text",
        "metadata": {
            "reddit_id": "abc",
            "post_reddit_id": "abc",
            "title": "A title",
            "permalink": "/r/ClaudeAI/comments/abc/a_title/",
            "score": 7,
            "chunk_index": 0,
        },
    }
    row.update(overrides)
    return row


class FakeEmbeddingClient:
    def __init__(self) -> None:
        self.calls: list[tuple[list[str], int | None]] = []

    def embed_texts(self, texts: list[str], *, batch_size: int | None = None) -> list[list[float]]:
        self.calls.append((texts, batch_size))
        return [[float(i), 0.0] for i, _text in enumerate(texts, start=1)]


class FakeVectorStore:
    def __init__(self) -> None:
        self.upserts: list[tuple[list[str], list[list[float]], list[str], list[dict[str, object]]]] = []

    def upsert_chunks(
        self,
        chunk_ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict[str, object]],
    ) -> None:
        self.upserts.append((chunk_ids, embeddings, documents, metadatas))

    def count(self) -> int:
        return sum(len(ids) for ids, _emb, _docs, _meta in self.upserts)


def test_index_chunk_rows_embeds_and_upserts_flattened_metadata() -> None:
    embedder = FakeEmbeddingClient()
    store = FakeVectorStore()
    summary = index_chunk_rows(
        [_row(), _row(id="chunk_2", text="   "), _row(id="chunk_3", text="More text")],
        embedding_client=embedder,
        vector_store=store,
        batch_size=2,
    )

    assert summary.rows_seen == 3
    assert summary.indexed == 2
    assert summary.skipped_empty_text == 1
    assert summary.vector_count == 2
    assert embedder.calls == [(["Useful chunk text", "More text"], 2)]
    ids, embeddings, documents, metadatas = store.upserts[0]
    assert ids == ["chunk_1", "chunk_3"]
    assert embeddings == [[1.0, 0.0], [2.0, 0.0]]
    assert documents == ["Useful chunk text", "More text"]
    assert metadatas[0]["subreddit"] == "ClaudeAI"
    assert metadatas[0]["source_type"] == "post"
    assert metadatas[0]["reddit_id"] == "abc"


def test_index_chunks_jsonl_reports_resolved_path(tmp_path: Path) -> None:
    chunks_path = tmp_path / "chunks.jsonl"
    chunks_path.write_text(json.dumps(_row()) + "\n", encoding="utf-8")
    embedder = FakeEmbeddingClient()
    store = FakeVectorStore()

    summary = index_chunks_jsonl(
        chunks_path,
        embedding_client=embedder,  # type: ignore[arg-type]
        vector_store=store,  # type: ignore[arg-type]
    )

    assert summary.chunks_path == chunks_path.resolve()
    assert summary.indexed == 1
    assert store.count() == 1


def test_index_chunk_rows_rejects_bad_batch_size() -> None:
    with pytest.raises(ValueError, match="batch_size"):
        index_chunk_rows(
            [_row()],
            embedding_client=FakeEmbeddingClient(),
            vector_store=FakeVectorStore(),
            batch_size=0,
        )
