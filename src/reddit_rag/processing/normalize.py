"""Normalize raw Reddit payloads into local typed records.

Target contracts are documented in memory/data_contracts.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class NormalizedPost:
    """Normalized post record used by downstream storage and chunking."""

    id: str
    reddit_id: str
    subreddit: str
    title: str
    body: str
    author: str | None
    score: int
    num_comments: int
    created_utc: float | None
    permalink: str
    url: str | None
    raw_path: str


@dataclass(frozen=True)
class NormalizedComment:
    """Normalized comment record used by downstream storage and chunking."""

    id: str
    reddit_id: str
    post_reddit_id: str
    parent_reddit_id: str
    subreddit: str
    body: str
    author: str | None
    score: int
    created_utc: float | None
    permalink: str
    raw_path: str


def normalize_submission_payload(raw_submission: dict[str, Any], raw_path: str) -> NormalizedPost:
    """Convert a Reddit JSON submission payload into a normalized post record."""
    data = _unwrap_thing_data(raw_submission)
    reddit_id = _required_string(data, "id")
    return NormalizedPost(
        id=f"post_{reddit_id}",
        reddit_id=reddit_id,
        subreddit=_required_string(data, "subreddit"),
        title=_string_or_empty(data.get("title")),
        body=_clean_body(data.get("selftext")),
        author=_normalize_author(data.get("author")),
        score=_int_or_zero(data.get("score")),
        num_comments=_int_or_zero(data.get("num_comments")),
        created_utc=_float_or_none(data.get("created_utc")),
        permalink=_string_or_empty(data.get("permalink")),
        url=_string_or_none(data.get("url")),
        raw_path=raw_path,
    )


def normalize_comment_payload(raw_comment: dict[str, Any], raw_path: str) -> NormalizedComment:
    """Convert a Reddit JSON comment payload into a normalized comment record."""
    data = _unwrap_thing_data(raw_comment)
    reddit_id = _required_string(data, "id")
    parent_reddit_id = _strip_kind_prefix(_required_string(data, "parent_id"))
    post_reddit_id = _strip_kind_prefix(_required_string(data, "link_id"))
    return NormalizedComment(
        id=f"comment_{reddit_id}",
        reddit_id=reddit_id,
        post_reddit_id=post_reddit_id,
        parent_reddit_id=parent_reddit_id,
        subreddit=_required_string(data, "subreddit"),
        body=_clean_body(data.get("body")),
        author=_normalize_author(data.get("author")),
        score=_int_or_zero(data.get("score")),
        created_utc=_float_or_none(data.get("created_utc")),
        permalink=_string_or_empty(data.get("permalink")),
        raw_path=raw_path,
    )


def _unwrap_thing_data(value: dict[str, Any]) -> dict[str, Any]:
    """Accept either a Reddit thing or its inner data mapping."""
    data = value.get("data")
    if isinstance(data, dict):
        return data
    return value


def _required_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Missing required Reddit field: {key}")
    return value.strip()


def _string_or_empty(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _string_or_none(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    return text


def _clean_body(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    text = value.strip()
    if text in {"[deleted]", "[removed]"}:
        return ""
    return text


def _normalize_author(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    author = value.strip()
    if not author or author == "[deleted]":
        return None
    return author


def _int_or_zero(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return 0


def _float_or_none(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _strip_kind_prefix(value: str) -> str:
    if "_" in value:
        return value.split("_", 1)[1]
    return value
