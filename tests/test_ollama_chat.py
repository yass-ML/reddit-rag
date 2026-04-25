from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from ollama import RequestError, ResponseError

from reddit_rag.rag.ollama_chat import ChatError, OllamaChatClient


class TestOllamaChatClient(unittest.TestCase):
    def test_rejects_empty_model(self) -> None:
        with self.assertRaises(ValueError):
            OllamaChatClient("")
        with self.assertRaises(ValueError):
            OllamaChatClient("   ")

    def test_complete_calls_chat_with_model(self) -> None:
        mock_client = Mock()
        mock_client.chat.return_value = SimpleNamespace(
            message=SimpleNamespace(content="  hello  \n")
        )
        client = OllamaChatClient("llama3.2", client=mock_client)
        out = client.complete(
            [
                {"role": "system", "content": "sys"},
                {"role": "user", "content": "user"},
            ]
        )
        self.assertEqual(out, "hello")
        mock_client.chat.assert_called_once()
        self.assertEqual(mock_client.chat.call_args.kwargs.get("model"), "llama3.2")
        self.assertEqual(mock_client.chat.call_args.kwargs.get("stream"), False)

    def test_complete_rejects_empty_messages(self) -> None:
        client = OllamaChatClient("m", client=Mock())
        with self.assertRaisesRegex(ValueError, "non-empty"):
            client.complete([])

    def test_response_error_wrapped(self) -> None:
        mock_client = Mock()
        mock_client.chat.side_effect = ResponseError('{"error":"bad"}', status_code=500)
        client = OllamaChatClient("m", client=mock_client)
        with self.assertRaises(ChatError) as ctx:
            client.complete([{"role": "user", "content": "x"}])
        self.assertEqual(ctx.exception.model, "m")
        self.assertIn("500", str(ctx.exception))

    def test_request_error_wrapped(self) -> None:
        mock_client = Mock()
        mock_client.chat.side_effect = RequestError("connection refused")
        client = OllamaChatClient("m", client=mock_client)
        with self.assertRaises(ChatError) as ctx:
            client.complete([{"role": "user", "content": "x"}])
        self.assertEqual(ctx.exception.model, "m")

    def test_missing_message_field(self) -> None:
        mock_client = Mock()
        mock_client.chat.return_value = SimpleNamespace()  # no .message
        client = OllamaChatClient("m", client=mock_client)
        with self.assertRaisesRegex(ChatError, "missing"):
            client.complete([{"role": "user", "content": "x"}])

    def test_message_as_dict_in_response(self) -> None:
        mock_client = Mock()
        mock_client.chat.return_value = {"message": {"content": "ok", "role": "assistant"}}
        client = OllamaChatClient("m", client=mock_client)
        self.assertEqual(
            client.complete([{"role": "user", "content": "x"}]),
            "ok",
        )

    def test_empty_content_raises(self) -> None:
        mock_client = Mock()
        mock_client.chat.return_value = SimpleNamespace(message=SimpleNamespace(content="   "))
        client = OllamaChatClient("m", client=mock_client)
        with self.assertRaisesRegex(ChatError, "empty"):
            client.complete([{"role": "user", "content": "x"}])


if __name__ == "__main__":
    unittest.main()
