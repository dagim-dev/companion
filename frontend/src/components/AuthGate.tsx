"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import {
  clearAccessToken,
  fetchMe,
  getAccessToken,
  login,
  register,
} from "@/lib/api";
import { OnboardingWizard } from "@/components/OnboardingWizard";

type AuthGateProps = {
  children: React.ReactNode;
};

export function AuthGate({ children }: AuthGateProps) {
  const [ready, setReady] = useState(false);
  const [authenticated, setAuthenticated] = useState(false);
  const [onboardingDone, setOnboardingDone] = useState(false);
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const refreshSession = useCallback(async () => {
    const token = getAccessToken();
    if (!token) {
      setAuthenticated(false);
      setOnboardingDone(false);
      setReady(true);
      return;
    }
    try {
      const me = await fetchMe();
      setAuthenticated(true);
      setOnboardingDone(me.onboarding_completed);
    } catch {
      clearAccessToken();
      setAuthenticated(false);
      setOnboardingDone(false);
    }
    setReady(true);
  }, []);

  useEffect(() => {
    refreshSession();
  }, [refreshSession]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        await register(email, password);
      }
      await refreshSession();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const handleSignOut = () => {
    clearAccessToken();
    setAuthenticated(false);
    setOnboardingDone(false);
  };

  if (!ready) {
    return (
      <main className="flex h-dvh items-center justify-center text-jarvis-muted">
        Loading…
      </main>
    );
  }

  if (!authenticated) {
    return (
      <main className="flex h-dvh flex-col items-center justify-center px-4">
        <div className="w-full max-w-sm rounded-xl border border-jarvis-border bg-jarvis-panel/80 p-6">
          <h1 className="text-lg font-semibold text-slate-100">J.A.R.V.I.S.</h1>
          <p className="mt-1 text-sm text-jarvis-muted">
            {mode === "login" ? "Sign in to continue" : "Create an account"}
          </p>

          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <label className="block text-sm text-jarvis-muted">
              Email
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-1 w-full rounded-lg border border-jarvis-border bg-jarvis-bg px-3 py-2 text-slate-100"
              />
            </label>
            <label className="block text-sm text-jarvis-muted">
              Password
              <input
                type="password"
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-1 w-full rounded-lg border border-jarvis-border bg-jarvis-bg px-3 py-2 text-slate-100"
              />
            </label>
            {error && (
              <p className="text-sm text-red-400">{error}</p>
            )}
            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-lg bg-sky-600 py-2 text-sm font-medium text-white hover:bg-sky-500 disabled:opacity-50"
            >
              {loading
                ? "Please wait…"
                : mode === "login"
                  ? "Sign in"
                  : "Register"}
            </button>
          </form>

          <button
            type="button"
            onClick={() => {
              setMode(mode === "login" ? "register" : "login");
              setError(null);
            }}
            className="mt-4 w-full text-center text-xs text-jarvis-muted hover:text-slate-300"
          >
            {mode === "login"
              ? "Need an account? Register"
              : "Already have an account? Sign in"}
          </button>
        </div>
      </main>
    );
  }

  if (!onboardingDone) {
    return (
      <OnboardingWizard
        onComplete={() => {
          setOnboardingDone(true);
        }}
      />
    );
  }

  return (
    <>
      <div className="fixed right-4 top-4 z-10">
        <button
          type="button"
          onClick={handleSignOut}
          className="rounded-full border border-jarvis-border px-3 py-1 text-xs text-jarvis-muted hover:text-slate-200"
        >
          Sign out
        </button>
      </div>
      {children}
    </>
  );
}
