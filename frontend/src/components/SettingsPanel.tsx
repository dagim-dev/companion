"use client";

import { FormEvent, useEffect, useState } from "react";
import {
  fetchPreferences,
  resetLearnedStyle,
  updateAddressAs,
  updatePreferences,
  type Preferences,
} from "@/lib/api";
import { NicknamePicker } from "./NicknamePicker";

type SettingsPanelProps = {
  open: boolean;
  onClose: () => void;
  addressAs: string | null;
  onAddressAsChange: (addressAs: string) => void;
};

export function SettingsPanel({
  open,
  onClose,
  addressAs,
  onAddressAsChange,
}: SettingsPanelProps) {
  const [prefs, setPrefs] = useState<Preferences | null>(null);
  const [communication, setCommunication] = useState<
    "direct" | "balanced" | "gentle"
  >("balanced");
  const [energy, setEnergy] = useState<"calm" | "upbeat">("calm");
  const [challengeLevel, setChallengeLevel] = useState<"low" | "medium" | "high">("medium");
  const [emotionalSupport, setEmotionalSupport] = useState<"low" | "medium" | "high">("medium");
  const [detailLevel, setDetailLevel] = useState<"concise" | "normal" | "detailed">("normal");
  const [examplesPreference, setExamplesPreference] = useState<"few" | "when_useful" | "often">("when_useful");
  const [accountabilityStyle, setAccountabilityStyle] = useState<"light" | "steady" | "firm">("steady");
  const [customNotes, setCustomNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [addressLoading, setAddressLoading] = useState(false);

  useEffect(() => {
    if (!open) return;
    fetchPreferences()
      .then((p) => {
        setPrefs(p);
        setCommunication(p.communication);
        setEnergy(p.energy);
        setChallengeLevel(p.challenge_level);
        setEmotionalSupport(p.emotional_support);
        setDetailLevel(p.detail_level);
        setExamplesPreference(p.examples_preference);
        setAccountabilityStyle(p.accountability_style);
        setCustomNotes(p.custom_notes || "");
      })
      .catch((e) => setError((e as Error).message));
  }, [open]);

  const handleAddressSubmit = async (value: string) => {
    setAddressLoading(true);
    setError(null);
    try {
      await updateAddressAs(value);
      onAddressAsChange(value);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setAddressLoading(false);
    }
  };

  const handleSave = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const updated = await updatePreferences({
        communication,
        energy,
        challenge_level: challengeLevel,
        emotional_support: emotionalSupport,
        detail_level: detailLevel,
        examples_preference: examplesPreference,
        accountability_style: accountabilityStyle,
        custom_notes: customNotes.trim() || undefined,
      });
      setPrefs(updated);
      onClose();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const handleResetLearned = async () => {
    setResetting(true);
    setError(null);
    try {
      await resetLearnedStyle();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setResetting(false);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4">
      <div className="max-h-[90vh] w-full max-w-md overflow-y-auto rounded-xl border border-jarvis-border bg-jarvis-panel p-6">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-100">Companion settings</h2>
          <button
            type="button"
            onClick={onClose}
            className="text-sm text-jarvis-muted hover:text-slate-200"
          >
            Close
          </button>
        </div>

        <div className="mt-4 border-b border-jarvis-border pb-4">
          <p className="text-xs text-jarvis-muted">
            Current: {addressAs ? addressAs : "Not set"}
          </p>
          <NicknamePicker
            onSubmit={handleAddressSubmit}
            loading={addressLoading}
            error={null}
            submitLabel="Update address"
            title="Address me as"
            subtitle="Used in greetings and when Jarvis speaks to you."
          />
        </div>

        {prefs ? (
          <form onSubmit={handleSave} className="mt-4 space-y-4">
            <div>
              <p className="text-sm text-jarvis-muted">Communication</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {(["direct", "balanced", "gentle"] as const).map((c) => (
                  <button
                    key={c}
                    type="button"
                    onClick={() => setCommunication(c)}
                    className={`rounded-full px-3 py-1 text-xs capitalize ${
                      communication === c
                        ? "bg-jarvis-accent text-slate-900"
                        : "border border-jarvis-border text-jarvis-muted"
                    }`}
                  >
                    {c}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <p className="text-sm text-jarvis-muted">Energy</p>
              <div className="mt-2 flex gap-2">
                {(["calm", "upbeat"] as const).map((e) => (
                  <button
                    key={e}
                    type="button"
                    onClick={() => setEnergy(e)}
                    className={`rounded-full px-3 py-1 text-xs capitalize ${
                      energy === e
                        ? "bg-jarvis-accent text-slate-900"
                        : "border border-jarvis-border text-jarvis-muted"
                    }`}
                  >
                    {e}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <p className="text-sm text-jarvis-muted">Challenge</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {(["low", "medium", "high"] as const).map((level) => (
                  <button
                    key={level}
                    type="button"
                    onClick={() => setChallengeLevel(level)}
                    className={`rounded-full px-3 py-1 text-xs capitalize ${
                      challengeLevel === level
                        ? "bg-jarvis-accent text-slate-900"
                        : "border border-jarvis-border text-jarvis-muted"
                    }`}
                  >
                    {level}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <p className="text-sm text-jarvis-muted">Emotional support</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {(["low", "medium", "high"] as const).map((level) => (
                  <button
                    key={level}
                    type="button"
                    onClick={() => setEmotionalSupport(level)}
                    className={`rounded-full px-3 py-1 text-xs capitalize ${
                      emotionalSupport === level
                        ? "bg-jarvis-accent text-slate-900"
                        : "border border-jarvis-border text-jarvis-muted"
                    }`}
                  >
                    {level}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <p className="text-sm text-jarvis-muted">Detail</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {(["concise", "normal", "detailed"] as const).map((level) => (
                  <button
                    key={level}
                    type="button"
                    onClick={() => setDetailLevel(level)}
                    className={`rounded-full px-3 py-1 text-xs capitalize ${
                      detailLevel === level
                        ? "bg-jarvis-accent text-slate-900"
                        : "border border-jarvis-border text-jarvis-muted"
                    }`}
                  >
                    {level}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <p className="text-sm text-jarvis-muted">Examples</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {([
                  ["few", "Few"],
                  ["when_useful", "When useful"],
                  ["often", "Often"],
                ] as const).map(([value, label]) => (
                  <button
                    key={value}
                    type="button"
                    onClick={() => setExamplesPreference(value)}
                    className={`rounded-full px-3 py-1 text-xs ${
                      examplesPreference === value
                        ? "bg-jarvis-accent text-slate-900"
                        : "border border-jarvis-border text-jarvis-muted"
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <p className="text-sm text-jarvis-muted">Accountability</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {(["light", "steady", "firm"] as const).map((style) => (
                <button
                  key={style}
                  type="button"
                  onClick={() => setAccountabilityStyle(style)}
                  className={`rounded-full px-3 py-1 text-xs capitalize ${
                    accountabilityStyle === style
                      ? "bg-jarvis-accent text-slate-900"
                      : "border border-jarvis-border text-jarvis-muted"
                  }`}
                >
                  {style}
                </button>
              ))}
            </div>
            </div>
            <textarea
              value={customNotes}
              onChange={(ev) => setCustomNotes(ev.target.value)}
              maxLength={300}
              rows={2}
              className="w-full rounded-lg border border-jarvis-border bg-jarvis-bg px-3 py-2 text-sm text-slate-100"
              placeholder="Custom notes"
            />
            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-lg bg-jarvis-accent py-2 text-sm font-medium text-slate-900"
            >
              {loading ? "Saving…" : "Save companion style"}
            </button>
            <button
              type="button"
              onClick={handleResetLearned}
              disabled={resetting}
              className="w-full rounded-lg border border-jarvis-border py-2 text-sm text-jarvis-muted"
            >
              {resetting ? "Resetting…" : "Reset learned style"}
            </button>
          </form>
        ) : (
          <p className="mt-4 text-sm text-jarvis-muted">Loading…</p>
        )}

        {error && <p className="mt-2 text-sm text-red-400">{error}</p>}
      </div>
    </div>
  );
}
