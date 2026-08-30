type Props = { generation: number; running?: boolean; ready?: boolean };

export default function LoopStrip({ generation, running, ready }: Props) {
  const steps = [
    { n: "1", name: "Identify", hint: "catalogue vectors" },
    { n: "2", name: "Generate", hint: "simulate attacks" },
    { n: "3", name: "Loop", hint: "scout & critic" },
    { n: "4", name: "Defend", hint: "detect & measure" },
  ];
  const lit = ready ? steps.length : generation > 0 ? Math.min(generation + 1, steps.length) : 1;

  return (
    <div className={`loop-strip${running ? " running" : ""}`} aria-label="Closed-loop stages">
      <div className="loop-track">
        {steps.map((s, i) => (
          <div className={`loop-step${i < lit ? " active" : ""}`} key={s.n}>
            <span className="loop-n">{s.n}</span>
            <div>
              <div className="loop-name">{s.name}</div>
              <div className="loop-hint">{s.hint}</div>
            </div>
            <div className="loop-flow" aria-hidden="true">
              <i />
            </div>
          </div>
        ))}
      </div>
      <span className="loop-gen num">
        Gen <strong>{generation}</strong>
      </span>
    </div>
  );
}
