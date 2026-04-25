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
- PRAW
- SQLite
- Chroma
- Ollama

## Core Idea

The user chooses subreddits, ingests posts/comments, embeds the data locally, asks questions, and receives answers with source posts/comments as evidence.