from __future__ import annotations

import os
import json
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from reddit_rag.config.load_config import (
    SUBREDDITS_FILENAME,
    SubredditEntry,
    SubredditsConfig,
    load_app_config,
    load_subreddits,
    save_subreddits,
)
from reddit_rag.embeddings.ollama_client import EmbeddingError, OllamaEmbeddingClient
from reddit_rag.env import load_dotenv_from_project
from reddit_rag.paths import (
    resolve_chroma_dir,
    resolve_config_dir,
    resolve_processed_dir,
    resolve_raw_dir,
)
from reddit_rag.processing.chunks_io import default_chunks_jsonl_path, load_records_from_jsonl
from reddit_rag.processing.comments import default_comments_jsonl_path
from reddit_rag.processing.posts import default_posts_jsonl_path
from reddit_rag.rag.answer import answer_question
from reddit_rag.rag.export import write_query_export
from reddit_rag.rag.ollama_chat import ChatError, OllamaChatClient
from reddit_rag.rag.retrieve import retrieve_relevant_chunks
from reddit_rag.storage import VectorStore

from reddit_rag.api.schemas import (
    ErrorResponse,
    HealthResponse,
    IngestionRunResponse,
    IngestionStepModel,
    QueryExportRequest,
    QueryExportResponse,
    QueryRequest,
    RagAnswerResponse,
    SourceEvidenceModel,
    SubredditConfigModel,
    SubredditCreateRequest,
    SubredditIngestionStatusModel,
    serialize_answer_response,
)

QueryRunner = Callable[[QueryRequest], RagAnswerResponse]
ExportWriter = Callable[[QueryExportRequest], QueryExportResponse]


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    payload = ErrorResponse(error={"code": code, "message": message})
    return JSONResponse(status_code=status_code, content=payload.model_dump())


