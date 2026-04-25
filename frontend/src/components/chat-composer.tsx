"use client";

import { useState } from "react";
import { SendHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

export function ChatComposer({
  onSubmit,
}: {
  onSubmit: (message: string) => void;
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
        onSubmit(trimmed);
        setMessage("");
      }}
    >
      <label htmlFor="chat-message" className="sr-only">
        Ask a follow-up question
      </label>
      <Textarea
        id="chat-message"
        value={message}
        onChange={(event) => setMessage(event.target.value)}
        placeholder="Ask a follow-up about themes, objections, or source evidence..."
        className="min-h-20 resize-none border-0 bg-transparent px-1 shadow-none focus-visible:ring-0"
        onKeyDown={(event) => {
          if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
            event.currentTarget.form?.requestSubmit();
          }
        }}
      />
      <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
        <p className="text-xs text-muted-foreground">
          Mock chat only. Press Ctrl+Enter or Cmd+Enter to send.
        </p>
        <Button type="submit">
          Send mock message
          <SendHorizontal className="h-4 w-4" aria-hidden />
        </Button>
      </div>
    </form>
  );
}
