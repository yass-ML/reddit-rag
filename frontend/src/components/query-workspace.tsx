"use client";

import { useMemo, useState } from "react";
import { PanelRightClose, PanelRightOpen, Sparkles } from "lucide-react";
import type {
  ChatMessage as ChatMessageType,
  ChatThread,
  QueryTemplate,
  QueryThemeInsight,
  RagAnswer,
  SourceEvidence,
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
import { cn } from "@/lib/utils";

export function QueryWorkspace({
  answer,
  thread,
  sources,
  templates,
  themes,
}: {
  answer: RagAnswer;
  thread: ChatThread;
  sources: SourceEvidence[];
  templates: QueryTemplate[];
  themes: QueryThemeInsight[];
}) {
  const [messages, setMessages] = useState<ChatMessageType[]>(thread.messages);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  const activeSourceIds = useMemo(
    () => new Set(sources.map((source) => source.id)),
    [sources],
  );

  function handleSubmit(content: string) {
    const createdAt = new Date().toISOString();
    const userMessage: ChatMessageType = {
      id: `msg-user-${Date.now()}`,
      role: "user",
      content,
      created_at: createdAt,
    };
    const assistantMessage: ChatMessageType = {
      id: `msg-assistant-${Date.now()}`,
      role: "assistant",
      content:
        "Mock response: I would retrieve fresh chunks for that follow-up, compare them against the current source trail, and answer with citations. For now, this prototype reuses the same fixture-backed evidence so you can evaluate the chat workflow before the backend exists.",
      created_at: new Date(Date.now() + 1000).toISOString(),
      citation_source_ids: sources.slice(0, 2).map((source) => source.id),
    };

    setMessages((current) => [...current, userMessage, assistantMessage]);
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
                <Badge variant="warning">Mock conversation</Badge>
                <Badge variant="secondary">{thread.title}</Badge>
              </div>
              <CardTitle className="flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-primary" aria-hidden />
                Chat with subreddit evidence
              </CardTitle>
              <CardDescription>
                Ask follow-ups in an LLM-style workspace while keeping citations
                and themes available in the right sidebar.
              </CardDescription>
            </div>
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
                  sources={sources}
                />
              ))}
            </div>
          </ScrollArea>

          <div className="border-t bg-slate-50/80 p-4">
            <ChatComposer onSubmit={handleSubmit} />
          </div>
        </CardContent>
      </Card>

      {isSidebarOpen ? (
        <div className="xl:sticky xl:top-8 xl:h-[calc(100vh-4rem)]">
          <QueryEvidenceSidebar
            answer={answer}
            sources={sources}
            templates={templates}
            themes={themes}
            onClose={() => setIsSidebarOpen(false)}
          />
        </div>
      ) : null}
    </div>
  );
}
