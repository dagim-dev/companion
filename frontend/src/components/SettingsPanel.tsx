"use client";

import { FormEvent, useEffect, useState } from "react";
import {
  fetchOnboardingRoles,
  fetchPreferences,
  resetLearnedStyle,
  updateAddressAs,
  updatePreferences,
  type OnboardingRole,
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
  const [roles, setRoles] = useState<OnboardingRole[]>([]);
  const [prefs, setPrefs] = useState<Preferences | null>(null);
  const [roleId, setRoleId] = useState("general_jarvis");
  const [communication, setCommunication] = useState<
    "direct" | "balanced" | "gentle"
  >("balanced");
  const [energy, setEnergy] = useState<"calm" | "upbeat">("calm");
  const [customNotes, setCustomNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [addressLoading, setAddressLoading] = useState(false);

  useEffect(() => {
    if (!open) return;
    Promise.all([fetchOnboardingRoles(), fetchPreferences()])
      .then(([r, p]) => {
        setRoles(r);
        setPrefs(p);
        setRoleId(p.role_id);
        setCommunication(p.communication);
        setEnergy(p.energy);
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
        role_id: roleId,
        communication,
        energy,
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
              <p className="text-sm text-jarvis-muted">Style</p>
              <div className="mt-2 grid gap-2">
                {roles.map((r) => (
                  <button
                    key={r.id}
                    type="button"
                    onClick={() => setRoleId(r.id)}
                    className={`rounded-lg border p-2 text-left text-xs ${
                      roleId === r.id
                        ? "border-jarvis-accent bg-jarvis-accent/10"
                        : "border-jarvis-border"
                    }`}
                  >
                    {r.title}
                  </button>
                ))}
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
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
            <div className="flex gap-2">
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
