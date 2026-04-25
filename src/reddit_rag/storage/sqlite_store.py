"""SQLite metadata store for normalized posts, comments, chunks, and ingestion runs."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

from reddit_rag.processing.chunks_io import chunk_record_dedupe_key
from reddit_rag.processing.comments import comment_record_dedupe_key
from reddit_rag.processing.posts import post_record_dedupe_key

SCHEMA_USER_VERSION = 1


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS posts (
            reddit_id TEXT PRIMARY KEY NOT NULL,
            id TEXT NOT NULL,
            subreddit TEXT NOT NULL,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            author TEXT,
            score INTEGER NOT NULL,
            num_comments INTEGER NOT NULL,
            created_utc REAL,
            permalink TEXT NOT NULL,
            url TEXT,
            raw_path TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_posts_subreddit ON posts (subreddit);

        CREATE TABLE IF NOT EXISTS comments (
            reddit_id TEXT PRIMARY KEY NOT NULL,
            id TEXT NOT NULL,
            post_reddit_id TEXT NOT NULL,
            parent_reddit_id TEXT NOT NULL,
            subreddit TEXT NOT NULL,
            body TEXT NOT NULL,
            author TEXT,
            score INTEGER NOT NULL,
            created_utc REAL,
            permalink TEXT NOT NULL,
            raw_path TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_comments_subreddit ON comments (subreddit);
        CREATE INDEX IF NOT EXISTS idx_comments_post_reddit_id ON comments (post_reddit_id);

        CREATE TABLE IF NOT EXISTS chunks (
            id TEXT PRIMARY KEY NOT NULL,
            source_type TEXT NOT NULL,
            source_id TEXT NOT NULL,
            subreddit TEXT NOT NULL,
            text TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_chunks_subreddit ON chunks (subreddit);

        CREATE TABLE IF NOT EXISTS ingestion_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subreddit TEXT NOT NULL,
            started_at TEXT,
            completed_at TEXT,
            status TEXT NOT NULL,
            stats_json TEXT,
            checkpoint_json TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_ingestion_runs_subreddit_id
            ON ingestion_runs (subreddit, id);
        """
    )
    # PRAGMA user_version does not accept bound parameters in all SQLite builds.
    conn.execute(f"PRAGMA user_version = {int(SCHEMA_USER_VERSION)}")
    conn.commit()


@dataclass(frozen=True)
class UpsertSummary:
    """Counts from a batch upsert."""

    processed: int


def _require_str(rec: dict[str, Any], key: str, *, label: str) -> str:
    v = rec.get(key)
    if not isinstance(v, str):
        raise ValueError(f"{label}: missing or invalid string field {key!r}")
    return v


def _optional_str(rec: dict[str, Any], key: str) -> str | None:
    v = rec.get(key)
    if v is None:
        return None
    if not isinstance(v, str):
        return None
    s = v.strip()
    return s or None


def _int_field(rec: dict[str, Any], key: str, default: int = 0) -> int:
    v = rec.get(key)
    if isinstance(v, bool):
        return default
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v)
    return default


def _optional_float(rec: dict[str, Any], key: str) -> float | None:
    v = rec.get(key)
    if v is None:
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    return None


def _post_tuple(rec: dict[str, Any], updated_at: str) -> tuple[Any, ...]:
    label = "post record"
    post_record_dedupe_key(rec)
    return (
        _require_str(rec, "reddit_id", label=label),
        _require_str(rec, "id", label=label),
        _require_str(rec, "subreddit", label=label),
        _require_str(rec, "title", label=label),
        _require_str(rec, "body", label=label),
        _optional_str(rec, "author"),
        _int_field(rec, "score"),
        _int_field(rec, "num_comments"),
        _optional_float(rec, "created_utc"),
        _require_str(rec, "permalink", label=label),
        _optional_str(rec, "url"),
        _require_str(rec, "raw_path", label=label),
        updated_at,
    )


def _comment_tuple(rec: dict[str, Any], updated_at: str) -> tuple[Any, ...]:
    label = "comment record"
    comment_record_dedupe_key(rec)
    return (
        _require_str(rec, "reddit_id", label=label),
        _require_str(rec, "id", label=label),
        _require_str(rec, "post_reddit_id", label=label),
        _require_str(rec, "parent_reddit_id", label=label),
        _require_str(rec, "subreddit", label=label),
        _require_str(rec, "body", label=label),
        _optional_str(rec, "author"),
        _int_field(rec, "score"),
        _optional_float(rec, "created_utc"),
        _require_str(rec, "permalink", label=label),
        _require_str(rec, "raw_path", label=label),
        updated_at,
    )


