import Link from "next/link";
import { ArrowRight, FolderPlus, ShieldCheck } from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
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
import { Textarea } from "@/components/ui/textarea";

export default function NewResearchSpacePage() {
  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader
        eyebrow="New Research Space"
        title="Frame the research question before collecting data."
        description="This mocked setup flow defines what the backend will later persist: workspace metadata, goals, and seed subreddit targets."
        badge="No auth required"
      />

      <div className="grid gap-6 lg:grid-cols-[1.3fr_0.7fr]">
        <Card>
          <CardHeader>
            <CardTitle>Create workspace</CardTitle>
            <CardDescription>
              These fields are local prototype inputs and do not call a backend yet.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="space-y-2">
              <Label htmlFor="workspace-name">Workspace name</Label>
              <Input
                id="workspace-name"
                defaultValue="Founder Pain Point Research"
                aria-describedby="workspace-name-help"
              />
              <p id="workspace-name-help" className="text-xs text-muted-foreground">
                Use a name that describes the decision this research supports.
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="workspace-goal">Research goal</Label>
              <Textarea
                id="workspace-goal"
                defaultValue="Understand recurring objections, language, and buying triggers from indie founder communities."
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="seed-subreddits">Seed subreddits</Label>
              <Input id="seed-subreddits" defaultValue="startups, SaaS, Entrepreneur" />
              <p className="text-xs text-muted-foreground">
                Comma-separated handles only. Live Reddit validation comes later.
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <Button asChild>
                <Link href="/subreddits">
                  Continue to subreddit setup
                  <ArrowRight className="h-4 w-4" aria-hidden="true" />
                </Link>
              </Button>
              <Button asChild variant="outline">
                <Link href="/">Back to dashboard</Link>
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-slate-950 text-white">
          <CardHeader>
            <div className="mb-2 w-fit rounded-xl bg-white/10 p-3">
              <ShieldCheck className="h-5 w-5" aria-hidden="true" />
            </div>
            <CardTitle>Local-first guardrails</CardTitle>
            <CardDescription className="text-slate-300">
              This milestone defines the interface and contract without collecting private credentials.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-slate-200">
            <div className="flex items-center justify-between rounded-lg bg-white/10 p-3">
              <span>Reddit credentials</span>
              <Badge variant="warning">Not used</Badge>
            </div>
            <div className="flex items-center justify-between rounded-lg bg-white/10 p-3">
              <span>Ingestion</span>
              <Badge variant="warning">Mocked</Badge>
            </div>
            <div className="flex items-center justify-between rounded-lg bg-white/10 p-3">
              <span>RAG answers</span>
              <Badge variant="warning">Fixture-backed</Badge>
            </div>
            <div className="pt-4">
              <FolderPlus className="mb-2 h-5 w-5 text-blue-200" aria-hidden="true" />
              <p>
                The form shape is the API contract preview for a future
                `createWorkspace` endpoint.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
