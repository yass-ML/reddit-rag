import Link from "next/link";
import { ArrowRight, Plus, Trash2 } from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { listSubreddits } from "@/lib/mock-api";

export default async function SubredditSetupPage() {
  const subreddits = await listSubreddits();

  return (
    <div className="mx-auto max-w-6xl">
      <PageHeader
        eyebrow="Subreddit Setup"
        title="Choose the communities this workspace will learn from."
        description="Set subreddit targets and local ingestion limits as mocked configuration. The frontend does not validate against Reddit or use credentials."
        badge="Configuration only"
      />

      <div className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Add subreddit</CardTitle>
            <CardDescription>
              The backend will later accept this payload and enqueue ingestion.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="space-y-2">
              <Label htmlFor="subreddit-name">Subreddit handle</Label>
              <Input id="subreddit-name" defaultValue="indiehackers" />
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="post-limit">Post limit</Label>
                <Input id="post-limit" type="number" defaultValue={100} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="comment-depth">Comment depth</Label>
                <Input id="comment-depth" type="number" defaultValue={3} />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="timeframe">Timeframe</Label>
              <select
                id="timeframe"
                className="h-10 w-full rounded-md border border-input bg-card px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                defaultValue="month"
              >
                <option value="week">Past week</option>
                <option value="month">Past month</option>
                <option value="year">Past year</option>
                <option value="all">All time</option>
              </select>
            </div>
            <Button className="w-full" type="button">
              <Plus className="h-4 w-4" aria-hidden="true" />
              Add mocked subreddit
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-start justify-between gap-4">
              <div>
                <CardTitle>Workspace targets</CardTitle>
                <CardDescription>
                  Current mocked subreddit configuration for Founder Pain Point Research.
                </CardDescription>
              </div>
              <Button asChild variant="outline" size="sm">
                <Link href="/ingestion">
                  Status
                  <ArrowRight className="h-4 w-4" aria-hidden="true" />
                </Link>
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {subreddits.map((subreddit) => (
              <div key={subreddit.id} className="rounded-xl border bg-slate-50 p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h2 className="font-heading text-lg font-semibold">
                      r/{subreddit.name}
                    </h2>
                    <p className="mt-1 text-sm text-muted-foreground">
                      {subreddit.description}
                    </p>
                  </div>
                  <StatusBadge status={subreddit.status} />
                </div>
                <div className="mt-4 grid gap-3 text-sm sm:grid-cols-4">
                  <span>
                    <strong>{subreddit.post_limit}</strong> posts
                  </span>
                  <span>
                    <strong>{subreddit.comment_depth}</strong> depth
                  </span>
                  <span>
                    <strong>{subreddit.timeframe}</strong> window
                  </span>
                  <button
                    type="button"
                    className="inline-flex items-center gap-1 text-sm font-semibold text-red-600 transition-colors hover:text-red-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    <Trash2 className="h-4 w-4" aria-hidden="true" />
                    Remove
                  </button>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
