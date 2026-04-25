"use client";

import { Lightbulb } from "lucide-react";
import type { QueryTemplate } from "@/lib/contracts";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export function QueryTemplateCard({ template }: { template: QueryTemplate }) {
  return (
    <Card className="transition-colors duration-200 hover:border-primary/40 hover:bg-blue-50/40">
      <CardHeader className="space-y-3">
        <div className="flex items-center justify-between gap-3">
          <div className="rounded-lg bg-primary/10 p-2 text-primary">
            <Lightbulb className="h-4 w-4" aria-hidden="true" />
          </div>
          <Badge variant="muted">{template.category.replace("_", " ")}</Badge>
        </div>
        <CardTitle className="text-base">{template.title}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-sm leading-6 text-muted-foreground">{template.prompt}</p>
      </CardContent>
    </Card>
  );
}
