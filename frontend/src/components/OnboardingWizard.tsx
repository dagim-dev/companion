"use client";

import { FormEvent, useEffect, useState } from "react";
import { completeOnboarding } from "@/lib/api";
import { NicknamePicker } from "./NicknamePicker";

type OnboardingWizardProps = {
  onComplete: () => void;
};

export function OnboardingWizard({ onComplete }: OnboardingWizardProps) {
  const [step, setStep] = useState(1);
  const [communication, setCommunication] = useState<
    "direct" | "balanced" | "gentle"
  >("balanced");
  const [energy, setEnergy] = useState<"calm" | "upbeat">("calm");
  const [challengeLevel, setChallengeLevel] = useState<"low" | "medium" | "high">("medium");
  const [emotionalSupport, setEmotionalSupport] = useState<"low" | "medium" | "high">("medium");
  const [detailLevel, setDetailLevel] = useState<"concise" | "normal" | "detailed">("normal");
  const [examplesPreference, setExamplesPreference] = useState<"few" | "when_useful" | "often">("when_useful");
  const [accountabilityStyle, setAccountabilityStyle] = useState<"light" | "steady" | "firm">("steady");
  const [addressAs, setAddressAs] = useState<string | null>(null);
  const [customNotes, setCustomNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setError(null);
  }, []);

  const handleFinish = async (e: FormEvent) => {
    e.preventDefault();
    if (!addressAs) return;
    setError(null);
    setLoading(true);
    try {
      await completeOnboarding({
        communication,
        energy,
        challenge_level: challengeLevel,
        emotional_support: emotionalSupport,
        detail_level: detailLevel,
        examples_preference: examplesPreference,
        accountability_style: accountabilityStyle,
        address_as: addressAs,
        custom_notes: customNotes.trim() || undefined,
      });
      onComplete();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="flex h-dvh flex-col items-center justify-center px-4">
      <div className="w-full max-w-lg rounded-xl border border-jarvis-border bg-jarvis-panel/80 p-6">
        <h1 className="text-lg font-semibold text-slate-100">
          Configure J.A.R.V.I.S.
        </h1>
        <p className="mt-1 text-sm text-jarvis-muted">
          Step {step} of 4 — personalize how Jarvis communicates
        </p>

        {step === 1 && (
          <div className="mt-6 space-y-4">
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
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setStep(2)}
                className="w-full rounded-lg bg-jarvis-accent py-2 text-sm font-medium text-slate-900"
              >
                Continue
              </button>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="mt-6 space-y-4">
            <div>
              <p className="text-sm text-jarvis-muted">Challenge level</p>
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
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setStep(1)}
                className="flex-1 rounded-lg border border-jarvis-border py-2 text-sm text-jarvis-muted"
              >
                Back
              </button>
              <button
                type="button"
                onClick={() => setStep(3)}
                className="flex-1 rounded-lg bg-jarvis-accent py-2 text-sm font-medium text-slate-900"
              >
                Continue
              </button>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="mt-6 space-y-4">
            <div>
              <p className="text-sm text-jarvis-muted">Detail level</p>
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
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setStep(2)}
                className="flex-1 rounded-lg border border-jarvis-border py-2 text-sm text-jarvis-muted"
              >
                Back
              </button>
              <button
                type="button"
                onClick={() => setStep(4)}
                className="flex-1 rounded-lg bg-jarvis-accent py-2 text-sm font-medium text-slate-900"
              >
                Continue
              </button>
            </div>
          </div>
        )}

        {step === 4 && (
          <div className="mt-6 space-y-4">
            <NicknamePicker
              onSubmit={async (value) => {
                setAddressAs(value);
              }}
              submitLabel="Next"
              subtitle="This is how Jarvis will greet you in chat."
            />
            {addressAs && (
              <p className="text-center text-xs text-jarvis-muted">
                Addressing you as: <span className="text-slate-200">{addressAs}</span>
              </p>
            )}
            <label className="block text-sm text-jarvis-muted">
              Anything else? (optional)
              <textarea
                value={customNotes}
                onChange={(e) => setCustomNotes(e.target.value)}
                maxLength={300}
                rows={3}
                className="mt-1 w-full rounded-lg border border-jarvis-border bg-jarvis-bg px-3 py-2 text-slate-100"
                placeholder="e.g. Prefer blunt feedback on workouts"
              />
            </label>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setStep(3)}
                className="flex-1 rounded-lg border border-jarvis-border py-2 text-sm text-jarvis-muted"
              >
                Back
              </button>
              <button
                type="button"
                onClick={handleFinish}
                disabled={loading || !addressAs}
                className="flex-1 rounded-lg bg-jarvis-accent py-2 text-sm font-medium text-slate-900 disabled:opacity-50"
              >
                {loading ? "Saving…" : "Start chatting"}
              </button>
            </div>
          </div>
        )}

        {error && (
          <p className="mt-4 text-center text-sm text-red-400">{error}</p>
        )}
      </div>
    </main>
  );
}
