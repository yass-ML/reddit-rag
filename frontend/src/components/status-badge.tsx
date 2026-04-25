import type { IngestionState } from "@/lib/contracts";
import { Badge } from "@/components/ui/badge";

const labels: Record<IngestionState, string> = {
  not_started: "Not started",
  queued: "Queued",
  mocked: "Mocked",
  ingesting: "Ingesting",
  processing: "Processing",
  ready: "Ready",
  needs_attention: "Needs attention",
};

const variants: Record<
  IngestionState,
  "default" | "secondary" | "success" | "warning" | "muted"
> = {
  not_started: "muted",
  queued: "secondary",
  mocked: "warning",
  ingesting: "default",
  processing: "default",
  ready: "success",
  needs_attention: "warning",
};

export function StatusBadge({ status }: { status: IngestionState }) {
  return <Badge variant={variants[status]}>{labels[status]}</Badge>;
}
