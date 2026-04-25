"""Local chat completion via the Ollama HTTP API."""

from __future__ import annotations

from collections.abc import Sequence

from ollama import Client, RequestError, ResponseError


class ChatError(RuntimeError):
    """Raised when the Ollama chat API fails after validation."""

    def __init__(self, message: str, *, model: str) -> None:
        super().__init__(message)
        self.model = model


def _message_content(msg: object) -> str:
    c = getattr(msg, "content", None)
    if c is not None and isinstance(c, str):
        return c
    if isinstance(msg, dict) and "content" in msg:
        raw = msg.get("content")
        if isinstance(raw, str):
            return raw
    return ""


class OllamaChatClient:
    """Thin wrapper around ``ollama.Client`` for chat (generation) models."""

    def __init__(
        self,
        model: str,
        *,
        host: str | None = None,
        client: Client | None = None,
    ) -> None:
        if not isinstance(model, str) or not model.strip():
            raise ValueError("model must be a non-empty string")
        self._model = model.strip()
        if client is not None:
            self._client = client
        elif host is not None and str(host).strip():
            self._client = Client(host=str(host).strip())
        else:
            self._client = Client()

    @property
    def model(self) -> str:
        return self._model

    def complete(self, messages: Sequence[dict[str, str]]) -> str:
        """Run one non-streaming chat and return the assistant text."""
        if not messages:
            raise ValueError("messages must be non-empty")

        msg_list: list[dict[str, str]] = [dict(m) for m in messages]

        try:
            response = self._client.chat(
                model=self._model,
                messages=msg_list,
                stream=False,
            )
        except (ResponseError, RequestError) as e:
            raise ChatError(
                f"Ollama chat request failed: {e}",
                model=self._model,
            ) from e
        except Exception as e:
            raise ChatError(
                f"Ollama chat failed: {e}",
                model=self._model,
            ) from e

        msg = getattr(response, "message", None)
        if msg is None and isinstance(response, dict):
            msg = response.get("message")
        if msg is None:
            raise ChatError(
                "Ollama chat response missing 'message'",
                model=self._model,
            )
        text = _message_content(msg)
        if not text or not str(text).strip():
            raise ChatError(
                "Ollama chat response has empty assistant content",
                model=self._model,
            )
        return str(text).strip()
