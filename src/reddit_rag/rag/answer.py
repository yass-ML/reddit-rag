"""Answer synthesis: prompt + Ollama chat from retrieved context."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from reddit_rag.rag.prompts import build_rag_messages
from reddit_rag.rag.retrieve import RetrievalResult

if TYPE_CHECKING:
    from reddit_rag.rag.ollama_chat import OllamaChatClient

_NO_EVIDENCE_MESSAGE = (
    "No retrieved passages match this query in the selected scope. "
    "Try a different question, broaden retrieval, or ensure chunks are embedded for this subreddit."
)


def _str_from_meta(meta: dict[str, Any], key: str) -> str:
    v = meta.get(key)
    if isinstance(v, str):
        return v.strip()
    return ""


def _reddit_score_from_meta(meta: dict[str, Any]) -> int:
    v = meta.get("score")
    if isinstance(v, bool):
        return 0
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v)
    return 0


@dataclass(frozen=True)
class AnswerSource:
    """One cited source line item for CLI / API consumers (1-based index matches prompt [n])."""

    index: int
    excerpt: str
    title: str
    subreddit: str
    score: int
    permalink: str


def retrieval_results_to_answer_sources(results: list[RetrievalResult]) -> list[AnswerSource]:
    """Map retrieval hits to stable source fields for display and export."""
    out: list[AnswerSource] = []
    for i, r in enumerate(results, start=1):
        meta: dict[str, Any] = r.metadata if isinstance(r.metadata, dict) else {}
        sub = _str_from_meta(meta, "subreddit")
        excerpt = (r.text or "").strip()
        title = (r.source_title or "").strip() or _str_from_meta(meta, "title")
        perm = (r.source_permalink or "").strip() or _str_from_meta(meta, "permalink")
        out.append(
            AnswerSource(
                index=i,
                excerpt=excerpt,
                title=title,
                subreddit=sub,
                score=_reddit_score_from_meta(meta),
                permalink=perm,
            )
        )
    return out


@dataclass(frozen=True)
class Answer:
    """Cited answer from the chat model and structured sources used for the prompt."""

    question: str
    answer_text: str
    sources: list[AnswerSource]


def format_answer_markdown(answer: Answer) -> str:
    """Render answer plus numbered sources (Markdown) for CLI output."""
    lines: list[str] = [answer.answer_text.strip(), "", "## Sources"]
    if not answer.sources:
        lines.append("")
        lines.append("_No sources._")
        return "\n".join(lines)
    for s in answer.sources:
        lines.append("")
        lines.append(f"### [{s.index}]")
        lines.append(f"- **title:** {s.title or '_(empty)_'}")
        lines.append(f"- **subreddit:** {s.subreddit or '_(empty)_'}")
        lines.append(f"- **score:** {s.score}")
        lines.append(f"- **permalink:** {s.permalink or '_(empty)_'}")
        lines.append("- **excerpt:**")
        excerpt = s.excerpt if s.excerpt else "_(empty)_"
        lines.append(f"  > {excerpt.replace(chr(10), ' ')}")
    return "\n".join(lines)


def answer_question(
    question: str,
    results: list[RetrievalResult],
    *,
    chat_client: OllamaChatClient,
) -> Answer:
    """Generate a cited answer from retrieved context using the local chat model."""
    q = (question or "").strip()
    if not results:
        return Answer(question=q, answer_text=_NO_EVIDENCE_MESSAGE, sources=[])

    messages = build_rag_messages(q, results)
    text = chat_client.complete(messages)
    sources = retrieval_results_to_answer_sources(results)
    return Answer(question=q, answer_text=text, sources=sources)
