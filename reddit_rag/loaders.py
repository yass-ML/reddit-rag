from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from reddit_rag.config import AppConfig, ModelsConfig, SubredditEntry, SubredditsConfig

SUBREDDITS_FILENAME = "subreddits.yaml"
MODELS_FILENAME = "models.yaml"


def _require_mapping(data: Any, path: Path, label: str) -> dict[str, Any]:
    if data is None:
        raise ValueError(f"{label}: empty file {path}")
    if not isinstance(data, dict):
        raise ValueError(f"{label}: root must be a mapping, got {type(data).__name__} in {path}")
    return data


def _is_strict_int(value: Any) -> bool:
    """True for int but not bool (bool subclasses int in Python)."""
    return isinstance(value, int) and not isinstance(value, bool)


def load_subreddits(path: Path) -> SubredditsConfig:
    if not path.is_file():
        raise FileNotFoundError(f"Subreddits config not found: {path}")

    with path.open(encoding="utf-8") as f:
        try:
            raw = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {path}: {e}") from e

    data = _require_mapping(raw, path, "subreddits")
    items = data.get("subreddits")
    if items is None:
        raise ValueError(f"subreddits: missing required key 'subreddits' in {path}")
    if not isinstance(items, list):
        raise ValueError(f"subreddits: 'subreddits' must be a list in {path}")

    entries: list[SubredditEntry] = []
    for i, item in enumerate(items):
        loc = f"{path} (subreddits[{i}])"
        if not isinstance(item, dict):
            raise ValueError(f"{loc}: expected mapping, got {type(item).__name__}")
        name = item.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"{loc}: 'name' must be a non-empty string")

        max_posts = item.get("max_posts")
        if max_posts is not None and not _is_strict_int(max_posts):
            raise ValueError(f"{loc}: 'max_posts' must be an integer or omitted")
        if _is_strict_int(max_posts) and max_posts < 0:
            raise ValueError(f"{loc}: 'max_posts' must be >= 0")

        max_comments = item.get("max_comments")
        if max_comments is not None and not _is_strict_int(max_comments):
            raise ValueError(f"{loc}: 'max_comments' must be an integer or omitted")
        if _is_strict_int(max_comments) and max_comments < 0:
            raise ValueError(f"{loc}: 'max_comments' must be >= 0")

        extra = set(item.keys()) - {"name", "max_posts", "max_comments"}
        if extra:
            raise ValueError(f"{loc}: unknown keys: {sorted(extra)}")

        entries.append(
            SubredditEntry(
                name=name.strip(),
                max_posts=max_posts,
                max_comments=max_comments,
            )
        )

    return SubredditsConfig(subreddits=entries)


def load_models(path: Path) -> ModelsConfig:
    if not path.is_file():
        raise FileNotFoundError(f"Models config not found: {path}")

    with path.open(encoding="utf-8") as f:
        try:
            raw = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {path}: {e}") from e

    data = _require_mapping(raw, path, "models")
    emb = data.get("embedding_model")
    chat = data.get("chat_model")
    if not isinstance(emb, str) or not emb.strip():
        raise ValueError(f"models: 'embedding_model' must be a non-empty string in {path}")
    if not isinstance(chat, str) or not chat.strip():
        raise ValueError(f"models: 'chat_model' must be a non-empty string in {path}")

    extra = set(data.keys()) - {"embedding_model", "chat_model"}
    if extra:
        raise ValueError(f"models: unknown keys in {path}: {sorted(extra)}")

    return ModelsConfig(embedding_model=emb.strip(), chat_model=chat.strip())


def load_app_config(config_dir: Path) -> AppConfig:
    config_dir = config_dir.resolve()
    sub_path = config_dir / SUBREDDITS_FILENAME
    models_path = config_dir / MODELS_FILENAME
    return AppConfig(
        subreddits=load_subreddits(sub_path),
        models=load_models(models_path),
    )
