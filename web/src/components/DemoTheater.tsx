import { useEffect, useMemo, useRef, useState } from "react";
import type { DemoStep, Genome } from "../types";

const STAGES = ["Contact", "Phish", "Agent trap", "Harvest", "Transfer"] as const;

type Props = {
  focus: Genome | null;
  chains: Record<string, DemoStep[]>;
  running: boolean;
};

function genomeBase(id: string) {
  const m = id.match(/^(GEN-\d+)/);
  return m ? m[1] : id.split("-g")[0];
}

export default function DemoTheater({ focus, chains, running }: Props) {
  const base = focus ? genomeBase(focus.id) : null;
  const steps = useMemo(
    () => (base && chains[base] ? chains[base] : []),
    [base, chains],
  );

  const [idx, setIdx] = useState(0);
  const [playing, setPlaying] = useState(false);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const listRef = useRef<HTMLUListElement>(null);

  useEffect(() => {
    setIdx(0);
    setPlaying(steps.length > 0);
  }, [base, steps]);

  useEffect(() => {
    if (running && steps.length) {
      setIdx(0);
      setPlaying(true);
    }
  }, [running, steps.length]);

  useEffect(() => {
    if (timer.current) clearInterval(timer.current);
    if (!playing || !steps.length) return;
    timer.current = setInterval(() => {
      setIdx((n) => {
        if (n >= steps.length - 1) {
          setPlaying(false);
          if (timer.current) clearInterval(timer.current);
          return n;
        }
        return n + 1;
      });
    }, 1800);
    return () => {
      if (timer.current) clearInterval(timer.current);
    };
  }, [playing, steps]);

  useEffect(() => {
    const el = listRef.current;
    if (!el) return;
    const instant = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    el.scrollTo({ top: el.scrollHeight, behavior: instant ? "instant" : "smooth" });
  }, [idx]);

  const visible = steps.slice(0, idx + 1);
  const step = steps[idx];
  const stage = step?.stage ?? 1;
  const transfers = visible.filter((s) => s.type === "transfer");
  const sentCaught = transfers.filter((s) => s.sentinel_caught).length;
  const rulesCaught = transfers.filter((s) => s.rules_caught).length;
  const done = idx >= steps.length - 1 && !playing;
  const sentWin = transfers.length > 0 && sentCaught > rulesCaught;
  const rulesWin = transfers.length > 0 && rulesCaught > sentCaught;
  const catchFmt = (n: number) => (transfers.length ? `${n}/${transfers.length}` : "—");

  return (
    <>
      <header className="pane-head">
        <span className="pane-step">2</span>
        <div>
          <h2 id="pane-generate-title">Generate → Defend</h2>
          <p>
            {focus
              ? `Live replay for ${focus.id} — attack unfolds, defenders score each transfer`
              : "Select a fraud vector in Identify"}
          </p>
        </div>
      </header>

      {!focus ? (
        <p className="empty">Pick a vector in Identify to start the replay.</p>
      ) : !steps.length ? (
        <p className="empty">
          No replay data for {focus.id}. Run <strong>Run generation</strong> once to build
          defender chains.
        </p>
      ) : (
        <div className="theater-arena">
          <div className="theater-scoreboard" aria-live="polite">
            <div className="sb-cell attacker">
              <span className="sb-label">Attacker stage</span>
              <span className="sb-val">{STAGES[Math.min(stage, 5) - 1]}</span>
            </div>
            <div className={`sb-cell defender sentinel${sentWin ? " win" : ""}`}>
              <span className="sb-label">Sentinel model</span>
              <span className="sb-val num">{catchFmt(sentCaught)} caught</span>
            </div>
            <div className={`sb-cell defender rules${rulesWin ? " win" : ""}`}>
              <span className="sb-label">Rules checklist</span>
              <span className="sb-val num">{catchFmt(rulesCaught)} caught</span>
            </div>
          </div>

          <div className="theater-controls">
            <button
              type="button"
              className="tc-btn"
              aria-pressed={playing}
              aria-label={playing ? "Pause replay" : done ? "Replay attack" : "Play replay"}
              onClick={() => {
                if (done) {
                  setIdx(0);
                  setPlaying(true);
                } else {
                  setPlaying((p) => !p);
                }
              }}
            >
              {playing ? "Pause" : done ? "Replay" : "Play"}
            </button>
            <button
              type="button"
              className="tc-btn ghost"
              onClick={() => {
                setIdx(0);
                setPlaying(true);
              }}
            >
              Restart
            </button>
            <span className="tc-progress num">
              {idx + 1} / {steps.length}
            </span>
          </div>

          <div className="chain-rail" aria-label="Kill chain stages">
            {STAGES.map((label, i) => (
              <span
                key={label}
                className={`chain-phase${i + 1 <= stage ? " lit" : ""}${i + 1 === stage ? " now" : ""}`}
              >
                {label}
              </span>
            ))}
          </div>

          <ul className="timeline" ref={listRef} aria-label="Attack replay timeline">
            {visible.map((s, i) => (
              <li
                key={`${s.ts}-${i}`}
                className={`tstep ${s.type}${i === idx ? " latest" : ""}`}
              >
                <span className="tstep-n">{i + 1}</span>
                <div>
                  <header>
                    <span className="tstep-stage">
                      {s.type === "transfer" ? "Transfer" : STAGES[s.stage - 1]}
                    </span>
                    <span className="tstep-title">
                      {s.title}
                      {s.llm ? <em>LLM</em> : null}
                    </span>
                  </header>
                  {s.type === "artifact" ? (
                    <p>{s.body}</p>
                  ) : (
                    <>
                      <p className="loss">{s.body}</p>
                      <div className="tstep-verdicts">
                        <span className={`tv ${s.sentinel_caught ? "catch" : "miss"}`}>
                          Sentinel {(s.sentinel_score ?? 0).toFixed(3)} —{" "}
                          {s.sentinel_caught ? "CAUGHT" : "missed"}
                        </span>
                        <span className={`tv ${s.rules_caught ? "catch" : "miss"}`}>
                          Rules — {s.rules_caught ? "CAUGHT" : "missed"}
                        </span>
                      </div>
                    </>
                  )}
                </div>
              </li>
            ))}
            {playing ? (
              <li className="tstep pulse" aria-hidden>
                <span className="tstep-n">…</span>
                <p>Advancing…</p>
              </li>
            ) : null}
          </ul>

          {done && transfers.length > 0 ? (
            <div className="theater-summary">
              <strong>Replay complete.</strong> Sentinel {sentCaught}/{transfers.length} · Rules{" "}
              {rulesCaught}/{transfers.length}.
              {sentWin
                ? " Trained model outperforms the straw checklist on this vector."
                : rulesWin
                  ? " Rules caught more here — model may need another loop."
                  : " Even split on this replay."}
              <span className="fine">Straw rules baseline — not Mastercard production.</span>
            </div>
          ) : null}
        </div>
      )}
    </>
  );
}
