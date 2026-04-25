"""Unit tests for semantic retrieval."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from reddit_rag.rag.retrieve import (
    RetrievalResult,
    _hit_to_result,
    chroma_cosine_distance_to_score,
    retrieve_relevant_chunks,
)


class ChromaScoreTests(unittest.TestCase):
    def test_chroma_cosine_distance_to_score(self) -> None:
        self.assertEqual(chroma_cosine_distance_to_score(0.1), 0.9)
        self.assertEqual(chroma_cosine_distance_to_score(0.0), 1.0)
        self.assertEqual(chroma_cosine_distance_to_score(None), 0.0)

    def test_hit_to_result_mapping(self) -> None:
        r = _hit_to_result(
            {
                "id": "c1",
                "document": " body ",
                "metadata": {
                    "source_type": "post",
                    "subreddit": "s",
                    "title": " T ",
                    "permalink": "/p",
                },
                "distance": 0.2,
            },
        )
        self.assertEqual(r.chunk_id, "c1")
        self.assertEqual(r.text, " body ")
        self.assertAlmostEqual(r.score, 0.8)
        self.assertEqual(r.source_type, "post")
        self.assertEqual(r.source_title, "T")
        self.assertEqual(r.source_permalink, "/p")
        self.assertIn("subreddit", r.metadata)


class RetrieveRelevantChunksTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = SimpleNamespace()
        self.client.embed_text = MagicMock(return_value=[0.0, 1.0])
        self.store = SimpleNamespace()
        self.store.query = MagicMock(
            return_value=[
                {
                    "id": "a",
                    "document": "doc",
                    "metadata": {
                        "source_type": "comment",
                        "title": "",
                        "subreddit": "x",
                    },
                    "distance": 0.5,
                }
            ],
        )

    def test_wires_embed_query_and_mapping(self) -> None:
        out = retrieve_relevant_chunks(
            "  what is python  ",
            embedding_client=self.client,  # type: ignore[arg-type]
            vector_store=self.store,  # type: ignore[arg-type]
            top_k=3,
        )
        self.client.embed_text.assert_called_once_with("what is python")
        self.store.query.assert_called_once_with([0.0, 1.0], 3, where=None)
        self.assertEqual(len(out), 1)
        self.assertIsInstance(out[0], RetrievalResult)
        self.assertEqual(out[0].text, "doc")
        self.assertAlmostEqual(out[0].score, 0.5)
        self.assertEqual(out[0].source_type, "comment")

    def test_subreddit_passes_where(self) -> None:
        retrieve_relevant_chunks(
            "q",
            embedding_client=self.client,  # type: ignore[arg-type]
            vector_store=self.store,  # type: ignore[arg-type]
            subreddit=" learnpython ",
        )
        self.store.query.assert_called_with([0.0, 1.0], 5, where={"subreddit": "learnpython"})

    def test_subreddit_empty_means_no_where(self) -> None:
        retrieve_relevant_chunks(
            "q",
            embedding_client=self.client,  # type: ignore[arg-type]
            vector_store=self.store,  # type: ignore[arg-type]
            subreddit="   ",
        )
        self.store.query.assert_called_with([0.0, 1.0], 5, where=None)

    def test_empty_question_raises(self) -> None:
        with self.assertRaises(ValueError):
            retrieve_relevant_chunks(
                "  ",
                embedding_client=self.client,  # type: ignore[arg-type]
                vector_store=self.store,  # type: ignore[arg-type]
            )

    def test_non_positive_top_k_raises(self) -> None:
        with self.assertRaises(ValueError):
            retrieve_relevant_chunks(
                "ok",
                embedding_client=self.client,  # type: ignore[arg-type]
                vector_store=self.store,  # type: ignore[arg-type]
                top_k=0,
            )
