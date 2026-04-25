"""JSONL persistence for chunk records."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

def _safe_path_part(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in value).strip("-") or "unknown"


def chunk_record_dedupe_key(rec: dict[str, Any]) -> str:
    """Stable key for deduplicating chunk records."""
    cid = rec.get("id")
    if isinstance(cid, str) and cid.strip():
        return cid.strip()
    raise ValueError("chunk record missing non-empty id")


def default_chunks_jsonl_path(processed_root: Path, subreddit: str) -> Path:
    """Default JSONL path: ``<processed_root>/<safe_subreddit>/chunks.jsonl``."""
    return (processed_root / _safe_path_part(subreddit) / "chunks.jsonl").resolve()


@dataclass(frozen=True)
class MergeResult:
    """Summary of merging new chunk dicts into a JSONL file."""

    path: Path
    existing_count: int
    appended: int
    skipped_duplicates: int
    total_after: int


def iter_jsonl_records(path: Path) -> Iterator[dict[str, Any]]:
    """Yield one dict per non-empty line; raises on invalid JSON."""
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                rec = json.loads(stripped)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON at {path}:{line_no}") from e
            if not isinstance(rec, dict):
                raise ValueError(f"Expected object per line at {path}:{line_no}")
            yield rec


def _load_existing_chunk_records(path: Path) -> tuple[list[dict[str, Any]], set[str], int]:
    """Load JSONL chunk records; dedupe by chunk id keeping first occurrence."""
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
            key = chunk_record_dedupe_key(rec)
            if key in keys:
                continue
            keys.add(key)
            records.append(rec)
    return records, keys, non_empty_line_count


def merge_chunk_records_jsonl(path: Path, new_records: list[dict[str, Any]]) -> MergeResult:
    """Merge ``new_records`` into ``path`` by chunk ``id``; keep existing rows on conflicts."""
    path = path.resolve()
    existing, prior_keys, prior_non_empty_lines = _load_existing_chunk_records(path)
    merged: list[dict[str, Any]] = list(existing)
    keys = set(prior_keys)
    appended = 0
    skipped = 0
    for rec in new_records:
        key = chunk_record_dedupe_key(rec)
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


def load_records_from_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load all records from a JSONL file (empty list if missing)."""
    if not path.is_file():
        return []
    return list(iter_jsonl_records(path))
