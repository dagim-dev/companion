"use client";

import { FormEvent, KeyboardEvent, useState } from "react";
import { VoiceButton } from "./VoiceButton";

type ChatInputProps = {
  disabled?: boolean;
  voiceAvailable?: boolean;
  onSend: (message: string) => void;
  lastAssistantText?: string;
};

export function ChatInput({
  disabled,
  voiceAvailable = true,
  onSend,
  lastAssistantText,
}: ChatInputProps) {
  const [value, setValue] = useState("");

  const submit = () => {
    if (!value.trim() || disabled) return;
    onSend(value);
    setValue("");
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    submit();
  };

  return (
    <form
      onSubmit={onSubmit}
      className="border-t border-jarvis-border bg-jarvis-panel/80 p-4 backdrop-blur"
    >
      <div className="mx-auto flex max-w-3xl items-end gap-3">
        <VoiceButton
          disabled={disabled}
          voiceAvailable={voiceAvailable}
          onTranscript={(text) => onSend(text)}
          lastAssistantText={lastAssistantText}
        />
        <textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={onKeyDown}
          disabled={disabled}
          rows={1}
          placeholder="Message JARVIS…"
          className="max-h-32 min-h-[44px] flex-1 resize-none rounded-xl border border-jarvis-border bg-jarvis-bg px-4 py-3 text-sm text-slate-100 placeholder:text-jarvis-muted focus:border-jarvis-accent focus:outline-none disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={disabled || !value.trim()}
          className="rounded-xl bg-jarvis-accent px-5 py-3 text-sm font-medium text-white transition hover:bg-jarvis-accent/90 disabled:opacity-40"
        >
          Send
        </button>
      </div>
    </form>
  );
}