def _chunk_tuple(rec: dict[str, Any], updated_at: str) -> tuple[Any, ...]:
    label = "chunk record"
    chunk_record_dedupe_key(rec)
    meta = rec.get("metadata")
    if not isinstance(meta, dict):
        raise ValueError(f"{label}: 'metadata' must be a dict")
    return (
        _require_str(rec, "id", label=label),
        _require_str(rec, "source_type", label=label),
        _require_str(rec, "source_id", label=label),
        _require_str(rec, "subreddit", label=label),
        _require_str(rec, "text", label=label),
        json.dumps(meta, ensure_ascii=False, sort_keys=True),
        updated_at,
    )


def _row_to_post(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    d.pop("updated_at", None)
    return d


def _row_to_comment(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    d.pop("updated_at", None)
    return d


def _row_to_chunk(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    meta_raw = d.pop("metadata_json", "{}")
    d["metadata"] = json.loads(meta_raw) if isinstance(meta_raw, str) else {}
    d.pop("updated_at", None)
    return d


class SqliteStore:
    """Local SQLite-backed metadata for posts, comments, chunks, and ingestion checkpoints."""

    def __init__(self, db_path: Path | None = None) -> None:
        from reddit_rag.paths import resolve_sqlite_path

        self._path = (db_path or resolve_sqlite_path()).resolve()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        ver = int(self._conn.execute("PRAGMA user_version").fetchone()[0])
        if ver == 0:
            _ensure_schema(self._conn)
        elif ver != SCHEMA_USER_VERSION:
            raise ValueError(
                f"Unsupported SQLite schema user_version={ver} at {self._path}; "
                f"expected {SCHEMA_USER_VERSION}. Remove or migrate the database file."
            )

    @property
    def path(self) -> Path:
        return self._path

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> SqliteStore:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def upsert_posts(self, records: list[dict[str, Any]]) -> UpsertSummary:
        """Insert or replace posts by ``reddit_id`` (refreshes row on conflict)."""
        if not records:
            return UpsertSummary(processed=0)
        ts = _now_iso()
        sql = """
            INSERT INTO posts (
                reddit_id, id, subreddit, title, body, author, score, num_comments,
                created_utc, permalink, url, raw_path, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(reddit_id) DO UPDATE SET
                id = excluded.id,
                subreddit = excluded.subreddit,
                title = excluded.title,
                body = excluded.body,
                author = excluded.author,
                score = excluded.score,
                num_comments = excluded.num_comments,
                created_utc = excluded.created_utc,
                permalink = excluded.permalink,
                url = excluded.url,
                raw_path = excluded.raw_path,
                updated_at = excluded.updated_at
        """
        for rec in records:
            self._conn.execute(sql, _post_tuple(rec, ts))
        self._conn.commit()
        return UpsertSummary(processed=len(records))

    def upsert_comments(self, records: list[dict[str, Any]]) -> UpsertSummary:
        """Insert or replace comments by ``reddit_id``."""
        if not records:
            return UpsertSummary(processed=0)
        ts = _now_iso()
        sql = """
            INSERT INTO comments (
                reddit_id, id, post_reddit_id, parent_reddit_id, subreddit, body,
                author, score, created_utc, permalink, raw_path, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(reddit_id) DO UPDATE SET
                id = excluded.id,
                post_reddit_id = excluded.post_reddit_id,
                parent_reddit_id = excluded.parent_reddit_id,
                subreddit = excluded.subreddit,
                body = excluded.body,
                author = excluded.author,
                score = excluded.score,
                created_utc = excluded.created_utc,
                permalink = excluded.permalink,
                raw_path = excluded.raw_path,
                updated_at = excluded.updated_at
        """
        for rec in records:
            self._conn.execute(sql, _comment_tuple(rec, ts))
        self._conn.commit()
        return UpsertSummary(processed=len(records))

    def upsert_chunks(self, records: list[dict[str, Any]]) -> UpsertSummary:
        """Insert or replace chunks by chunk ``id``."""
        if not records:
            return UpsertSummary(processed=0)
        ts = _now_iso()
        sql = """
            INSERT INTO chunks (
                id, source_type, source_id, subreddit, text, metadata_json, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                source_type = excluded.source_type,
                source_id = excluded.source_id,
                subreddit = excluded.subreddit,
                text = excluded.text,
                metadata_json = excluded.metadata_json,
                updated_at = excluded.updated_at
        """
        for rec in records:
            self._conn.execute(sql, _chunk_tuple(rec, ts))
        self._conn.commit()
        return UpsertSummary(processed=len(records))

    def record_ingestion_run(
        self,
        *,
        subreddit: str,
        checkpoint: dict[str, Any],
        status: str,
        stats: dict[str, Any] | None = None,
        started_at: str | None = None,
        completed_at: str | None = None,
    ) -> int:
        """Append one ingestion run row. Returns the new row ``id``."""
        if not subreddit.strip():
            raise ValueError("subreddit must be non-empty")
        cur = self._conn.execute(
            """
            INSERT INTO ingestion_runs (
                subreddit, started_at, completed_at, status, stats_json, checkpoint_json
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                subreddit.strip(),
                started_at,
                completed_at,
                status,
                json.dumps(stats, ensure_ascii=False, sort_keys=True) if stats is not None else None,
                json.dumps(checkpoint, ensure_ascii=False, sort_keys=True),
            ),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def get_post_by_reddit_id(self, reddit_id: str) -> dict[str, Any] | None:
        cur = self._conn.execute("SELECT * FROM posts WHERE reddit_id = ?", (reddit_id.strip(),))
        row = cur.fetchone()
        return _row_to_post(row) if row else None

    def iter_posts_by_subreddit(
        self,
        subreddit: str,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> Iterator[dict[str, Any]]:
        sub = subreddit.strip()
        if limit is None:
            cur = self._conn.execute(
                "SELECT * FROM posts WHERE subreddit = ? ORDER BY reddit_id",
                (sub,),
            )
        else:
            cur = self._conn.execute(
                "SELECT * FROM posts WHERE subreddit = ? ORDER BY reddit_id LIMIT ? OFFSET ?",
                (sub, limit, offset),
            )
        yield from (_row_to_post(r) for r in cur)

    def get_comment_by_reddit_id(self, reddit_id: str) -> dict[str, Any] | None:
        cur = self._conn.execute("SELECT * FROM comments WHERE reddit_id = ?", (reddit_id.strip(),))
        row = cur.fetchone()
        return _row_to_comment(row) if row else None

    def iter_comments_by_subreddit(
        self,
        subreddit: str,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> Iterator[dict[str, Any]]:
        sub = subreddit.strip()
        if limit is None:
            cur = self._conn.execute(
                "SELECT * FROM comments WHERE subreddit = ? ORDER BY reddit_id",
                (sub,),
            )
        else:
            cur = self._conn.execute(
                "SELECT * FROM comments WHERE subreddit = ? ORDER BY reddit_id LIMIT ? OFFSET ?",
                (sub, limit, offset),
            )
        yield from (_row_to_comment(r) for r in cur)

    def iter_comments_for_post(
        self,
        post_reddit_id: str,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> Iterator[dict[str, Any]]:
        pid = post_reddit_id.strip()
        if limit is None:
            cur = self._conn.execute(
                "SELECT * FROM comments WHERE post_reddit_id = ? ORDER BY reddit_id",
                (pid,),
            )
        else:
            cur = self._conn.execute(
                "SELECT * FROM comments WHERE post_reddit_id = ? ORDER BY reddit_id LIMIT ? OFFSET ?",
                (pid, limit, offset),
            )
        yield from (_row_to_comment(r) for r in cur)

    def get_chunk(self, chunk_id: str) -> dict[str, Any] | None:
        cur = self._conn.execute("SELECT * FROM chunks WHERE id = ?", (chunk_id.strip(),))
        row = cur.fetchone()
        return _row_to_chunk(row) if row else None

    def iter_chunks_by_subreddit(
        self,
        subreddit: str,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> Iterator[dict[str, Any]]:
        sub = subreddit.strip()
        if limit is None:
            cur = self._conn.execute(
                "SELECT * FROM chunks WHERE subreddit = ? ORDER BY id",
                (sub,),
            )
        else:
            cur = self._conn.execute(
                "SELECT * FROM chunks WHERE subreddit = ? ORDER BY id LIMIT ? OFFSET ?",
                (sub, limit, offset),
            )
        yield from (_row_to_chunk(r) for r in cur)

    def list_ingestion_runs(self, subreddit: str, *, limit: int | None = 50) -> list[dict[str, Any]]:
        sub = subreddit.strip()
        if limit is None:
            cur = self._conn.execute(
                "SELECT id, subreddit, started_at, completed_at, status, stats_json, checkpoint_json "
                "FROM ingestion_runs WHERE subreddit = ? ORDER BY id DESC",
                (sub,),
            )
        else:
            cur = self._conn.execute(
                "SELECT id, subreddit, started_at, completed_at, status, stats_json, checkpoint_json "
                "FROM ingestion_runs WHERE subreddit = ? ORDER BY id DESC LIMIT ?",
                (sub, limit),
            )
        out: list[dict[str, Any]] = []
        for row in cur:
            d = {
                "id": row["id"],
                "subreddit": row["subreddit"],
                "started_at": row["started_at"],
                "completed_at": row["completed_at"],
                "status": row["status"],
                "stats": json.loads(row["stats_json"]) if row["stats_json"] else None,
                "checkpoint": json.loads(row["checkpoint_json"]),
            }
            out.append(d)
        return out

    def get_latest_checkpoint(self, subreddit: str) -> dict[str, Any] | None:
        """Return checkpoint dict from the latest *completed* run, or ``None``."""
        cur = self._conn.execute(
            """
            SELECT checkpoint_json FROM ingestion_runs
            WHERE subreddit = ? AND status = ?
            ORDER BY id DESC LIMIT 1
            """,
            (subreddit.strip(), "completed"),
        )
        row = cur.fetchone()
        if not row:
            return None
        return json.loads(row["checkpoint_json"])
