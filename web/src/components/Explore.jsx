import { useMemo, useState } from "react";
import { Brush, CartesianGrid, ComposedChart, Legend, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { fmt } from "../api";

const COLORS = ["#0e6b73", "#c98a12", "#7a4fa3", "#b03a48", "#2f6fa8"];
const T = (d) => Date.parse(d + "T00:00:00");
const tick = (t) => new Date(t).toLocaleDateString(undefined, { month: "short", year: "2-digit" });
const RANGES = [["3 months", 91], ["6 months", 182], ["Whole year", 9999]];

export default function Explore({ d, initial }) {
  const all = Object.keys(d.series);
  const [sel, setSel] = useState((initial?.length ? initial : all.slice(0, 2)).filter((k) => all.includes(k)));
  const [range, setRange] = useState(9999);
  const [mode, setMode] = useState("index");   // index = % change vs own usual, raw = real units (first measure only)
  const toggle = (k) => setSel((s) => (s.includes(k) ? (s.length > 1 ? s.filter((x) => x !== k) : s) : s.length >= 4 ? s : [...s, k]));

  const { rows, stats } = useMemo(() => {
    const by = {};
    const stats = sel.map((k) => {
      const s = d.series[k];
      const base = s.windows?.meanFirst ?? (s.rows.find((r) => r.w != null)?.w ?? 1);
      s.rows.forEach((r) => { if (r.w != null) { (by[r.d] ||= { d: r.d, t: T(r.d) })[k] = mode === "index" ? ((r.w - base) / base) * 100 : r.w; } });
      return { k, label: s.label, unit: s.unit, dec: s.decimals, first: s.windows?.meanFirst, last: s.windows?.meanLast };
    });
    let rows = Object.values(by).sort((a, b) => a.t - b.t);
    if (rows.length) { const from = rows[rows.length - 1].t - range * 86400000; rows = rows.filter((r) => r.t >= from); }
    return { rows, stats };
  }, [d, sel, range, mode]);

  return (
    <section className="explore">
      <h2>Compare measures</h2>
      <p className="muted">Pick up to four measures. Each line shows its weekly average as a percentage change from your own first 90 days, so different units sit on one scale.</p>
      <div className="controls">
        <div className="pills" role="group" aria-label="Measures">
          {all.map((k, n) => <button key={k} aria-pressed={sel.includes(k)} className={"pill" + (sel.includes(k) ? " on" : "")} onClick={() => toggle(k)}>{d.series[k].label}</button>)}
        </div>
        <div className="pills" role="group" aria-label="Time range">
          {RANGES.map(([l, n]) => <button key={l} aria-pressed={range === n} className={"pill" + (range === n ? " on" : "")} onClick={() => setRange(n)}>{l}</button>)}
        </div>
        <div className="pills" role="group" aria-label="Scale">
          <button className={"pill" + (mode === "index" ? " on" : "")} aria-pressed={mode === "index"} onClick={() => setMode("index")}>% change</button>
          <button className={"pill" + (mode === "raw" ? " on" : "")} aria-pressed={mode === "raw"} onClick={() => setMode("raw")} disabled={sel.length > 2} title={sel.length > 2 ? "Real units need two measures or fewer" : ""}>Real units</button>
        </div>
      </div>
      <div className="chartcard">
        <ResponsiveContainer width="100%" height={400}>
          <ComposedChart data={rows} margin={{ top: 14, right: 16, bottom: 4, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" opacity={0.25} />
            <XAxis dataKey="t" type="number" scale="time" domain={["dataMin", "dataMax"]} tickFormatter={tick} minTickGap={40} />
            <YAxis tickFormatter={(v) => (mode === "index" ? `${v.toFixed(0)}%` : fmt(v, 0))} width={50} />
            <Tooltip labelFormatter={(t) => new Date(t).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" })}
              formatter={(v, n) => [mode === "index" ? `${Number(v).toFixed(1)}%` : fmt(v, 1), n]} />
            <Legend verticalAlign="top" height={28} />
            {mode === "index" && <ReferenceLine y={0} stroke="#889" strokeDasharray="4 4" />}
            {sel.map((k, n) => <Line key={k} dataKey={k} name={d.series[k].label} stroke={COLORS[n % COLORS.length]} strokeWidth={2.5} dot={false} connectNulls isAnimationActive={false} />)}
            <Brush dataKey="t" height={26} stroke="#0e6b73" tickFormatter={tick} travellerWidth={10} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <div className="tablewrap"><table><thead><tr><th>Measure</th><th>First 90 days</th><th>Last 90 days</th><th>Change</th></tr></thead>
        <tbody>{stats.map((s) => (
          <tr key={s.k}><td>{s.label}</td><td>{fmt(s.first, s.dec)} {s.unit}</td><td>{fmt(s.last, s.dec)} {s.unit}</td>
            <td>{s.first != null && s.last != null ? `${s.last - s.first > 0 ? "+" : ""}${fmt(s.last - s.first, s.dec)} (${(((s.last - s.first) / s.first) * 100).toFixed(1)}%)` : "—"}</td></tr>))}</tbody></table></div>
      <p className="muted small">Lines moving apart or together can hint at links worth raising with a healthcare provider. They do not show that one measure causes another.</p>
    </section>
  );
}
