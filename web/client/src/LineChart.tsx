// Grafico a linee in SVG puro (nessuna libreria): valore del conto e capitale versato.
type P = { x: string; y: number; y2?: number };

export function LineChart({ points }: { points: P[] }) {
  if (points.length < 2)
    return <p className="muted">Il grafico compare dal secondo giorno di valutazione.</p>;
  const W = 640, H = 200, pad = 36;
  const ys = points.flatMap((p) => [p.y, p.y2 ?? p.y]);
  let lo = Math.min(...ys), hi = Math.max(...ys);
  if (hi - lo < 1e-9) { lo -= 1; hi += 1; }
  const m = (hi - lo) * 0.08;
  lo -= m; hi += m;
  const x = (i: number) => pad + (i / (points.length - 1)) * (W - pad * 1.5);
  const y = (v: number) => H - pad / 2 - ((v - lo) / (hi - lo)) * (H - pad);
  const path = (f: (p: P) => number) => points.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(f(p)).toFixed(1)}`).join("");
  const ticks = [lo + m, (lo + hi) / 2, hi - m];
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="chart" role="img" aria-label="Andamento del valore del conto">
      {ticks.map((t) => (
        <g key={t}>
          <line x1={pad} x2={W - pad / 2} y1={y(t)} y2={y(t)} className="grid" />
          <text x={pad - 4} y={y(t) + 4} textAnchor="end" className="axis">
            {Math.round(t).toLocaleString("it-IT")}
          </text>
        </g>
      ))}
      <path d={path((p) => p.y2 ?? p.y)} className="line2" />
      <path d={path((p) => p.y)} className="line" />
      <text x={pad} y={H - 2} className="axis">{new Date(points[0]!.x).toLocaleDateString("it-IT")}</text>
      <text x={W - pad / 2} y={H - 2} textAnchor="end" className="axis">
        {new Date(points.at(-1)!.x).toLocaleDateString("it-IT")}
      </text>
    </svg>
  );
}
