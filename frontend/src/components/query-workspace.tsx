"use client";

import { useMemo, useState } from "react";
import {
  Download,
  Loader2,
  PanelRightClose,
  PanelRightOpen,
  Sparkles,
} from "lucide-react";
import type {
  ChatMessage as ChatMessageType,
  ChatThread,
  QueryTemplate,
  QueryThemeInsight,
  RagAnswer,
  SourceEvidence,
  SubredditConfig,
} from "@/lib/contracts";
import { ChatComposer } from "@/components/chat-composer";
import { ChatMessage } from "@/components/chat-message";
import { QueryEvidenceSidebar } from "@/components/query-evidence-sidebar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { askLiveQuestion, exportLiveAnswer, LiveApiError } from "@/lib/live-api";
import { cn } from "@/lib/utils";

export function QueryWorkspace({
  answer,
  thread,
  sources,
  subreddits,
  templates,
  themes,
}: {
  answer: RagAnswer;
  thread: ChatThread;
  sources: SourceEvidence[];
  subreddits: SubredditConfig[];
  templates: QueryTemplate[];
  themes: QueryThemeInsight[];
}) {
  const [messages, setMessages] = useState<ChatMessageType[]>(
    thread.messages.filter((message) => !message.content.toLowerCase().includes("mock")),
  );
  const [currentAnswer, setCurrentAnswer] = useState(answer);
  const [currentSources, setCurrentSources] = useState(sources);
  const [selectedSubreddit, setSelectedSubreddit] = useState("");
  const [currentSubredditFilter, setCurrentSubredditFilter] = useState<string | null>(
    null,
  );
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [hasLiveAnswer, setHasLiveAnswer] = useState(false);
  const [exportState, setExportState] = useState<
    | { status: "idle" }
    | { status: "saving" }
    | { status: "saved"; path: string }
    | { status: "error"; message: string }
  >({ status: "idle" });

  const subredditOptions = useMemo(
    () => Array.from(new Set(subreddits.map((subreddit) => subreddit.name))).sort(),
    [subreddits],
  );

  const activeSourceIds = useMemo(
    () => new Set(currentSources.map((source) => source.id)),
    [currentSources],
  );

  async function handleSubmit(content: string) {
    const createdAt = new Date().toISOString();
    const loadingId = `msg-assistant-loading-${Date.now()}`;
    const userMessage: ChatMessageType = {
      id: `msg-user-${Date.now()}`,
      role: "user",
      content,
      created_at: createdAt,
    };
    const loadingMessage: ChatMessageType = {
      id: loadingId,
      role: "assistant",
      content: "Retrieving relevant chunks and asking the local model...",
      created_at: new Date().toISOString(),
    };

    setErrorMessage(null);
    setExportState({ status: "idle" });
    setIsLoading(true);
    setMessages((current) => [...current, userMessage, loadingMessage]);

    try {
      const liveAnswer = await askLiveQuestion({
        workspace_id: thread.workspace_id,
        question: content,
        subreddit: selectedSubreddit || undefined,
        top_k: 5,
      });
      const assistantMessage: ChatMessageType = {
        id: `msg-assistant-${Date.now()}`,
        role: "assistant",
        content: liveAnswer.answer_text,
        created_at: new Date().toISOString(),
        citation_source_ids: liveAnswer.sources.map((source) => source.id),
      };
      setCurrentAnswer(liveAnswer);
      setCurrentSources(liveAnswer.sources);
      setCurrentSubredditFilter(selectedSubreddit || null);
      setHasLiveAnswer(true);
      setMessages((current) =>
        current.map((message) =>
          message.id === loadingId ? assistantMessage : message,
        ),
      );
    } catch (error) {
      const message =
        error instanceof LiveApiError
          ? `${error.code}: ${error.message}`
          : error instanceof Error
            ? error.message
            : "Query failed.";
      setErrorMessage(message);
      setMessages((current) =>
        current.map((chatMessage) =>
          chatMessage.id === loadingId
            ? {
                id: `msg-system-${Date.now()}`,
                role: "system",
                content: `Query failed: ${message}`,
                created_at: new Date().toISOString(),
              }
            : chatMessage,
        ),
      );
    } finally {
      setIsLoading(false);
    }
  }

  async function handleExport() {
    if (!hasLiveAnswer) {
      return;
    }
    setExportState({ status: "saving" });
    try {
      const result = await exportLiveAnswer({
        question: currentAnswer.question,
        subreddit: currentSubredditFilter,
        answer_text: currentAnswer.answer_text,
        sources: currentSources,
      });
      setExportState({ status: "saved", path: result.path });
    } catch (error) {
      const message =
        error instanceof LiveApiError
          ? `${error.code}: ${error.message}`
          : error instanceof Error
            ? error.message
            : "Export failed.";
      setExportState({ status: "error", message });
    }
  }

  return (
    <div
      className={cn(
        "grid gap-5",
        isSidebarOpen ? "xl:grid-cols-[minmax(0,1fr)_430px]" : "xl:grid-cols-1",
      )}
    >
      <Card className="min-h-[calc(100vh-12rem)] overflow-hidden border-primary/10 bg-white/90">
        <CardHeader className="border-b bg-white/80">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="mb-2 flex flex-wrap items-center gap-2">
                <Badge variant="success">Live RAG</Badge>
                <Badge variant="secondary">{thread.title}</Badge>
              </div>
              <CardTitle className="flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-primary" aria-hidden />
                Chat with subreddit evidence
              </CardTitle>
              <CardDescription>
                Ask questions against indexed Chroma chunks while keeping
                citations and evidence available in the right sidebar.
              </CardDescription>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={handleExport}
                disabled={!hasLiveAnswer || exportState.status === "saving"}
              >
                {exportState.status === "saving" ? (
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                ) : (
                  <Download className="h-4 w-4" aria-hidden />
                )}
                Export Markdown
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => setIsSidebarOpen((current) => !current)}
                aria-expanded={isSidebarOpen}
              >
                {isSidebarOpen ? (
                  <PanelRightClose className="h-4 w-4" aria-hidden />
                ) : (
                  <PanelRightOpen className="h-4 w-4" aria-hidden />
                )}
                {isSidebarOpen ? "Hide context" : "Show context"}
              </Button>
            </div>
          </div>
        </CardHeader>

        <CardContent className="flex min-h-[calc(100vh-18rem)] flex-col p-0">
          <ScrollArea className="flex-1">
            <div className="space-y-5 p-4 sm:p-6">
              {messages.map((message) => (
                <ChatMessage
                  key={message.id}
                  message={{
                    ...message,
                    citation_source_ids: message.citation_source_ids?.filter((id) =>
                      activeSourceIds.has(id),
                    ),
                  }}
                  sources={currentSources}
                />
              ))}
            </div>
          </ScrollArea>

          <div className="border-t bg-slate-50/80 p-4">
            {errorMessage ? (
              <div className="mb-3 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                {errorMessage}
              </div>
            ) : null}
            {exportState.status === "saved" ? (
              <div className="mb-3 rounded-xl border border-green-200 bg-green-50 p-3 text-sm text-green-700">
                Export saved to <span className="font-mono">{exportState.path}</span>
              </div>
            ) : null}
            {exportState.status === "error" ? (
              <div className="mb-3 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                {exportState.message}
              </div>
            ) : null}
            <ChatComposer
              onSubmit={handleSubmit}
              disabled={isLoading}
              selectedSubreddit={selectedSubreddit}
              subredditOptions={subredditOptions}
              onSubredditChange={setSelectedSubreddit}
              helperText={
                isLoading
                  ? "Waiting for retrieval and local generation."
                  : "Press Ctrl+Enter or Cmd+Enter to send."
              }
              submitLabel={isLoading ? "Asking..." : "Ask RAG"}
            />
          </div>
        </CardContent>
      </Card>

      {isSidebarOpen ? (
        <div className="xl:sticky xl:top-8 xl:h-[calc(100vh-4rem)]">
          <QueryEvidenceSidebar
            answer={currentAnswer}
            sources={currentSources}
            templates={templates}
            themes={themes}
            onClose={() => setIsSidebarOpen(false)}
          />
        </div>
      ) : null}
    </div>
  );
}
