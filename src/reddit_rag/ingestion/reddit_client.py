"""Reddit API client placeholders.

Use official Reddit API access through PRAW (or a clean wrapper) only.
Do not scrape Reddit HTML and do not attempt to bypass rate limits.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from reddit_rag.env import (
    REDDIT_CLIENT_ID,
    REDDIT_CLIENT_SECRET,
    REDDIT_USER_AGENT,
)


@dataclass(frozen=True)
class RedditClientSettings:
    """Runtime settings required to build a Reddit API client."""

    client_id: str
    client_secret: str
    user_agent: str


def load_reddit_client_settings_from_env() -> RedditClientSettings:
    """Build validated client settings from environment variables."""
    values = {
        REDDIT_CLIENT_ID: os.environ.get(REDDIT_CLIENT_ID, "").strip(),
        REDDIT_CLIENT_SECRET: os.environ.get(REDDIT_CLIENT_SECRET, "").strip(),
        REDDIT_USER_AGENT: os.environ.get(REDDIT_USER_AGENT, "").strip(),
    }
    missing = [name for name, value in values.items() if not value]
    if missing:
        missing_fmt = ", ".join(missing)
        raise ValueError(f"Missing required Reddit client environment variables: {missing_fmt}")

    return RedditClientSettings(
        client_id=values[REDDIT_CLIENT_ID],
        client_secret=values[REDDIT_CLIENT_SECRET],
        user_agent=values[REDDIT_USER_AGENT],
    )


def create_reddit_client(settings: RedditClientSettings) -> Any:
    """Create and return a configured Reddit API client."""
    import praw

    return praw.Reddit(
        client_id=settings.client_id,
        client_secret=settings.client_secret,
        user_agent=settings.user_agent,
    )


def smoke_test_reddit_client(client: Any, subreddit_name: str = "redditdev") -> str:
    """Perform a small read-only API request to verify connectivity."""
    subreddit = client.subreddit(subreddit_name)
    # Force an API call by reading a lazily-fetched attribute.
    return str(subreddit.display_name)


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
