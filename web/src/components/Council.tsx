import type { AgentLog } from "../types";

export default function Council({ logs }: { logs: AgentLog[] }) {
  const shown = (logs || []).slice(-14).reverse();
  return (
    <>
      <header className="pane-head">
        <span className="pane-step">3</span>
        <div>
          <h2 id="pane-loop-title">Loop</h2>
          <p>Scout invents · Critic mutates</p>
        </div>
      </header>
      <div className="feed">
        {shown.length === 0 ? (
          <p className="empty">Council log fills when you run a generation.</p>
        ) : (
          shown.map((l, i) => (
            <article className={`brief ${l.agent || ""}`} key={i}>
              <header className="who">
                {(l.agent || "agent").toUpperCase()} · gen {l.gen}
              </header>
              <p>{l.message}</p>
            </article>
          ))
        )}
      </div>
    </>
  );
}
