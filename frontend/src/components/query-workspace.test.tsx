import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { QueryWorkspace } from "@/components/query-workspace";
import type {
  ChatThread,
  QueryTemplate,
  QueryThemeInsight,
  RagAnswer,
  SourceEvidence,
  SubredditConfig,
} from "@/lib/contracts";

const source: SourceEvidence = {
  id: "src-001",
  citation_index: 1,
  chunk_id: "chunk-1",
  source_id: "post_abc",
  source_type: "post",
  subreddit: "ClaudeAI",
  text: "Grounded source text",
  score: 0.91,
  metadata: {
    reddit_id: "abc",
    post_reddit_id: "abc",
    title: "Claude thread",
    permalink: "/r/ClaudeAI/comments/abc/claude_thread/",
    score: 7,
    created_utc: 1700000000,
    chunk_index: 0,
  },
  source_permalink: "/r/ClaudeAI/comments/abc/claude_thread/",
  source_title: "Claude thread",
  author: null,
  source_score: 7,
  excerpt: "Grounded source text",
  local_raw_path: "",
};

const initialAnswer: RagAnswer = {
  id: "answer-initial",
  question: "Initial?",
  answer_text: "Initial answer.",
  sources: [],
};

const thread: ChatThread = {
  id: "thread-1",
  workspace_id: "local",
  title: "Local RAG",
  messages: [],
};

const subreddits: SubredditConfig[] = [
  {
    id: "sr-ClaudeAI",
    workspace_id: "local",
    name: "ClaudeAI",
    description: "Configured local ingestion target.",
    post_limit: 20,
    comment_depth: 100,
    timeframe: "all",
    status: "ready",
    last_ingested_at: null,
  },
];

const templates: QueryTemplate[] = [];
const themes: QueryThemeInsight[] = [];

function renderWorkspace() {
  render(
    <QueryWorkspace
      answer={initialAnswer}
      thread={thread}
      sources={[]}
      subreddits={subreddits}
      templates={templates}
      themes={themes}
    />,
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("QueryWorkspace", () => {
  it("submits a live query, renders citations, and exports markdown", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            id: "answer-latest",
            question: "What do users want?",
            answer_text: "Users want reliable citations [1].",
            sources: [source],
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ filename: "answer.md", path: "/tmp/answer.md" }), {
          status: 200,
          headers: { "content-type": "application/json" },
        }),
      );
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    renderWorkspace();
    await user.selectOptions(screen.getByLabelText(/subreddit filter/i), "ClaudeAI");
    await user.type(
      screen.getByLabelText(/ask a question/i),
      "What do users want?",
    );
    await user.click(screen.getByRole("button", { name: /ask rag/i }));

    await screen.findByText("Users want reliable citations [1].");
    expect(screen.getAllByText("Source 1").length).toBeGreaterThan(0);
    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "http://localhost:8000/api/query",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          question: "What do users want?",
          subreddit: "ClaudeAI",
          top_k: 5,
        }),
      }),
    );

    await user.click(screen.getByRole("button", { name: /export markdown/i }));
    await waitFor(() => {
      expect(fetchMock).toHaveBeenNthCalledWith(
        2,
        "http://localhost:8000/api/query/export",
        expect.objectContaining({ method: "POST" }),
      );
    });
    expect(await screen.findByText(/Export saved to/)).toBeInTheDocument();
  });
});
