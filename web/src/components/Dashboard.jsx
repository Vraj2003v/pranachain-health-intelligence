import { AREAS } from "../areas.js";

// Dates arrive as text ("09 Aug 2026 – 07 Nov 2026"); turn them into times for the timeline.
const parse = (s) => {
  if (!s) return null;
  const [a, b] = String(s).split(/\s[–-]\s/);
  const x = Date.parse(a + " UTC"), y = Date.parse((b ?? a) + " UTC");
  return Number.isNaN(x) || Number.isNaN(y) ? null : [x, y];
};
const MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
export const short = (t) => { const d = new Date(t); return `${d.getUTCDate()} ${MON[d.getUTCMonth()]} ${d.getUTCFullYear()}`; };
const span = (w) => (w ? (w[0] === w[1] ? short(w[0]) : `${short(w[0])} to ${short(w[1])}`) : "");
const areaOf = (ins) => AREAS.find((a) => a.scenario === ins.scenario) || AREAS[0];
const rank = (l = "") => (l.startsWith("Worth discussing") ? 3 : l.startsWith("Worth watching") ? 2 : 1);

export function when(ins) {
  const e = ins.evidence?.[0];
  return e ? { first: parse(e.first_window), last: parse(e.last_window) } : { first: null, last: null };
}

// Every measure in a finding that has a date it crossed the change threshold, oldest first.
export const onsetsOf = (ins) => (ins.onsets || []).map((o) => ({ ...o, t: Date.parse(o.date) })).sort((a, b) => a.t - b.t);
const num = (v, d) => Number(v).toLocaleString(undefined, { maximumFractionDigits: d ?? 1 });
export const moved = (o) => o.kind === "cycle" ? `longest early cycle ${num(o.at_onset, 0)} days` : `${num(o.baseline, o.decimals)} → ${num(o.now, o.decimals)} ${o.unit}`;

function Kpi({ label, value, note, tone }) {
  return (
    <div className={"dkpi " + (tone || "")}>
      <div className="dk-l">{label}</div>
      <div className="dk-v">{value}</div>
      {note && <div className="dk-n">{note}</div>}
    </div>);
}

export default function Dashboard({ detail }) {
  const ins = detail.insights || [];
  const start = Date.parse(detail.patient.start), end = Date.parse(detail.patient.end);
  const days = Math.max(1, Math.round((end - start) / 864e5));
  const areasHit = AREAS.filter((a) => ins.some((i) => i.scenario === a.scenario)).length;
  const limited = ins.filter((i) => i.flag === "Limited").length;
  const pos = (t) => `${Math.min(100, Math.max(0, ((t - start) / (end - start)) * 100))}%`;

  const ticks = [];
  const d = new Date(start); d.setUTCDate(1); d.setUTCMonth(d.getUTCMonth() + 1);
  while (d.getTime() < end) { ticks.push(d.getTime()); d.setUTCMonth(d.getUTCMonth() + 1); }

  // one row for every measure that crossed its threshold, in the order it happened
  const rows = ins.flatMap((i) => onsetsOf(i).map((o) => ({ i, a: areaOf(i), o }))).sort((x, y) => x.o.t - y.o.t);
  const undated = ins.filter((i) => onsetsOf(i).length === 0);
  const first = rows[0];

  return (
    <div className="dash">
      <div className="dkpis">
        <Kpi label="Changes found" value={rows.length + undated.length} note={rows.length ? `${rows.length} measure${rows.length > 1 ? "s" : ""} crossed their threshold, in ${areasHit} of 3 areas` : "nothing beyond the usual range"} tone={rows.length ? "warn" : "ok"} />
        <Kpi label={first ? "First change began" : "Latest reading"} value={short(first ? first.o.t : end)} note={first ? `${first.o.label}. Latest reading ${short(end)}` : `${days} days of readings`} tone={first ? "warn" : ""} />
        <Kpi label="Data quality" value={limited ? `${limited} limited` : "Sufficient"} note={limited ? "some expected data was missing" : "enough data behind every finding"} tone={limited ? "mid" : "ok"} />
      </div>

      <section className="dpanel" aria-label="What changed and when">
        <div className="dp-head">
          <h2>What changed, and when</h2>
          <div className="dp-legend"><span><i className="sw earlier" /> Within the usual level</span><span><i className="sw recent" /> Past the change threshold</span></div>
        </div>
        {rows.length === 0 && undated.length === 0 ? <p className="muted">No changes were found. The readings from {short(start)} to {short(end)} stayed within the patient's own usual range.</p> : (
          <div className="tl" role="table">
            <div className="tl-axis" aria-hidden>
              <span className="tl-lab" />
              <div className="tl-track axis">{ticks.map((t) => <span key={t} className="tick" style={{ left: pos(t) }}>{MON[new Date(t).getUTCMonth()]}</span>)}</div>
              <span />
            </div>
            {rows.map(({ i, a, o }) => (
              <div className="tl-row" key={i.id + o.key} style={{ "--hue": a.hue }} role="row">
                <div className="tl-lab"><b>{o.label}</b><span className="muted small">{a.title} · {i.id}</span></div>
                <div className="tl-track">
                  {ticks.map((t) => <span key={t} className="grid" style={{ left: pos(t) }} />)}
                  <span className="bar over" style={{ left: pos(o.t), width: `calc(100% - ${pos(o.t)})` }} title={`Past the threshold from ${short(o.t)}`} />
                  <span className="pin" style={{ left: pos(o.t) }} title={`Crossed the threshold on ${short(o.t)}`} />
                </div>
                <div className="tl-when small">
                  <b className="tl-date">{short(o.t)}</b>
                  <span className="muted">{moved(o)}</span>
                </div>
              </div>))}
            {undated.map((i) => (
              <div className="tl-row" key={i.id} style={{ "--hue": areaOf(i).hue }} role="row">
                <div className="tl-lab"><b>{i.title}</b><span className="muted small">{areaOf(i).title} · {i.id}</span></div>
                <div className="tl-track" />
                <div className="tl-when small"><b>Date not clear</b><span className="muted">{when(i).last ? `latest readings ${span(when(i).last)}` : ""}</span></div>
              </div>))}
          </div>)}
        {rows.length > 0 && <p className="muted small dp-foot">The date is the day a two-week average first moved past the patient's change threshold and stayed there. It marks when the change began to show, not a diagnosis.</p>}
      </section>
    </div>);
}
