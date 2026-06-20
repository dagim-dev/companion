"use client";

import { FormEvent, useState } from "react";

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
  title = "How should NOVA address you?",
  subtitle,
}: NicknamePickerProps) {
  const [custom, setCustom] = useState("");
  const resolved = custom.trim();

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
        <p className="text-xs text-nova-muted">{subtitle}</p>
      )}

      <label className="block text-sm text-nova-muted">
        Custom address
        <input
          type="text"
          value={custom}
          onChange={(e) => setCustom(e.target.value)}
          maxLength={MAX_LEN}
          placeholder="Name or title, e.g. Alex or Captain"
          className="mt-1 w-full rounded-lg border border-nova-border bg-nova-bg px-3 py-2 text-slate-100"
        />
      </label>

      <button
        type="submit"
        disabled={loading || !resolved}
        className="w-full rounded-lg bg-nova-accent py-2 text-sm font-medium text-slate-900 disabled:opacity-50"
      >
        {loading ? "Saving…" : submitLabel}
      </button>

      {error && (
        <p className="text-center text-sm text-red-400">{error}</p>
      )}
    </form>
  );
}
