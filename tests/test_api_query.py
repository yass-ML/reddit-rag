from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

import reddit_rag.api.app as api_app
from reddit_rag.api.app import create_app
from reddit_rag.api.schemas import QueryRequest, serialize_answer_response
from reddit_rag.embeddings.ollama_client import EmbeddingError
from reddit_rag.rag.answer import Answer
from reddit_rag.rag.ollama_chat import ChatError
from reddit_rag.rag.retrieve import RetrievalResult


def _retrieval_result() -> RetrievalResult:
    return RetrievalResult(
        chunk_id="chunk-1",
        text="source text",
        score=0.82,
        metadata={
            "source_id": "comment_abc",
            "source_type": "comment",
            "subreddit": "ClaudeAI",
            "reddit_id": "abc",
            "post_reddit_id": "post123",
            "title": "Parent title",
            "permalink": "https://reddit.example/comment",
            "score": 12,
            "chunk_index": 3,
            "author": "commenter",
            "raw_path": "/tmp/raw.json",
        },
        source_permalink="https://reddit.example/comment",
        source_title="Parent title",
        source_type="comment",
    )


class ApiQueryTests(unittest.TestCase):
    def test_request_validation_rejects_blank_question(self) -> None:
        client = TestClient(create_app(query_runner=lambda _request: None))  # type: ignore[arg-type]
        response = client.post("/api/query", json={"question": "   ", "top_k": 3})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "validation_failed")

    def test_request_validation_rejects_invalid_top_k(self) -> None:
        client = TestClient(create_app(query_runner=lambda _request: None))  # type: ignore[arg-type]
        response = client.post("/api/query", json={"question": "ok", "top_k": 0})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "validation_failed")

    def test_source_serialization_matches_frontend_shape(self) -> None:
        def runner(request: QueryRequest):
            result = _retrieval_result()
            return serialize_answer_response(
                answer=Answer(
                    question=request.question,
                    answer_text="Answer with [1].",
                    sources=[],
                ),
                retrieval_results=[result],
                retrieval_ms=25,
                embedding_model="embed",
                generation_model="chat",
                top_k=request.top_k,
                subreddit=request.subreddit,
            )

        client = TestClient(create_app(query_runner=runner))
        response = client.post(
            "/api/query",
            json={"question": "What changed?", "subreddit": "ClaudeAI", "top_k": 1},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        source = body["sources"][0]
        self.assertEqual(body["question"], "What changed?")
        self.assertEqual(source["id"], "src-001")
        self.assertEqual(source["citation_index"], 1)
        self.assertEqual(source["chunk_id"], "chunk-1")
        self.assertEqual(source["source_id"], "comment_abc")
        self.assertEqual(source["source_type"], "comment")
        self.assertEqual(source["source_title"], "Parent title")
        self.assertEqual(source["source_permalink"], "https://reddit.example/comment")
        self.assertEqual(source["metadata"]["chunk_index"], 3)
        self.assertEqual(source["source_score"], 12)
        self.assertEqual(source["excerpt"], "source text")
        self.assertEqual(body["retrieval_debug_optional"]["top_k"], 1)

    def test_no_result_response_is_valid_answer(self) -> None:
        def runner(request: QueryRequest):
            return serialize_answer_response(
                answer=Answer(
                    question=request.question,
                    answer_text="No retrieved passages match this query.",
                    sources=[],
                ),
                retrieval_results=[],
                retrieval_ms=1,
                embedding_model="embed",
                generation_model="chat",
                top_k=request.top_k,
                subreddit=request.subreddit,
            )

        client = TestClient(create_app(query_runner=runner))
        response = client.post("/api/query", json={"question": "missing"})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("No retrieved passages", body["answer_text"])
        self.assertEqual(body["sources"], [])

    def test_default_query_runner_times_retrieval_without_generation(self) -> None:
        phase = "starting"
        result = _retrieval_result()
        cfg = SimpleNamespace(
            models=SimpleNamespace(embedding_model="embed", chat_model="chat")
        )

        def fake_perf_counter() -> float:
            if phase == "starting":
                return 100.0
            if phase == "retrieved":
                return 100.25
            return 105.0

        def fake_retrieve(*_args, **_kwargs) -> list[RetrievalResult]:
            nonlocal phase
            phase = "retrieved"
            return [result]

        def fake_answer(
            question: str,
            _results: list[RetrievalResult],
            *,
            chat_client: object,
        ) -> Answer:
            nonlocal phase
            phase = "answered"
            return Answer(question=question, answer_text="Answer with [1].", sources=[])

        with (
            patch.object(api_app, "load_dotenv_from_project"),
            patch.object(api_app, "load_app_config", return_value=cfg),
            patch.object(api_app, "OllamaEmbeddingClient"),
            patch.object(api_app, "OllamaChatClient"),
            patch.object(api_app, "VectorStore"),
            patch.object(api_app, "resolve_chroma_dir", return_value="/tmp/chroma"),
            patch.object(api_app, "retrieve_relevant_chunks", side_effect=fake_retrieve),
            patch.object(api_app, "answer_question", side_effect=fake_answer),
            patch.object(api_app.time, "perf_counter", side_effect=fake_perf_counter),
        ):
            response = api_app._default_query_runner(
                QueryRequest(question="What changed?", top_k=1)
            )

        self.assertEqual(response.retrieval_debug_optional.retrieval_ms, 250)

    def test_error_mapping_for_embedding_chat_and_value_errors(self) -> None:
        cases = [
            (ValueError("bad input"), 400, "invalid_query"),
            (EmbeddingError("embed failed", model="m"), 502, "embedding_failed"),
            (ChatError("chat failed", model="m"), 502, "chat_failed"),
        ]
        for exc, status, code in cases:
            with self.subTest(code=code):
                def runner(_request: QueryRequest, exc: Exception = exc):
                    raise exc

                client = TestClient(create_app(query_runner=runner))
                response = client.post("/api/query", json={"question": "q"})
                self.assertEqual(response.status_code, status)
                self.assertEqual(response.json()["error"]["code"], code)


if __name__ == "__main__":
    unittest.main()
