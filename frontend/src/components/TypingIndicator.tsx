"use client";

export function TypingIndicator() {
  return (
    <div className="animate-fade-in flex justify-start">
      <div className="rounded-2xl border border-jarvis-border bg-jarvis-panel px-4 py-3">
        <p className="text-sm text-jarvis-muted">JARVIS is thinking…</p>
        <div className="mt-2 flex gap-1">
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-jarvis-accent" />
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-jarvis-accent [animation-delay:150ms]" />
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-jarvis-accent [animation-delay:300ms]" />
        </div>
      </div>
    </div>
  );
}
