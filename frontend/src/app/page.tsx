import type React from "react";
import Link from "next/link";
import { ArrowRight, Database, FileText, MessageSquare, Plus } from "lucide-react";
import { IngestionStatusCard } from "@/components/ingestion-status-card";
import { PageHeader } from "@/components/page-header";
import { SourceCard } from "@/components/source-card";
import { StatusBadge } from "@/components/status-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { listWorkspaces } from "@/lib/mock-api";
import { getLiveIngestionStatus, listLiveSources } from "@/lib/live-api";

export const dynamic = "force-dynamic";

export default async function Dashboard() {
  const [workspaces, ingestionRun, sources] = await Promise.all([
    listWorkspaces(),
    getLiveIngestionStatus(),
    listLiveSources(3),
  ]);
  const featuredWorkspace = workspaces[0];

  return (
    <div className="mx-auto max-w-7xl">
      <PageHeader
        eyebrow="Dashboard"
        title="Build and test a local subreddit evidence base."
        description="Inspect local ingestion readiness, open the live query workspace, and audit sources returned by the Python backend."
        badge="Live backend"
      />

      <div className="grid gap-6 lg:grid-cols-[1.25fr_0.75fr]">
        <Card className="overflow-hidden">
          <CardHeader className="border-b bg-white/70">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <CardTitle>{featuredWorkspace.name}</CardTitle>
                <CardDescription>{featuredWorkspace.goal}</CardDescription>
              </div>
              <StatusBadge status={featuredWorkspace.status} />
            </div>
          </CardHeader>
          <CardContent className="space-y-6 pt-6">
            <div className="grid gap-3 sm:grid-cols-4">
              <Metric label="Posts" value={featuredWorkspace.stats.posts} icon={FileText} />
              <Metric
                label="Comments"
                value={featuredWorkspace.stats.comments}
                icon={MessageSquare}
              />
              <Metric label="Chunks" value={featuredWorkspace.stats.chunks} icon={Database} />
              <Metric
                label="Sources"
                value={featuredWorkspace.stats.sources_ready}
                icon={ArrowRight}
              />
            </div>
            <div className="flex flex-wrap gap-2">
              {featuredWorkspace.subreddit_ids.map((subredditId) => (
                <Badge key={subredditId} variant="secondary">
                  {subredditId.replace("sr-", "r/")}
                </Badge>
              ))}
            </div>
            <div className="flex flex-wrap gap-3">
              <Button asChild>
                <Link href="/query">
                  Open query workspace
                  <ArrowRight className="h-4 w-4" aria-hidden="true" />
                </Link>
              </Button>
              <Button asChild variant="outline">
                <Link href="/spaces/new">
                  <Plus className="h-4 w-4" aria-hidden="true" />
                  New research space
                </Link>
              </Button>
            </div>
          </CardContent>
        </Card>

        <IngestionStatusCard run={ingestionRun} />
      </div>

      <section className="mt-8">
        <div className="mb-4 flex items-center justify-between gap-4">
          <div>
            <h2 className="font-heading text-2xl font-semibold">
              Inspectable source trail
            </h2>
            <p className="text-sm text-muted-foreground">
              Indexed chunks appear here once Chroma contains embedded subreddit evidence.
            </p>
          </div>
          <Button asChild variant="outline">
            <Link href="/sources">View inspector</Link>
          </Button>
        </div>
        <div className="grid gap-4 lg:grid-cols-3">
          {sources.map((source) => (
            <SourceCard key={source.id} source={source} />
          ))}
        </div>
      </section>
    </div>
  );
}

function Metric({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: number;
  icon: React.ComponentType<{ className?: string; "aria-hidden"?: boolean }>;
}) {
  return (
    <div className="rounded-xl border bg-slate-50 p-4">
      <Icon className="mb-3 h-4 w-4 text-primary" aria-hidden />
      <div className="font-heading text-2xl font-semibold">{value.toLocaleString()}</div>
      <div className="text-xs font-medium text-muted-foreground">{label}</div>
    </div>
  );
}
