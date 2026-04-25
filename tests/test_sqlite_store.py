"""Tests for SQLite metadata store."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from reddit_rag.storage.sqlite_store import SqliteStore


def _sample_post(**overrides: object) -> dict:
    base = {
        "id": "post_abc",
        "reddit_id": "abc",
        "subreddit": "learnpython",
        "title": "Hello",
        "body": "World",
        "author": "u1",
        "score": 5,
        "num_comments": 2,
        "created_utc": 1700000000.0,
        "permalink": "/r/learnpython/comments/abc/hello/",
        "url": None,
        "raw_path": "data/raw/learnpython/threads/abc.json",
    }
    base.update(overrides)
    return base


def _sample_comment(**overrides: object) -> dict:
    base = {
        "id": "comment_xyz",
        "reddit_id": "xyz",
        "post_reddit_id": "abc",
        "parent_reddit_id": "abc",
        "subreddit": "learnpython",
        "body": "Nice",
        "author": "u2",
        "score": 1,
        "created_utc": 1700000001.0,
        "permalink": "/r/learnpython/comments/abc/hello/xyz/",
        "raw_path": "data/raw/learnpython/threads/abc.json",
    }
    base.update(overrides)
    return base


def _sample_chunk(**overrides: object) -> dict:
    base = {
        "id": "chunk_v1_cs100_ov10_post_post_abc_0000",
        "source_type": "post",
        "source_id": "post_abc",
        "subreddit": "learnpython",
        "text": "Hello\n\nWorld",
        "metadata": {
            "reddit_id": "abc",
            "post_reddit_id": "abc",
            "title": "Hello",
            "score": 5,
            "created_utc": 1700000000.0,
            "chunk_index": 0,
            "chunk_size": 100,
            "chunk_overlap": 10,
        },
    }
    base.update(overrides)
    return base


class SqliteStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmp.name) / "test.sqlite"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_upsert_post_refreshes_on_conflict(self) -> None:
        with SqliteStore(self.db_path) as store:
            store.upsert_posts([_sample_post(title="First")])
            store.upsert_posts([_sample_post(title="Second")])
            row = store.get_post_by_reddit_id("abc")
            posts = list(store.iter_posts_by_subreddit("learnpython"))
        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(row["title"], "Second")
        self.assertEqual(posts, [row])

    def test_upsert_comments_and_query_by_post(self) -> None:
        with SqliteStore(self.db_path) as store:
            store.upsert_comments([_sample_comment(body="A")])
            store.upsert_comments([_sample_comment(body="B")])
            c = store.get_comment_by_reddit_id("xyz")
        self.assertIsNotNone(c)
        assert c is not None
        self.assertEqual(c["body"], "B")
        with SqliteStore(self.db_path) as store:
            on_post = list(store.iter_comments_for_post("abc"))
        self.assertEqual(len(on_post), 1)
        self.assertEqual(on_post[0]["reddit_id"], "xyz")

    def test_upsert_chunks_metadata_roundtrip(self) -> None:
        with SqliteStore(self.db_path) as store:
            store.upsert_chunks([_sample_chunk()])
            store.upsert_chunks([_sample_chunk(text="updated")])
            ch = store.get_chunk("chunk_v1_cs100_ov10_post_post_abc_0000")
        self.assertIsNotNone(ch)
        assert ch is not None
        self.assertEqual(ch["text"], "updated")
        self.assertEqual(ch["metadata"]["chunk_index"], 0)

    def test_ingestion_runs_and_latest_checkpoint(self) -> None:
        cp1 = {
            "subreddit": "learnpython",
            "after": "t1",
            "seen_post_names": ["a"],
            "fetched_thread_ids": ["x"],
            "comments_seen": 1,
            "updated_at": "2024-01-01T00:00:00+00:00",
        }
        cp2 = {
            "subreddit": "learnpython",
            "after": "t2",
            "seen_post_names": ["a", "b"],
            "fetched_thread_ids": ["x", "y"],
            "comments_seen": 3,
            "updated_at": "2024-01-02T00:00:00+00:00",
        }
        with SqliteStore(self.db_path) as store:
            store.record_ingestion_run(
                subreddit="learnpython",
                checkpoint=cp1,
                status="completed",
                stats={"posts_seen": 1},
            )
            store.record_ingestion_run(
                subreddit="learnpython",
                checkpoint=cp2,
                status="running",
                stats=None,
            )
            store.record_ingestion_run(
                subreddit="learnpython",
                checkpoint=cp2,
                status="completed",
                stats={"posts_seen": 2},
            )
            latest = store.get_latest_checkpoint("learnpython")
            runs = store.list_ingestion_runs("learnpython", limit=10)
        self.assertEqual(latest, cp2)
        self.assertEqual(len(runs), 3)
        self.assertEqual(runs[0]["status"], "completed")
        self.assertEqual(runs[0]["checkpoint"]["after"], "t2")

    def test_get_latest_checkpoint_none_when_no_completed(self) -> None:
        with SqliteStore(self.db_path) as store:
            store.record_ingestion_run(
                subreddit="x",
                checkpoint={"subreddit": "x", "after": None, "seen_post_names": [], "fetched_thread_ids": [], "comments_seen": 0},
                status="running",
            )
            latest = store.get_latest_checkpoint("x")
        self.assertIsNone(latest)

    def test_unsupported_user_version_raises(self) -> None:
        import sqlite3

        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA user_version = 99")
        conn.commit()
        conn.close()
        with self.assertRaises(ValueError):
            SqliteStore(self.db_path)


if __name__ == "__main__":
    unittest.main()
