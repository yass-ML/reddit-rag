from __future__ import annotations

import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from reddit_rag.config.load_config import load_app_config
from reddit_rag.embeddings.ollama_client import EmbeddingError, OllamaEmbeddingClient
from reddit_rag.env import load_dotenv_from_project
from reddit_rag.paths import resolve_chroma_dir
from reddit_rag.rag.answer import answer_question
from reddit_rag.rag.export import write_query_export
from reddit_rag.rag.ollama_chat import ChatError, OllamaChatClient
from reddit_rag.rag.retrieve import retrieve_relevant_chunks
from reddit_rag.storage import VectorStore

from reddit_rag.api.schemas import (
    ErrorResponse,
    QueryExportRequest,
    QueryExportResponse,
    QueryRequest,
    RagAnswerResponse,
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
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

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
