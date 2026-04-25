"""Local embedding clients."""

from reddit_rag.embeddings.ollama_client import EmbeddingError, OllamaEmbeddingClient

__all__ = [
    "EmbeddingError",
    "OllamaEmbeddingClient",
]
