"""Persistent local vector storage via Chroma."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import chromadb
from chromadb.api.models.Collection import Collection

DEFAULT_COLLECTION_METADATA: dict[str, Any] = {"hnsw:space": "cosine"}


def chunk_jsonl_row_to_chroma_metadata(row: dict[str, Any]) -> dict[str, Any]:
    """Flatten a chunk JSONL object for Chroma record metadata.

    Chroma accepts flat scalar metadata (str, int, float, bool). Nested objects
    are not supported. Keys with ``None`` values are omitted.
    """
    out: dict[str, Any] = {}

    for key in ("source_type", "source_id", "subreddit"):
        v = row.get(key)
        if v is None:
            continue
        if isinstance(v, str):
            stripped = v.strip()
            if stripped:
                out[key] = stripped
        elif isinstance(v, (int, float, bool)):
            out[key] = v

    inner = row.get("metadata")
    if not isinstance(inner, dict):
        return out

    for k, v in inner.items():
        if v is None:
            continue
        if k == "score":
            if isinstance(v, bool):
                continue
            if isinstance(v, (int, float)):
                out[k] = int(v)
            else:
                continue
        elif isinstance(v, bool):
            out[k] = v
        elif isinstance(v, str):
            if k == "permalink" and not v.strip():
                continue
            out[k] = v
        elif isinstance(v, (int, float)):
            out[k] = v

    return out


class VectorStore:
    """Persistent Chroma collection for chunk embeddings and metadata."""

    def __init__(
        self,
        persist_dir: Path,
        collection_name: str = "reddit_chunks",
        *,
        collection_metadata: dict[str, Any] | None = None,
    ) -> None:
        self._persist_dir = Path(persist_dir).expanduser().resolve()
        self._persist_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(self._persist_dir))
        meta = dict(DEFAULT_COLLECTION_METADATA) if collection_metadata is None else dict(collection_metadata)
        self._collection: Collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata=meta,
        )

    @property
    def collection(self) -> Collection:
        """Underlying Chroma collection (for advanced use)."""
        return self._collection

    def count(self) -> int:
        """Number of records in the collection."""
        return self._collection.count()

    def upsert_chunks(
        self,
        chunk_ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict[str, Any]],
    ) -> None:
        """Insert or update chunks by stable chunk ``id`` (idempotent)."""
        n = len(chunk_ids)
        if not (n == len(embeddings) == len(documents) == len(metadatas)):
            raise ValueError(
                "chunk_ids, embeddings, documents, and metadatas must have equal length: "
                f"ids={n}, embeddings={len(embeddings)}, documents={len(documents)}, "
                f"metadatas={len(metadatas)}",
            )
        if n == 0:
            return
        self._collection.upsert(
            ids=chunk_ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

    def query(
        self,
        query_embedding: list[float],
        top_k: int,
        *,
        where: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Return nearest chunk matches with document text and metadata.

        If ``where`` is set, Chroma returns only results whose metadata matches
        (e.g. ``{"subreddit": "learnpython"}`` for a single subreddit).
        """
        if top_k <= 0:
            raise ValueError("top_k must be > 0")
        kwargs: dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": top_k,
            "include": ["documents", "metadatas", "distances"],
        }
        if where is not None:
            kwargs["where"] = where
        result = self._collection.query(**kwargs)
        ids_batch = result.get("ids") or []
        docs_batch = result.get("documents") or []
        meta_batch = result.get("metadatas") or []
        dist_batch = result.get("distances") or []

        if not ids_batch:
            return []
        ids = ids_batch[0] or []
        docs = (docs_batch[0] or []) if docs_batch else []
        metas = (meta_batch[0] or []) if meta_batch else []
        dists = (dist_batch[0] or []) if dist_batch else []

        out: list[dict[str, Any]] = []
        for i, chunk_id in enumerate(ids):
            doc = docs[i] if i < len(docs) else None
            meta = metas[i] if i < len(metas) else {}
            dist = dists[i] if i < len(dists) else None
            if not isinstance(meta, dict):
                meta = {}
            out.append(
                {
                    "id": chunk_id,
                    "document": doc,
                    "metadata": meta,
                    "distance": dist,
                },
            )
        return out
