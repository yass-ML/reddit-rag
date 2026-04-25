from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from reddit_rag.processing.comments import (
    comment_record_dedupe_key,
    comment_record_to_dict,
    default_comments_jsonl_path,
    merge_comment_records_jsonl,
    normalize_comments_from_thread_file,
)
from reddit_rag.processing.normalize import normalize_comment_payload


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "reddit_thread.json"


def _comment_dict(reddit_id: str, body: str = "text") -> dict:
    return {
        "author": "u",
        "body": body,
        "created_utc": None,
        "id": f"comment_{reddit_id}",
        "parent_reddit_id": "p",
        "permalink": "/r/test/x",
        "post_reddit_id": "post1",
        "reddit_id": reddit_id,
        "raw_path": "/tmp/x.json",
        "score": 0,
        "subreddit": "testsub",
    }


class CommentRecordDedupeKeyTests(unittest.TestCase):
    def test_prefers_reddit_id(self) -> None:
        self.assertEqual(comment_record_dedupe_key({"reddit_id": "abc", "id": "comment_xyz"}), "abc")

    def test_falls_back_to_id(self) -> None:
        self.assertEqual(comment_record_dedupe_key({"id": "comment_only"}), "comment_only")

    def test_raises_when_missing_keys(self) -> None:
        with self.assertRaises(ValueError):
            comment_record_dedupe_key({"body": "x"})


class DefaultCommentsJsonlPathTests(unittest.TestCase):
    def test_safe_subfolder(self) -> None:
        root = Path("/data/processed")
        p = default_comments_jsonl_path(root, "Foo/Bar")
        self.assertEqual(p, Path("/data/processed/Foo-Bar/comments.jsonl"))


class MergeCommentRecordsJsonlTests(unittest.TestCase):
    def test_appends_new_preserves_order(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "comments.jsonl"
            seed = [_comment_dict("a", "first"), _comment_dict("b", "second")]
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8") as f:
                for row in seed:
                    f.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
                    f.write("\n")

            r = merge_comment_records_jsonl(path, [_comment_dict("b", "changed"), _comment_dict("c", "third")])

            self.assertEqual(r.existing_count, 2)
            self.assertEqual(r.appended, 1)
            self.assertEqual(r.skipped_duplicates, 1)
            self.assertEqual(r.total_after, 3)

            lines = path.read_text(encoding="utf-8").strip().split("\n")
            self.assertEqual(len(lines), 3)
            self.assertEqual(json.loads(lines[0])["reddit_id"], "a")
            self.assertEqual(json.loads(lines[1])["reddit_id"], "b")
            self.assertEqual(json.loads(lines[1])["body"], "second")
            self.assertEqual(json.loads(lines[2])["reddit_id"], "c")

    def test_skips_duplicate_within_new_batch(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "comments.jsonl"
            r = merge_comment_records_jsonl(
                path,
                [_comment_dict("x", "one"), _comment_dict("x", "two")],
            )
            self.assertEqual(r.appended, 1)
            self.assertEqual(r.skipped_duplicates, 1)
            self.assertEqual(r.total_after, 1)

    def test_invalid_json_raises(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "bad.jsonl"
            path.write_text("not json\n", encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                merge_comment_records_jsonl(path, [_comment_dict("z")])
            self.assertIn("Invalid JSON", str(ctx.exception))


class NormalizeCommentsFromThreadFileTests(unittest.TestCase):
    def setUp(self) -> None:
        with FIXTURE_PATH.open(encoding="utf-8") as f:
            self.raw = json.load(f)
        payload = self.raw["payload"]
        self.comment_thing = payload[1]["data"]["children"][0]
        self.deleted_comment_thing = payload[1]["data"]["children"][1]

    def test_matches_individual_normalization(self) -> None:
        comments = normalize_comments_from_thread_file(FIXTURE_PATH)
        resolved = str(FIXTURE_PATH.resolve())
        expected = [
            normalize_comment_payload(self.comment_thing, resolved),
            normalize_comment_payload(self.deleted_comment_thing, resolved),
        ]
        self.assertEqual(comments, expected)

    def test_comment_record_to_dict_roundtrip_keys(self) -> None:
        comments = normalize_comments_from_thread_file(FIXTURE_PATH)
        self.assertEqual(len(comments), 2)
        c = comments[0]
        d = comment_record_to_dict(c)
        self.assertEqual(d["reddit_id"], c.reddit_id)
        self.assertEqual(d["permalink"], c.permalink)
        self.assertEqual(d["parent_reddit_id"], c.parent_reddit_id)
        self.assertEqual(d["post_reddit_id"], c.post_reddit_id)
        self.assertIn("raw_path", d)


if __name__ == "__main__":
    unittest.main()
