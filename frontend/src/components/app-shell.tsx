"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  DatabaseZap,
  FileSearch,
  Home,
  MessageSquareText,
  PlusCircle,
  Settings,
  SlidersHorizontal,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

const navItems = [
  { href: "/", label: "Dashboard", icon: Home },
  { href: "/spaces/new", label: "New Research Space", icon: PlusCircle },
  { href: "/subreddits", label: "Subreddit Setup", icon: SlidersHorizontal },
  { href: "/ingestion", label: "Ingestion Status", icon: DatabaseZap },
  { href: "/query", label: "Query Workspace", icon: MessageSquareText },
  { href: "/sources", label: "Source Inspector", icon: FileSearch },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[280px_1fr]">
      <aside className="border-b bg-white/85 backdrop-blur lg:sticky lg:top-0 lg:h-screen lg:border-b-0 lg:border-r">
        <div className="flex h-full flex-col gap-6 p-5">
          <Link href="/" className="flex items-center gap-3">
            <div className="rounded-xl bg-primary p-2 text-primary-foreground">
              <BarChart3 className="h-5 w-5" aria-hidden="true" />
            </div>
            <div>
              <div className="font-heading text-lg font-semibold">
                Reddit RAG
              </div>
              <div className="text-xs text-muted-foreground">
                Local research prototype
              </div>
            </div>
          </Link>

          <div className="rounded-xl border bg-slate-50 p-3">
            <div className="flex items-center justify-between gap-3">
              <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Mode
              </span>
              <Badge variant="warning">Mock data</Badge>
            </div>
            <p className="mt-2 text-sm leading-5 text-muted-foreground">
              Frontend-only contract preview. No Reddit API, ingestion, or
              embeddings are running.
            </p>
          </div>

          <nav className="grid gap-1">
            {navItems.map((item) => {
              const isActive =
                item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
              const Icon = item.icon;

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-semibold text-muted-foreground transition-colors duration-200 hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                    isActive && "bg-primary text-primary-foreground hover:bg-primary hover:text-primary-foreground",
                  )}
                >
                  <Icon className="h-4 w-4" aria-hidden="true" />
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>
      </aside>
      <main className="min-w-0 p-4 sm:p-6 lg:p-8">{children}</main>
    </div>
  );
}
