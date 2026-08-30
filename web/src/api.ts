import type { TunnelState } from "./types";

const RUN_TIMEOUT_MS = 600_000;

export async function fetchState(): Promise<TunnelState> {
  const r = await fetch("/api/state");
  if (!r.ok) throw new Error(`State ${r.status}`);
  return r.json();
}

export async function runGeneration(generations = 1): Promise<void> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), RUN_TIMEOUT_MS);
  try {
    const r = await fetch("/api/loop/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ generations }),
      signal: ctrl.signal,
    });
    if (!r.ok) throw new Error(`Run ${r.status}`);
  } finally {
    clearTimeout(timer);
  }
}
