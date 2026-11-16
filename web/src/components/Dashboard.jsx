import { AREAS } from "../areas.js";

// Dates arrive as text ("09 Aug 2026 – 07 Nov 2026"); turn them into times for the timeline.
const parse = (s) => {
  if (!s) return null;
  const [a, b] = String(s).split(/\s[–-]\s/);
  const x = Date.parse(a), y = Date.parse(b ?? a);
  return Number.isNaN(x) || Number.isNaN(y) ? null : [x, y];
};
const MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
export const short = (t) => { const d = new Date(t); return `${d.getDate()} ${MON[d.getMonth()]} ${d.getFullYear()}`; };
const span = (w) => (w ? (w[0] === w[1] ? short(w[0]) : `${short(w[0])} to ${short(w[1])}`) : "");
const areaOf = (ins) => AREAS.find((a) => a.scenario === ins.scenario) || AREAS[0];
const rank = (l = "") => (l.startsWith("Worth discussing") ? 3 : l.startsWith("Worth watching") ? 2 : 1);

export function when(ins) {
  const e = ins.evidence?.[0];
  return e ? { first: parse(e.first_window), last: parse(e.last_window) } : { first: null, last: null };
}

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
  const levels = Object.values(detail.attention || {}).map((a) => a.level);
  const top = levels.sort((a, b) => rank(b) - rank(a))[0] || "No clear change";
  const limited = ins.filter((i) => i.flag === "Limited").length;
  const pos = (t) => `${Math.min(100, Math.max(0, ((t - start) / (end - start)) * 100))}%`;
  const wid = (w) => `${Math.max(1.2, ((w[1] - w[0]) / (end - start)) * 100)}%`;

  // month ticks along the top of the timeline
  const ticks = [];
  const d = new Date(start); d.setDate(1); d.setMonth(d.getMonth() + 1);
  while (d.getTime() < end) { ticks.push(d.getTime()); d.setMonth(d.getMonth() + 1); }

  const rows = ins.map((i) => ({ i, a: areaOf(i), ...when(i) })).filter((r) => r.last || r.first)
    .sort((x, y) => (y.last?.[1] ?? 0) - (x.last?.[1] ?? 0));

  return (
    <div className="dash">
      <div className="dkpis">
        <Kpi label="Changes found" value={ins.length} note={ins.length ? `across ${areasHit} of 3 areas` : "nothing beyond the usual range"} tone={ins.length ? "warn" : "ok"} />
        <Kpi label="Attention level" value={top.replace(" with a healthcare provider", "")} note="a rule on the findings, not a diagnosis" tone={rank(top) === 3 ? "warn" : rank(top) === 2 ? "mid" : "ok"} />
        <Kpi label="Latest reading" value={short(end)} note={`${days} days of readings`} />
        <Kpi label="Data quality" value={limited ? `${limited} limited` : "Sufficient"} note={limited ? "some expected data was missing" : "enough data behind every finding"} tone={limited ? "mid" : "ok"} />
      </div>

      <section className="dpanel" aria-label="What changed and when">
        <div className="dp-head">
          <h2>What changed, and when</h2>
          <div className="dp-legend"><span><i className="sw earlier" /> Earlier period</span><span><i className="sw recent" /> Recent period (where the change shows)</span></div>
        </div>
        {rows.length === 0 ? <p className="muted">No changes were found. The readings from {short(start)} to {short(end)} stayed within the patient's own usual range.</p> : (
          <div className="tl" role="table">
            <div className="tl-axis" aria-hidden>
              <span className="tl-lab" />
              <div className="tl-track axis">{ticks.map((t) => <span key={t} className="tick" style={{ left: pos(t) }}>{MON[new Date(t).getMonth()]}</span>)}</div>
            </div>
            {rows.map(({ i, a, first, last }) => (
              <div className="tl-row" key={i.id} style={{ "--hue": a.hue }} role="row">
                <div className="tl-lab"><b>{i.title}</b><span className="muted small">{a.title} · {i.id}</span></div>
                <div className="tl-track">
                  {ticks.map((t) => <span key={t} className="grid" style={{ left: pos(t) }} />)}
                  {first && <span className="bar earlier" style={{ left: pos(first[0]), width: wid(first) }} title={`Earlier period: ${span(first)}`} />}
                  {last && <span className="bar recent" style={{ left: pos(last[0]), width: wid(last) }} title={`Recent period: ${span(last)}`} />}
                </div>
                <div className="tl-when small">
                  {last && <span><b>Changed by</b> {short(last[1])}</span>}
                  {first && last && <span className="muted">vs {span(first)}</span>}
                </div>
              </div>))}
          </div>)}
      </section>
    </div>);
}
