"""Local text embeddings via the Ollama HTTP API."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from ollama import Client, RequestError, ResponseError


class EmbeddingError(RuntimeError):
    """Raised when the Ollama embedding API fails after validation."""

    def __init__(self, message: str, *, model: str) -> None:
        super().__init__(message)
        self.model = model


class OllamaEmbeddingClient:
    """Thin wrapper around ``ollama.Client`` for embedding models."""

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
            # Ollama Client resolves OLLAMA_HOST from the environment when host is None.
            self._client = Client()

    @property
    def model(self) -> str:
        return self._model

    def embed_text(self, text: str) -> list[float]:
        """Embed a single non-empty string. Leading/trailing whitespace is stripped."""
        cleaned = text.strip()
        if not cleaned:
            raise ValueError("text must be non-empty after stripping whitespace")
        return self._embed_raw([cleaned])[0]

    def embed_texts(
        self,
        texts: Sequence[str],
        *,
        batch_size: int | None = None,
    ) -> list[list[float]]:
        """Embed many strings in input order.

        When ``batch_size`` is ``None`` or greater than the number of inputs, a single
        ``embed`` request is used with ``input`` as a list. When ``batch_size`` is a
        positive integer smaller than ``len(texts)``, texts are split into consecutive
        slices of at most that size so large corpora do not produce oversized HTTP payloads.

        Every text is stripped; empty results raise ``ValueError``.
        """
        if not texts:
            return []
        cleaned = [t.strip() for t in texts]
        for i, t in enumerate(cleaned):
            if not t:
                raise ValueError(f"texts[{i}] must be non-empty after stripping whitespace")

        if batch_size is None:
            return self._embed_raw(cleaned)

        if batch_size <= 0:
            raise ValueError("batch_size must be > 0 when set")

        out: list[list[float]] = []
        for start in range(0, len(cleaned), batch_size):
            out.extend(self._embed_raw(cleaned[start : start + batch_size]))
        return out

    def _embed_raw(self, inputs: list[str]) -> list[list[float]]:
        try:
            response = self._client.embed(model=self._model, input=inputs)
        except (ResponseError, RequestError) as e:
            raise EmbeddingError(
                f"Ollama embedding request failed: {e}",
                model=self._model,
            ) from e
        except Exception as e:
            raise EmbeddingError(
                f"Ollama embedding failed: {e}",
                model=self._model,
            ) from e

        vectors = getattr(response, "embeddings", None)
        if vectors is None:
            raise EmbeddingError(
                "Ollama embed response missing 'embeddings'",
                model=self._model,
            )
        if len(vectors) != len(inputs):
            raise EmbeddingError(
                f"expected {len(inputs)} embedding(s), got {len(vectors)}",
                model=self._model,
            )
        return [_coerce_vector(v, self._model) for v in vectors]


def _coerce_vector(raw: Any, model: str) -> list[float]:
    try:
        return [float(x) for x in raw]
    except (TypeError, ValueError) as e:
        raise EmbeddingError(
            f"embedding vector is not a sequence of floats: {e!s}",
            model=model,
        ) from e
