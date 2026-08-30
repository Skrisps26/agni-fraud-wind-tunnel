import type { HistoryRow, Protocol, Shadow } from "../types";

type Props = {
  history: HistoryRow[];
  rates: Record<string, number>;
  protocol?: Protocol;
  shadow?: Shadow;
};

function fmt(n: number | null | undefined, d = 3) {
  if (n == null || Number.isNaN(Number(n))) return "—";
  return Number(n).toFixed(d);
}

function pct(n: number | null | undefined) {
  if (n == null) return "—";
  return `${(Number(n) * 100).toFixed(1)}%`;
}

export default function Sentinel({ history, rates, protocol, shadow }: Props) {
  const last = history[history.length - 1] || {};
  const proto = last.protocol || protocol || {};
  return (
    <>
      <header className="pane-head">
        <span className="pane-step">4</span>
        <div>
          <h2 id="pane-defend-title">Defend</h2>
          <p>
            {proto.headline ||
              "Family-holdout and recall at production base rate — not in-generator ROC"}
          </p>
        </div>
      </header>

      <div className="defend-body">
        <dl className="stats">
          <div>
            <dt>Lab ROC AUC</dt>
            <dd className="num">{fmt(last.roc_auc)}</dd>
          </div>
          <div>
            <dt>Family holdout AUC</dt>
            <dd className="num">{fmt(proto.family_holdout_auc)}</dd>
          </div>
          <div>
            <dt>Recall @ 0.2% base rate</dt>
            <dd className="num">{pct(proto.recall_at_base_rate)}</dd>
          </div>
          <div>
            <dt>Frozen / TtE</dt>
            <dd className="num">
              {fmt(last.frozen_auc)} / {shadow?.tte_generations ?? 0} gen
            </dd>
          </div>
          <div>
            <dt>Straw rules recall</dt>
            <dd className="num">{pct(last.baseline_recall)}</dd>
          </div>
          <div>
            <dt>Bank checklist recall</dt>
            <dd className="num">{pct(last.checklist_recall)}</dd>
          </div>
        </dl>

        <div className="charts">
          <Trace
            title="Retrain vs frozen AUC"
            series={[
              { key: "roc_auc", color: "#1c1712", label: "retrained" },
              { key: "frozen_auc", color: "#6b6258", label: "frozen" },
            ]}
            history={history}
            ymin={0.5}
            ymax={1}
          />
          <Trace
            title="Attacks caught"
            series={[
              { key: "recall", color: "#1f6b42", label: "model" },
              { key: "baseline_recall", color: "#9b1c1c", label: "rules" },
            ]}
            history={history}
            ymin={0}
            ymax={1}
          />
        </div>

        <div className="heat-block">
          <p className="heat-label">Catch rate by vector — red = still evading</p>
          <Heat rates={rates} />
          {shadow?.note ? <p className="heat-label">{shadow.note}</p> : null}
          {proto.ablation_auc ? (
            <p className="heat-label">
              Ablation AUC · tabular {fmt(proto.ablation_auc.tabular)} · graph{" "}
              {fmt(proto.ablation_auc.graph)} · sequence {fmt(proto.ablation_auc.sequence)}
              {proto.occupant_iforest_auc != null
                ? ` · IsolationForest ${fmt(proto.occupant_iforest_auc)}`
                : ""}
            </p>
          ) : null}
        </div>
      </div>
    </>
  );
}

function Trace({
  title,
  series,
  history,
  ymin,
  ymax,
}: {
  title: string;
  series: { key: keyof HistoryRow; color: string; label: string }[];
  history: HistoryRow[];
  ymin: number;
  ymax: number;
}) {
  const w = 280;
  const h = 72;
  const pad = 6;
  const n = Math.max(history.length, 2);
  const path = (key: keyof HistoryRow) => {
    const pts = history
      .map((row, i) => {
        const v = row[key];
        if (typeof v !== "number") return null;
        const x = pad + (i / (n - 1)) * (w - pad * 2);
        const y = pad + (1 - (v - ymin) / (ymax - ymin)) * (h - pad * 2);
        return `${x},${y}`;
      })
      .filter(Boolean);
    return pts.length ? `M ${pts.join(" L ")}` : "";
  };
  return (
    <div className="chart-wrap">
      <p className="chart-title">
        {title}
        {series.map((s) => (
          <span key={String(s.key)} style={{ color: s.color }}>
            {s.label}
          </span>
        ))}
      </p>
      <svg viewBox={`0 0 ${w} ${h}`} role="img" aria-label={title}>
        {series.map((s) => (
          <path key={String(s.key)} d={path(s.key)} fill="none" stroke={s.color} strokeWidth="2" />
        ))}
      </svg>
    </div>
  );
}

function Heat({ rates }: { rates: Record<string, number> }) {
  const ids = Object.keys(rates).sort().slice(0, 36);
  if (!ids.length) return <p className="empty">Heatmap after first run.</p>;
  return (
    <div className="heat" aria-label="Detection rate by vector">
      {ids.map((id) => {
        const r = rates[id];
        const cls = r < 0.5 ? "lo" : r < 0.8 ? "mid" : "hi";
        return (
          <i key={id} className={cls} title={`${id}: ${(r * 100).toFixed(0)}% caught`}>
            {id.replace("GEN-", "").slice(0, 8)}
          </i>
        );
      })}
    </div>
  );
}
