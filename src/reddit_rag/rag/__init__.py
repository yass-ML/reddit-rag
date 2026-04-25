"""RAG retrieval and answer generation."""

from reddit_rag.rag.answer import Answer, AnswerSource, answer_question, format_answer_markdown
from reddit_rag.rag.ollama_chat import ChatError, OllamaChatClient
from reddit_rag.rag.retrieve import RetrievalResult, retrieve_relevant_chunks

__all__ = [
    "Answer",
    "AnswerSource",
    "ChatError",
    "OllamaChatClient",
    "RetrievalResult",
    "answer_question",
    "format_answer_markdown",
    "retrieve_relevant_chunks",
]
