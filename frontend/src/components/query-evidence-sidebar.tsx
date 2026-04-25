"use client";

import { X } from "lucide-react";
import type {
  QueryTemplate,
  QueryThemeInsight,
  RagAnswer,
  SourceEvidence,
} from "@/lib/contracts";
import { QueryTemplateCard } from "@/components/query-template-card";
import { SourceCard } from "@/components/source-card";
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export function QueryEvidenceSidebar({
  answer,
  sources,
  templates,
  themes,
  onClose,
}: {
  answer: RagAnswer;
  sources: SourceEvidence[];
  templates: QueryTemplate[];
  themes: QueryThemeInsight[];
  onClose: () => void;
}) {
  return (
    <aside className="h-full rounded-2xl border bg-white/95 shadow-sm backdrop-blur">
      <div className="flex items-start justify-between gap-3 border-b p-4">
        <div>
          <h2 className="font-heading text-lg font-semibold">Research context</h2>
          <p className="text-sm text-muted-foreground">
            Sources, themes, prompts, and debug details stay close to the chat.
          </p>
        </div>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          aria-label="Hide research context sidebar"
          onClick={onClose}
        >
          <X className="h-4 w-4" aria-hidden />
        </Button>
      </div>

      <Tabs defaultValue="sources" className="p-4">
        <TabsList className="grid h-auto w-full grid-cols-4">
          <TabsTrigger value="sources" className="text-xs">
            Sources
          </TabsTrigger>
          <TabsTrigger value="themes" className="text-xs">
            Themes
          </TabsTrigger>
          <TabsTrigger value="templates" className="text-xs">
            Prompts
          </TabsTrigger>
          <TabsTrigger value="debug" className="text-xs">
            Debug
          </TabsTrigger>
        </TabsList>

        <ScrollArea className="h-[calc(100vh-18rem)] min-h-[420px] pr-3">
          <TabsContent value="sources" className="space-y-4">
            {sources.map((source) => (
              <SourceCard key={source.id} source={source} />
            ))}
          </TabsContent>

          <TabsContent value="themes" className="space-y-4">
            {themes.map((theme) => (
              <Card key={theme.id}>
                <CardHeader>
                  <div className="flex items-start justify-between gap-3">
                    <CardTitle className="text-base">{theme.title}</CardTitle>
                    <Badge variant={theme.confidence === "high" ? "success" : "warning"}>
                      {theme.confidence}
                    </Badge>
                  </div>
                  <CardDescription>{theme.summary}</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-2">
                    {theme.source_ids.map((sourceId) => (
                      <Badge key={sourceId} variant="muted">
                        {sourceId}
                      </Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ))}
          </TabsContent>

          <TabsContent value="templates" className="space-y-4">
            {templates.map((template) => (
              <QueryTemplateCard key={template.id} template={template} />
            ))}
          </TabsContent>

          <TabsContent value="debug" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Retrieval preview</CardTitle>
                <CardDescription>
                  This mirrors the future backend response metadata.
                </CardDescription>
              </CardHeader>
              <CardContent className="grid gap-3">
                {answer.retrieval_debug_optional ? (
                  <>
                    <DebugValue
                      label="retrieval"
                      value={`${answer.retrieval_debug_optional.retrieval_ms}ms`}
                    />
                    <DebugValue
                      label="top k"
                      value={answer.retrieval_debug_optional.top_k.toString()}
                    />
                    <DebugValue
                      label="embedding"
                      value={answer.retrieval_debug_optional.embedding_model}
                    />
                    <DebugValue
                      label="generation"
                      value={answer.retrieval_debug_optional.generation_model}
                    />
                  </>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    No debug metadata available.
                  </p>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </ScrollArea>
      </Tabs>
    </aside>
  );
}

function DebugValue({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border bg-slate-50 p-3">
      <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        {label}
      </div>
      <div className="mt-1 break-words font-mono text-xs">{value}</div>
    </div>
  );
}
