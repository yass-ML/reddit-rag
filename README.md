# Local Reddit RAG

A local-first research tool for querying selected Reddit subreddits with a local RAG pipeline.

## Current Status

Frontend-first build.

The first milestone is a polished clickable frontend using mocked data. Backend ingestion, embeddings, vector storage, and local LLM integration will be implemented later.

## Planned Stack

Frontend:
- Next.js
- TypeScript
- Tailwind
- shadcn/ui

Backend later:
- Python
- FastAPI
- Reddit JSON source adapter
- SQLite
- Chroma
- Ollama

## Core Idea

The user chooses subreddits, ingests posts/comments, embeds the data locally, asks questions, and receives answers with source posts/comments as evidence.

## Browser End-to-End Smoke Test

Run the automated checks first:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider
npm --prefix frontend run lint
npm --prefix frontend run test
npm --prefix frontend exec -- tsc --noEmit --incremental false -p frontend/tsconfig.json
```

Then build a small local index that the frontend can query:

```bash
.venv/bin/reddit-rag validate-config
.venv/bin/reddit-rag check-env
.venv/bin/reddit-rag ingest-raw --subreddit ClaudeAI --max-posts 2 --max-comments 20 --raw-dir /tmp/reddit-rag-raw
.venv/bin/reddit-rag normalize-posts --subreddit ClaudeAI --raw-dir /tmp/reddit-rag-raw --processed-dir /tmp/reddit-rag-processed
.venv/bin/reddit-rag normalize-comments --subreddit ClaudeAI --raw-dir /tmp/reddit-rag-raw --processed-dir /tmp/reddit-rag-processed
.venv/bin/reddit-rag create-chunks --subreddit ClaudeAI --processed-dir /tmp/reddit-rag-processed
.venv/bin/reddit-rag index-chunks --subreddit ClaudeAI --processed-dir /tmp/reddit-rag-processed --chroma-dir /tmp/reddit-rag-chroma
```

Start the local API and frontend in separate terminals:

```bash
REDDIT_RAG_CHROMA_DIR=/tmp/reddit-rag-chroma .venv/bin/python -m uvicorn reddit_rag.api.app:app --host 127.0.0.1 --port 8000
NEXT_PUBLIC_REDDIT_RAG_API_BASE_URL=http://127.0.0.1:8000 npm --prefix frontend run dev
```

Open `http://localhost:3000/query`, ask a question with the `ClaudeAI` filter, confirm cited sources render in the sidebar, then use `Export Markdown` and verify the saved path appears.