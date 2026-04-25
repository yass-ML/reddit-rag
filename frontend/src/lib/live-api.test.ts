import { afterEach, describe, expect, it, vi } from "vitest";
import {
  askLiveQuestion,
  exportLiveAnswer,
  getHealth,
  getLiveIngestionStatus,
  listLiveSources,
  listLiveSubreddits,
} from "@/lib/live-api";
import type { SourceEvidence } from "@/lib/contracts";

const source: SourceEvidence = {
  id: "src-001",
  citation_index: 1,
  chunk_id: "chunk-1",
  source_id: "post_abc",
  source_type: "post",
  subreddit: "ClaudeAI",
  text: "source text",
  score: 0.91,
  metadata: {
    reddit_id: "abc",
    post_reddit_id: "abc",
    title: "Title",
    permalink: "/r/ClaudeAI/comments/abc/title/",
    score: 7,
    created_utc: 1700000000,
    chunk_index: 0,
  },
  source_permalink: "/r/ClaudeAI/comments/abc/title/",
  source_title: "Title",
  author: null,
  source_score: 7,
  excerpt: "source text",
  local_raw_path: "",
};

function mockFetch(payload: unknown, init?: ResponseInit) {
  const fetchMock = vi.fn().mockResolvedValue(
    new Response(JSON.stringify(payload), {
      status: init?.status ?? 200,
      headers: { "content-type": "application/json" },
    }),
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("live-api", () => {
  it("posts query requests to the live backend contract", async () => {
    const fetchMock = mockFetch({
      id: "answer-latest",
      question: "What changed?",
      answer_text: "Answer with [1].",
      sources: [source],
    });

    const result = await askLiveQuestion({
      workspace_id: "local",
      question: "What changed?",
      subreddit: "ClaudeAI",
      top_k: 3,
    });

    expect(result.sources).toHaveLength(1);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/query",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          question: "What changed?",
          subreddit: "ClaudeAI",
          top_k: 3,
        }),
      }),
    );
  });

  it("reads health, subreddits, sources, and ingestion status", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ status: "ready", embedding_model: "e", generation_model: "g", chroma_count: 1 })))
      .mockResolvedValueOnce(new Response(JSON.stringify([{ id: "sr-ClaudeAI", name: "ClaudeAI" }])))
      .mockResolvedValueOnce(new Response(JSON.stringify([source])))
      .mockResolvedValueOnce(new Response(JSON.stringify({ id: "local", status: "ready", progress: 100, steps: [], subreddit_statuses: [] })));
    vi.stubGlobal("fetch", fetchMock);

    await expect(getHealth()).resolves.toMatchObject({ chroma_count: 1 });
    await expect(listLiveSubreddits()).resolves.toMatchObject([{ name: "ClaudeAI" }]);
    await expect(listLiveSources(5)).resolves.toHaveLength(1);
    await expect(getLiveIngestionStatus()).resolves.toMatchObject({ progress: 100 });
    expect(fetchMock).toHaveBeenNthCalledWith(3, "http://localhost:8000/api/sources?limit=5", { method: "GET" });
  });

  it("posts export requests and parses backend errors", async () => {
    const exportFetch = mockFetch({ filename: "answer.md", path: "/tmp/answer.md" });
    await expect(
      exportLiveAnswer({
        question: "Question?",
        subreddit: null,
        answer_text: "Answer.",
        sources: [source],
      }),
    ).resolves.toMatchObject({ filename: "answer.md" });
    expect(exportFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/query/export",
      expect.objectContaining({ method: "POST" }),
    );

    mockFetch({ error: { code: "bad_query", message: "Bad query" } }, { status: 400 });
    await expect(askLiveQuestion({ workspace_id: "local", question: "x" })).rejects.toMatchObject({
      code: "bad_query",
      status: 400,
      message: "Bad query",
    });
  });
});
