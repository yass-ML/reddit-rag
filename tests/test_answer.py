from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from reddit_rag.rag.answer import (
    Answer,
    AnswerSource,
    answer_question,
    format_answer_markdown,
    retrieval_results_to_answer_sources,
)
from reddit_rag.rag.ollama_chat import OllamaChatClient
from reddit_rag.rag.retrieve import RetrievalResult


class TestAnswerQuestion(unittest.TestCase):
    def test_returns_answer_with_sources(self) -> None:
        mock_client = Mock()
        mock_client.chat.return_value = SimpleNamespace(
            message=SimpleNamespace(content="According to [1], yes.")
        )
        chat = OllamaChatClient("m", client=mock_client)
        r = RetrievalResult(
            chunk_id="c1",
            text="detail",
            score=0.8,
            metadata={"subreddit": "SaaS", "score": 12},
            source_permalink="/p/1",
            source_title="T",
            source_type="post",
        )
        out = answer_question("  is it?  ", [r], chat_client=chat)
        self.assertEqual(out.question, "is it?")
        self.assertEqual(out.answer_text, "According to [1], yes.")
        self.assertEqual(
            out.sources,
            [
                AnswerSource(
                    index=1,
                    excerpt="detail",
                    title="T",
                    subreddit="SaaS",
                    score=12,
                    permalink="/p/1",
                )
            ],
        )
        mock_client.chat.assert_called_once()

    def test_no_results_skips_chat(self) -> None:
        mock_client = Mock()
        chat = OllamaChatClient("m", client=mock_client)
        out = answer_question("why?", [], chat_client=chat)
        self.assertIn("No retrieved passages", out.answer_text)
        self.assertEqual(out.sources, [])
        mock_client.chat.assert_not_called()


class TestRetrievalResultsToAnswerSources(unittest.TestCase):
    def test_falls_back_to_metadata_title_and_permalink(self) -> None:
        r = RetrievalResult(
            chunk_id="c",
            text=" excerpt ",
            score=0.5,
            metadata={"subreddit": "x", "score": 3, "title": "From meta", "permalink": "/m"},
            source_permalink="",
            source_title="",
            source_type="comment",
        )
        src = retrieval_results_to_answer_sources([r])[0]
        self.assertEqual(src.title, "From meta")
        self.assertEqual(src.permalink, "/m")
        self.assertEqual(src.excerpt, "excerpt")
        self.assertEqual(src.score, 3)


class TestFormatAnswerMarkdown(unittest.TestCase):
    def test_includes_sources_block(self) -> None:
        ans = Answer(
            question="q",
            answer_text="A line.",
            sources=[
                AnswerSource(
                    index=1,
                    excerpt="e",
                    title="T",
                    subreddit="S",
                    score=1,
                    permalink="http://p",
                )
            ],
        )
        md = format_answer_markdown(ans)
        self.assertIn("A line.", md)
        self.assertIn("## Sources", md)
        self.assertIn("http://p", md)
        self.assertIn("**score:** 1", md)

    def test_empty_sources_section(self) -> None:
        md = format_answer_markdown(Answer(question="q", answer_text="Only.", sources=[]))
        self.assertIn("_No sources._", md)


if __name__ == "__main__":
    unittest.main()
