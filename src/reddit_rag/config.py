from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SubredditEntry:
    name: str
    max_posts: int | None = None
    max_comments: int | None = None


@dataclass(frozen=True)
class SubredditsConfig:
    subreddits: list[SubredditEntry]


@dataclass(frozen=True)
class ModelsConfig:
    embedding_model: str
    chat_model: str


@dataclass(frozen=True)
class AppConfig:
    subreddits: SubredditsConfig
    models: ModelsConfig
