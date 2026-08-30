import { useCallback, useEffect, useState } from "react";
import { fetchState, runGeneration } from "./api";
import Council from "./components/Council";
import GenomePane from "./components/GenomePane";
import DemoTheater from "./components/DemoTheater";
import LoopStrip from "./components/LoopStrip";
import Sentinel from "./components/Sentinel";
import type { Genome, TunnelState } from "./types";

const empty: TunnelState = {
  history: [],
  genomes: [],
  alerts: [],
  artifacts: [],
  agent_log: [],
  vector_det_rates: {},
  demo_chains: {},
    tte_generations: 0,
    loop_gain_auc: 0,
    fidelity_mean: 0,
    atlas: {},
    protocol: {},
    shadow: {},
    calibrated: false,
  llm_enabled: false,
};

const PANES = [
  { id: "identify", label: "Identify", step: "1" },
  { id: "generate", label: "Generate", step: "2" },
  { id: "loop", label: "Loop", step: "3" },
  { id: "defend", label: "Defend", step: "4" },
] as const;

function fmt(n: number | null | undefined, d = 2) {
  if (n == null || Number.isNaN(Number(n))) return "—";
  return Number(n).toFixed(d);
}

export default function App() {
  const [state, setState] = useState<TunnelState>(empty);
  const [query, setQuery] = useState("");
  const [picked, setPicked] = useState<Genome | null>(null);
  const [pane, setPane] = useState<(typeof PANES)[number]["id"]>("identify");
  const [running, setRunning] = useState(false);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  const refresh = useCallback(async () => {
    const s = await fetchState();
    setState(s);
    setPicked((p) => p || s.genomes[0] || null);
    setLoading(false);
  }, []);

  useEffect(() => {
    refresh().catch(() => {
      setLoading(false);
      setErr("Could not reach the API. Run make api (or make ui with the API on port 8000).");
    });
  }, [refresh]);

  const last = state.history[state.history.length - 1];
  const gen = last?.generation ?? state.history.length;
  const ready = !loading && state.genomes.length > 0;

  async function onRun() {
    setRunning(true);
    setErr("");
    try {
      await runGeneration(1);
      await refresh();
      setPane("loop");
    } catch (e) {
      const msg =
        e instanceof DOMException && e.name === "AbortError"
          ? "Run timed out after 10 minutes — check the API log."
          : "Run failed — seeded data remains. Check the API log and try again.";
      setErr(msg);
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="app" aria-busy={loading || running}>
      <header className="topbar">
        <div className="brand">
          <h1 className="logo">
            AGNI
            <span>Fraud Wind Tunnel</span>
          </h1>
          <p className="tagline">
            <strong>Identify</strong> → generate → detect → mutate
          </p>
        </div>

        <dl className="metrics" aria-label="Wind tunnel metrics">
          <div>
            <dt>Vectors</dt>
            <dd className="num">{loading ? "…" : state.genomes.length || "—"}</dd>
          </div>
          <div>
            <dt>Twin fidelity</dt>
            <dd className="num">{loading ? "…" : fmt(state.fidelity_mean)}</dd>
          </div>
          <div>
            <dt>ROC AUC</dt>
            <dd className="num">{loading ? "…" : fmt(last?.roc_auc, 3)}</dd>
          </div>
          <div>
            <dt>Time to evade</dt>
            <dd className="num">{loading ? "…" : `${state.tte_generations ?? 0} gen`}</dd>
          </div>
        </dl>

        <div className="actions">
          <div className="badges">
            <span className={`badge${state.calibrated ? " on" : ""}`}>
              {state.calibrated ? "IEEE twin" : "Offline"}
            </span>
            <span className={`badge${state.llm_enabled ? " on" : ""}`}>
              {state.llm_enabled ? "LLM on" : "LLM off"}
            </span>
          </div>
          <button
            className="run"
            type="button"
            onClick={onRun}
            disabled={running || loading}
            aria-busy={running}
          >
            {running ? "Running…" : "Run generation"}
          </button>
        </div>
      </header>

      {err ? (
        <p className="banner err" role="alert">
          {err}
        </p>
      ) : null}

      <LoopStrip generation={gen} running={running} ready={ready} />

      <nav className="rail" aria-label="Sections">
        {PANES.map((p) => (
          <button
            key={p.id}
            type="button"
            className={pane === p.id ? "on" : ""}
            aria-pressed={pane === p.id}
            onClick={() => setPane(p.id)}
          >
            <span className="rail-n">{p.step}</span>
            {p.label}
          </button>
        ))}
      </nav>

      <main className="workspace">
        {loading ? (
          <div className="pane pane-loading on" aria-live="polite">
            <p className="loading-msg">Loading wind tunnel state…</p>
          </div>
        ) : (
          <>
            <section
              className={`pane pane-identify${pane === "identify" ? " on" : ""}`}
              aria-labelledby="pane-identify-title"
            >
              <GenomePane
                genomes={state.genomes}
                query={query}
                onQuery={setQuery}
                selected={picked}
                atlas={state.atlas}
                onSelect={(g) => {
                  setPicked(g);
                  setPane("generate");
                }}
              />
            </section>
            <section
              className={`pane pane-generate${pane === "generate" ? " on" : ""}`}
              aria-labelledby="pane-generate-title"
            >
              <DemoTheater
                focus={picked}
                chains={state.demo_chains || {}}
                running={running}
              />
            </section>
            <section
              className={`pane pane-loop${pane === "loop" ? " on" : ""}`}
              aria-labelledby="pane-loop-title"
            >
              <Council logs={state.agent_log} />
            </section>
            <section
              className={`pane pane-defend${pane === "defend" ? " on" : ""}`}
              aria-labelledby="pane-defend-title"
            >
              <Sentinel
                history={state.history}
                rates={state.vector_det_rates}
                protocol={state.protocol}
                shadow={state.shadow}
              />
            </section>
          </>
        )}
      </main>

      <footer className="foot">
        Synthetic IDs only · no raw PII · straw rules + bank checklist are not Mastercard production
        · lab AUC is not the headline — see family holdout and recall at base rate
      </footer>
    </div>
  );
}
