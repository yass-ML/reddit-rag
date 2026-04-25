"""Normalize raw Reddit payloads into local typed records.

Target contracts are documented in memory/data_contracts.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class NormalizedPost:
    """Placeholder normalized post record."""

    id: str
    reddit_id: str
    subreddit: str
    title: str
    body: str
    permalink: str


@dataclass(frozen=True)
class NormalizedComment:
    """Placeholder normalized comment record."""

    id: str
    reddit_id: str
    post_reddit_id: str
    subreddit: str
    body: str
    permalink: str


def normalize_submission_payload(_raw_submission: dict[str, Any], _raw_path: str) -> NormalizedPost:
    """Convert a raw submission payload into a normalized post record.

    TODO:
    - Map all required fields from data_contracts.md.
    - Handle deleted/removed text consistently.
    """
    raise NotImplementedError("Submission normalization is not implemented yet.")


def normalize_comment_payload(_raw_comment: dict[str, Any], _raw_path: str) -> NormalizedComment:
    """Convert a raw comment payload into a normalized comment record.

    TODO:
    - Map parent references and timestamps from raw payload.
    - Normalize author/permalink fields consistently.
    """
    raise NotImplementedError("Comment normalization is not implemented yet.")
