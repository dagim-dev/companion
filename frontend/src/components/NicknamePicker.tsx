"use client";

import { FormEvent, useState } from "react";

const PRESETS = ["Sir", "Boss", "Chief"] as const;
const MAX_LEN = 32;

type NicknamePickerProps = {
  onSubmit: (addressAs: string) => Promise<void>;
  loading?: boolean;
  error?: string | null;
  submitLabel?: string;
  title?: string;
  subtitle?: string;
};

export function NicknamePicker({
  onSubmit,
  loading = false,
  error = null,
  submitLabel = "Continue",
  title = "How should Jarvis address you?",
  subtitle,
}: NicknamePickerProps) {
  const [preset, setPreset] = useState<string | null>(null);
  const [custom, setCustom] = useState("");

  const resolved =
    preset && preset !== "custom"
      ? preset
      : custom.trim();

  const handlePreset = (value: string) => {
    setPreset(value);
    if (value !== "custom") {
      setCustom("");
    }
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const value = resolved.slice(0, MAX_LEN);
    if (!value) return;
    await onSubmit(value);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {title && (
        <p className="text-sm font-medium text-slate-200">{title}</p>
      )}
      {subtitle && (
        <p className="text-xs text-jarvis-muted">{subtitle}</p>
      )}

      <div className="flex flex-wrap justify-center gap-2">
        {PRESETS.map((p) => (
          <button
            key={p}
            type="button"
            onClick={() => handlePreset(p)}
            className={`rounded-full px-4 py-2 text-sm transition ${
              preset === p
                ? "bg-jarvis-accent text-slate-900"
                : "border border-jarvis-border text-jarvis-muted hover:border-slate-500"
            }`}
          >
            {p}
          </button>
        ))}
        <button
          type="button"
          onClick={() => handlePreset("custom")}
          className={`rounded-full px-4 py-2 text-sm transition ${
            preset === "custom"
              ? "bg-jarvis-accent text-slate-900"
              : "border border-jarvis-border text-jarvis-muted hover:border-slate-500"
          }`}
        >
          Custom
        </button>
      </div>

      <label className="block text-sm text-jarvis-muted">
        Or type your own
        <input
          type="text"
          value={custom}
          onChange={(e) => {
            setCustom(e.target.value);
            if (e.target.value.trim()) {
              setPreset("custom");
            }
          }}
          maxLength={MAX_LEN}
          placeholder="Name or title, e.g. Alex or Captain"
          className="mt-1 w-full rounded-lg border border-jarvis-border bg-jarvis-bg px-3 py-2 text-slate-100"
        />
      </label>

      <button
        type="submit"
        disabled={loading || !resolved}
        className="w-full rounded-lg bg-jarvis-accent py-2 text-sm font-medium text-slate-900 disabled:opacity-50"
      >
        {loading ? "Saving…" : submitLabel}
      </button>

      {error && (
        <p className="text-center text-sm text-red-400">{error}</p>
      )}
    </form>
  );
}