def _cors_origins() -> list[str]:
    raw = os.environ.get("REDDIT_RAG_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
    return [item.strip() for item in raw.split(",") if item.strip()]


def _default_query_runner(request: QueryRequest) -> RagAnswerResponse:
    load_dotenv_from_project()
    config_dir = (
        Path(os.environ["REDDIT_RAG_CONFIG_DIR"]).expanduser().resolve()
        if os.environ.get("REDDIT_RAG_CONFIG_DIR")
        else None
    )
    cfg = load_app_config(config_dir=config_dir)
    host = os.environ.get("OLLAMA_HOST")
    embedding_client = OllamaEmbeddingClient(cfg.models.embedding_model, host=host)
    chat_client = OllamaChatClient(cfg.models.chat_model, host=host)
    vector_store = VectorStore(resolve_chroma_dir())

    retrieval_start = time.perf_counter()
    results = retrieve_relevant_chunks(
        request.question,
        embedding_client=embedding_client,
        vector_store=vector_store,
        top_k=request.top_k,
        subreddit=request.subreddit,
    )
    retrieval_ms = int((time.perf_counter() - retrieval_start) * 1000)
    answer = answer_question(request.question, results, chat_client=chat_client)

    return serialize_answer_response(
        answer=answer,
        retrieval_results=results,
        retrieval_ms=retrieval_ms,
        embedding_model=cfg.models.embedding_model,
        generation_model=cfg.models.chat_model,
        top_k=request.top_k,
        subreddit=request.subreddit,
    )


def _default_export_writer(request: QueryExportRequest) -> QueryExportResponse:
    path = write_query_export(
        question=request.question,
        subreddit=request.subreddit,
        answer_text=request.answer_text,
        sources=request.sources,
    )
    return QueryExportResponse(filename=path.name, path=str(path))


def _config_dir_from_env() -> Path | None:
    return (
        Path(os.environ["REDDIT_RAG_CONFIG_DIR"]).expanduser().resolve()
        if os.environ.get("REDDIT_RAG_CONFIG_DIR")
        else None
    )


def _subreddits_yaml_path() -> Path:
    base = _config_dir_from_env() or resolve_config_dir()
    return (base / SUBREDDITS_FILENAME).resolve()


def _safe_subreddit_id(name: str) -> str:
    safe = "".join(ch.lower() if ch.isalnum() else "-" for ch in name).strip("-")
    return f"sr-{safe or 'unknown'}"


def _record_count(path: Path) -> int:
    try:
        return len(load_records_from_jsonl(path))
    except (OSError, ValueError):
        return 0


def _read_checkpoint(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        with path.open(encoding="utf-8") as f:
            payload = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _source_from_chroma_hit(
    *,
    citation_index: int,
    chunk_id: str,
    document: str | None,
    metadata: dict[str, Any],
) -> SourceEvidenceModel:
    text = (document or "").strip()
    source_type = str(metadata.get("source_type") or "thread_context")
    title = str(metadata.get("title") or metadata.get("parent_post_title") or "").strip()
    permalink = str(metadata.get("permalink") or "").strip()
    score = metadata.get("score")
    source_score = int(score) if isinstance(score, (int, float)) and not isinstance(score, bool) else 0
    chunk_index = metadata.get("chunk_index")
    return SourceEvidenceModel(
        id=f"src-{citation_index:03d}",
        citation_index=citation_index,
        chunk_id=chunk_id,
        source_id=str(metadata.get("source_id") or ""),
        subreddit=str(metadata.get("subreddit") or ""),
        text=text,
        score=0.0,
        metadata={
            **metadata,
            "reddit_id": str(metadata.get("reddit_id") or ""),
            "post_reddit_id": str(metadata.get("post_reddit_id") or ""),
            "title": title,
            "permalink": permalink,
            "score": source_score,
            "chunk_index": int(chunk_index) if isinstance(chunk_index, (int, float)) else 0,
        },
        source_permalink=permalink,
        source_title=title,
        source_type=source_type,
        author=str(metadata.get("author") or "") or None,
        source_score=source_score,
        comment_count=(
            int(metadata["num_comments"])
            if isinstance(metadata.get("num_comments"), (int, float))
            and not isinstance(metadata.get("num_comments"), bool)
            else None
        ),
        excerpt=text,
        local_raw_path=str(metadata.get("raw_path") or ""),
        parent_post_title=str(metadata.get("parent_post_title") or ""),
        retrieval_metadata={"chunk_id": chunk_id, "chunk_index": int(chunk_index) if isinstance(chunk_index, (int, float)) else 0},
    )


def _health_response() -> HealthResponse:
    load_dotenv_from_project()
    cfg = load_app_config(config_dir=_config_dir_from_env())
    count = VectorStore(resolve_chroma_dir()).count()
    return HealthResponse(
        status="ready" if count > 0 else "not_indexed",
        embedding_model=cfg.models.embedding_model,
        generation_model=cfg.models.chat_model,
        chroma_count=count,
    )


def _subreddit_configs() -> list[SubredditConfigModel]:
    load_dotenv_from_project()
    cfg = load_app_config(config_dir=_config_dir_from_env())
    raw_root = resolve_raw_dir()
    processed_root = resolve_processed_dir()
    out: list[SubredditConfigModel] = []
    for entry in cfg.subreddits.subreddits:
        checkpoint = _read_checkpoint(raw_root / entry.name / "_checkpoint.json")
        chunks_ready = _record_count(default_chunks_jsonl_path(processed_root, entry.name))
        status = "ready" if chunks_ready > 0 else "not_started"
        last_ingested_at = str(checkpoint.get("updated_at")) if checkpoint and checkpoint.get("updated_at") else None
        out.append(
            SubredditConfigModel(
                id=_safe_subreddit_id(entry.name),
                name=entry.name,
                description=f"Configured local ingestion target for r/{entry.name}.",
                post_limit=entry.max_posts or 0,
                comment_depth=entry.max_comments or 0,
                status=status,
                last_ingested_at=last_ingested_at,
            )
        )
    return out


def _sources(limit: int = 50) -> list[SourceEvidenceModel]:
    store = VectorStore(resolve_chroma_dir())
    count = store.count()
    if count <= 0:
        return []
    got = store.collection.get(
        limit=max(1, min(limit, 200)),
        include=["documents", "metadatas"],
    )
    ids = got.get("ids") or []
    documents = got.get("documents") or []
    metadatas = got.get("metadatas") or []
    out: list[SourceEvidenceModel] = []
    for idx, chunk_id in enumerate(ids, start=1):
        metadata = metadatas[idx - 1] if idx - 1 < len(metadatas) else {}
        if not isinstance(metadata, dict):
            metadata = {}
        document = documents[idx - 1] if idx - 1 < len(documents) else None
        out.append(
            _source_from_chroma_hit(
                citation_index=idx,
                chunk_id=str(chunk_id),
                document=document if isinstance(document, str) else None,
                metadata=metadata,
            )
        )
    return out


def _ingestion_status() -> IngestionRunResponse:
    load_dotenv_from_project()
    cfg = load_app_config(config_dir=_config_dir_from_env())
    raw_root = resolve_raw_dir()
    processed_root = resolve_processed_dir()
    statuses: list[SubredditIngestionStatusModel] = []
    total_posts = 0
    total_comments = 0
    total_chunks = 0
    latest_finished: str | None = None

    for entry in cfg.subreddits.subreddits:
        checkpoint = _read_checkpoint(raw_root / entry.name / "_checkpoint.json")
        posts_seen = _record_count(default_posts_jsonl_path(processed_root, entry.name))
        comments_seen = _record_count(default_comments_jsonl_path(processed_root, entry.name))
        chunks_ready = _record_count(default_chunks_jsonl_path(processed_root, entry.name))
        total_posts += posts_seen
        total_comments += comments_seen
        total_chunks += chunks_ready
        updated_at = str(checkpoint.get("updated_at")) if checkpoint and checkpoint.get("updated_at") else None
        if updated_at and (latest_finished is None or updated_at > latest_finished):
            latest_finished = updated_at
        status = "ready" if chunks_ready > 0 else "processing" if posts_seen or comments_seen else "not_started"
        message = (
            f"{chunks_ready} chunks ready for retrieval."
            if chunks_ready
            else "No chunks indexed yet for this subreddit."
        )
        statuses.append(
            SubredditIngestionStatusModel(
                subreddit=entry.name,
                status=status,
                posts_seen=posts_seen,
                comments_seen=comments_seen,
                chunks_ready=chunks_ready,
                message=message,
            )
        )

    ready_steps = sum(1 for count in (total_posts, total_comments, total_chunks, VectorStore(resolve_chroma_dir()).count()) if count > 0)
    progress = int((ready_steps / 4) * 100)
    status = "ready" if progress == 100 else "processing" if progress > 0 else "not_started"
    return IngestionRunResponse(
        id="local-ingestion-status",
        started_at=latest_finished or _now_iso(),
        finished_at=latest_finished,
        status=status,
        progress=progress,
        steps=[
            IngestionStepModel(
                id="raw",
                label="Raw Reddit JSON",
                description="Thread/listing payloads saved under local raw storage.",
                status="ready" if any(_read_checkpoint(raw_root / e.name / "_checkpoint.json") for e in cfg.subreddits.subreddits) else "not_started",
                count=len(statuses),
            ),
            IngestionStepModel(
                id="normalized",
                label="Normalized records",
                description="Posts and comments normalized into processed JSONL files.",
                status="ready" if total_posts or total_comments else "not_started",
                count=total_posts + total_comments,
            ),
            IngestionStepModel(
                id="chunks",
                label="Chunks",
                description="Normalized records split into retrieval chunks.",
                status="ready" if total_chunks else "not_started",
                count=total_chunks,
            ),
            IngestionStepModel(
                id="vectors",
                label="Chroma vectors",
                description="Chunks embedded and persisted for semantic search.",
                status="ready" if ready_steps == 4 else "not_started",
                count=VectorStore(resolve_chroma_dir()).count(),
            ),
        ],
        subreddit_statuses=statuses,
    )


def create_app(
    *,
    query_runner: QueryRunner | None = None,
    export_writer: ExportWriter | None = None,
) -> FastAPI:
    app = FastAPI(title="Local Reddit RAG API")
    app.state.query_runner = query_runner or _default_query_runner
    app.state.export_writer = export_writer or _default_export_writer

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.get("/api/health", response_model=HealthResponse, responses={500: {"model": ErrorResponse}})
    def health() -> HealthResponse | JSONResponse:
        try:
            return _health_response()
        except Exception as e:
            return _error_response(500, "health_failed", str(e))

    @app.get(
        "/api/subreddits",
        response_model=list[SubredditConfigModel],
        responses={500: {"model": ErrorResponse}},
    )
    def subreddits() -> list[SubredditConfigModel] | JSONResponse:
        try:
            return _subreddit_configs()
        except Exception as e:
            return _error_response(500, "subreddits_failed", str(e))

    @app.post(
        "/api/subreddits",
        response_model=list[SubredditConfigModel],
        responses={
            400: {"model": ErrorResponse},
            409: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            500: {"model": ErrorResponse},
        },
    )
    def create_subreddit(body: SubredditCreateRequest) -> list[SubredditConfigModel] | JSONResponse:
        path = _subreddits_yaml_path()
        try:
            cfg = load_subreddits(path)
        except FileNotFoundError as e:
            return _error_response(400, "subreddits_file_missing", str(e))
        except ValueError as e:
            return _error_response(400, "subreddits_invalid", str(e))
        names_cf = {e.name.casefold() for e in cfg.subreddits}
        if body.name.casefold() in names_cf:
            return _error_response(409, "subreddit_exists", f"r/{body.name} is already configured")
        new_cfg = SubredditsConfig(
            subreddits=[
                *cfg.subreddits,
                SubredditEntry(
                    name=body.name,
                    max_posts=body.max_posts,
                    max_comments=body.max_comments,
                ),
            ]
        )
        try:
            save_subreddits(path, new_cfg)
        except (OSError, ValueError) as e:
            return _error_response(500, "subreddits_save_failed", str(e))
        try:
            return _subreddit_configs()
        except Exception as e:
            return _error_response(500, "subreddits_failed", str(e))

    @app.delete(
        "/api/subreddits/{name}",
        response_model=list[SubredditConfigModel],
        responses={
            400: {"model": ErrorResponse},
            404: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            500: {"model": ErrorResponse},
        },
    )
    def delete_subreddit(name: str) -> list[SubredditConfigModel] | JSONResponse:
        raw = name.strip()
        if raw.lower().startswith("r/"):
            raw = raw[2:].lstrip("/")
        path = _subreddits_yaml_path()
        try:
            cfg = load_subreddits(path)
        except FileNotFoundError as e:
            return _error_response(400, "subreddits_file_missing", str(e))
        except ValueError as e:
            return _error_response(400, "subreddits_invalid", str(e))
        key = raw.casefold()
        remaining = [e for e in cfg.subreddits if e.name.casefold() != key]
        if len(remaining) == len(cfg.subreddits):
            return _error_response(404, "subreddit_not_found", f"No configured entry for {name!r}")
        try:
            save_subreddits(path, SubredditsConfig(subreddits=remaining))
        except (OSError, ValueError) as e:
            return _error_response(500, "subreddits_save_failed", str(e))
        try:
            return _subreddit_configs()
        except Exception as e:
            return _error_response(500, "subreddits_failed", str(e))

    @app.get(
        "/api/sources",
        response_model=list[SourceEvidenceModel],
        responses={500: {"model": ErrorResponse}},
    )
    def sources(limit: int = 50) -> list[SourceEvidenceModel] | JSONResponse:
        try:
            return _sources(limit=limit)
        except Exception as e:
            return _error_response(500, "sources_failed", str(e))

    @app.get(
        "/api/ingestion/status",
        response_model=IngestionRunResponse,
        responses={500: {"model": ErrorResponse}},
    )
    def ingestion_status() -> IngestionRunResponse | JSONResponse:
        try:
            return _ingestion_status()
        except Exception as e:
            return _error_response(500, "ingestion_status_failed", str(e))

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return _error_response(422, "validation_failed", str(exc.errors()))

    @app.post(
        "/api/query",
        response_model=RagAnswerResponse,
        responses={400: {"model": ErrorResponse}, 422: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
    )
    def query(request: QueryRequest) -> RagAnswerResponse | JSONResponse:
        try:
            return app.state.query_runner(request)
        except ValueError as e:
            return _error_response(400, "invalid_query", str(e))
        except EmbeddingError as e:
            return _error_response(502, "embedding_failed", str(e))
        except ChatError as e:
            return _error_response(502, "chat_failed", str(e))
        except FileNotFoundError as e:
            return _error_response(400, "config_not_found", str(e))
        except Exception as e:
            return _error_response(500, "internal_error", str(e))

    @app.post(
        "/api/query/export",
        response_model=QueryExportResponse,
        responses={400: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    )
    def export_query(request: QueryExportRequest) -> QueryExportResponse | JSONResponse:
        try:
            return app.state.export_writer(request)
        except ValueError as e:
            return _error_response(400, "export_failed", str(e))
        except OSError as e:
            return _error_response(500, "export_failed", str(e))

    return app


app = create_app()
