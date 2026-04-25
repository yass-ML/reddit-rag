"""Reddit API client placeholders.

Use official Reddit API access through PRAW (or a clean wrapper) only.
Do not scrape Reddit HTML and do not attempt to bypass rate limits.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RedditClientSettings:
    """Runtime settings required to build a Reddit API client."""

    client_id: str
    client_secret: str
    user_agent: str


def create_reddit_client(_settings: RedditClientSettings) -> Any:
    """Create and return a configured Reddit API client.

    TODO:
    - Wire this to PRAW once ingestion work begins.
    - Keep request behavior compliant with Reddit API terms and limits.
    """
    raise NotImplementedError("PRAW client creation is not implemented yet.")


def fetch_subreddit_stream(
    _client: Any,
    _subreddit_name: str,
    _max_posts: int | None = None,
    _max_comments: int | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Fetch post/comment payloads for a configured subreddit.

    TODO:
    - Define stable payload shape for downstream normalization.
    - Add checkpoint/resume behavior in a later phase.
    """
    raise NotImplementedError("Subreddit ingestion is not implemented yet.")
