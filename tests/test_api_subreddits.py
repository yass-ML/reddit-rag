from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from reddit_rag.api.app import create_app
from reddit_rag.paths import resolve_project_root


class ApiSubredditsMutationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        cfg_src = resolve_project_root() / "config"
        dst = Path(self._dir.name)
        shutil.copy(cfg_src / "subreddits.yaml", dst / "subreddits.yaml")
        shutil.copy(cfg_src / "models.yaml", dst / "models.yaml")
        self._prev = os.environ.get("REDDIT_RAG_CONFIG_DIR")
        os.environ["REDDIT_RAG_CONFIG_DIR"] = str(dst)

    def tearDown(self) -> None:
        if self._prev is None:
            os.environ.pop("REDDIT_RAG_CONFIG_DIR", None)
        else:
            os.environ["REDDIT_RAG_CONFIG_DIR"] = self._prev

    def test_post_appends_and_duplicate_is_409(self) -> None:
        client = TestClient(create_app())
        before = client.get("/api/subreddits")
        self.assertEqual(before.status_code, 200)
        n_before = len(before.json())

        r = client.post(
            "/api/subreddits",
            json={"name": "NewSubXYZ", "max_posts": 5, "max_comments": 10},
        )
        self.assertEqual(r.status_code, 200, r.text)
        data = r.json()
        self.assertEqual(len(data), n_before + 1)
        names = {x["name"] for x in data}
        self.assertIn("NewSubXYZ", names)

        dup = client.post(
            "/api/subreddits",
            json={"name": "newsubxyz", "max_posts": 1, "max_comments": 2},
        )
        self.assertEqual(dup.status_code, 409)
        self.assertEqual(dup.json()["error"]["code"], "subreddit_exists")

    def test_delete_removes_and_allows_empty_list(self) -> None:
        client = TestClient(create_app())
        # Start from known file with multiple entries
        full = client.get("/api/subreddits")
        self.assertEqual(full.status_code, 200)
        names = [x["name"] for x in full.json()]
        self.assertGreaterEqual(len(names), 1)

        for nm in list(names):
            d = client.delete(f"/api/subreddits/{nm}")
            self.assertEqual(d.status_code, 200, d.text)

        empty = client.get("/api/subreddits")
        self.assertEqual(empty.status_code, 200)
        self.assertEqual(empty.json(), [])

        missing = client.delete("/api/subreddits/NoSuchSubreddit")
        self.assertEqual(missing.status_code, 404)
