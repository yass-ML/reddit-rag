from __future__ import annotations

import os
from typing import Final

from reddit_rag.ingestion.reddit_source import JsonRedditSourceSettings
from reddit_rag.paths import resolve_project_root

REDDIT_CLIENT_ID: Final = "REDDIT_CLIENT_ID"
REDDIT_CLIENT_SECRET: Final = "REDDIT_CLIENT_SECRET"
REDDIT_OAUTH_TOKEN: Final = "REDDIT_OAUTH_TOKEN"
REDDIT_USER_AGENT: Final = "REDDIT_USER_AGENT"
REDDIT_RAG_REDDIT_SOURCE: Final = "REDDIT_RAG_REDDIT_SOURCE"

REQUIRED_REDDIT_JSON_ENV: Final = (
    REDDIT_USER_AGENT,
)
REQUIRED_REDDIT_JSON_OAUTH_ENV: Final = (
    REDDIT_USER_AGENT,
    REDDIT_OAUTH_TOKEN,
)
SUPPORTED_REDDIT_SOURCES: Final = ("json", "json_oauth")

# Kept as the public "required env" contract for the default JSON source.
REQUIRED_REDDIT_ENV: Final = REQUIRED_REDDIT_JSON_ENV


def load_dotenv_from_project() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(resolve_project_root() / ".env", override=False)


def reddit_source_mode() -> str:
    """Return the configured Reddit source mode."""
    mode = os.environ.get(REDDIT_RAG_REDDIT_SOURCE, "json").strip().lower()
    if not mode:
        return "json"
    return mode


def missing_reddit_env() -> list[str]:
    """Return names of required Reddit source variables that are missing or empty."""
    mode = reddit_source_mode()
    required = REQUIRED_REDDIT_JSON_OAUTH_ENV if mode == "json_oauth" else REQUIRED_REDDIT_JSON_ENV
    missing: list[str] = []
    for key in required:
        val = os.environ.get(key)
        if val is None or not str(val).strip():
            missing.append(key)
    return missing


def load_reddit_source_settings_from_env() -> JsonRedditSourceSettings:
    """Build direct JSON source settings from environment variables."""
    mode = reddit_source_mode()
    if mode not in SUPPORTED_REDDIT_SOURCES:
        supported = ", ".join(SUPPORTED_REDDIT_SOURCES)
        raise ValueError(f"Unsupported {REDDIT_RAG_REDDIT_SOURCE}={mode!r}. Supported values: {supported}.")

    missing = missing_reddit_env()
    if missing:
        missing_fmt = ", ".join(missing)
        raise ValueError(f"Missing required Reddit source environment variables: {missing_fmt}")

    oauth_token = os.environ.get(REDDIT_OAUTH_TOKEN, "").strip() if mode == "json_oauth" else None
    return JsonRedditSourceSettings(
        user_agent=os.environ.get(REDDIT_USER_AGENT, "").strip(),
        oauth_token=oauth_token or None,
    )
