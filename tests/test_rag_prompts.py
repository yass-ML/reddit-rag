from __future__ import annotations

import unittest

from reddit_rag.rag.prompts import RAG_SYSTEM_MESSAGE, build_rag_messages, build_rag_user_content
from reddit_rag.rag.retrieve import RetrievalResult


def _one_result(
    text: str,
    *,
    chunk_id: str = "c1",
    title: str = "",
    permalink: str = "",
    source_type: str = "post",
    subreddit: str | None = None,
) -> RetrievalResult:
    meta: dict = {}
    if subreddit is not None:
        meta["subreddit"] = subreddit
    return RetrievalResult(
        chunk_id=chunk_id,
        text=text,
        score=0.9,
        metadata=meta,
        source_permalink=permalink,
        source_title=title,
        source_type=source_type,
    )


class TestRagSystemMessage(unittest.TestCase):
    def test_instructs_use_only_provided_sources(self) -> None:
        self.assertIn("ONLY the numbered sources", RAG_SYSTEM_MESSAGE)
        self.assertIn("Do not use outside knowledge", RAG_SYSTEM_MESSAGE)

    def test_asks_cite_with_bracket_numbers(self) -> None:
        self.assertIn("cite it", RAG_SYSTEM_MESSAGE)
        self.assertIn("[1]", RAG_SYSTEM_MESSAGE)
        self.assertIn("[2]", RAG_SYSTEM_MESSAGE)

    def test_tells_model_insufficient_evidence(self) -> None:
        self.assertIn("enough information", RAG_SYSTEM_MESSAGE)
        self.assertIn("do not", RAG_SYSTEM_MESSAGE.lower() or "")
        self.assertIn("invent", RAG_SYSTEM_MESSAGE)


class TestBuildRagUserContent(unittest.TestCase):
    def test_numbered_blocks_match_order(self) -> None:
        r1 = _one_result("first chunk", title="A")
        r2 = _one_result("second", title="B")
        r3 = _one_result("third", title="C")
        out = build_rag_user_content("q?", [r1, r2, r3])
        self.assertIn("--- Source [1] ---", out)
        self.assertIn("--- Source [2] ---", out)
        self.assertIn("--- Source [3] ---", out)
        self.assertIn("first chunk", out)
        self.assertIn("second", out)
        self.assertIn("third", out)
        self.assertLess(out.index("--- Source [1] ---"), out.index("--- Source [2] ---"))
        self.assertLess(out.index("--- Source [2] ---"), out.index("--- Source [3] ---"))

    def test_includes_metadata_lines(self) -> None:
        r = RetrievalResult(
            chunk_id="x",
            text="body",
            score=0.5,
            metadata={"subreddit": "testsub", "score": 42},
            source_permalink="/r/test/p/1",
            source_title="Hello",
            source_type="comment",
        )
        out = build_rag_user_content("What?", [r])
        self.assertIn("subreddit: testsub", out)
        self.assertIn("permalink: /r/test/p/1", out)
        self.assertIn("title: Hello", out)
        self.assertIn("source_type: comment", out)
        self.assertIn("source_score: 42", out)
        self.assertIn("body", out)

    def test_no_results_section(self) -> None:
        out = build_rag_user_content("anything", [])
        self.assertIn("No passages were retrieved", out)
        self.assertIn("evidence is insufficient", out)


class TestBuildRagMessages(unittest.TestCase):
    def test_roles_and_user_contains_question(self) -> None:
        r = _one_result("x")
        msgs = build_rag_messages("  my question?  ", [r])
        self.assertEqual(len(msgs), 2)
        self.assertEqual(msgs[0]["role"], "system")
        self.assertEqual(msgs[0]["content"], RAG_SYSTEM_MESSAGE)
        self.assertEqual(msgs[1]["role"], "user")
        self.assertIn("my question?", msgs[1]["content"])
        self.assertIn("--- Source [1] ---", msgs[1]["content"])


if __name__ == "__main__":
    unittest.main()
