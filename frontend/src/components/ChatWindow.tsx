"use client";

import { useEffect, useRef } from "react";
import { ChatMessage } from "@/lib/api";
import { MessageBubble } from "./MessageBubble";
import { TypingIndicator } from "./TypingIndicator";

type ChatWindowProps = {
  messages: ChatMessage[];
  isThinking: boolean;
};

export function ChatWindow({ messages, isThinking }: ChatWindowProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isThinking]);

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6">
      <div className="mx-auto flex max-w-3xl flex-col gap-4">
        {messages.length === 0 && (
          <div className="animate-fade-in py-16 text-center">
            <h2 className="text-lg font-medium text-slate-200">
              J.A.R.V.I.S.
            </h2>
            <p className="mt-2 text-sm text-jarvis-muted">
              Good evening, Sir. How may I assist you?
            </p>
          </div>
        )}
        {messages.map((m) => (
          <MessageBubble key={m.id} message={m} />
        ))}
        {isThinking && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
