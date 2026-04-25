import { PageHeader } from "@/components/page-header";
import { QueryWorkspace } from "@/components/query-workspace";
import {
  getChatThread,
  getLatestAnswer,
  listQueryTemplates,
  listQueryThemeInsights,
} from "@/lib/mock-api";
import { listLiveSources, listLiveSubreddits } from "@/lib/live-api";

export const dynamic = "force-dynamic";

export default async function QueryWorkspacePage() {
  const [answer, thread, sources, subreddits, templates, themes] = await Promise.all([
    getLatestAnswer(),
    getChatThread(),
    listLiveSources(),
    listLiveSubreddits(),
    listQueryTemplates(),
    listQueryThemeInsights(),
  ]);

  return (
    <div className="mx-auto max-w-7xl">
      <PageHeader
        eyebrow="Query Workspace"
        title="Chat with your local Reddit RAG index."
        description="Ask questions against indexed Chroma chunks. Supporting sources, themes, prompt templates, and retrieval metadata stay in the toggleable right context sidebar."
        badge="Live RAG"
      />
      <QueryWorkspace
        answer={answer}
        thread={thread}
        sources={sources}
        subreddits={subreddits}
        templates={templates}
        themes={themes}
      />
    </div>
  );
}
