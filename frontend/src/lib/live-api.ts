import type {
  AskQuestionInput,
  ExportQueryResultInput,
  ExportQueryResultResponse,
  RagAnswer,
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

async function postJson<TResponse>(
  path: string,
  body: unknown,
): Promise<TResponse> {
  const response = await fetch(`${apiBaseUrl()}${path}`, {
    method: "POST",
    headers: {
      "content-type": "application/json",
    },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw await parseApiError(response);
  }
  return (await response.json()) as TResponse;
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
