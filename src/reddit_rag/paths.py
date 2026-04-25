from __future__ import annotations

import os
from pathlib import Path


def resolve_project_root() -> Path:
    """Repository root (directory containing ``src/`` and ``config/``)."""
    return Path(__file__).resolve().parent.parent.parent


def resolve_config_dir() -> Path:
    """Return the directory containing subreddits.yaml and models.yaml."""
    env = os.environ.get("REDDIT_RAG_CONFIG_DIR")
    if env:
        return Path(env).expanduser().resolve()
    return (Path.cwd() / "config").resolve()


def resolve_query_templates_dir(config_dir: Path | None = None) -> Path:
    """Directory containing editable ``*.md`` query templates (YAML front matter + body)."""
    env = os.environ.get("REDDIT_RAG_QUERY_TEMPLATES_DIR")
    if env:
        return Path(env).expanduser().resolve()
    base = config_dir if config_dir is not None else resolve_config_dir()
    return (Path(base) / "query_templates").resolve()


def resolve_data_root() -> Path:
    """Base directory for local data (raw, processed, chroma, exports)."""
    env = os.environ.get("REDDIT_RAG_DATA_DIR")
    if env:
        return Path(env).expanduser().resolve()
    return (resolve_project_root() / "data").resolve()


def _resolve_data_subpath(name: str, env_key: str) -> Path:
    """Resolve a data subdirectory, with optional per-stage override."""
    override = os.environ.get(env_key)
    if override:
        return Path(override).expanduser().resolve()
    return (resolve_data_root() / name).resolve()


def resolve_raw_dir() -> Path:
    return _resolve_data_subpath("raw", "REDDIT_RAG_RAW_DIR")


def resolve_processed_dir() -> Path:
    return _resolve_data_subpath("processed", "REDDIT_RAG_PROCESSED_DIR")


def resolve_chroma_dir() -> Path:
    return _resolve_data_subpath("chroma", "REDDIT_RAG_CHROMA_DIR")


def resolve_exports_dir() -> Path:
    return _resolve_data_subpath("exports", "REDDIT_RAG_EXPORTS_DIR")


def resolve_sqlite_path() -> Path:
    """Default SQLite database path for normalized metadata and ingestion runs."""
    env = os.environ.get("REDDIT_RAG_SQLITE_PATH")
    if env:
        return Path(env).expanduser().resolve()
    return (resolve_data_root() / "reddit_rag.sqlite").resolve()
