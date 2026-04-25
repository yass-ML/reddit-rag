"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
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
import type { SubredditConfig } from "@/lib/contracts";
import { addLiveSubreddit, LiveApiError, removeLiveSubreddit } from "@/lib/live-api";

export function SubredditSetupPanel({ initialSubreddits }: { initialSubreddits: SubredditConfig[] }) {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [name, setName] = useState("");
  const [maxPosts, setMaxPosts] = useState(100);
  const [maxComments, setMaxComments] = useState(1000);
  const [error, setError] = useState<string | null>(null);

  const run = async (fn: () => Promise<unknown>) => {
    setError(null);
    setPending(true);
    try {
      await fn();
      router.refresh();
    } catch (e) {
      if (e instanceof LiveApiError) {
        setError(e.message);
      } else if (e instanceof Error) {
        setError(e.message);
      } else {
        setError("Something went wrong.");
      }
    } finally {
      setPending(false);
    }
  };

  const handleAdd = () => {
    void run(async () => {
      await addLiveSubreddit({
        name: name.trim() || "",
        max_posts: maxPosts,
        max_comments: maxComments,
      });
      setName("");
      setMaxPosts(100);
      setMaxComments(1000);
    });
  };

  const handleRemove = (subName: string) => {
    void run(async () => {
      await removeLiveSubreddit(subName);
    });
  };

  return (
    <>
      <PageHeader
        eyebrow="Subreddit Setup"
        title="Choose the communities this workspace will learn from."
        description="Review subreddit targets and local ingestion limits loaded from the Python backend config."
        badge="Live config"
      />

      <div className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Add subreddit</CardTitle>
            <CardDescription>
              Writes to <code className="text-xs">subreddits.yaml</code> under your config directory (
              <code className="text-xs">REDDIT_RAG_CONFIG_DIR</code> or project <code className="text-xs">config/</code>
              ). Run ingestion and indexing separately so retrieval stays in sync.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            {error ? (
              <p className="text-sm text-red-600" role="alert">
                {error}
              </p>
            ) : null}
            <div className="space-y-2">
              <Label htmlFor="subreddit-name">Subreddit handle</Label>
              <Input
                id="subreddit-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="indiehackers"
                autoComplete="off"
              />
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="max-posts">Max posts</Label>
                <Input
                  id="max-posts"
                  type="number"
                  min={0}
                  value={maxPosts}
                  onChange={(e) => setMaxPosts(Number(e.target.value) || 0)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="max-comments">Max comments</Label>
                <Input
                  id="max-comments"
                  type="number"
                  min={0}
                  value={maxComments}
                  onChange={(e) => setMaxComments(Number(e.target.value) || 0)}
                />
              </div>
            </div>
            <Button
              className="w-full"
              type="button"
              disabled={pending || !name.trim()}
              onClick={handleAdd}
            >
              <Plus className="h-4 w-4" aria-hidden="true" />
              Add subreddit
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-start justify-between gap-4">
              <div>
                <CardTitle>Workspace targets</CardTitle>
                <CardDescription>Current subreddit configuration from the local backend.</CardDescription>
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
            {initialSubreddits.length === 0 ? (
              <p className="text-sm text-muted-foreground">No subreddits configured yet.</p>
            ) : null}
            {initialSubreddits.map((subreddit) => (
              <div key={subreddit.id} className="rounded-xl border bg-slate-50 p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h2 className="font-heading text-lg font-semibold">r/{subreddit.name}</h2>
                    <p className="mt-1 text-sm text-muted-foreground">{subreddit.description}</p>
                  </div>
                  <StatusBadge status={subreddit.status} />
                </div>
                <div className="mt-4 grid gap-3 text-sm sm:grid-cols-3">
                  <span>
                    <strong>{subreddit.post_limit}</strong> max posts
                  </span>
                  <span>
                    <strong>{subreddit.comment_depth}</strong> max comments
                  </span>
                  <button
                    type="button"
                    disabled={pending}
                    onClick={() => handleRemove(subreddit.name)}
                    className="inline-flex items-center gap-1 text-sm font-semibold text-red-600 transition-colors hover:text-red-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50"
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
    </>
  );
}
