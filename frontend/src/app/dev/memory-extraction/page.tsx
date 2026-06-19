"use client";

import { useCallback, useEffect, useState } from "react";
import { AuthGate } from "@/components/AuthGate";
import {
  fetchMemoryExtractionHealth,
  type MemoryExtractionHealth,
} from "@/lib/api";

function StatCard({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <div className="rounded-xl border border-jarvis-border bg-jarvis-panel/80 p-4">
      <p className="text-xs uppercase tracking-wide text-jarvis-muted">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-slate-100">{value}</p>
    </div>
  );
}

function MemoryExtractionDashboard() {
  const [health, setHealth] = useState<MemoryExtractionHealth | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const loadHealth = useCallback(async () => {
    try {
      const data = await fetchMemoryExtractionHealth();
      setHealth(data);
      setError(null);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadHealth();
    const timer = window.setInterval(loadHealth, 15000);
    return () => window.clearInterval(timer);
  }, [loadHealth]);

  const successRate = health
    ? `${(health.success_rate * 100).toFixed(1)}%`
    : "0.0%";

  return (
    <main className="min-h-dvh px-4 py-8">
      <div className="mx-auto max-w-5xl">
        <header className="mb-6">
          <p className="text-xs uppercase tracking-[0.3em] text-jarvis-muted">
            Developer Tools
          </p>
          <h1 className="mt-2 text-2xl font-semibold text-slate-100">
            Memory Extraction Health
          </h1>
          <p className="mt-2 max-w-2xl text-sm text-jarvis-muted">
            Tracks async LLM memory extraction jobs, retries, permanent failures,
            and recent failure reasons.
          </p>
        </header>

        {health?.show_warning && (
          <div className="mb-6 rounded-xl border border-amber-500/40 bg-amber-500/10 p-4 text-sm text-amber-100">
            <p className="font-medium">Memory extraction backlog detected.</p>
            <p>{health.pending_retry} jobs waiting for retry.</p>
          </div>
        )}

        {error && (
          <div className="mb-6 rounded-xl border border-red-500/40 bg-red-500/10 p-4 text-sm text-red-200">
            {error}
          </div>
        )}

        {loading && !health ? (
          <p className="text-sm text-jarvis-muted">Loading memory health…</p>
        ) : (
          <>
            <section className="grid gap-4 md:grid-cols-3">
              <StatCard label="Pending" value={health?.pending ?? 0} />
              <StatCard label="Retrying" value={health?.pending_retry ?? 0} />
              <StatCard
                label="Failed"
                value={health?.failed_permanently ?? 0}
              />
              <StatCard
                label="Processing"
                value={health?.processing ?? 0}
              />
              <StatCard label="Success Rate" value={successRate} />
              <StatCard
                label="Total Jobs Processed"
                value={health?.total_jobs_processed ?? 0}
              />
            </section>

            <section className="mt-6 rounded-xl border border-jarvis-border bg-jarvis-panel/80 p-4">
              <h2 className="text-sm font-semibold text-slate-100">
                Last Failure
              </h2>
              <p className="mt-3 text-sm text-jarvis-muted">
                {health?.last_failure_reason || "No recorded failures."}
              </p>
              {health?.last_failed_job && (
                <dl className="mt-4 grid gap-3 text-sm md:grid-cols-3">
                  <div>
                    <dt className="text-jarvis-muted">Job ID</dt>
                    <dd className="text-slate-100">{health.last_failed_job.id}</dd>
                  </div>
                  <div>
                    <dt className="text-jarvis-muted">Status</dt>
                    <dd className="text-slate-100">
                      {health.last_failed_job.status}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-jarvis-muted">Retries</dt>
                    <dd className="text-slate-100">
                      {health.last_failed_job.retry_count}
                    </dd>
                  </div>
                </dl>
              )}
            </section>
          </>
        )}
      </div>
    </main>
  );
}

export default function MemoryExtractionPage() {
  return (
    <AuthGate>
      <MemoryExtractionDashboard />
    </AuthGate>
  );
}
