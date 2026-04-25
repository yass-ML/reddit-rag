import type {
  AskQuestionInput,
  ExportQueryResultInput,
  ExportQueryResultResponse,
  IngestionRun,
  RagAnswer,
  SourceEvidence,
  SubredditConfig,
  SubredditCreateInput,
} from "@/lib/contracts";

const DEFAULT_API_BASE_URL = "http://localhost:8000";

interface ApiErrorPayload {
  error?: {
    code?: string;
    message?: string;
  };
}

export class LiveApiError extends Error {
  code: string;
  status: number;

  constructor(message: string, { code, status }: { code: string; status: number }) {
    super(message);
    this.name = "LiveApiError";
    this.code = code;
    this.status = status;
  }
}

function apiBaseUrl() {
  return (
    process.env.NEXT_PUBLIC_REDDIT_RAG_API_BASE_URL?.replace(/\/+$/, "") ||
    DEFAULT_API_BASE_URL
  );
}

async function parseApiError(response: Response): Promise<LiveApiError> {
  let payload: ApiErrorPayload | null = null;
  try {
    payload = (await response.json()) as ApiErrorPayload;
  } catch {
    payload = null;
  }
  const code = payload?.error?.code || `http_${response.status}`;
  const message =
    payload?.error?.message || `Request failed with HTTP ${response.status}`;
  return new LiveApiError(message, { code, status: response.status });
}

function debugLog(
  hypothesisId: string,
  location: string,
  message: string,
  data: Record<string, unknown>,
  runId = "pre-fix",
) {
  // #region agent log
  fetch("http://localhost:7743/ingest/079bb857-3c02-4d26-9eab-35be537da386", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Debug-Session-Id": "e339a4" },
    body: JSON.stringify({
      sessionId: "e339a4",
      runId,
      hypothesisId,
      location,
      message,
      data,
      timestamp: Date.now(),
    }),
  }).catch(() => {});
  // #endregion
}

function serializeFetchThrown(err: unknown): Record<string, unknown> {
  if (!(err instanceof Error)) {
    return { stringified: String(err) };
  }
  const base: Record<string, unknown> = {
    name: err.name,
    message: err.message,
    cause:
      err.cause instanceof Error
        ? { name: err.cause.name, message: err.cause.message, code: (err.cause as NodeJS.ErrnoException).code }
        : err.cause != null
          ? String(err.cause)
          : null,
  };
  if (err instanceof AggregateError) {
    base.aggregateErrors = err.errors.map((e) =>
      e instanceof Error ? { name: e.name, message: e.message, code: (e as NodeJS.ErrnoException).code } : String(e),
    );
  }
  return base;
}

async function postJson<TResponse>(
  path: string,
  body: unknown,
): Promise<TResponse> {
  const base = apiBaseUrl();
  const url = `${base}${path}`;
  debugLog("H1-H2", "live-api.ts:postJson", "before fetch", {
    url,
    base,
    hasCustomEnv: Boolean(process.env.NEXT_PUBLIC_REDDIT_RAG_API_BASE_URL),
    method: "POST",
  });
  let response: Response;
  try {
    response = await fetch(url, {
      method: "POST",
      headers: {
        "content-type": "application/json",
      },
      body: JSON.stringify(body),
    });
  } catch (err) {
    debugLog("H1", "live-api.ts:postJson", "fetch threw", {
      url,
      ...serializeFetchThrown(err),
    });
    throw err;
  }
  if (!response.ok) {
    throw await parseApiError(response);
  }
  return (await response.json()) as TResponse;
}

async function getJson<TResponse>(path: string): Promise<TResponse> {
  const base = apiBaseUrl();
  const url = `${base}${path}`;
  debugLog("H1-H2", "live-api.ts:getJson", "before fetch", {
    url,
    base,
    hasCustomEnv: Boolean(process.env.NEXT_PUBLIC_REDDIT_RAG_API_BASE_URL),
    method: "GET",
  });
  let response: Response;
  try {
    response = await fetch(url, {
      method: "GET",
    });
  } catch (err) {
    debugLog("H1", "live-api.ts:getJson", "fetch threw", {
      url,
      ...serializeFetchThrown(err),
    });
    throw err;
  }
  if (!response.ok) {
    throw await parseApiError(response);
  }
  return (await response.json()) as TResponse;
}

async function deleteJson<TResponse>(path: string): Promise<TResponse> {
  const base = apiBaseUrl();
  const url = `${base}${path}`;
  debugLog("H1-H2", "live-api.ts:deleteJson", "before fetch", {
    url,
    base,
    hasCustomEnv: Boolean(process.env.NEXT_PUBLIC_REDDIT_RAG_API_BASE_URL),
    method: "DELETE",
  });
  let response: Response;
  try {
    response = await fetch(url, { method: "DELETE" });
  } catch (err) {
    debugLog("H1", "live-api.ts:deleteJson", "fetch threw", {
      url,
      ...serializeFetchThrown(err),
    });
    throw err;
  }
  if (!response.ok) {
    throw await parseApiError(response);
  }
  return (await response.json()) as TResponse;
}

export interface HealthResponse {
  status: string;
  embedding_model: string;
  generation_model: string;
  chroma_count: number;
}

export async function getHealth(): Promise<HealthResponse> {
  return getJson<HealthResponse>("/api/health");
}

export async function listLiveSubreddits(): Promise<SubredditConfig[]> {
  return getJson<SubredditConfig[]>("/api/subreddits");
}

export async function addLiveSubreddit(input: SubredditCreateInput): Promise<SubredditConfig[]> {
  return postJson<SubredditConfig[]>("/api/subreddits", {
    name: input.name.trim(),
    max_posts: input.max_posts,
    max_comments: input.max_comments,
  });
}

export async function removeLiveSubreddit(name: string): Promise<SubredditConfig[]> {
  const segment = encodeURIComponent(name.trim());
  return deleteJson<SubredditConfig[]>(`/api/subreddits/${segment}`);
}

export async function listLiveSources(limit = 50): Promise<SourceEvidence[]> {
  return getJson<SourceEvidence[]>(`/api/sources?limit=${encodeURIComponent(limit)}`);
}

export async function getLiveIngestionStatus(): Promise<IngestionRun> {
  return getJson<IngestionRun>("/api/ingestion/status");
}

export async function askLiveQuestion(input: AskQuestionInput): Promise<RagAnswer> {
  return postJson<RagAnswer>("/api/query", {
    question: input.question,
    subreddit: input.subreddit || null,
    top_k: input.top_k ?? 5,
  });
}

export async function exportLiveAnswer(
  input: ExportQueryResultInput,
): Promise<ExportQueryResultResponse> {
  return postJson<ExportQueryResultResponse>("/api/query/export", input);
}
