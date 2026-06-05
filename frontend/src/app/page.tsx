"use client";

import { ChatInput } from "@/components/ChatInput";
import { ChatWindow } from "@/components/ChatWindow";
import { useChat } from "@/hooks/useChat";

export default function Home() {
  const { messages, isThinking, isStreaming, error, sendMessage } = useChat();

  const lastAssistant = [...messages]
    .reverse()
    .find((m) => m.role === "assistant" && m.content.trim());

  return (
    <main className="flex h-dvh flex-col">
      <header className="border-b border-jarvis-border bg-jarvis-panel/60 px-4 py-4 backdrop-blur">
        <div className="mx-auto flex max-w-3xl items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold tracking-tight text-slate-100">
              J.A.R.V.I.S.
            </h1>
            <p className="text-xs text-jarvis-muted">
              Just A Rather Very Intelligent System
            </p>
          </div>
          <span className="rounded-full border border-jarvis-border px-3 py-1 text-xs text-jarvis-muted">
            {isStreaming ? "Online" : "Ready"}
          </span>
        </div>
      </header>

      <ChatWindow messages={messages} isThinking={isThinking} />

      {error && (
        <p className="mx-auto max-w-3xl px-4 pb-2 text-center text-sm text-red-400">
          {error}
        </p>
      )}

      <ChatInput
        disabled={isStreaming}
        onSend={sendMessage}
        lastAssistantText={lastAssistant?.content}
      />
    </main>
  );
}
