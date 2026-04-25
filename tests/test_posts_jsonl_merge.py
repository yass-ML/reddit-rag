from __future__ import annotations

import json
import unittest
from pathlib import Path

from reddit_rag.processing.posts import (
    default_posts_jsonl_path,
    merge_post_records_jsonl,
    post_record_dedupe_key,
)


def _post_dict(reddit_id: str, title: str = "t") -> dict:
    return {
        "author": None,
        "body": "",
        "created_utc": None,
        "id": f"post_{reddit_id}",
        "num_comments": 0,
        "permalink": "/r/test/x",
        "reddit_id": reddit_id,
        "score": 0,
        "subreddit": "testsub",
        "title": title,
        "url": None,
        "raw_path": "/tmp/x.json",
    }


class PostRecordDedupeKeyTests(unittest.TestCase):
    def test_prefers_reddit_id(self) -> None:
        self.assertEqual(post_record_dedupe_key({"reddit_id": "abc", "id": "post_xyz"}), "abc")

    def test_falls_back_to_id(self) -> None:
        self.assertEqual(post_record_dedupe_key({"id": "post_only"}), "post_only")

    def test_raises_when_missing_keys(self) -> None:
        with self.assertRaises(ValueError):
            post_record_dedupe_key({"title": "x"})


class DefaultPostsJsonlPathTests(unittest.TestCase):
    def test_safe_subfolder(self) -> None:
        root = Path("/data/processed")
        p = default_posts_jsonl_path(root, "Foo/Bar")
        self.assertEqual(p, Path("/data/processed/Foo-Bar/posts.jsonl"))


class MergePostRecordsJsonlTests(unittest.TestCase):
    def test_appends_new_preserves_order(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "posts.jsonl"
            seed = [_post_dict("a", "first"), _post_dict("b", "second")]
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8") as f:
                for row in seed:
                    f.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
                    f.write("\n")

            r = merge_post_records_jsonl(path, [_post_dict("b", "changed"), _post_dict("c", "third")])

            self.assertEqual(r.existing_count, 2)
            self.assertEqual(r.appended, 1)
            self.assertEqual(r.skipped_duplicates, 1)
            self.assertEqual(r.total_after, 3)

            lines = path.read_text(encoding="utf-8").strip().split("\n")
            self.assertEqual(len(lines), 3)
            first = json.loads(lines[0])
            third = json.loads(lines[2])
            self.assertEqual(first["reddit_id"], "a")
            self.assertEqual(first["title"], "first")
            self.assertEqual(json.loads(lines[1])["reddit_id"], "b")
            self.assertEqual(json.loads(lines[1])["title"], "second")
            self.assertEqual(third["reddit_id"], "c")

    def test_skips_duplicate_within_new_batch(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "posts.jsonl"
            r = merge_post_records_jsonl(
                path,
                [_post_dict("x", "one"), _post_dict("x", "two")],
            )
            self.assertEqual(r.appended, 1)
            self.assertEqual(r.skipped_duplicates, 1)
            self.assertEqual(r.total_after, 1)

    def test_dedupes_duplicate_lines_when_rewriting(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "posts.jsonl"
            dup = _post_dict("same", "v1")
            with path.open("w", encoding="utf-8") as f:
                f.write(json.dumps(dup, ensure_ascii=False, sort_keys=True) + "\n")
                f.write(json.dumps(_post_dict("same", "v2"), ensure_ascii=False, sort_keys=True) + "\n")

            r = merge_post_records_jsonl(path, [_post_dict("other", "new")])

            self.assertEqual(r.existing_count, 1)
            self.assertEqual(r.appended, 1)
            self.assertEqual(r.total_after, 2)

            lines = [json.loads(x) for x in path.read_text(encoding="utf-8").strip().split("\n")]
            self.assertEqual(len(lines), 2)
            self.assertEqual({x["reddit_id"] for x in lines}, {"same", "other"})
            self.assertEqual(lines[0]["title"], "v1")

    def test_dedupes_ondisk_duplicates_when_merge_batch_empty(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "posts.jsonl"
            row = _post_dict("same", "v1")
            with path.open("w", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
                f.write(
                    json.dumps(
                        _post_dict("same", "v2"),
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                    + "\n"
                )

            r = merge_post_records_jsonl(path, [])

            self.assertEqual(r.existing_count, 1)
            self.assertEqual(r.appended, 0)
            self.assertEqual(r.total_after, 1)
            self.assertEqual(r.skipped_duplicates, 0)

            lines = path.read_text(encoding="utf-8").strip().split("\n")
            self.assertEqual(len(lines), 1)
            self.assertEqual(json.loads(lines[0])["title"], "v1")

    def test_empty_new_no_file_creates_nothing(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "missing.jsonl"
            r = merge_post_records_jsonl(path, [])
            self.assertFalse(path.exists())
            self.assertEqual(r.total_after, 0)
            self.assertEqual(r.appended, 0)

    def test_invalid_json_raises(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "bad.jsonl"
            path.write_text("not json\n", encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                merge_post_records_jsonl(path, [_post_dict("z")])
            self.assertIn("Invalid JSON", str(ctx.exception))
