import type { Atlas, Genome } from "../types";

type Props = {
  genomes: Genome[];
  query: string;
  onQuery: (q: string) => void;
  selected: Genome | null;
  onSelect: (g: Genome) => void;
  atlas?: Atlas | null;
};

export default function GenomePane({
  genomes, query, onQuery, selected, onSelect, atlas,
}: Props) {
  const q = query.toLowerCase();
  const list = genomes.filter((g) => !q || JSON.stringify(g).toLowerCase().includes(q));
  const holes = atlas?.holes?.slice(0, 3) || [];

  return (
    <>
      <header className="pane-head">
        <span className="pane-step">1</span>
        <div>
          <h2 id="pane-identify-title">Identify</h2>
          <p>
            {atlas
              ? `${atlas.n_families ?? "—"} families · ${atlas.n_tier_a ?? "—"} tier-A · coverage ${(atlas.coverage ?? 0).toFixed(2)}`
              : "Novel fraud vectors — pick one to inspect"}
          </p>
        </div>
      </header>
      {atlas?.disclaimer ? <p className="atlas-note">{atlas.disclaimer}</p> : null}
      {holes.length ? (
        <ul className="holes">
          {holes.map((h) => (
            <li key={`${h.rail}-${h.surface}-${h.capability}`}>
              Hole · {h.rail} / {h.surface} — {h.note}
            </li>
          ))}
        </ul>
      ) : null}
      <input
        className="search"
        value={query}
        onChange={(e) => onQuery(e.target.value)}
        placeholder="Search ID, rail, surface…"
        aria-label="Search fraud vectors"
        autoComplete="off"
      />
      <ul className="glist" role="listbox" aria-label="Fraud vectors">
        {list.length === 0 ? (
          <li className="empty">No match.</li>
        ) : (
          list.map((g) => (
            <li key={g.id} role="none">
              <button
                type="button"
                role="option"
                aria-selected={selected?.id === g.id}
                className={selected?.id === g.id ? "sel" : ""}
                onClick={() => onSelect(g)}
              >
                <span className="gid">{g.id}</span>
                <span className="tier">{g.tier || "B"}</span>
                <span className="gname">{g.name}</span>
              </button>
            </li>
          ))
        )}
      </ul>
      <div className="gdetail">
        {selected ? (
          <>
            <strong>{selected.name}</strong>
            <p className="meta-line">
              Tier {selected.tier || "?"} · {(selected.rails || []).join(", ")} ·{" "}
              {(selected.surfaces || []).join(", ")}
            </p>
            <p>{selected.summary}</p>
          </>
        ) : (
          <p className="empty">Select a vector from the list.</p>
        )}
      </div>
    </>
  );
}
