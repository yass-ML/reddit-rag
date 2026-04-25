from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from reddit_rag.api.schemas import SourceEvidenceModel
from reddit_rag.paths import resolve_exports_dir


def sanitize_query_label(query: str, *, max_length: int = 60) -> str:
    """Create a lowercase, path-safe label from a user question."""
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", query.strip().lower()).strip("-")
    if not normalized:
        return "query"
    return normalized[:max_length].strip("-") or "query"


def build_query_export_markdown(
    *,
    question: str,
    subreddit: str | None,
    answer_text: str,
    sources: list[SourceEvidenceModel],
) -> str:
    lines: list[str] = [
        "# RAG Query Result",
        "",
        "## Question",
        "",
        question.strip(),
        "",
        "## Subreddit Filter",
        "",
        subreddit.strip() if subreddit and subreddit.strip() else "All subreddits",
        "",
        "## Answer",
        "",
        answer_text.strip(),
        "",
        "## Sources",
    ]
    if not sources:
        lines.extend(["", "_No sources returned._"])
        return "\n".join(lines) + "\n"

    for source in sources:
        lines.extend(
            [
                "",
                f"### [{source.citation_index}] {source.source_title or '(untitled)'}",
                "",
                f"- **source type:** {source.source_type or '(unknown)'}",
                f"- **subreddit:** {source.subreddit or '(unknown)'}",
                f"- **permalink:** {source.source_permalink or '(missing)'}",
                f"- **relevance score:** {source.score:.4f}",
                f"- **reddit score:** {source.source_score}",
                f"- **chunk id:** {source.chunk_id or '(missing)'}",
                f"- **chunk index:** {source.metadata.chunk_index}",
                "- **excerpt:**",
                f"  > {(source.excerpt or source.text or '').replace(chr(10), ' ')}",
            ]
        )
    return "\n".join(lines) + "\n"


def write_query_export(
    *,
    question: str,
    subreddit: str | None,
    answer_text: str,
    sources: list[SourceEvidenceModel],
    now: datetime | None = None,
    exports_dir: Path | None = None,
) -> Path:
    resolved_dir = (exports_dir or resolve_exports_dir()).expanduser().resolve()
    resolved_dir.mkdir(parents=True, exist_ok=True)
    stamp = (now or datetime.now()).strftime("%Y%m%d-%H%M%S")
    label = sanitize_query_label(question)
    path = resolved_dir / f"{stamp}-{label}.md"
    markdown = build_query_export_markdown(
        question=question,
        subreddit=subreddit,
        answer_text=answer_text,
        sources=sources,
    )
    path.write_text(markdown, encoding="utf-8")
    return path
