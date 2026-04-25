"use client";

import Link from "next/link";
import { Bot, Info, User } from "lucide-react";
import type { ChatMessage as ChatMessageType, SourceEvidence } from "@/lib/contracts";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export function ChatMessage({
  message,
  sources,
}: {
  message: ChatMessageType;
  sources: SourceEvidence[];
}) {
  const citedSources = sources.filter((source) =>
    message.citation_source_ids?.includes(source.id),
  );
  const isUser = message.role === "user";
  const isSystem = message.role === "system";

  return (
    <article
      className={cn(
        "flex gap-3",
        isUser && "justify-end",
        isSystem && "justify-center",
      )}
    >
      {!isUser && !isSystem ? <MessageAvatar role={message.role} /> : null}

      <div
        className={cn(
          "max-w-[min(720px,100%)] rounded-2xl border px-4 py-3 shadow-sm",
          isUser && "bg-primary text-primary-foreground",
          message.role === "assistant" && "bg-white",
          isSystem && "bg-amber-50 text-amber-900",
        )}
      >
        <div className="mb-2 flex flex-wrap items-center gap-2">
          <Badge variant={isUser ? "secondary" : isSystem ? "warning" : "muted"}>
            {message.role === "assistant"
              ? "Assistant"
              : message.role === "system"
                ? "System"
                : "You"}
          </Badge>
          <time
            className={cn(
              "font-mono text-[11px]",
              isUser ? "text-blue-100" : "text-muted-foreground",
            )}
          >
            {new Date(message.created_at).toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </time>
        </div>

        <p className="whitespace-pre-wrap text-sm leading-7">{message.content}</p>

        {citedSources.length > 0 ? (
          <div className="mt-4 flex flex-wrap gap-2">
            {citedSources.map((source, index) => (
              <Button
                key={source.id}
                asChild
                variant="outline"
                size="sm"
                className="h-8 bg-white/90 text-xs text-foreground"
              >
                <Link href="/sources">
                  Source {source.citation_index ?? index + 1}
                  <span className="font-mono text-muted-foreground">
                    r/{source.subreddit}
                  </span>
                </Link>
              </Button>
            ))}
          </div>
        ) : null}
      </div>

      {isUser ? <MessageAvatar role={message.role} /> : null}
      {isSystem ? <Info className="mt-3 h-4 w-4 shrink-0 text-amber-700" /> : null}
    </article>
  );
}

function MessageAvatar({ role }: { role: ChatMessageType["role"] }) {
  const Icon = role === "user" ? User : Bot;

  return (
    <div
      className={cn(
        "mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-full border shadow-sm",
        role === "user" ? "bg-primary text-primary-foreground" : "bg-white text-primary",
      )}
    >
      <Icon className="h-4 w-4" aria-hidden />
    </div>
  );
}
