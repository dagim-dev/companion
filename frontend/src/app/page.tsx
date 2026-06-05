"use client";

import { useCallback, useEffect, useState } from "react";
import { AuthGate } from "@/components/AuthGate";
import { ChatInput } from "@/components/ChatInput";
import { ChatWindow } from "@/components/ChatWindow";
import { SettingsPanel } from "@/components/SettingsPanel";
import { fetchHealth, fetchProfile } from "@/lib/api";
import { useChat } from "@/hooks/useChat";

function ChatApp() {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [addressAs, setAddressAs] = useState<string | null>(null);
  const [profileLoaded, setProfileLoaded] = useState(false);
  const [voiceAvailable, setVoiceAvailable] = useState(false);
  const { messages, isThinking, isStreaming, error, sendMessage } = useChat();

  const loadProfile = useCallback(async () => {
    try {
      const profile = await fetchProfile();
      setAddressAs(profile.address_as);
    } catch {
      setAddressAs(null);
    } finally {
      setProfileLoaded(true);
    }
  }, []);

  useEffect(() => {
    loadProfile();
  }, [loadProfile]);

  useEffect(() => {
    fetchHealth()
      .then((h) => setVoiceAvailable(h.voice?.available ?? false))
      .catch(() => setVoiceAvailable(false));
  }, []);

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
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setSettingsOpen(true)}
              className="rounded-full border border-jarvis-border px-3 py-1 text-xs text-jarvis-muted hover:text-slate-200"
            >
              Settings
            </button>
            <span className="rounded-full border border-jarvis-border px-3 py-1 text-xs text-jarvis-muted">
              {isStreaming ? "Online" : "Ready"}
            </span>
          </div>
        </div>
      </header>

      <SettingsPanel
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        addressAs={addressAs}
        onAddressAsChange={setAddressAs}
      />

      <ChatWindow
        messages={messages}
        isThinking={isThinking}
        addressAs={addressAs}
        profileLoaded={profileLoaded}
        onAddressAsChange={setAddressAs}
      />

      {error && (
        <p className="mx-auto max-w-3xl px-4 pb-2 text-center text-sm text-red-400">
          {error}
        </p>
      )}

      <ChatInput
        disabled={isStreaming}
        voiceAvailable={voiceAvailable}
        onSend={sendMessage}
        lastAssistantText={lastAssistant?.content}
      />
    </main>
  );
}

export default function Home() {
  return (
    <AuthGate>
      <ChatApp />
    </AuthGate>
  );
}
