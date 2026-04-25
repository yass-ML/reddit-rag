from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from reddit_rag.processing.chunk import (
    CHUNK_ID_FORMAT_VERSION,
    chunk_records,
    chunk_to_dict,
    chunks_from_comment_dict,
    chunks_from_post_dict,
)
from reddit_rag.processing.chunks_io import (
    default_chunks_jsonl_path,
    merge_chunk_records_jsonl,
)


def _post(
    *,
    rid: str = "abc",
    title: str = "T",
    body: str = "B",
    permalink: str = "/r/x/comments/abc/t/",
) -> dict:
    return {
        "id": f"post_{rid}",
        "reddit_id": rid,
        "subreddit": "learnpython",
        "title": title,
        "body": body,
        "author": "a",
        "score": 1,
        "num_comments": 0,
        "created_utc": 1.0,
        "permalink": permalink,
        "url": None,
        "raw_path": "/tmp/x.json",
    }


def _comment(
    *,
    rid: str = "c1",
    post_rid: str = "abc",
    body: str = "hello",
    permalink: str = "/r/x/comments/abc/t/c1/",
) -> dict:
    return {
        "id": f"comment_{rid}",
        "reddit_id": rid,
        "post_reddit_id": post_rid,
        "parent_reddit_id": post_rid,
        "subreddit": "learnpython",
        "body": body,
        "author": "b",
        "score": 2,
        "created_utc": 2.0,
        "permalink": permalink,
        "raw_path": "/tmp/x.json",
    }


class ChunkStableIdTests(unittest.TestCase):
    def test_same_input_same_ids(self) -> None:
        rec = _post(body="x" * 50)
        a = chunks_from_post_dict(rec, chunk_size=20, chunk_overlap=5)
        b = chunks_from_post_dict(rec, chunk_size=20, chunk_overlap=5)
        self.assertEqual([c.id for c in a], [c.id for c in b])

    def test_id_includes_version_size_overlap_type_index(self) -> None:
        rec = _post(title="Hi", body="")
        chunks = chunks_from_post_dict(rec, chunk_size=100, chunk_overlap=10)
        self.assertEqual(len(chunks), 1)
        cid = chunks[0].id
        self.assertIn(CHUNK_ID_FORMAT_VERSION, cid)
        self.assertIn("cs100", cid)
        self.assertIn("ov10", cid)
        self.assertIn("post", cid)
        self.assertTrue(cid.endswith("_0000"))


class ChunkMetadataTests(unittest.TestCase):
    def test_post_metadata_has_contract_keys_and_permalink(self) -> None:
        rec = _post()
        ch = chunks_from_post_dict(rec, chunk_size=500, chunk_overlap=0)[0]
        meta = ch.metadata
        self.assertEqual(meta["reddit_id"], "abc")
        self.assertEqual(meta["post_reddit_id"], "abc")
        self.assertEqual(meta["title"], "T")
        self.assertEqual(meta["permalink"], "/r/x/comments/abc/t/")
        self.assertEqual(meta["chunk_index"], 0)
        self.assertEqual(meta["chunk_size"], 500)
        self.assertEqual(meta["chunk_overlap"], 0)

    def test_comment_omits_permalink_when_empty(self) -> None:
        rec = _comment(permalink="  ")
        ch = chunks_from_comment_dict(rec, chunk_size=50, chunk_overlap=0)[0]
        self.assertNotIn("permalink", ch.metadata)

    def test_comment_includes_permalink_when_present(self) -> None:
        rec = _comment()
        ch = chunks_from_comment_dict(rec, chunk_size=50, chunk_overlap=0)[0]
        self.assertEqual(ch.metadata.get("permalink"), "/r/x/comments/abc/t/c1/")
        self.assertEqual(ch.metadata["title"], "")


class ChunkSplitTests(unittest.TestCase):
    def test_long_post_multiple_windows_with_overlap(self) -> None:
        body = "a" * 100
        rec = _post(title="", body=body)
        chunks = chunks_from_post_dict(rec, chunk_size=30, chunk_overlap=10)
        self.assertGreater(len(chunks), 1)
        for i, c in enumerate(chunks):
            self.assertEqual(c.metadata["chunk_index"], i)
        # Overlap: second chunk should share tail of first
        self.assertTrue(chunks[1].text.startswith("a" * 10) or "aaaa" in chunks[0].text)

    def test_title_only_post_single_chunk(self) -> None:
        rec = _post(title="Only title", body="")
        chunks = chunks_from_post_dict(rec, chunk_size=100, chunk_overlap=0)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].text, "Only title")

    def test_empty_comment_zero_chunks(self) -> None:
        rec = _comment(body="   ")
        chunks = chunks_from_comment_dict(rec, chunk_size=50, chunk_overlap=0)
        self.assertEqual(chunks, [])


class ChunkRecordsDispatchTests(unittest.TestCase):
    def test_chunk_records_order(self) -> None:
        records = [_post(rid="1", title="A", body=""), _comment(rid="2", body="c")]
        out = chunk_records(records, chunk_size=50, chunk_overlap=0)
        self.assertEqual(out[0].source_type, "post")
        self.assertEqual(out[1].source_type, "comment")

    def test_unknown_id_prefix_raises(self) -> None:
        with self.assertRaises(ValueError):
            chunk_records([{"id": "thread_x"}], chunk_size=10, chunk_overlap=0)

    def test_invalid_overlap_raises(self) -> None:
        with self.assertRaises(ValueError):
            chunks_from_post_dict(_post(), chunk_size=10, chunk_overlap=10)


class ChunksJsonlMergeTests(unittest.TestCase):
    def test_merge_dedupes_by_chunk_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "chunks.jsonl"
            d1 = chunk_to_dict(chunks_from_post_dict(_post(rid="z", title="t", body="b"), chunk_size=100, chunk_overlap=0)[0])
            d2 = dict(d1)
            r1 = merge_chunk_records_jsonl(path, [d1])
            self.assertEqual(r1.appended, 1)
            r2 = merge_chunk_records_jsonl(path, [d2])
            self.assertEqual(r2.skipped_duplicates, 1)
            self.assertEqual(r2.total_after, 1)


class DefaultChunksPathTests(unittest.TestCase):
    def test_default_chunks_jsonl_path(self) -> None:
        p = default_chunks_jsonl_path(Path("/data/processed"), "LearnPython")
        self.assertTrue(str(p).endswith("LearnPython/chunks.jsonl") or "learnpython" in str(p).lower())


class ChunkToDictJsonTests(unittest.TestCase):
    def test_chunk_to_dict_roundtrips_json(self) -> None:
        ch = chunks_from_post_dict(_post(), chunk_size=50, chunk_overlap=0)[0]
        s = json.dumps(chunk_to_dict(ch))
        self.assertIn("metadata", json.loads(s))
