from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from reddit_rag.rag.answer import Answer
from reddit_rag.rag.retrieve import RetrievalResult


SourceType = Literal["post", "comment", "thread_context"]


class QueryRequest(BaseModel):
    question: str = Field(min_length=1)
    subreddit: str | None = None
    top_k: int = Field(default=5, gt=0, le=50)

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("question must be a non-empty string")
        return stripped

    @field_validator("subreddit")
    @classmethod
    def empty_subreddit_is_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class ChunkMetadataModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    reddit_id: str = ""
    post_reddit_id: str = ""
    title: str = ""
    permalink: str = ""
    score: int = 0
    created_utc: str | float | int | None = None
    chunk_index: int = 0


class RetrievalDebugModel(BaseModel):
    retrieval_ms: int
    embedding_model: str
    generation_model: str
    top_k: int
    subreddit: str | None = None
    mocked: bool = False


class SourceEvidenceModel(BaseModel):
    id: str
    citation_index: int
    chunk_id: str
    source_id: str
    subreddit: str
    text: str
    score: float
    metadata: ChunkMetadataModel
    source_permalink: str
    source_title: str
    source_type: SourceType | str
    author: str | None = None
    source_score: int = 0
    comment_count: int | None = None
    excerpt: str
    local_raw_path: str = ""
    parent_post_title: str = ""
    retrieval_metadata: dict[str, Any] = Field(default_factory=dict)


class RagAnswerResponse(BaseModel):
    id: str
    question: str
    answer_text: str
    sources: list[SourceEvidenceModel]
    retrieval_debug_optional: RetrievalDebugModel | None = None


class QueryExportRequest(BaseModel):
    question: str = Field(min_length=1)
    subreddit: str | None = None
    answer_text: str
    sources: list[SourceEvidenceModel] = Field(default_factory=list)

    @field_validator("question")
    @classmethod
    def export_question_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("question must be a non-empty string")
        return stripped

    @field_validator("subreddit")
    @classmethod
    def export_empty_subreddit_is_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class QueryExportResponse(BaseModel):
    filename: str
    path: str


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


def _str_from_meta(meta: dict[str, Any], key: str) -> str:
    value = meta.get(key)
    if isinstance(value, str):
        return value.strip()
    return ""


def _int_from_meta(meta: dict[str, Any], key: str) -> int:
    value = meta.get(key)
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return 0


def _optional_int_from_meta(meta: dict[str, Any], key: str) -> int | None:
    value = meta.get(key)
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return None


def _created_utc_from_meta(meta: dict[str, Any]) -> str | float | int | None:
    value = meta.get("created_utc")
    if isinstance(value, (str, int, float)) and not isinstance(value, bool):
        return value
    return None


def retrieval_result_to_source_evidence(
    result: RetrievalResult,
    *,
    citation_index: int,
) -> SourceEvidenceModel:
    meta = result.metadata if isinstance(result.metadata, dict) else {}
    title = (result.source_title or "").strip() or _str_from_meta(meta, "title")
    permalink = (result.source_permalink or "").strip() or _str_from_meta(meta, "permalink")
    source_type = (result.source_type or "").strip() or _str_from_meta(meta, "source_type")
    source_id = _str_from_meta(meta, "source_id")
    subreddit = _str_from_meta(meta, "subreddit")
    source_score = _int_from_meta(meta, "score")
    parent_title = (
        _str_from_meta(meta, "parent_post_title")
        or _str_from_meta(meta, "post_title")
        or (title if source_type == "comment" else "")
    )
    chunk_index = _int_from_meta(meta, "chunk_index")
    metadata = ChunkMetadataModel(
        reddit_id=_str_from_meta(meta, "reddit_id"),
        post_reddit_id=_str_from_meta(meta, "post_reddit_id"),
        title=title,
        permalink=permalink,
        score=source_score,
        created_utc=_created_utc_from_meta(meta),
        chunk_index=chunk_index,
        **{
            key: value
            for key, value in meta.items()
            if key
            not in {
                "reddit_id",
                "post_reddit_id",
                "title",
                "permalink",
                "score",
                "created_utc",
                "chunk_index",
            }
        },
    )
    text = (result.text or "").strip()
    return SourceEvidenceModel(
        id=f"src-{citation_index:03d}",
        citation_index=citation_index,
        chunk_id=result.chunk_id,
        source_id=source_id,
        subreddit=subreddit,
        text=text,
        score=float(result.score),
        metadata=metadata,
        source_permalink=permalink,
        source_title=title or parent_title,
        source_type=source_type or "thread_context",
        author=_str_from_meta(meta, "author") or None,
        source_score=source_score,
        comment_count=_optional_int_from_meta(meta, "num_comments"),
        excerpt=text,
        local_raw_path=_str_from_meta(meta, "raw_path"),
        parent_post_title=parent_title,
        retrieval_metadata={
            "chunk_id": result.chunk_id,
            "similarity_score": float(result.score),
            "chunk_index": chunk_index,
        },
    )


def serialize_answer_response(
    *,
    answer: Answer,
    retrieval_results: list[RetrievalResult],
    retrieval_ms: int,
    embedding_model: str,
    generation_model: str,
    top_k: int,
    subreddit: str | None,
) -> RagAnswerResponse:
    sources = [
        retrieval_result_to_source_evidence(result, citation_index=i)
        for i, result in enumerate(retrieval_results, start=1)
    ]
    return RagAnswerResponse(
        id="answer-latest",
        question=answer.question,
        answer_text=answer.answer_text,
        sources=sources,
        retrieval_debug_optional=RetrievalDebugModel(
            retrieval_ms=retrieval_ms,
            embedding_model=embedding_model,
            generation_model=generation_model,
            top_k=top_k,
            subreddit=subreddit,
        ),
    )
