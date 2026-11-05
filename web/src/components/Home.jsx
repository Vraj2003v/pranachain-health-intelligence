import { useEffect, useState } from "react";
import { STEPS, getSteps, mark } from "../progress.js";
import { Line, LineChart, ReferenceLine, ResponsiveContainer, Bar, BarChart } from "recharts";
import { AREAS } from "../areas.js";
import AreaChart, { defaultKey } from "./AreaChart.jsx";
import MeasureSummary from "./MeasureSummary.jsx";
import Overview from "./Overview.jsx";
import Ask from "./Ask.jsx";

const T = (d) => Date.parse(d + "T00:00:00");
const attClass = (l) => (l.startsWith("Worth discussing") ? "out" : l.startsWith("Worth watching") ? "in" : "none");
const hello = () => { const h = new Date().getHours(); return h < 5 ? "Hello" : h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening"; };
const dismissed = () => { try { return localStorage.getItem("pranapulse.coach") === "1"; } catch { return false; } };
const dismiss = () => { try { localStorage.setItem("pranapulse.coach", "1"); } catch { /* storage may be blocked */ } };

function Spark({ d, area }) {
  if (area.measures.length === 0) {
    const c = d.cycles.slice(-12);
    return c.length ? <ResponsiveContainer width="100%" height={54}><BarChart data={c}><Bar dataKey="v" fill={area.hue} radius={2} isAnimationActive={false} /></BarChart></ResponsiveContainer> : null;
  }
  const wanted = d.insights.find((i) => i.scenario === area.scenario && i.forecastKey)?.forecastKey;
  const key = wanted || area.measures.find((k) => d.series[k]?.rows.some((r) => r.w != null));
  const s = key && d.series[key];
  if (!s) return null;
  const data = s.rows.filter((r) => r.w != null).map((r) => ({ t: T(r.d), w: r.w }));
  return (
    <div className="spark" aria-label={`${s.label} over the year`}>
      <ResponsiveContainer width="100%" height={54}>
        <LineChart data={data}><ReferenceLine y={s.windows?.meanFirst} stroke="#8aa" strokeDasharray="3 3" />
          <Line dataKey="w" stroke={area.hue} strokeWidth={2.5} dot={false} isAnimationActive={false} /></LineChart>
      </ResponsiveContainer>
      <span className="muted small">{s.label}, weekly average</span>
    </div>);
}

export default function Home({ user, canFull = true, docs, selected, detail, onPick, onFull, onTrends }) {
  const [open, setOpen] = useState(null);
  const [sel, setSel] = useState(null);
  const [coach, setCoach] = useState(!dismissed());
  const [done, setDone] = useState(getSteps());
  useEffect(() => { const f = () => setDone(getSteps()); window.addEventListener("pp-steps", f); return () => window.removeEventListener("pp-steps", f); }, []);
  const first = user.name.split(" ")[0];
  const glow = (e) => { const r = e.currentTarget.getBoundingClientRect(); e.currentTarget.style.setProperty("--mx", `${e.clientX - r.left}px`); e.currentTarget.style.setProperty("--my", `${e.clientY - r.top}px`); };
  if (!detail) return <div className="muted pad">Loading your summary…</div>;

  const by = (a) => detail.insights.filter((i) => i.scenario === a.scenario);
  const found = AREAS.filter((a) => by(a).length).length;
  const area = AREAS.find((a) => a.scenario === open);

  return (
    <section className="home">
      <div className="greet">
        <div>
          <h1>{user.role === "patient" ? `${hello()}, ${first}` : `Patient ${detail.patient.id}`}</h1>
          <p className="lede">
            {found === 0 ? "Nothing in the latest readings moved beyond the usual range."
              : `${found} of 3 health areas show changes that may be worth a closer look.`}
          </p>
        </div>
      </div>
      <p className="muted small">Patient {detail.patient.id}, {detail.patient.age ?? "age unknown"}, {detail.patient.sex ?? "sex unknown"}. Readings from {detail.patient.start} to {detail.patient.end}.</p>

      {coach && (
        <aside className="starter" aria-label="Getting started">
          <div className="starthead"><b>Getting started</b><span className="muted small">{done.length} of {STEPS.length} done</span>
            <button type="button" className="iconbtn" onClick={() => { dismiss(); setCoach(false); }} aria-label="Hide getting started" title="Hide">✕</button></div>
          <div className="meter" aria-hidden><i style={{ width: `${(done.length / STEPS.length) * 100}%` }} /></div>
          <ul>{STEPS.map(([k, label]) => <li key={k} className={done.includes(k) ? "ok" : ""}><span aria-hidden>{done.includes(k) ? "✓" : "○"}</span> {label}</li>)}</ul>
          {done.length === STEPS.length && <p className="small">All done. You can hide this card with ✕.</p>}
        </aside>)}

      <div className="areas-grid">
        {AREAS.map((a) => {
          const items = by(a), hit = items.length > 0, on = open === a.scenario;
          return (
            <button key={a.scenario} onMouseMove={glow} className={"acard" + (hit ? " hit" : "") + (on ? " on" : "")} style={{ "--hue": a.hue }}
              aria-expanded={on} onClick={() => { setOpen(on ? null : a.scenario); mark("area"); }}>
              <span className="ahead"><span className="aicon" aria-hidden>{a.icon}</span><b>{a.title}</b></span>
              <span className="asub">{a.sub}</span>
              <span className={"chip " + (hit ? "warn" : "ok")}>{hit ? `${items.length} change${items.length > 1 ? "s" : ""} found` : "No clear change"}</span>
              {detail.attention?.[a.scenario] && !detail.attention[a.scenario].level.startsWith("No clear") && <span className={"chip tier " + attClass(detail.attention[a.scenario].level)} title={detail.attention[a.scenario].note}>{detail.attention[a.scenario].level}</span>}
              <span className="asum">{hit ? items[0].summary : a.calm}</span>
              <Spark d={detail} area={a} />
              <span className="acta">{on ? "Hide details" : hit ? "See what changed" : "See your readings"}</span>
            </button>);
        })}
      </div>

      {area && (
        <div className="adetail" style={{ "--hue": area.hue }} key={area.scenario}>
          <h2>{area.icon} {area.title}</h2>
          {detail.attention?.[area.scenario] && !detail.attention[area.scenario].level.startsWith("No clear") &&
            <p className="muted small" title={detail.attention[area.scenario].note}><b>Attention level for this area:</b> {detail.attention[area.scenario].level}</p>}
          {by(area).length === 0 && <p className="muted">{area.calm}</p>}
          <Overview ov={detail.overview?.[area.scenario]} />
          <MeasureSummary d={detail} area={area} sel={area.measures.includes(sel) ? sel : defaultKey(detail, area)} />
          <AreaChart d={detail} area={area} onSelect={setSel} />
          <Ask pkey={selected} area={area.scenario} title={`Ask about ${area.title.toLowerCase()}`} />
          <div className="row">
            {canFull && <button className="btn ghost small" onClick={onFull}>See the full evidence</button>}
            <button className="btn ghost small" onClick={onTrends}>Open all trends</button>
          </div>
        </div>)}
    </section>
  );
}
