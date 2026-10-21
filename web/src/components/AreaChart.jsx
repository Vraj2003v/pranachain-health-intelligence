import { useMemo, useState } from "react";
import { Area, Bar, BarChart, Brush, CartesianGrid, ComposedChart, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { fmt } from "../api";
import { mark } from "../progress.js";

const T = (d) => Date.parse(d + "T00:00:00");
const tick = (t) => new Date(t).toLocaleDateString(undefined, { month: "short", year: "2-digit" });
const RANGES = [["3 months", 91], ["6 months", 182], ["Whole year", 9999]];

function Tip({ active, payload, label, unit, dec }) {
  if (!active || !payload?.length) return null;
  const get = (k) => payload.find((p) => p.dataKey === k)?.value;
  const band = payload.find((p) => p.dataKey === "band")?.value;
  const rows = [["Daily reading", get("v")], ["Weekly average", get("w")], ["Projection", get("p")]].filter(([, v]) => v != null);
  return (
    <div className="tip"><b>{new Date(label).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" })}</b>
      {rows.map(([n, v]) => <div key={n}>{n}: {fmt(v, dec)} {unit}</div>)}
      {band && <div>95% range: {fmt(band[0], dec)} to {fmt(band[1], dec)} {unit}</div>}
    </div>);
}

export default function AreaChart({ d, area }) {
  const keys = area.measures.filter((k) => d.series[k] && d.series[k].rows.some((r) => r.w != null));
  const wanted = d.insights.find((i) => i.scenario === area.scenario && i.forecastKey)?.forecastKey;
  const [key, setKey] = useState(keys.includes(wanted) ? wanted : keys[0]);
  const [range, setRange] = useState(9999);
  const [proj, setProj] = useState(true);
  const [dots, setDots] = useState(true);

  const s = d.series[key];
  const rows = useMemo(() => {
    if (!s) return [];
    const all = s.rows.map((r) => ({ ...r, t: T(r.d) }));
    const lastReal = Math.max(...all.filter((r) => r.v != null || r.w != null).map((r) => r.t));
    const from = lastReal - range * 86400000;
    return all.filter((r) => r.t >= from && (proj || r.p == null));
  }, [s, range, proj]);

  if (area.measures.length === 0) {
    const cyc = d.cycles.map((c) => ({ ...c, t: T(c.d) }));
    return (
      <div className="achart">
        <h4>Length of each cycle (days)</h4>
        {cyc.length === 0 ? <p className="muted small">No cycle records in this file.</p> : (
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={cyc} margin={{ top: 12, right: 12, bottom: 4, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.25} />
              <XAxis dataKey="t" type="number" scale="time" domain={["dataMin", "dataMax"]} tickFormatter={tick} />
              <YAxis domain={[0, "dataMax + 7"]} width={36} />
              <Tooltip labelFormatter={(t) => new Date(t).toLocaleDateString()} formatter={(v) => [`${v} days`, "Cycle"]} />
              <ReferenceLine y={21} stroke="#7a4fa3" strokeDasharray="4 4" label={{ value: "21", position: "left", fontSize: 10 }} />
              <ReferenceLine y={35} stroke="#7a4fa3" strokeDasharray="4 4" label={{ value: "35", position: "left", fontSize: 10 }} />
              <Bar dataKey="v" fill="#7a4fa3" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>)}
        <p className="muted small">Dashed lines mark the usual 21 to 35 day range.</p>
      </div>);
  }
  if (!s) return <p className="muted small">No readings for this area in this file.</p>;
  const dom = (() => {
    const v = rows.flatMap((r) => [r.v, r.w, r.p, ...(r.band || [])]).filter((x) => x != null);
    const lo = Math.min(...v), hi = Math.max(...v), pad = (hi - lo) * 0.08 || 1;
    return [lo - pad, hi + pad];
  })();

  return (
    <div className="achart">
      <div className="controls">
        <div className="pills" role="tablist" aria-label="Measure">
          {keys.map((k) => <button key={k} role="tab" aria-selected={k === key} className={"pill" + (k === key ? " on" : "")} onClick={() => { setKey(k); mark("chart"); }}>{d.series[k].label}</button>)}
        </div>
        <div className="pills" role="group" aria-label="Time range">
          {RANGES.map(([l, n]) => <button key={l} aria-pressed={range === n} className={"pill" + (range === n ? " on" : "")} onClick={() => { setRange(n); mark("chart"); }}>{l}</button>)}
        </div>
        <label className="toggle"><input type="checkbox" checked={proj} onChange={(e) => { setProj(e.target.checked); mark("chart"); }} /> Projection</label>
        <label className="toggle"><input type="checkbox" checked={dots} onChange={(e) => { setDots(e.target.checked); mark("chart"); }} /> Daily readings</label>
      </div>
      <h4>{s.label} ({s.unit})</h4>
      <ResponsiveContainer width="100%" height={340}>
        <ComposedChart data={rows} margin={{ top: 14, right: 16, bottom: 4, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" opacity={0.25} />
          <XAxis dataKey="t" type="number" scale="time" domain={["dataMin", "dataMax"]} tickFormatter={tick} minTickGap={40} />
          <YAxis domain={dom} tickFormatter={(v) => fmt(v, s.decimals)} width={54} />
          <Tooltip content={<Tip unit={s.unit} dec={s.decimals} />} />
          {s.windows && <ReferenceLine y={s.windows.meanFirst} stroke="#14919b" strokeDasharray="5 4"
            label={{ value: `Your usual: ${fmt(s.windows.meanFirst, s.decimals)}`, position: "insideTopLeft", fontSize: 11, fill: "#14919b" }} />}
          {proj && <Area dataKey="band" name="95% range" stroke="none" fill="#e0a21f" fillOpacity={0.18} connectNulls isAnimationActive={false} />}
          {dots && <Line dataKey="v" stroke="none" dot={{ r: 1.8, fill: "#9db8bb", strokeWidth: 0 }} activeDot={false} isAnimationActive={false} />}
          <Line dataKey="w" stroke="#14919b" strokeWidth={3} dot={false} connectNulls isAnimationActive={false} />
          {proj && <Line dataKey="p" stroke="#e0a21f" strokeWidth={3} strokeDasharray="7 5" dot={false} connectNulls isAnimationActive={false} />}
          <Brush onChange={() => mark("chart")} dataKey="t" height={26} stroke="#14919b" tickFormatter={tick} travellerWidth={10} />
        </ComposedChart>
      </ResponsiveContainer>
      <details className="howto"><summary>How to read this chart</summary>
        <ul>
          <li><b>Thick teal line:</b> your weekly average.</li>
          <li><b>Small dots:</b> each day's reading.</li>
          <li><b>Dashed teal line:</b> your own usual level from your first 90 days.</li>
          <li><b>Amber dashed line and shading:</b> where the trend could go over the next 8 weeks if nothing changes. It is not a prediction.</li>
          <li><b>Handles under the chart:</b> drag to zoom into any stretch of time.</li>
        </ul>
      </details>
      <p className="muted small">Drag the handles under the chart to zoom. The dashed teal line is your own usual level; the amber dashed line is a straight-line projection, not a prediction.</p>
    </div>);
}
