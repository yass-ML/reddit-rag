from __future__ import annotations

import os
from typing import Final

from reddit_rag.paths import resolve_project_root

REDDIT_CLIENT_ID: Final = "REDDIT_CLIENT_ID"
REDDIT_CLIENT_SECRET: Final = "REDDIT_CLIENT_SECRET"
REDDIT_USER_AGENT: Final = "REDDIT_USER_AGENT"

REQUIRED_REDDIT_ENV: Final = (
    REDDIT_CLIENT_ID,
    REDDIT_CLIENT_SECRET,
    REDDIT_USER_AGENT,
)


def load_dotenv_from_project() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(resolve_project_root() / ".env", override=False)


def missing_reddit_env() -> list[str]:
    """Return names of required Reddit/PRAW variables that are missing or empty."""
    missing: list[str] = []
    for key in REQUIRED_REDDIT_ENV:
        val = os.environ.get(key)
        if val is None or not str(val).strip():
            missing.append(key)
    return missing
