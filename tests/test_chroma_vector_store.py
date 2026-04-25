"""Tests for Chroma-backed vector store."""

from __future__ import annotations

import pytest

from reddit_rag.storage.vector_store import VectorStore, chunk_jsonl_row_to_chroma_metadata


def _sample_chunk_row(**overrides: object) -> dict:
    row = {
        "id": "chunk_v1_cs1500_ov200_post_post_abc_0000",
        "source_type": "post",
        "source_id": "post_abc",
        "subreddit": "learnpython",
        "text": "Hello world chunk text",
        "metadata": {
            "reddit_id": "abc",
            "post_reddit_id": "abc",
            "title": "Hello",
            "score": 5,
            "created_utc": 1700000000.0,
            "chunk_index": 0,
            "chunk_size": 1500,
            "chunk_overlap": 200,
            "permalink": "/r/learnpython/comments/abc/hello/",
        },
    }
    row.update(overrides)
    return row


def test_chunk_jsonl_row_to_chroma_metadata_flattens_and_omits_none() -> None:
    row = _sample_chunk_row(
        metadata={
            "reddit_id": "abc",
            "post_reddit_id": "abc",
            "title": "",
            "score": 5,
            "created_utc": None,
            "chunk_index": 0,
            "chunk_size": 1500,
            "chunk_overlap": 200,
        },
    )
    meta = chunk_jsonl_row_to_chroma_metadata(row)
    assert meta["source_type"] == "post"
    assert meta["source_id"] == "post_abc"
    assert meta["subreddit"] == "learnpython"
    assert meta["reddit_id"] == "abc"
    assert meta["score"] == 5
    assert "created_utc" not in meta
    assert "permalink" not in meta


def test_chunk_jsonl_row_to_chroma_metadata_skips_empty_permalink() -> None:
    row = _sample_chunk_row(
        metadata={
            **dict(_sample_chunk_row()["metadata"]),
            "permalink": "   ",
        },
    )
    meta = chunk_jsonl_row_to_chroma_metadata(row)
    assert "permalink" not in meta


def test_upsert_roundtrip_metadata_and_documents(tmp_path) -> None:
    persist = tmp_path / "chroma_data"
    store = VectorStore(persist)

    row_a = _sample_chunk_row(id="id_a", text="doc a")
    row_b = _sample_chunk_row(
        id="id_b",
        source_id="post_def",
        text="doc b",
        metadata={**dict(_sample_chunk_row()["metadata"]), "reddit_id": "def"},
    )

    ids = [row_a["id"], row_b["id"]]
    emb = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]
    docs = [row_a["text"], row_b["text"]]
    metas = [chunk_jsonl_row_to_chroma_metadata(row_a), chunk_jsonl_row_to_chroma_metadata(row_b)]

    store.upsert_chunks(ids, emb, docs, metas)
    assert store.count() == 2

    got = store.collection.get(ids=ids, include=["documents", "metadatas"])
    assert set(got["ids"]) == set(ids)
    by_id = {i: {"document": d, "metadata": m} for i, d, m in zip(got["ids"], got["documents"], got["metadatas"])}
    assert by_id["id_a"]["document"] == "doc a"
    assert by_id["id_a"]["metadata"]["subreddit"] == "learnpython"
    assert by_id["id_b"]["metadata"]["reddit_id"] == "def"


def test_upsert_same_ids_is_idempotent(tmp_path) -> None:
    persist = tmp_path / "chroma_data"
    store = VectorStore(persist)
    row = _sample_chunk_row()
    cid = row["id"]
    meta = chunk_jsonl_row_to_chroma_metadata(row)
    emb = [[0.0, 0.0, 1.0]]
    store.upsert_chunks([cid], emb, [row["text"]], [meta])
    assert store.count() == 1
    store.upsert_chunks([cid], emb, ["updated text"], [meta])
    assert store.count() == 1
    got = store.collection.get(ids=[cid], include=["documents"])
    assert got["documents"][0] == "updated text"


def test_upsert_chunks_length_mismatch_raises(tmp_path) -> None:
    store = VectorStore(tmp_path / "c")
    with pytest.raises(ValueError, match="equal length"):
        store.upsert_chunks(["a"], [[1.0], [2.0]], ["x"], [{}])


def test_query_returns_hits(tmp_path) -> None:
    store = VectorStore(tmp_path / "c")
    row = _sample_chunk_row()
    store.upsert_chunks(
        [row["id"]],
        [[1.0, 0.0, 0.0]],
        [row["text"]],
        [chunk_jsonl_row_to_chroma_metadata(row)],
    )
    hits = store.query([1.0, 0.0, 0.0], top_k=3)
    assert len(hits) == 1
    assert hits[0]["id"] == row["id"]
    assert hits[0]["document"] == row["text"]
    assert hits[0]["metadata"]["subreddit"] == "learnpython"
    assert hits[0]["distance"] is not None


def test_query_filters_by_subreddit_metadata(tmp_path) -> None:
    store = VectorStore(tmp_path / "c2")
    row_a = _sample_chunk_row(
        id="id_sub_a",
        subreddit="sub_a",
    )
    row_b = _sample_chunk_row(
        id="id_sub_b",
        source_id="post_other",
        subreddit="sub_b",
        text="other doc",
        metadata={
            **dict(_sample_chunk_row()["metadata"]),
            "title": "Other",
        },
    )
    m_a = chunk_jsonl_row_to_chroma_metadata(row_a)
    m_b = chunk_jsonl_row_to_chroma_metadata(row_b)
    emb = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]
    store.upsert_chunks(
        [row_a["id"], row_b["id"]],
        emb,
        [row_a["text"], row_b["text"]],
        [m_a, m_b],
    )
    assert store.count() == 2
    only_a = store.query([0.0, 0.0, 1.0], top_k=10, where={"subreddit": "sub_a"})
    assert {h["id"] for h in only_a} == {row_a["id"]}
    for h in only_a:
        assert h["metadata"]["subreddit"] == "sub_a"
    only_b = store.query([1.0, 0.0, 0.0], top_k=10, where={"subreddit": "sub_b"})
    assert {h["id"] for h in only_b} == {row_b["id"]}
