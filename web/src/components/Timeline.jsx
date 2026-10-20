import { useMemo, useState } from "react";
import { Area, Bar, BarChart, CartesianGrid, ComposedChart, Legend, Line, LineChart, ReferenceArea, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { fmt, shortDate } from "../api";

const C = { dots: "#9fb6cc", line: "#1f4e79", proj: "#c55a11", band: "#c55a11" };
const tick = (t) => new Date(t).toLocaleDateString(undefined, { month: "short", year: "2-digit" });
const T = (d) => Date.parse(d + "T00:00:00");

function Tip({ active, payload, label, unit, dec }) {
  if (!active || !payload?.length) return null;
  const get = (k) => payload.find((p) => p.dataKey === k)?.value;
  const band = payload.find((p) => p.dataKey === "band")?.value;
  const rows = [["Daily value", get("v")], ["Weekly average", get("w")], ["Projection", get("p")]].filter(([, v]) => v != null);
  return (
    <div className="tip"><b>{new Date(label).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" })}</b>
      {rows.map(([n, v]) => <div key={n}>{n}: {fmt(v, dec)} {unit}</div>)}
      {band && <div>95% range: {fmt(band[0], dec)}–{fmt(band[1], dec)} {unit}</div>}
    </div>);
}

export default function Timeline({ d, initialKey }) {
  const keys = Object.keys(d.series);
  const first = (keys.includes(initialKey) && initialKey) || d.insights.find((i) => i.forecastKey)?.forecastKey || keys[0];
  const [key, setKey] = useState(first);
  const s = d.series[key];
  const labNames = Object.keys(d.labs);
  const [lab, setLab] = useState(labNames.includes("HbA1c") ? "HbA1c" : labNames[0]);

  const data = useMemo(() => s.rows.map((r) => ({ ...r, t: T(r.d) })), [s]);
  const dom = useMemo(() => {
    const vals = data.flatMap((r) => [r.v, r.w, r.p, ...(r.band || [])]).filter((v) => v != null);
    const lo = Math.min(...vals), hi = Math.max(...vals), pad = (hi - lo) * 0.08 || 1;
    return [lo - pad, hi + pad];
  }, [data]);
  const start = d.patient.start;
  const inWin = d.markers.filter((m) => !m.before);
  const before = d.markers.filter((m) => m.before);
  const L = lab && d.labs[lab];

  return (
    <section>
      <div className="pills">
        {keys.map((k) => <button key={k} className={"pill" + (k === key ? " on" : "")} onClick={() => setKey(k)}>{d.series[k].label}</button>)}
      </div>
      <div className="chartcard">
        <h3>{s.label} ({s.unit})</h3>
        <ResponsiveContainer width="100%" height={430}>
          <ComposedChart data={data} margin={{ top: 28, right: 18, bottom: 6, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" opacity={0.25} />
            <XAxis dataKey="t" type="number" scale="time" domain={["dataMin", "dataMax"]} tickFormatter={tick} minTickGap={40} />
            <YAxis domain={dom} tickFormatter={(v) => fmt(v, s.decimals)} width={56} />
            <Tooltip content={<Tip unit={s.unit} dec={s.decimals} />} />
            <Legend verticalAlign="top" height={30} />
            {s.windows && [["first", "Earlier", s.windows.meanFirst], ["last", "Recent", s.windows.meanLast]].map(([w, name, mean]) => (
              <ReferenceArea key={w} x1={T(s.windows[w][0])} x2={T(s.windows[w][1])} fill="#788" fillOpacity={0.1}
                label={{ value: `${name} 90 days · avg ${fmt(mean, s.decimals)} ${s.unit}`, position: "insideTopLeft", fontSize: 11, fill: "#667" }} />))}
            {inWin.map((m) => (
              <ReferenceLine key={m.date + m.text} x={T(m.date)} stroke="#889" strokeDasharray="2 3"
                label={{ value: m.text, angle: -90, position: "insideTopRight", fontSize: 10, fill: "#667" }} />))}
            <Area dataKey="band" name="95% range" stroke="none" fill={C.band} fillOpacity={0.16} connectNulls isAnimationActive={false} />
            <Line dataKey="v" name="Daily value" stroke="none" dot={{ r: 1.8, fill: C.dots, strokeWidth: 0 }} activeDot={false} isAnimationActive={false} legendType="circle" />
            <Line dataKey="w" name="Weekly average" stroke={C.line} strokeWidth={3} dot={false} connectNulls isAnimationActive={false} />
            <Line dataKey="p" name="Projection" stroke={C.proj} strokeWidth={3} strokeDasharray="7 5" dot={false} connectNulls isAnimationActive={false} />
          </ComposedChart>
        </ResponsiveContainer>
        {before.length > 0 && <p className="muted small">◀ Before this window: {before.map((m) => `${m.text} (${shortDate(m.date)})`).join("; ")}</p>}
        <p className="muted small">
          {s.hasProjection
            ? "The dashed line is a straight-line projection of the last 26 weeks, 8 weeks ahead, with a 95% range. It shows what happens if the recent trend simply continues; it is not a prediction of health outcomes."
            : "Not enough weekly data to draw a projection for this signal."}
        </p>
      </div>

      {L && (
        <div className="chartcard">
          <div className="row between"><h3>Lab result</h3>
            <select value={lab} onChange={(e) => setLab(e.target.value)}>{labNames.map((n) => <option key={n}>{n}</option>)}</select></div>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={L.points.map((p) => ({ ...p, t: T(p.d) }))} margin={{ top: 24, right: 18, bottom: 6, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.25} />
              <XAxis dataKey="t" type="number" scale="time" domain={["dataMin - 2000000000", "dataMax + 2000000000"]} tickFormatter={tick} />
              <YAxis domain={["auto", "auto"]} width={56} unit={` ${L.unit}`.length > 8 ? "" : ""} />
              {L.refLow != null && L.refHigh != null && <ReferenceArea y1={L.refLow} y2={L.refHigh} fill="#2ea043" fillOpacity={0.13} label={{ value: "Reference range", position: "insideTopLeft", fontSize: 11, fill: "#667" }} />}
              <Tooltip formatter={(v) => `${v} ${L.unit}`} labelFormatter={(t) => shortDate(new Date(t).toISOString().slice(0, 10))} />
              <Line dataKey="v" name={lab} stroke={C.line} strokeWidth={2} dot={{ r: 4 }} label={{ position: "top", fontSize: 11 }} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>)}

      {d.cycles.length > 0 && (
        <div className="chartcard">
          <h3>Cycle length (days)</h3>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={d.cycles.map((c) => ({ ...c, n: new Date(c.d + "T00:00:00").toLocaleDateString(undefined, { day: "numeric", month: "short" }) }))} margin={{ top: 16, right: 18, bottom: 6, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.25} />
              <XAxis dataKey="n" /><YAxis domain={[0, "auto"]} width={40} />
              <ReferenceLine y={21} stroke="#2ea043" strokeDasharray="4 4" label={{ value: "21", position: "left", fontSize: 10, fill: "#2ea043" }} />
              <ReferenceLine y={35} stroke="#2ea043" strokeDasharray="4 4" label={{ value: "Usual range 21–35 days", position: "insideTopRight", fontSize: 11, fill: "#2ea043" }} />
              <Tooltip formatter={(v) => `${v} days`} />
              <Bar dataKey="v" name="Cycle length" fill={C.line} radius={[4, 4, 0, 0]} isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
        </div>)}
    </section>
  );
}
