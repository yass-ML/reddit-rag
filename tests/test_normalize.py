from __future__ import annotations

import json
import unittest
from copy import deepcopy
from pathlib import Path

from reddit_rag.processing.normalize import normalize_comment_payload, normalize_submission_payload


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "reddit_thread.json"


class NormalizeRedditJsonTests(unittest.TestCase):
    def setUp(self) -> None:
        with FIXTURE_PATH.open(encoding="utf-8") as f:
            self.raw = json.load(f)
        payload = self.raw["payload"]
        self.post_thing = payload[0]["data"]["children"][0]
        self.comment_thing = payload[1]["data"]["children"][0]
        self.deleted_comment_thing = payload[1]["data"]["children"][1]

    def test_normalizes_submission_payload(self) -> None:
        post = normalize_submission_payload(self.post_thing, str(FIXTURE_PATH))

        self.assertEqual(post.id, "post_abc123")
        self.assertEqual(post.reddit_id, "abc123")
        self.assertEqual(post.subreddit, "example")
        self.assertEqual(post.title, "Example title")
        self.assertEqual(post.body, "Post body")
        self.assertEqual(post.author, "example_author")
        self.assertEqual(post.score, 42)
        self.assertEqual(post.num_comments, 2)
        self.assertEqual(post.created_utc, 1713980000.0)
        self.assertEqual(post.permalink, "/r/example/comments/abc123/example_title/")
        self.assertEqual(post.raw_path, str(FIXTURE_PATH))

    def test_normalizes_comment_payload(self) -> None:
        comment = normalize_comment_payload(self.comment_thing, str(FIXTURE_PATH))

        self.assertEqual(comment.id, "comment_def456")
        self.assertEqual(comment.reddit_id, "def456")
        self.assertEqual(comment.post_reddit_id, "abc123")
        self.assertEqual(comment.parent_reddit_id, "abc123")
        self.assertEqual(comment.subreddit, "example")
        self.assertEqual(comment.body, "First comment")
        self.assertEqual(comment.author, "comment_author")
        self.assertEqual(comment.score, 7)
        self.assertEqual(comment.created_utc, 1713981000.0)
        self.assertEqual(comment.permalink, "/r/example/comments/abc123/example_title/def456/")

    def test_deleted_comment_content_is_empty_and_authorless(self) -> None:
        comment = normalize_comment_payload(self.deleted_comment_thing, str(FIXTURE_PATH))

        self.assertEqual(comment.body, "")
        self.assertIsNone(comment.author)
        self.assertEqual(comment.parent_reddit_id, "def456")

    def test_submission_url_is_stripped_when_present(self) -> None:
        post_thing = deepcopy(self.post_thing)
        post_thing["data"]["url"] = "  https://example.com/path  "

        post = normalize_submission_payload(post_thing, str(FIXTURE_PATH))

        self.assertEqual(post.url, "https://example.com/path")


if __name__ == "__main__":
    unittest.main()
