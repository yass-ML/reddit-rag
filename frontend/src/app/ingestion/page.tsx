import Link from "next/link";
import { ArrowRight, CheckCircle2, Clock3 } from "lucide-react";
import { IngestionStatusCard } from "@/components/ingestion-status-card";
import { PageHeader } from "@/components/page-header";
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
import { getIngestionStatus } from "@/lib/mock-api";

export default async function IngestionStatusPage() {
  const ingestionRun = await getIngestionStatus();

  return (
    <div className="mx-auto max-w-6xl">
      <PageHeader
        eyebrow="Ingestion Status"
        title="Preview the local pipeline without running ingestion."
        description="This page establishes how the frontend will display the future Reddit API fetch, normalization, chunking, and embedding pipeline."
        badge="Mock pipeline"
      />

      <div className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
        <IngestionStatusCard run={ingestionRun} />

        <Card>
          <CardHeader>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <CardTitle>Pipeline steps</CardTitle>
                <CardDescription>
                  Contract states the Python backend will update later.
                </CardDescription>
              </div>
              <Badge variant="warning">No worker running</Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {ingestionRun.steps.map((step, index) => (
              <div key={step.id} className="flex gap-4 rounded-xl border bg-slate-50 p-4">
                <div className="mt-1">
                  {step.status === "ready" ? (
                    <CheckCircle2 className="h-5 w-5 text-green-600" aria-hidden="true" />
                  ) : (
                    <Clock3 className="h-5 w-5 text-primary" aria-hidden="true" />
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <h2 className="font-heading font-semibold">
                      {index + 1}. {step.label}
                    </h2>
                    <StatusBadge status={step.status} />
                  </div>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {step.description}
                  </p>
                  {step.count ? (
                    <p className="mt-2 font-mono text-xs text-muted-foreground">
                      preview count: {step.count.toLocaleString()}
                    </p>
                  ) : null}
                </div>
              </div>
            ))}

            <Button asChild>
              <Link href="/query">
                Ask a mocked question
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
