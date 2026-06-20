"use client";

export function TypingIndicator() {
  return (
    <div className="animate-fade-in flex justify-start">
      <div className="rounded-2xl border border-nova-border bg-nova-panel px-4 py-3">
        <p className="text-sm text-nova-muted">NOVA is thinking…</p>
        <div className="mt-2 flex gap-1">
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-nova-accent" />
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-nova-accent [animation-delay:150ms]" />
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-nova-accent [animation-delay:300ms]" />
        </div>
      </div>
    </div>
  );
}
