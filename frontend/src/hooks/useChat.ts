"use client";

import { useCallback, useRef, useState } from "react";
import { ChatMessage, streamChat } from "@/lib/api";

function newId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isThinking, setIsThinking] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || isStreaming) return;

    setError(null);
    abortRef.current?.abort();
    abortRef.current = new AbortController();

    const userMsg: ChatMessage = {
      id: newId(),
      role: "user",
      content: trimmed,
    };
    const assistantId = newId();

    setMessages((prev) => [
      ...prev,
      userMsg,
      { id: assistantId, role: "assistant", content: "" },
    ]);
    setIsThinking(true);
    setIsStreaming(true);

    let gotFirstToken = false;

    try {
      await streamChat(
        trimmed,
        (event) => {
          if (event.type === "token") {
            if (!gotFirstToken) {
              gotFirstToken = true;
              setIsThinking(false);
            }
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? { ...m, content: m.content + event.content }
                  : m,
              ),
            );
          } else if (event.type === "done") {
            setIsThinking(false);
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? { ...m, content: event.content }
                  : m,
              ),
            );
          } else if (event.type === "error") {
            setIsThinking(false);
            setError(event.message);
            setMessages((prev) => prev.filter((m) => m.id !== assistantId));
          }
        },
        abortRef.current.signal,
      );
    } catch (err) {
      if ((err as Error).name === "AbortError") return;
      setError((err as Error).message);
      setMessages((prev) => prev.filter((m) => m.id !== assistantId));
    } finally {
      setIsThinking(false);
      setIsStreaming(false);
      abortRef.current = null;
    }
  }, [isStreaming]);

  return {
    messages,
    isThinking,
    isStreaming,
    error,
    sendMessage,
    replaceMessages: setMessages,
  };
}
