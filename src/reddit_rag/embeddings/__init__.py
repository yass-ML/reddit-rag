"""Local embedding clients."""

from reddit_rag.embeddings.index_chunks import ChunkIndexSummary, index_chunks_jsonl
from reddit_rag.embeddings.ollama_client import EmbeddingError, OllamaEmbeddingClient

__all__ = [
    "ChunkIndexSummary",
    "EmbeddingError",
    "OllamaEmbeddingClient",
    "index_chunks_jsonl",
]
