"""Raw Reddit JSON ingestion and persistence."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from reddit_rag.ingestion.reddit_source import RedditJsonResponse, RedditSource
from reddit_rag.paths import resolve_raw_dir


@dataclass(frozen=True)
class SavedRawResponse:
    """A persisted Reddit JSON response."""

    path: Path
    url: str
    status_code: int


@dataclass(frozen=True)
class RawThreadResult:
    """Metadata for one persisted thread payload."""

    post_id: str
    permalink: str
    path: Path
    comment_count: int


@dataclass(frozen=True)
class RawIngestionResult:
    """Summary of a raw subreddit ingestion run."""

    subreddit: str
    listing_pages: int
    posts_seen: int
    threads_fetched: int
    comments_seen: int
    raw_paths: list[Path] = field(default_factory=list)
    checkpoint_path: Path | None = None


def fetch_thread_to_raw(
    source: RedditSource,
    permalink: str,
    *,
    raw_dir: Path | None = None,
) -> SavedRawResponse:
    """Fetch one thread JSON payload and save it under the raw data directory."""
    response = source.fetch_thread(permalink)
    subreddit, post_id = _thread_identity_from_payload(response.payload, fallback_permalink=permalink)
    thread_dir = (raw_dir or resolve_raw_dir()) / _safe_path_part(subreddit) / "threads"
    path = thread_dir / f"{_safe_path_part(post_id)}.json"
    _write_raw_response(path, response)
    return SavedRawResponse(path=path, url=response.url, status_code=response.status_code)


def ingest_subreddit_raw(
    source: RedditSource,
    subreddit_name: str,
    *,
    max_posts: int | None = None,
    max_comments: int | None = None,
    raw_dir: Path | None = None,
    reset_checkpoint: bool = False,
) -> RawIngestionResult:
    """Fetch subreddit listing pages and selected thread payloads into raw JSON files."""
    subreddit = subreddit_name.strip()
    base_raw_dir = raw_dir or resolve_raw_dir()
    subreddit_dir = base_raw_dir / _safe_path_part(subreddit)
    listing_dir = subreddit_dir / "listings"
    thread_dir = subreddit_dir / "threads"
    checkpoint_path = subreddit_dir / "_checkpoint.json"

    checkpoint = _empty_checkpoint(subreddit)
    if checkpoint_path.exists() and not reset_checkpoint:
        checkpoint = _read_checkpoint(checkpoint_path, subreddit)
    elif reset_checkpoint and checkpoint_path.exists():
        checkpoint_path.unlink()

    seen_post_names = set(checkpoint["seen_post_names"])
    fetched_thread_ids = set(checkpoint["fetched_thread_ids"])
    after = checkpoint.get("after")
    listing_pages = 0
    posts_seen = len(seen_post_names)
    threads_fetched = 0
    comments_seen = int(checkpoint.get("comments_seen", 0))
    raw_paths: list[Path] = []

    while _below_limit(posts_seen, max_posts):
        page_limit = _page_limit(max_posts, posts_seen)
        listing_response = source.fetch_subreddit_listing(subreddit, limit=page_limit, after=after)
        listing_pages += 1
        page_token = _safe_path_part(str(after or "start"))
        listing_path = listing_dir / f"page-{listing_pages:04d}-{page_token}.json"
        _write_raw_response(listing_path, listing_response)
        raw_paths.append(listing_path)

        payload_data = _payload_data(listing_response.payload)
        children = payload_data.get("children")
        if not isinstance(children, list) or not children:
            after = None
            break

        for child in children:
            post = _thing_data(child)
            post_id = str(post.get("id") or "").strip()
            fullname = str(post.get("name") or f"t3_{post_id}").strip()
            permalink = str(post.get("permalink") or "").strip()
            if not post_id or not permalink:
                continue
            if fullname not in seen_post_names:
                seen_post_names.add(fullname)
                posts_seen += 1
            if post_id not in fetched_thread_ids and _below_limit(comments_seen, max_comments):
                thread_response = source.fetch_thread(permalink)
                thread_path = thread_dir / f"{_safe_path_part(post_id)}.json"
                _write_raw_response(thread_path, thread_response)
                raw_paths.append(thread_path)
                fetched_thread_ids.add(post_id)
                threads_fetched += 1
                comments_seen += count_comments_in_thread(thread_response.payload)
            if not _below_limit(posts_seen, max_posts) or not _below_limit(comments_seen, max_comments):
                break

        after_value = payload_data.get("after")
        after = str(after_value) if after_value else None
        _write_checkpoint(
            checkpoint_path,
            subreddit=subreddit,
            after=after,
            seen_post_names=seen_post_names,
            fetched_thread_ids=fetched_thread_ids,
            comments_seen=comments_seen,
        )
        if after is None:
            break

    _write_checkpoint(
        checkpoint_path,
        subreddit=subreddit,
        after=after,
        seen_post_names=seen_post_names,
        fetched_thread_ids=fetched_thread_ids,
        comments_seen=comments_seen,
    )
    return RawIngestionResult(
        subreddit=subreddit,
        listing_pages=listing_pages,
        posts_seen=posts_seen,
        threads_fetched=threads_fetched,
        comments_seen=comments_seen,
        raw_paths=raw_paths,
        checkpoint_path=checkpoint_path,
    )


def fetch_subreddit_stream(
    source: RedditSource,
    subreddit_name: str,
    max_posts: int | None = None,
    max_comments: int | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Fetch raw posts/comments into memory for small inspection workflows."""
    if max_posts == 0:
        return {"posts": [], "comments": []}
    listing_response = source.fetch_subreddit_listing(subreddit_name, limit=_page_limit(max_posts, 0))
    posts: list[dict[str, Any]] = []
    comments: list[dict[str, Any]] = []
    for child in _payload_data(listing_response.payload).get("children", []):
        post = _thing_data(child)
        if not post:
            continue
        posts.append(post)
        if max_posts is not None and len(posts) >= max_posts:
            break
    for post in posts:
        if max_comments is not None and len(comments) >= max_comments:
            break
        permalink = str(post.get("permalink") or "")
        if not permalink:
            continue
        thread_response = source.fetch_thread(permalink, limit=500)
        for comment in iter_comment_payloads(thread_response.payload):
            comments.append(comment)
            if max_comments is not None and len(comments) >= max_comments:
                break
    return {"posts": posts, "comments": comments}


