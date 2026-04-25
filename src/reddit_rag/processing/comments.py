"""Load saved Reddit thread JSON and normalize comments."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from reddit_rag.ingestion.raw_ingestion import iter_comment_payloads
from reddit_rag.processing.normalize import NormalizedComment, normalize_comment_payload
from reddit_rag.processing.posts import (
    iter_thread_json_paths,
    load_saved_thread_json,
    resolve_threads_dir,
)


def comment_record_to_dict(comment: NormalizedComment) -> dict[str, Any]:
    """Serialize a normalized comment for JSON / JSONL output."""
    return asdict(comment)


@dataclass(frozen=True)
class MergeResult:
    """Summary of merging new comment dicts into a JSONL file."""

    path: Path
    existing_count: int
    appended: int
    skipped_duplicates: int
    total_after: int


def comment_record_dedupe_key(rec: dict[str, Any]) -> str:
    """Stable key for deduplicating normalized comment records (prefer Reddit comment id)."""
    rid = rec.get("reddit_id")
    if isinstance(rid, str) and rid.strip():
        return rid.strip()
    internal = rec.get("id")
    if isinstance(internal, str) and internal.strip():
        return internal.strip()
    raise ValueError("comment record missing non-empty reddit_id and id")


def default_comments_jsonl_path(processed_root: Path, subreddit: str) -> Path:
    """Default JSONL path: ``<processed_root>/<safe_subreddit>/comments.jsonl``."""
    return (processed_root / _safe_path_part(subreddit) / "comments.jsonl").resolve()


def _load_existing_comment_records(path: Path) -> tuple[list[dict[str, Any]], set[str], int]:
    """Load JSONL comment records; dedupe by :func:`comment_record_dedupe_key` keeping first occurrence."""
    if not path.is_file():
        return [], set(), 0
    records: list[dict[str, Any]] = []
    keys: set[str] = set()
    non_empty_line_count = 0
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            non_empty_line_count += 1
            try:
                rec = json.loads(stripped)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON at {path}:{line_no}") from e
            if not isinstance(rec, dict):
                raise ValueError(f"Expected object per line at {path}:{line_no}")
            key = comment_record_dedupe_key(rec)
            if key in keys:
                continue
            keys.add(key)
            records.append(rec)
    return records, keys, non_empty_line_count


def merge_comment_records_jsonl(path: Path, new_records: list[dict[str, Any]]) -> MergeResult:
    """Merge ``new_records`` into ``path`` by ``reddit_id``; keep existing rows on conflicts; create parent dirs."""
    path = path.resolve()
    existing, prior_keys, prior_non_empty_lines = _load_existing_comment_records(path)
    merged: list[dict[str, Any]] = list(existing)
    keys = set(prior_keys)
    appended = 0
    skipped = 0
    for rec in new_records:
        key = comment_record_dedupe_key(rec)
        if key in keys:
            skipped += 1
            continue
        keys.add(key)
        merged.append(rec)
        appended += 1

    on_disk_had_redundant_key_lines = path.is_file() and prior_non_empty_lines > len(existing)
    should_write = (
        appended > 0
        or (not path.is_file() and len(merged) > 0)
        or on_disk_had_redundant_key_lines
    )
    if should_write:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            for row in merged:
                f.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
                f.write("\n")

    return MergeResult(
        path=path,
        existing_count=len(existing),
        appended=appended,
        skipped_duplicates=skipped,
        total_after=len(merged),
    )


def normalize_comments_from_thread_file(path: Path) -> list[NormalizedComment]:
    """Normalize all comments in one saved thread JSON file."""
    saved = load_saved_thread_json(path)
    payload = saved.get("payload")
    raw_payloads = iter_comment_payloads(payload)
    raw_path = str(path.resolve())
    return [normalize_comment_payload(data, raw_path) for data in raw_payloads]


def normalize_comments_from_subreddit(
    subreddit: str,
    *,
    raw_dir: Path | None = None,
) -> list[NormalizedComment]:
    """Normalize comments from all thread JSON files for one subreddit under raw storage."""
    threads = resolve_threads_dir(raw_dir=raw_dir, subreddit=subreddit)
    comments: list[NormalizedComment] = []
    for path in iter_thread_json_paths(threads):
        comments.extend(normalize_comments_from_thread_file(path))
    return comments


def _safe_path_part(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in value).strip("-") or "unknown"
