"""Compatibility helpers for the Reddit JSON source.

The implementation uses structured JSON responses for public content. It does
not scrape Reddit HTML or attempt to bypass rate limits.
"""

from __future__ import annotations

from reddit_rag.env import load_reddit_source_settings_from_env
from reddit_rag.ingestion.raw_ingestion import fetch_subreddit_stream
from reddit_rag.ingestion.reddit_source import (
    JsonRedditSource,
    JsonRedditSourceSettings,
    RedditSource,
)


RedditClientSettings = JsonRedditSourceSettings


def load_reddit_client_settings_from_env() -> RedditClientSettings:
    """Build direct JSON source settings from environment variables."""
    return load_reddit_source_settings_from_env()


def create_reddit_client(settings: RedditClientSettings) -> RedditSource:
    """Create and return a configured Reddit JSON source."""
    return JsonRedditSource(settings)


def smoke_test_reddit_client(client: RedditSource, subreddit_name: str = "redditdev") -> str:
    """Perform a small read-only JSON request to verify connectivity."""
    response = client.fetch_subreddit_listing(subreddit_name, limit=1)
    data = response.payload.get("data") if isinstance(response.payload, dict) else None
    if not isinstance(data, dict):
        raise ValueError("Unexpected Reddit listing payload shape.")
    children = data.get("children")
    if not isinstance(children, list):
        raise ValueError("Unexpected Reddit listing children shape.")
    return subreddit_name


__all__ = [
    "RedditClientSettings",
    "create_reddit_client",
    "fetch_subreddit_stream",
    "load_reddit_client_settings_from_env",
    "smoke_test_reddit_client",
]
