"use client";

import Link from "next/link";
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
  return (
    <Card className="group transition-shadow duration-200 hover:shadow-md">
      <CardHeader className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="secondary">r/{source.subreddit}</Badge>
          <Badge variant="outline">{source.source_type.replace("_", " ")}</Badge>
          <span className="font-mono text-xs text-muted-foreground">
            relevance {(source.score * 100).toFixed(0)}%
          </span>
        </div>
        <CardTitle className="text-base leading-snug">
          {source.source_title}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm leading-6 text-muted-foreground">{source.excerpt}</p>
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
          <span className="font-mono">chunk {source.metadata.chunk_index}</span>
        </div>
      </CardContent>
      <CardFooter>
        <Button asChild variant="outline" size="sm">
          <Link href="/sources">
            Inspect source
            <ArrowUpRight className="h-4 w-4" aria-hidden="true" />
          </Link>
        </Button>
      </CardFooter>
    </Card>
  );
}
