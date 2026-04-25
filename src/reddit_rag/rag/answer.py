"""Answer synthesis placeholders for local subreddit RAG."""

from __future__ import annotations

from dataclasses import dataclass

from reddit_rag.rag.retrieve import RetrievalResult


@dataclass(frozen=True)
class Answer:
    """Placeholder answer contract with required source references."""

    question: str
    answer_text: str
    sources: list[RetrievalResult]


def answer_question(_question: str, _results: list[RetrievalResult]) -> Answer:
    """Generate a cited answer from retrieved context.

    TODO:
    - Build prompt context from retrieval results.
    - Call local LLM and preserve source references in output.
    """
    raise NotImplementedError("Answer generation is not implemented yet.")
