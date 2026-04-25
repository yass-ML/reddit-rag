import Link from "next/link";
import { ArrowLeft, ExternalLink, FileJson, Link2, Quote } from "lucide-react";
import { PageHeader } from "@/components/page-header";
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
import { Separator } from "@/components/ui/separator";
import { listLiveSources } from "@/lib/live-api";

export const dynamic = "force-dynamic";

export default async function SourceInspectorPage() {
  const sources = await listLiveSources();
  const selectedSource = sources[0] ?? null;

  return (
    <div className="mx-auto max-w-7xl">
      <PageHeader
        eyebrow="Source Inspector"
        title="Audit the posts and comments behind a RAG answer."
        description="Source inspection is a first-class workflow: citations are not decorative, they are the evidence trail the backend must preserve."
        badge="Evidence-first"
      />

      <div className="grid gap-6 xl:grid-cols-[0.8fr_1.2fr]">
        <div className="space-y-4">
          <Button asChild variant="outline">
            <Link href="/query">
              <ArrowLeft className="h-4 w-4" aria-hidden="true" />
              Back to query workspace
            </Link>
          </Button>
          {sources.length > 0 ? (
            sources.map((source) => <SourceCard key={source.id} source={source} />)
          ) : (
            <Card>
              <CardHeader>
                <CardTitle>No indexed sources yet</CardTitle>
                <CardDescription>
                  Run the ingestion, chunking, and indexing commands to populate Chroma.
                </CardDescription>
              </CardHeader>
            </Card>
          )}
        </div>

        {selectedSource ? (
          <Card className="overflow-hidden">
            <CardHeader className="border-b bg-white/80">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <CardTitle>{selectedSource.source_title}</CardTitle>
                  <CardDescription>
                    r/{selectedSource.subreddit} source evidence preview
                  </CardDescription>
                </div>
                <Badge variant="secondary">{selectedSource.source_type}</Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-6 pt-6">
              <section className="rounded-xl border bg-blue-50/50 p-5">
                <div className="mb-3 flex items-center gap-2 font-heading font-semibold">
                  <Quote className="h-5 w-5 text-primary" aria-hidden="true" />
                  Retrieved chunk
                </div>
                <p className="text-base leading-8">{selectedSource.text}</p>
              </section>

              <div className="grid gap-4 md:grid-cols-2">
                <Metadata label="Author" value={selectedSource.author ?? "unknown"} />
                <Metadata label="Reddit score" value={selectedSource.source_score.toString()} />
                <Metadata
                  label="Retrieval score"
                  value={`${(selectedSource.score * 100).toFixed(0)}%`}
                />
                <Metadata label="Chunk index" value={selectedSource.metadata.chunk_index.toString()} />
                <Metadata
                  label="Created UTC"
                  value={String(selectedSource.metadata.created_utc ?? "unknown")}
                />
                <Metadata label="Reddit ID" value={selectedSource.metadata.reddit_id} />
              </div>

              <Separator />

              <div className="grid gap-4 md:grid-cols-2">
                <div className="rounded-xl border bg-slate-50 p-4">
                  <div className="mb-2 flex items-center gap-2 font-heading font-semibold">
                    <FileJson className="h-4 w-4 text-primary" aria-hidden="true" />
                    Local raw path
                  </div>
                  <p className="font-mono text-xs text-muted-foreground">
                    {selectedSource.local_raw_path || "unknown"}
                  </p>
                </div>
                <div className="rounded-xl border bg-slate-50 p-4">
                  <div className="mb-2 flex items-center gap-2 font-heading font-semibold">
                    <Link2 className="h-4 w-4 text-primary" aria-hidden="true" />
                    Permalink
                  </div>
                  {selectedSource.source_permalink ? (
                    <a
                      href={selectedSource.source_permalink}
                      className="inline-flex items-center gap-2 text-sm font-semibold text-primary hover:underline"
                    >
                      Reddit permalink
                      <ExternalLink className="h-4 w-4" aria-hidden="true" />
                    </a>
                  ) : (
                    <p className="text-sm text-muted-foreground">No permalink available.</p>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        ) : null}
      </div>
    </div>
  );
}

function Metadata({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border bg-slate-50 p-4">
      <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        {label}
      </div>
      <div className="mt-1 break-words font-mono text-sm">{value}</div>
    </div>
  );
}
