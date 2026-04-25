"use client";

import { ArrowUpRight, MessageSquare, Star } from "lucide-react";
import type { SourceEvidence } from "@/lib/contracts";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export function SourceCard({ source }: { source: SourceEvidence }) {
  const title =
    source.source_title ||
    source.parent_post_title ||
    source.metadata.title ||
    "Untitled source";
  const excerpt = source.excerpt || source.text || "No source text returned.";
  const subreddit = source.subreddit || "unknown";
  const chunkIndex = source.metadata?.chunk_index ?? 0;
  const relevance = Number.isFinite(source.score)
    ? `${(source.score * 100).toFixed(0)}%`
    : "unknown";

  return (
    <Card className="group transition-shadow duration-200 hover:shadow-md">
      <CardHeader className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="secondary">r/{subreddit}</Badge>
          <Badge variant="outline">{source.source_type.replace("_", " ")}</Badge>
          {source.citation_index ? (
            <Badge variant="muted">Source {source.citation_index}</Badge>
          ) : null}
          <span className="font-mono text-xs text-muted-foreground">
            relevance {relevance}
          </span>
        </div>
        <CardTitle className="text-base leading-snug">{title}</CardTitle>
        {source.source_type === "comment" && source.parent_post_title ? (
          <p className="text-xs text-muted-foreground">
            Parent post: {source.parent_post_title}
          </p>
        ) : null}
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm leading-6 text-muted-foreground">{excerpt}</p>
        <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-1">
            <Star className="h-3.5 w-3.5" aria-hidden="true" />
            {source.source_score} score
          </span>
          {source.comment_count ? (
            <span className="inline-flex items-center gap-1">
              <MessageSquare className="h-3.5 w-3.5" aria-hidden="true" />
              {source.comment_count} comments
            </span>
          ) : null}
          <span className="font-mono">chunk {chunkIndex}</span>
          {source.chunk_id ? (
            <span className="font-mono">id {source.chunk_id}</span>
          ) : null}
        </div>
        {source.retrieval_metadata ? (
          <div className="rounded-xl border bg-slate-50 p-3">
            <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Retrieval metadata
            </div>
            <div className="mt-2 space-y-1 font-mono text-[11px] text-muted-foreground">
              {Object.entries(source.retrieval_metadata).map(([key, value]) => (
                <div key={key}>
                  {key}: {String(value)}
                </div>
              ))}
            </div>
          </div>
        ) : null}
      </CardContent>
      <CardFooter>
        {source.source_permalink ? (
          <Button asChild variant="outline" size="sm">
            <a href={source.source_permalink} target="_blank" rel="noreferrer">
              Open permalink
              <ArrowUpRight className="h-4 w-4" aria-hidden="true" />
            </a>
          </Button>
        ) : (
          <p className="text-xs text-muted-foreground">No permalink available.</p>
        )}
      </CardFooter>
    </Card>
  );
}
