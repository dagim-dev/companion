"use client";

import { useEffect, useRef, useState } from "react";
import { ChatMessage, updateAddressAs } from "@/lib/api";
import { buildEmptyStateGreeting } from "@/lib/greeting";
import { MessageBubble } from "./MessageBubble";
import { NicknamePicker } from "./NicknamePicker";
import { TypingIndicator } from "./TypingIndicator";

type ChatWindowProps = {
  messages: ChatMessage[];
  isThinking: boolean;
  addressAs: string | null;
  profileLoaded: boolean;
  onAddressAsChange: (addressAs: string) => void;
};

export function ChatWindow({
  messages,
  isThinking,
  addressAs,
  profileLoaded,
  onAddressAsChange,
}: ChatWindowProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const [pickerLoading, setPickerLoading] = useState(false);
  const [pickerError, setPickerError] = useState<string | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isThinking]);

  const handleNicknameSubmit = async (value: string) => {
    setPickerError(null);
    setPickerLoading(true);
    try {
      await updateAddressAs(value);
      onAddressAsChange(value);
    } catch (err) {
      setPickerError((err as Error).message);
    } finally {
      setPickerLoading(false);
    }
  };

  const showEmpty = messages.length === 0;

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6">
      <div className="mx-auto flex max-w-3xl flex-col gap-4">
        {showEmpty && (
          <div className="animate-fade-in py-8 text-center">
            <h2 className="text-lg font-medium text-slate-200">
              J.A.R.V.I.S.
            </h2>
            {profileLoaded && !addressAs && (
              <div className="mx-auto mt-6 max-w-sm text-left">
                <NicknamePicker
                  onSubmit={handleNicknameSubmit}
                  loading={pickerLoading}
                  error={pickerError}
                  submitLabel="Save"
                  subtitle="Choose a title or enter how you'd like to be addressed."
                />
              </div>
            )}
            {profileLoaded && addressAs && (
              <p className="mt-2 text-sm text-jarvis-muted">
                {buildEmptyStateGreeting(addressAs)}
              </p>
            )}
            {!profileLoaded && (
              <p className="mt-2 text-sm text-jarvis-muted">Loading…</p>
            )}
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
