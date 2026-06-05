"use client";

import { FormEvent, useEffect, useState } from "react";
import {
  completeOnboarding,
  fetchOnboardingRoles,
  type OnboardingRole,
} from "@/lib/api";
import { NicknamePicker } from "./NicknamePicker";

type OnboardingWizardProps = {
  onComplete: () => void;
};

export function OnboardingWizard({ onComplete }: OnboardingWizardProps) {
  const [step, setStep] = useState(1);
  const [roles, setRoles] = useState<OnboardingRole[]>([]);
  const [roleId, setRoleId] = useState("general_jarvis");
  const [communication, setCommunication] = useState<
    "direct" | "balanced" | "gentle"
  >("balanced");
  const [energy, setEnergy] = useState<"calm" | "upbeat">("calm");
  const [addressAs, setAddressAs] = useState<string | null>(null);
  const [customNotes, setCustomNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchOnboardingRoles()
      .then(setRoles)
      .catch((e) => setError((e as Error).message));
  }, []);

  const handleFinish = async (e: FormEvent) => {
    e.preventDefault();
    if (!addressAs) return;
    setError(null);
    setLoading(true);
    try {
      await completeOnboarding({
        role_id: roleId,
        communication,
        energy,
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
          Step {step} of 3 — personalize how your companion behaves
        </p>

        {step === 1 && (
          <div className="mt-6 space-y-3">
            <p className="text-sm text-jarvis-muted">Choose your companion style</p>
            <div className="grid gap-2 sm:grid-cols-2">
              {(roles.length > 0
                ? roles
                : [{ id: "general_jarvis", title: "General JARVIS", description: "" }]
              ).map((r) => (
                <button
                  key={r.id}
                  type="button"
                  onClick={() => setRoleId(r.id)}
                  className={`rounded-lg border p-3 text-left text-sm transition ${
                    roleId === r.id
                      ? "border-jarvis-accent bg-jarvis-accent/10 text-slate-100"
                      : "border-jarvis-border text-jarvis-muted hover:border-slate-500"
                  }`}
                >
                  <span className="font-medium text-slate-200">{r.title}</span>
                  <span className="mt-1 block text-xs">{r.description}</span>
                </button>
              ))}
            </div>
            <button
              type="button"
              onClick={() => setStep(2)}
              className="mt-4 w-full rounded-lg bg-jarvis-accent py-2 text-sm font-medium text-slate-900"
            >
              Continue
            </button>
          </div>
        )}

        {step === 2 && (
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
                onClick={() => setStep(2)}
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
