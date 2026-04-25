"""Load saved Reddit thread JSON and normalize posts."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterator

from reddit_rag.paths import resolve_raw_dir
from reddit_rag.processing.normalize import NormalizedPost, normalize_submission_payload


def post_record_to_dict(post: NormalizedPost) -> dict[str, Any]:
    """Serialize a normalized post for JSON / JSONL output."""
    return asdict(post)


@dataclass(frozen=True)
class MergeResult:
    """Summary of merging new post dicts into a JSONL file."""

    path: Path
    existing_count: int
    appended: int
    skipped_duplicates: int
    total_after: int


def post_record_dedupe_key(rec: dict[str, Any]) -> str:
    """Stable key for deduplicating normalized post records (prefer Reddit submission id)."""
    rid = rec.get("reddit_id")
    if isinstance(rid, str) and rid.strip():
        return rid.strip()
    internal = rec.get("id")
    if isinstance(internal, str) and internal.strip():
        return internal.strip()
    raise ValueError("post record missing non-empty reddit_id and id")


def default_posts_jsonl_path(processed_root: Path, subreddit: str) -> Path:
    """Default JSONL path: ``<processed_root>/<safe_subreddit>/posts.jsonl``."""
    return (processed_root / _safe_path_part(subreddit) / "posts.jsonl").resolve()


def _load_existing_post_records(path: Path) -> tuple[list[dict[str, Any]], set[str], int]:
    """Load JSONL post records; dedupe by :func:`post_record_dedupe_key` keeping first occurrence.

    Returns ``(records, key_set, non_empty_line_count)`` so callers can tell when the on-disk
    file contained duplicate keys (line count above unique count) and must be rewritten.
    """
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
            key = post_record_dedupe_key(rec)
            if key in keys:
                continue
            keys.add(key)
            records.append(rec)
    return records, keys, non_empty_line_count


def merge_post_records_jsonl(path: Path, new_records: list[dict[str, Any]]) -> MergeResult:
    """Merge ``new_records`` into ``path`` by ``reddit_id``; keep existing rows on conflicts; create parent dirs."""
    path = path.resolve()
    existing, prior_keys, prior_non_empty_lines = _load_existing_post_records(path)
    merged: list[dict[str, Any]] = list(existing)
    keys = set(prior_keys)
    appended = 0
    skipped = 0
    for rec in new_records:
        key = post_record_dedupe_key(rec)
        if key in keys:
            skipped += 1
            continue
        keys.add(key)
        merged.append(rec)
        appended += 1

    # Rewrite when the file on disk had duplicate key lines, even if new_records is empty, so
    # deduplication in memory is not lost.
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


def load_saved_thread_json(path: Path) -> dict[str, Any]:
    """Load a raw saved thread file (envelope with ``payload`` key)."""
    with path.open(encoding="utf-8") as f:
        raw = json.load(f)
    if not isinstance(raw, dict):
        raise ValueError(f"Expected object at root of {path}")
    return raw


def iter_submission_things_from_thread_payload(payload: Any) -> list[dict[str, Any]]:
    """Extract ``t3`` submission things from a Reddit thread JSON payload (list form)."""
    if not isinstance(payload, list) or not payload:
        return []
    first = payload[0]
    if not isinstance(first, dict):
        return []
    data = first.get("data")
    if not isinstance(data, dict):
        return []
    children = data.get("children")
    if not isinstance(children, list):
        return []
    out: list[dict[str, Any]] = []
    for child in children:
        if isinstance(child, dict) and child.get("kind") == "t3":
            out.append(child)
    return out


def normalize_posts_from_thread_file(path: Path) -> list[NormalizedPost]:
    """Normalize all submissions in one saved thread JSON file."""
    saved = load_saved_thread_json(path)
    payload = saved.get("payload")
    things = iter_submission_things_from_thread_payload(payload)
    raw_path = str(path.resolve())
    return [normalize_submission_payload(thing, raw_path) for thing in things]


def iter_thread_json_paths(threads_dir: Path) -> Iterator[Path]:
    """Yield ``*.json`` paths under a ``threads`` directory, sorted by name."""
    if not threads_dir.is_dir():
        return iter(())
    paths = sorted(p for p in threads_dir.iterdir() if p.is_file() and p.suffix.lower() == ".json")
    return iter(paths)


def resolve_threads_dir(*, raw_dir: Path | None, subreddit: str) -> Path:
    """``<raw_dir>/<subreddit>/threads``."""
    base = raw_dir if raw_dir is not None else resolve_raw_dir()
    return (base / _safe_path_part(subreddit) / "threads").resolve()


def _safe_path_part(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in value).strip("-") or "unknown"


def normalize_posts_from_subreddit(
    subreddit: str,
    *,
    raw_dir: Path | None = None,
) -> list[NormalizedPost]:
    """Normalize all thread JSON files for one subreddit under raw storage."""
    threads = resolve_threads_dir(raw_dir=raw_dir, subreddit=subreddit)
    posts: list[NormalizedPost] = []
    for path in iter_thread_json_paths(threads):
        posts.extend(normalize_posts_from_thread_file(path))
    return posts
