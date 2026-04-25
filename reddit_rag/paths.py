from __future__ import annotations

import os
from pathlib import Path


def resolve_config_dir() -> Path:
    """Return the directory containing subreddits.yaml and models.yaml."""
    env = os.environ.get("REDDIT_RAG_CONFIG_DIR")
    if env:
        return Path(env).expanduser().resolve()
    return (Path.cwd() / "config").resolve()
