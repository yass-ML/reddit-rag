import { HardDrive, KeyRound, Server, Shield } from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const settings = [
  {
    icon: HardDrive,
    title: "Local storage path",
    description: "Backend location for raw payloads, processed JSONL, SQLite metadata, and Chroma data.",
    value: "./data",
  },
  {
    icon: Server,
    title: "Local model provider",
    description: "Ollama generation and embedding model selection is read from backend config.",
    value: "Ollama",
  },
  {
    icon: KeyRound,
    title: "Reddit API credentials",
    description: "Not collected in the frontend. Credentials will stay server-side or local config only.",
    value: "Not configured",
  },
];

export default function SettingsPage() {
  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader
        eyebrow="Settings"
        title="Local-first settings without secrets in the browser."
        description="This page documents local backend configuration while avoiding auth and Reddit credentials in the frontend."
        badge="Local backend"
      />

      <div className="grid gap-6">
        <Card className="border-green-200 bg-green-50/70">
          <CardHeader>
            <div className="flex items-start gap-3">
              <div className="rounded-xl bg-green-100 p-2 text-green-700">
                <Shield className="h-5 w-5" aria-hidden="true" />
              </div>
              <div>
                <CardTitle>Privacy stance</CardTitle>
                <CardDescription className="text-green-900/70">
                  The frontend talks to your local FastAPI server. It does not expose Reddit API secrets,
                  authenticate users, or send subreddit data to a hosted RAG service.
                </CardDescription>
              </div>
            </div>
          </CardHeader>
        </Card>

        <div className="grid gap-4 md:grid-cols-3">
          {settings.map((setting) => {
            const Icon = setting.icon;

            return (
              <Card key={setting.title}>
                <CardHeader>
                  <div className="mb-2 w-fit rounded-xl bg-primary/10 p-2 text-primary">
                    <Icon className="h-5 w-5" aria-hidden="true" />
                  </div>
                  <CardTitle className="text-lg">{setting.title}</CardTitle>
                  <CardDescription>{setting.description}</CardDescription>
                </CardHeader>
                <CardContent>
                  <Badge variant="muted">{setting.value}</Badge>
                </CardContent>
              </Card>
            );
          })}
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Backend endpoint</CardTitle>
            <CardDescription>
              Local API base URL used by the live frontend calls.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <Label htmlFor="api-url">API base URL</Label>
            <Input id="api-url" defaultValue="http://localhost:8000" disabled />
            <p className="text-xs text-muted-foreground">
              Configure this with `NEXT_PUBLIC_REDDIT_RAG_API_BASE_URL` before starting Next.js.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
