import type {
  AskQuestionInput,
  ChatThread,
  CreateWorkspaceInput,
  QueryThemeInsight,
  RagAnswer,
  ResearchWorkspace,
  SourceEvidence,
  SubredditConfig,
} from "@/lib/contracts";
import {
  answers,
  chatThread,
  ingestionRun,
  queryTemplates,
  queryThemeInsights,
  questions,
  sources,
  subredditConfigs,
  workspaces,
} from "@/lib/mock-data";

const MOCK_DELAY_MS = 80;

async function mockDelay() {
  await new Promise((resolve) => setTimeout(resolve, MOCK_DELAY_MS));
}

export async function listWorkspaces(): Promise<ResearchWorkspace[]> {
  await mockDelay();
  return workspaces;
}

export async function getWorkspace(
  workspaceId = "ws-founder-research",
): Promise<ResearchWorkspace> {
  await mockDelay();
  return workspaces.find((workspace) => workspace.id === workspaceId) ?? workspaces[0];
}

export async function createWorkspace(
  input: CreateWorkspaceInput,
): Promise<ResearchWorkspace> {
  await mockDelay();

  return {
    id: "ws-new-local-draft",
    name: input.name || "Untitled research space",
    goal: input.goal || "Draft local research goal",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    status: "not_started",
    subreddit_ids: input.seed_subreddits.map((name) => `draft-${name}`),
    recent_question_ids: [],
    stats: {
      posts: 0,
      comments: 0,
      chunks: 0,
      sources_ready: 0,
    },
  };
}

export async function listSubreddits(
  workspaceId = "ws-founder-research",
): Promise<SubredditConfig[]> {
  await mockDelay();
  return subredditConfigs.filter((config) => config.workspace_id === workspaceId);
}

export async function getIngestionStatus() {
  await mockDelay();
  return ingestionRun;
}

export async function listQueryTemplates() {
  await mockDelay();
  return queryTemplates;
}

export async function getChatThread(): Promise<ChatThread> {
  await mockDelay();
  return chatThread;
}

export async function listQueryThemeInsights(): Promise<QueryThemeInsight[]> {
  await mockDelay();
  return queryThemeInsights;
}

export async function listRecentQuestions() {
  await mockDelay();
  return questions;
}

export async function askQuestion(input: AskQuestionInput): Promise<RagAnswer> {
  await mockDelay();
  return {
    ...answers[0],
    question: input.question || answers[0].question,
    retrieval_debug_optional: {
      ...answers[0].retrieval_debug_optional!,
      top_k: input.top_k ?? answers[0].retrieval_debug_optional!.top_k,
    },
  };
}

export async function getLatestAnswer(): Promise<RagAnswer> {
  await mockDelay();
  return answers[0];
}

export async function listSources(): Promise<SourceEvidence[]> {
  await mockDelay();
  return sources;
}

export async function getSource(sourceId = "src-001"): Promise<SourceEvidence> {
  await mockDelay();
  return sources.find((source) => source.id === sourceId) ?? sources[0];
}
