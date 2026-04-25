from __future__ import annotations

import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from reddit_rag.api.schemas import SourceEvidenceModel
from reddit_rag.rag.export import (
    build_query_export_markdown,
    sanitize_query_label,
    write_query_export,
)


def _source() -> SourceEvidenceModel:
    return SourceEvidenceModel(
        id="src-001",
        citation_index=1,
        chunk_id="chunk-abc",
        source_id="post_abc",
        subreddit="ClaudeAI",
        text="Full chunk text",
        score=0.91,
        metadata={
            "reddit_id": "abc",
            "post_reddit_id": "abc",
            "title": "A source title",
            "permalink": "https://reddit.example/post",
            "score": 44,
            "created_utc": 1.0,
            "chunk_index": 2,
        },
        source_permalink="https://reddit.example/post",
        source_title="A source title",
        source_type="post",
        author=None,
        source_score=44,
        excerpt="An excerpt",
        local_raw_path="",
    )


class QueryExportTests(unittest.TestCase):
    def test_sanitize_query_label_is_path_safe(self) -> None:
        self.assertEqual(
            sanitize_query_label("  What do users say about C++ / Rust?  "),
            "what-do-users-say-about-c-rust",
        )
        self.assertEqual(sanitize_query_label("?!"), "query")

    def test_markdown_contains_expected_sections_and_source_fields(self) -> None:
        markdown = build_query_export_markdown(
            question="What matters?",
            subreddit="ClaudeAI",
            answer_text="Answer text.",
            sources=[_source()],
        )
        self.assertIn("# RAG Query Result", markdown)
        self.assertIn("## Question", markdown)
        self.assertIn("What matters?", markdown)
        self.assertIn("## Subreddit Filter", markdown)
        self.assertIn("ClaudeAI", markdown)
        self.assertIn("## Answer", markdown)
        self.assertIn("Answer text.", markdown)
        self.assertIn("### [1] A source title", markdown)
        self.assertIn("**source type:** post", markdown)
        self.assertIn("**chunk id:** chunk-abc", markdown)
        self.assertIn("**chunk index:** 2", markdown)
        self.assertIn("> An excerpt", markdown)

    def test_write_query_export_uses_timestamp_and_sanitized_label(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = write_query_export(
                question="What matters?",
                subreddit=None,
                answer_text="Answer text.",
                sources=[_source()],
                now=datetime(2026, 4, 25, 19, 49, 0),
                exports_dir=Path(tmp),
            )
            self.assertEqual(path.name, "20260425-194900-what-matters.md")
            self.assertTrue(path.is_file())
            self.assertIn("All subreddits", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
