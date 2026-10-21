import { useState } from "react";
import { Line, LineChart, ReferenceLine, ResponsiveContainer, Bar, BarChart } from "recharts";
import { AREAS } from "../areas.js";
import AreaChart from "./AreaChart.jsx";
import Ask from "./Ask.jsx";

const T = (d) => Date.parse(d + "T00:00:00");
const seen = () => { try { return localStorage.getItem("pranapulse.coach") === "1"; } catch { return false; } };
const markSeen = () => { try { localStorage.setItem("pranapulse.coach", "1"); } catch { /* storage may be blocked */ } };

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
  const [coach, setCoach] = useState(!seen());
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
          <h1>{user.role === "patient" ? `Hello, ${first}` : `Patient ${detail.patient.id}`}</h1>
          <p className="lede">
            {found === 0 ? "Nothing in the latest readings moved beyond the usual range."
              : `${found} of 3 health areas show changes that may be worth a closer look.`}
          </p>
        </div>
        {docs.length > 1 && (
          <label className="who">Viewing
            <select value={selected || ""} onChange={(e) => { setOpen(null); onPick(e.target.value); }}>
              {docs.map((p) => <option key={p.key} value={p.key}>{p.id}</option>)}
            </select></label>)}
      </div>
      <p className="muted small">Patient {detail.patient.id}, {detail.patient.age ?? "age unknown"}, {detail.patient.sex ?? "sex unknown"}. Readings from {detail.patient.start} to {detail.patient.end}.</p>

      {coach && (
        <div className="coach" role="note">
          <div><b>Start here.</b> Tap a health area below to see what changed and why. Use the question box inside it if something is unclear.</div>
          <button className="btn ghost small" onClick={() => { markSeen(); setCoach(false); }}>Got it</button>
        </div>)}

      <div className="areas-grid">
        {AREAS.map((a) => {
          const items = by(a), hit = items.length > 0, on = open === a.scenario;
          return (
            <button key={a.scenario} onMouseMove={glow} className={"acard" + (hit ? " hit" : "") + (on ? " on" : "")} style={{ "--hue": a.hue }}
              aria-expanded={on} onClick={() => setOpen(on ? null : a.scenario)}>
              <span className="ahead"><span className="aicon" aria-hidden>{a.icon}</span><b>{a.title}</b></span>
              <span className={"chip " + (hit ? "warn" : "ok")}>{hit ? `${items.length} change${items.length > 1 ? "s" : ""} found` : "No clear change"}</span>
              <span className="asum">{hit ? items[0].summary : a.calm}</span>
              <Spark d={detail} area={a} />
              <span className="acta">{on ? "Hide details" : hit ? "See what changed" : "See your readings"}</span>
            </button>);
        })}
      </div>

      {area && (
        <div className="adetail" style={{ "--hue": area.hue }} key={area.scenario}>
          <h2>{area.icon} {area.title}</h2>
          {by(area).length > 0 ? (
            <>
              <p className="impact"><b>Why it may matter.</b> {area.why}</p>
              {by(area).map((ins, n) => (
                <div className="finding" key={n}>
                  <h3>{ins.title}</h3>
                  {ins.tiles.length > 0 && (
                    <div className="tiles">{ins.tiles.map((t) => (
                      <div className="tile" key={t.label}><div className="l">{t.label}</div>
                        <div className="v">{Number(t.value).toLocaleString(undefined, { maximumFractionDigits: t.decimals })} <span className="u">{t.unit}</span></div>
                        <div className="d">{t.diff > 0 ? "up" : "down"} {Math.abs(t.diff).toLocaleString(undefined, { maximumFractionDigits: t.decimals })} compared with your first 90 days</div></div>))}
                    </div>)}
                  <ul>{ins.bullets.map((b) => <li key={b}>{b}</li>)}</ul>
                  {ins.context.length > 0 && <p className="ctx"><b>Connects to your history:</b> {ins.context.slice(0, 3).map((c) => c.split(" — ")[0]).join(" · ")}</p>}
                  <p className="muted small">Data: {ins.flag === "Limited" ? "limited, some readings were missing" : "sufficient"}.</p>
                </div>))}
            </>) : <p className="muted">{area.calm} Here are your readings, in case you want to look closer.</p>}
          <AreaChart d={detail} area={area} />
          <Ask pkey={selected} area={area.scenario} title={`Ask about ${area.title.toLowerCase()}`} />
          <div className="row">
            {canFull && <button className="btn ghost small" onClick={onFull}>See the full evidence</button>}
            <button className="btn ghost small" onClick={onTrends}>Open all trends</button>
          </div>
        </div>)}
    </section>
  );
}
