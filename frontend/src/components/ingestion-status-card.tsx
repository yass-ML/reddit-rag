import { Database, FileText, MessagesSquare } from "lucide-react";
import type { IngestionRun, SubredditIngestionStatus } from "@/lib/contracts";
import { Progress } from "@/components/ui/progress";
import { StatusBadge } from "@/components/status-badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export function IngestionStatusCard({ run }: { run: IngestionRun }) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-4">
          <div>
            <CardTitle>Ingestion status</CardTitle>
            <CardDescription>
              Mocked pipeline preview for the future Python worker.
            </CardDescription>
          </div>
          <StatusBadge status={run.status} />
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium">Workspace readiness</span>
            <span className="font-mono text-muted-foreground">{run.progress}%</span>
          </div>
          <Progress value={run.progress} />
        </div>
        <div className="grid gap-3">
          {run.subreddit_statuses.map((status) => (
            <SubredditStatusRow key={status.subreddit} status={status} />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function SubredditStatusRow({ status }: { status: SubredditIngestionStatus }) {
  return (
    <div className="rounded-lg border bg-slate-50/70 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="font-heading font-semibold">r/{status.subreddit}</div>
          <p className="mt-1 text-sm text-muted-foreground">{status.message}</p>
        </div>
        <StatusBadge status={status.status} />
      </div>
      <div className="mt-4 grid grid-cols-3 gap-3 text-xs text-muted-foreground">
        <span className="inline-flex items-center gap-1">
          <FileText className="h-3.5 w-3.5" aria-hidden="true" />
          {status.posts_seen} posts
        </span>
        <span className="inline-flex items-center gap-1">
          <MessagesSquare className="h-3.5 w-3.5" aria-hidden="true" />
          {status.comments_seen} comments
        </span>
        <span className="inline-flex items-center gap-1">
          <Database className="h-3.5 w-3.5" aria-hidden="true" />
          {status.chunks_ready} chunks
        </span>
      </div>
    </div>
  );
}