def iter_comment_payloads(thread_payload: Any) -> list[dict[str, Any]]:
    """Return flattened comment payloads from a Reddit thread JSON response."""
    comments: list[dict[str, Any]] = []
    if not isinstance(thread_payload, list) or len(thread_payload) < 2:
        return comments
    comment_listing = thread_payload[1]
    children = _payload_data(comment_listing).get("children", [])
    if not isinstance(children, list):
        return comments
    for child in children:
        _collect_comment_payloads(child, comments)
    return comments


def count_comments_in_thread(thread_payload: Any) -> int:
    """Count real comment nodes in a Reddit thread JSON payload."""
    return len(iter_comment_payloads(thread_payload))


def _collect_comment_payloads(node: Any, comments: list[dict[str, Any]]) -> None:
    if not isinstance(node, dict) or node.get("kind") != "t1":
        return
    data = _thing_data(node)
    if not data:
        return
    comments.append(data)
    replies = data.get("replies")
    if not isinstance(replies, dict):
        return
    children = _payload_data(replies).get("children", [])
    if isinstance(children, list):
        for child in children:
            _collect_comment_payloads(child, comments)


def _write_raw_response(path: Path, response: RedditJsonResponse) -> None:
    payload = {
        "source": "reddit_json",
        "fetched_at": _now_iso(),
        "url": response.url,
        "status_code": response.status_code,
        "headers": response.headers,
        "payload": response.payload,
    }
    _write_json(path, payload)


def _write_checkpoint(
    path: Path,
    *,
    subreddit: str,
    after: str | None,
    seen_post_names: set[str],
    fetched_thread_ids: set[str],
    comments_seen: int,
) -> None:
    payload = {
        "subreddit": subreddit,
        "after": after,
        "seen_post_names": sorted(seen_post_names),
        "fetched_thread_ids": sorted(fetched_thread_ids),
        "comments_seen": comments_seen,
        "updated_at": _now_iso(),
    }
    _write_json(path, payload)


def _read_checkpoint(path: Path, subreddit: str) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        payload = json.load(f)
    if payload.get("subreddit") != subreddit:
        return _empty_checkpoint(subreddit)
    payload.setdefault("after", None)
    payload.setdefault("seen_post_names", [])
    payload.setdefault("fetched_thread_ids", [])
    payload.setdefault("comments_seen", 0)
    return payload


def _empty_checkpoint(subreddit: str) -> dict[str, Any]:
    return {
        "subreddit": subreddit,
        "after": None,
        "seen_post_names": [],
        "fetched_thread_ids": [],
        "comments_seen": 0,
    }


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")


def _payload_data(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        data = payload.get("data")
        if isinstance(data, dict):
            return data
    return {}


def _thing_data(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        data = value.get("data")
        if isinstance(data, dict):
            return data
    return {}


def _thread_identity_from_payload(payload: Any, *, fallback_permalink: str) -> tuple[str, str]:
    if isinstance(payload, list) and payload:
        children = _payload_data(payload[0]).get("children", [])
        if isinstance(children, list) and children:
            post = _thing_data(children[0])
            subreddit = str(post.get("subreddit") or "unknown").strip() or "unknown"
            post_id = str(post.get("id") or "unknown").strip() or "unknown"
            return subreddit, post_id
    return "unknown", _safe_path_part(fallback_permalink.strip("/") or "thread")


def _safe_path_part(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in value).strip("-") or "unknown"


def _page_limit(max_posts: int | None, posts_seen: int) -> int:
    if max_posts is None:
        return 100
    remaining = max(max_posts - posts_seen, 1)
    return min(remaining, 100)


def _below_limit(value: int, limit: int | None) -> bool:
    return limit is None or value < limit


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()
