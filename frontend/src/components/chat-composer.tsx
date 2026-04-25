"use client";

import { useState } from "react";
import { SendHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

export function ChatComposer({
  onSubmit,
  disabled = false,
  selectedSubreddit,
  subredditOptions,
  onSubredditChange,
  helperText = "Press Ctrl+Enter or Cmd+Enter to send.",
  submitLabel = "Ask RAG",
}: {
  onSubmit: (message: string) => void | Promise<void>;
  disabled?: boolean;
  selectedSubreddit: string;
  subredditOptions: string[];
  onSubredditChange: (subreddit: string) => void;
  helperText?: string;
  submitLabel?: string;
}) {
  const [message, setMessage] = useState("");

  return (
    <form
      className="rounded-2xl border bg-white p-3 shadow-lg"
      onSubmit={(event) => {
        event.preventDefault();
        const trimmed = message.trim();
        if (!trimmed) {
          return;
        }
        void onSubmit(trimmed);
        setMessage("");
      }}
    >
      <div className="mb-3 grid gap-3 md:grid-cols-[minmax(0,1fr)_220px] md:items-end">
        <div>
          <label htmlFor="chat-message" className="sr-only">
            Ask a question
          </label>
          <Textarea
            id="chat-message"
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            placeholder="Ask about themes, objections, vocabulary, or source evidence..."
            className="min-h-20 resize-none border-0 bg-transparent px-1 shadow-none focus-visible:ring-0"
            disabled={disabled}
            onKeyDown={(event) => {
              if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
                event.currentTarget.form?.requestSubmit();
              }
            }}
          />
        </div>
        <div>
          <label
            htmlFor="subreddit-filter"
            className="mb-1 block text-xs font-semibold uppercase tracking-wide text-muted-foreground"
          >
            Subreddit filter
          </label>
          <select
            id="subreddit-filter"
            value={selectedSubreddit}
            onChange={(event) => onSubredditChange(event.target.value)}
            disabled={disabled}
            className="h-10 w-full rounded-md border border-input bg-card px-3 py-2 text-sm shadow-xs transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
          >
            <option value="">All indexed subreddits</option>
            {subredditOptions.map((subreddit) => (
              <option key={subreddit} value={subreddit}>
                r/{subreddit}
              </option>
            ))}
          </select>
        </div>
      </div>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
        <p className="text-xs text-muted-foreground">{helperText}</p>
        <Button type="submit" disabled={disabled}>
          {submitLabel}
          <SendHorizontal className="h-4 w-4" aria-hidden />
        </Button>
      </div>
    </form>
  );
}
