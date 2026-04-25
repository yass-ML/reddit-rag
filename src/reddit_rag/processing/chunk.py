"""Chunk normalized records while preserving source metadata.

Post and comment bodies are expected to be cleaned already via
``reddit_rag.processing.text_clean.clean_reddit_text`` during normalization.
Assemble chunk text from normalized fields without re-running the full cleaner
unless a future pipeline adds a minimal defensive step (e.g. null-byte strip).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

CHUNK_ID_FORMAT_VERSION = "v1"


@dataclass(frozen=True)
class Chunk:
    """Chunk contract for retrieval and embedding."""

    id: str
    source_type: str
    source_id: str
    subreddit: str
    text: str
    metadata: dict[str, Any]


def _validate_chunk_params(chunk_size: int, chunk_overlap: int) -> None:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must satisfy 0 <= chunk_overlap < chunk_size")


def _iter_windows(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split non-empty text into overlapping character windows."""
    _validate_chunk_params(chunk_size, overlap)
    stripped = text.strip()
    if not stripped:
        return []
    n = len(stripped)
    if n <= chunk_size:
        return [stripped]
    step = chunk_size - overlap
    out: list[str] = []
    start = 0
    while start < n:
        end = min(start + chunk_size, n)
        out.append(stripped[start:end])
        if end >= n:
            break
        start += step
    return out


def _safe_chunk_id_segment(value: str) -> str:
    """Restrict characters so chunk IDs stay URL/path friendly."""
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in value).strip("-") or "x"


def _chunk_id(
    *,
    chunk_size: int,
    overlap: int,
    source_type: str,
    source_id: str,
    chunk_index: int,
) -> str:
    seg = _safe_chunk_id_segment(source_id)
    return (
        f"chunk_{CHUNK_ID_FORMAT_VERSION}_cs{chunk_size}_ov{overlap}_"
        f"{source_type}_{seg}_{chunk_index:04d}"
    )


def _str_field(rec: dict[str, Any], key: str, default: str = "") -> str:
    v = rec.get(key)
    if isinstance(v, str):
        return v
    return default


def _optional_float(rec: dict[str, Any], key: str) -> float | None:
    v = rec.get(key)
    if v is None:
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    return None


def _int_field(rec: dict[str, Any], key: str, default: int = 0) -> int:
    v = rec.get(key)
    if isinstance(v, bool):
        return default
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v)
    return default


def _base_metadata(
    *,
    rec: dict[str, Any],
    chunk_size: int,
    chunk_overlap: int,
    chunk_index: int,
    title: str,
    post_reddit_id: str,
    permalink_if_present: str | None,
) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "reddit_id": _str_field(rec, "reddit_id"),
        "post_reddit_id": post_reddit_id,
        "title": title,
        "score": _int_field(rec, "score", 0),
        "created_utc": _optional_float(rec, "created_utc"),
        "chunk_index": chunk_index,
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap,
    }
    if permalink_if_present and permalink_if_present.strip():
        meta["permalink"] = permalink_if_present.strip()
    author = _str_field(rec, "author").strip()
    if author:
        meta["author"] = author
    raw_path = _str_field(rec, "raw_path").strip()
    if raw_path:
        meta["raw_path"] = raw_path
    num_comments = rec.get("num_comments")
    if isinstance(num_comments, int) and not isinstance(num_comments, bool):
        meta["num_comments"] = num_comments
    parent_title = (
        _str_field(rec, "parent_post_title").strip()
        or _str_field(rec, "post_title").strip()
    )
    if parent_title:
        meta["parent_post_title"] = parent_title
    return meta


def chunks_from_post_dict(
    rec: dict[str, Any],
    *,
    chunk_size: int,
    chunk_overlap: int,
) -> list[Chunk]:
    """Build chunk records from one normalized post dict (JSONL row)."""
    _validate_chunk_params(chunk_size, chunk_overlap)
    source_id = _str_field(rec, "id")
    if not source_id:
        raise ValueError("post record missing non-empty id")
    subreddit = _str_field(rec, "subreddit")
    title = _str_field(rec, "title").strip()
    body = _str_field(rec, "body").strip()
    if body:
        combined = f"{title}\n\n{body}".strip() if title else body
    else:
        combined = title
    windows = _iter_windows(combined, chunk_size, chunk_overlap)
    reddit_id = _str_field(rec, "reddit_id")
    permalink = _str_field(rec, "permalink")
    out: list[Chunk] = []
    for idx, text in enumerate(windows):
        cid = _chunk_id(
            chunk_size=chunk_size,
            overlap=chunk_overlap,
            source_type="post",
            source_id=source_id,
            chunk_index=idx,
        )
        meta = _base_metadata(
            rec=rec,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            chunk_index=idx,
            title=title,
            post_reddit_id=reddit_id,
            permalink_if_present=permalink,
        )
        out.append(
            Chunk(
                id=cid,
                source_type="post",
                source_id=source_id,
                subreddit=subreddit,
                text=text,
                metadata=meta,
            )
        )
    return out


def chunks_from_comment_dict(
    rec: dict[str, Any],
    *,
    chunk_size: int,
    chunk_overlap: int,
) -> list[Chunk]:
    """Build chunk records from one normalized comment dict (JSONL row)."""
    _validate_chunk_params(chunk_size, chunk_overlap)
    source_id = _str_field(rec, "id")
    if not source_id:
        raise ValueError("comment record missing non-empty id")
    subreddit = _str_field(rec, "subreddit")
    body = _str_field(rec, "body").strip()
    windows = _iter_windows(body, chunk_size, chunk_overlap)
    permalink_stripped = _str_field(rec, "permalink").strip()
    permalink_arg = permalink_stripped if permalink_stripped else None
    post_rid = _str_field(rec, "post_reddit_id")
    out: list[Chunk] = []
    for idx, text in enumerate(windows):
        cid = _chunk_id(
            chunk_size=chunk_size,
            overlap=chunk_overlap,
            source_type="comment",
            source_id=source_id,
            chunk_index=idx,
        )
        meta = _base_metadata(
            rec=rec,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            chunk_index=idx,
            title="",
            post_reddit_id=post_rid,
            permalink_if_present=permalink_arg,
        )
        out.append(
            Chunk(
                id=cid,
                source_type="comment",
                source_id=source_id,
                subreddit=subreddit,
                text=text,
                metadata=meta,
            )
        )
    return out


def _dispatch_record(rec: dict[str, Any], chunk_size: int, chunk_overlap: int) -> list[Chunk]:
    rid = _str_field(rec, "id")
    if rid.startswith("post_"):
        return chunks_from_post_dict(rec, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    if rid.startswith("comment_"):
        return chunks_from_comment_dict(rec, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    raise ValueError(
        f"Record id must start with 'post_' or 'comment_' to chunk, got {rid!r}",
    )


def chunk_records(records: list[dict[str, Any]], chunk_size: int, chunk_overlap: int) -> list[Chunk]:
    """Create chunked text units from normalized post/comment dicts in input order.

    Each dict must be a NormalizedPost or NormalizedComment row (``id`` prefix ``post_`` / ``comment_``).
    """
    _validate_chunk_params(chunk_size, chunk_overlap)
    out: list[Chunk] = []
    for rec in records:
        if not isinstance(rec, dict):
            raise ValueError(f"Expected dict record, got {type(rec).__name__}")
        out.extend(_dispatch_record(rec, chunk_size, chunk_overlap))
    return out


def chunk_to_dict(chunk: Chunk) -> dict[str, Any]:
    """Serialize a chunk for JSONL (flat metadata, JSON-safe values)."""
    return asdict(chunk)
