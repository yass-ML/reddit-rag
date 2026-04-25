"""RAG prompt construction for Ollama chat: system rules and numbered user context."""

from __future__ import annotations

from typing import TypedDict

from reddit_rag.rag.retrieve import RetrievalResult


class OllamaMessage(TypedDict):
    role: str
    content: str


# Citations: use [1], [2] in the answer; matches source numbering in the user message.
RAG_SYSTEM_MESSAGE = """You are a careful assistant that answers using ONLY the numbered sources provided in the user message. Do not use outside knowledge, common sense not stated in the sources, or the web.

When you rely on a fact from a source, cite it in your answer with the source number in square brackets, e.g. [1] for the first source, [2] for the second, and so on. You may cite the same number more than once if needed.

If the sources are missing, empty, or do not contain enough information to answer the question, say so clearly. Do not invent details to fill gaps."""


def _format_source_block(index: int, r: RetrievalResult) -> str:
    lines: list[str] = [f"--- Source [{index}] ---"]
    st = (r.source_type or "").strip()
    if st:
        lines.append(f"source_type: {st}")
    t = (r.source_title or "").strip()
    if t:
        lines.append(f"title: {t}")
    p = (r.source_permalink or "").strip()
    if p:
        lines.append(f"permalink: {p}")
    sub = r.metadata.get("subreddit")
    if isinstance(sub, str) and sub.strip():
        lines.append(f"subreddit: {sub.strip()}")
    score_v = r.metadata.get("score")
    if isinstance(score_v, bool):
        pass
    elif isinstance(score_v, int):
        lines.append(f"source_score: {score_v}")
    elif isinstance(score_v, float):
        lines.append(f"source_score: {int(score_v)}")
    text = (r.text or "").strip() if r.text else ""
    lines.append("text:")
    lines.append(text if text else "[empty text]")
    return "\n".join(lines)


def build_rag_user_content(question: str, results: list[RetrievalResult]) -> str:
    """User message body: the question and numbered retrieved passages, or a no-sources notice."""
    q = (question or "").strip()
    if not q:
        q = "[empty question]"

    parts: list[str] = [f"Question:\n{q}"]

    if not results:
        parts.append(
            "Retrieved sources:\n"
            "No passages were retrieved. You must not invent content; state that the evidence is insufficient."
        )
        return "\n\n".join(parts)

    blocks: list[str] = []
    for i, r in enumerate(results, start=1):
        blocks.append(_format_source_block(i, r))
    parts.append("Retrieved sources (use only these; cite with [1], [2], … in your answer):\n" + "\n\n".join(blocks))
    return "\n\n".join(parts)


def build_rag_messages(question: str, results: list[RetrievalResult]) -> list[OllamaMessage]:
    """Ollama-style message list: system (rules) and user (question + numbered context)."""
    return [
        {"role": "system", "content": RAG_SYSTEM_MESSAGE},
        {"role": "user", "content": build_rag_user_content(question, results)},
    ]
