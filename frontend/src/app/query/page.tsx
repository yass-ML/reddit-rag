import { PageHeader } from "@/components/page-header";
import { QueryWorkspace } from "@/components/query-workspace";
import {
  getChatThread,
  getLatestAnswer,
  listQueryTemplates,
  listQueryThemeInsights,
  listSources,
} from "@/lib/mock-api";

export default async function QueryWorkspacePage() {
  const [answer, thread, sources, templates, themes] = await Promise.all([
    getLatestAnswer(),
    getChatThread(),
    listSources(),
    listQueryTemplates(),
    listQueryThemeInsights(),
  ]);

  return (
    <div className="mx-auto max-w-7xl">
      <PageHeader
        eyebrow="Query Workspace"
        title="Chat with a mocked local research assistant."
        description="Discuss subreddit findings in an LLM-style workspace. Supporting sources, themes, prompt templates, and retrieval metadata stay in the toggleable right context sidebar."
        badge="RAG mocked"
      />
      <QueryWorkspace
        answer={answer}
        thread={thread}
        sources={sources}
        templates={templates}
        themes={themes}
      />
    </div>
  );
}
