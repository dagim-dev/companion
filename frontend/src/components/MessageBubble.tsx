"use client";

import type { ChatMessage } from "@/lib/api";

export function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";

  return (
    <div
      className={`animate-fade-in flex ${isUser ? "justify-end" : "justify-start"}`}
    >
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
          isUser
            ? "bg-jarvis-accent/20 text-slate-100"
            : "border border-jarvis-border bg-jarvis-panel text-slate-200"
        }`}
      >
        {!isUser && (
          <p className="mb-1 text-xs font-medium uppercase tracking-wider text-jarvis-accent">
            J.A.R.V.I.S.
          </p>
        )}
        <p className="whitespace-pre-wrap">{message.content || "\u00a0"}</p>
      </div>
    </div>
  );
}
