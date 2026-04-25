from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from ollama import RequestError, ResponseError

from reddit_rag.embeddings import EmbeddingError, OllamaEmbeddingClient


class TestOllamaEmbeddingClient(unittest.TestCase):
    def test_rejects_empty_model(self) -> None:
        with self.assertRaises(ValueError):
            OllamaEmbeddingClient("")
        with self.assertRaises(ValueError):
            OllamaEmbeddingClient("   ")

    def test_embed_text_calls_client_with_model(self) -> None:
        mock_client = Mock()
        mock_client.embed.return_value = SimpleNamespace(embeddings=[[0.25, 0.5, 1.0]])
        client = OllamaEmbeddingClient("nomic-embed-text", client=mock_client)
        vec = client.embed_text("  hello  ")
        self.assertEqual(vec, [0.25, 0.5, 1.0])
        mock_client.embed.assert_called_once_with(model="nomic-embed-text", input=["hello"])

    def test_embed_text_rejects_blank(self) -> None:
        mock_client = Mock()
        client = OllamaEmbeddingClient("m", client=mock_client)
        with self.assertRaisesRegex(ValueError, "non-empty"):
            client.embed_text("")
        with self.assertRaisesRegex(ValueError, "non-empty"):
            client.embed_text("   ")
        mock_client.embed.assert_not_called()

    def test_embed_texts_batch_single_request(self) -> None:
        mock_client = Mock()
        mock_client.embed.return_value = SimpleNamespace(
            embeddings=[
                [1.0, 0.0],
                [0.0, 1.0],
                [0.5, 0.5],
            ]
        )
        client = OllamaEmbeddingClient("m", client=mock_client)
        out = client.embed_texts(["a", "b", "c"])
        self.assertEqual(len(out), 3)
        self.assertEqual(out[0], [1.0, 0.0])
        mock_client.embed.assert_called_once_with(model="m", input=["a", "b", "c"])

    def test_embed_texts_empty_sequence(self) -> None:
        client = OllamaEmbeddingClient("m", client=Mock())
        self.assertEqual(client.embed_texts([]), [])

    def test_embed_texts_rejects_empty_string_in_batch(self) -> None:
        client = OllamaEmbeddingClient("m", client=Mock())
        with self.assertRaisesRegex(ValueError, r"texts\[1\]"):
            client.embed_texts(["ok", "  "])

    def test_embed_texts_batch_size_slices(self) -> None:
        mock_client = Mock()
        mock_client.embed.side_effect = [
            SimpleNamespace(embeddings=[[1.0], [2.0]]),
            SimpleNamespace(embeddings=[[3.0], [4.0]]),
            SimpleNamespace(embeddings=[[5.0]]),
        ]
        client = OllamaEmbeddingClient("m", client=mock_client)
        out = client.embed_texts(["t0", "t1", "t2", "t3", "t4"], batch_size=2)
        self.assertEqual(out, [[1.0], [2.0], [3.0], [4.0], [5.0]])
        self.assertEqual(mock_client.embed.call_count, 3)
        calls = mock_client.embed.call_args_list
        self.assertEqual(calls[0].kwargs["input"], ["t0", "t1"])
        self.assertEqual(calls[1].kwargs["input"], ["t2", "t3"])
        self.assertEqual(calls[2].kwargs["input"], ["t4"])

    def test_embed_texts_rejects_non_positive_batch_size(self) -> None:
        client = OllamaEmbeddingClient("m", client=Mock())
        with self.assertRaisesRegex(ValueError, "batch_size"):
            client.embed_texts(["a"], batch_size=0)

    def test_response_error_wrapped(self) -> None:
        mock_client = Mock()
        mock_client.embed.side_effect = ResponseError('{"error":"nope"}', status_code=500)
        client = OllamaEmbeddingClient("m", client=mock_client)
        with self.assertRaises(EmbeddingError) as ctx:
            client.embed_text("x")
        self.assertEqual(ctx.exception.model, "m")
        self.assertIn("nope", str(ctx.exception))

    def test_request_error_wrapped(self) -> None:
        mock_client = Mock()
        mock_client.embed.side_effect = RequestError("connection refused")
        client = OllamaEmbeddingClient("m", client=mock_client)
        with self.assertRaises(EmbeddingError) as ctx:
            client.embed_text("x")
        self.assertEqual(ctx.exception.model, "m")

    def test_missing_embeddings_field(self) -> None:
        mock_client = Mock()
        mock_client.embed.return_value = SimpleNamespace()
        client = OllamaEmbeddingClient("m", client=mock_client)
        with self.assertRaisesRegex(EmbeddingError, "missing"):
            client.embed_text("x")

    def test_wrong_embedding_count(self) -> None:
        mock_client = Mock()
        mock_client.embed.return_value = SimpleNamespace(embeddings=[[1.0]])
        client = OllamaEmbeddingClient("m", client=mock_client)
        with self.assertRaisesRegex(EmbeddingError, "expected 2"):
            client.embed_texts(["a", "b"])

    def test_coerce_vector_invalid(self) -> None:
        mock_client = Mock()
        mock_client.embed.return_value = SimpleNamespace(embeddings=[["not", "floats"]])
        client = OllamaEmbeddingClient("m", client=mock_client)
        with self.assertRaises(EmbeddingError):
            client.embed_text("x")
