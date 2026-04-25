export type SourceType = "post" | "comment" | "thread_context";

export type IngestionState =
  | "not_started"
  | "queued"
  | "mocked"
  | "ingesting"
  | "processing"
  | "ready"
  | "needs_attention";

export interface NormalizedPost {
  id: string;
  reddit_id: string;
  subreddit: string;
  title: string;
  body: string;
  author: string | null;
  score: number;
  num_comments: number;
  created_utc: string;
  permalink: string;
  url: string | null;
  raw_path: string;
}

export interface NormalizedComment {
  id: string;
  reddit_id: string;
  post_reddit_id: string;
  parent_reddit_id: string;
  subreddit: string;
  body: string;
  author: string | null;
  score: number;
  created_utc: string;
  permalink: string;
  raw_path: string;
}

export interface ChunkMetadata {
  reddit_id: string;
  post_reddit_id: string;
  title: string;
  permalink: string;
  score: number;
  created_utc: string | number | null;
  chunk_index: number;
  chunk_size?: number;
  chunk_overlap?: number;
}

export interface Chunk {
  id: string;
  source_type: SourceType;
  source_id: string;
  subreddit: string;
  text: string;
  metadata: ChunkMetadata;
}

export interface RetrievalResult {
  chunk_id: string;
  text: string;
  score: number;
  metadata: ChunkMetadata;
  source_permalink: string;
  source_title: string;
  source_type: SourceType;
}

export interface SourceEvidence extends RetrievalResult {
  id: string;
  citation_index?: number;
  source_id: string;
  subreddit: string;
  author: string | null;
  source_score: number;
  comment_count?: number;
  excerpt: string;
  local_raw_path: string;
  parent_post_title?: string;
  retrieval_metadata?: Record<string, string | number | boolean | null>;
}

export interface RagAnswer {
  id: string;
  question: string;
  answer_text: string;
  sources: SourceEvidence[];
  retrieval_debug_optional?: {
    retrieval_ms: number;
    embedding_model: string;
    generation_model: string;
    top_k: number;
    subreddit?: string | null;
    mocked?: boolean;
  };
}

export interface ResearchWorkspace {
  id: string;
  name: string;
  goal: string;
  created_at: string;
  updated_at: string;
  status: IngestionState;
  subreddit_ids: string[];
  recent_question_ids: string[];
  stats: {
    posts: number;
    comments: number;
    chunks: number;
    sources_ready: number;
  };
}

export interface SubredditConfig {
  id: string;
  workspace_id: string;
  name: string;
  description: string;
  post_limit: number;
  comment_depth: number;
  timeframe: "week" | "month" | "year" | "all";
  status: IngestionState;
  last_ingested_at: string | null;
}

export interface IngestionRun {
  id: string;
  workspace_id: string;
  started_at: string;
  finished_at: string | null;
  status: IngestionState;
  progress: number;
  steps: IngestionStep[];
  subreddit_statuses: SubredditIngestionStatus[];
}

export interface IngestionStep {
  id: string;
  label: string;
  description: string;
  status: IngestionState;
  count?: number;
}

export interface SubredditIngestionStatus {
  subreddit: string;
  status: IngestionState;
  posts_seen: number;
  comments_seen: number;
  chunks_ready: number;
  message: string;
}

export interface QueryTemplate {
  id: string;
  title: string;
  prompt: string;
  category: "themes" | "pain_points" | "vocabulary" | "objections";
}

export interface QueryThemeInsight {
  id: string;
  title: string;
  summary: string;
  source_ids: string[];
  confidence: "low" | "medium" | "high";
}

export interface ChatMessage {
  id: string;
  role: "system" | "user" | "assistant";
  content: string;
  created_at: string;
  citation_source_ids?: string[];
}

export interface ChatThread {
  id: string;
  workspace_id: string;
  title: string;
  messages: ChatMessage[];
}

export interface RagQuestion {
  id: string;
  workspace_id: string;
  question: string;
  created_at: string;
  answer_id: string;
}

export interface CreateWorkspaceInput {
  name: string;
  goal: string;
  seed_subreddits: string[];
}

export interface AskQuestionInput {
  workspace_id: string;
  question: string;
  subreddit?: string;
  top_k?: number;
}

export interface ExportQueryResultInput {
  question: string;
  subreddit?: string | null;
  answer_text: string;
  sources: SourceEvidence[];
}

export interface ExportQueryResultResponse {
  filename: string;
  path: string;
}
