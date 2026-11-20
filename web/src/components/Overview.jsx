import { fmt } from "../api";
import { short } from "./Dashboard.jsx";

const POS = {
  above: ["Above", "out", "▲"], below: ["Below", "out", "▼"], within: ["Within", "in", "✓"],
  "no range": ["Own baseline only", "none", "–"], "no data": ["Not enough data", "none", "–"],
};

// Where the latest value sits on a bar, with the usual range shaded.
export function RangeBar({ r }) {
  const v = r.value, lo = r.rng_low, hi = r.rng_high;
  if (v == null || (lo == null && hi == null)) return <span className="muted small">{r.range}</span>;
  const a = lo ?? Math.min(0, v), b = hi ?? Math.max(v, (lo ?? 0) * 1.5), span = (b - a) || 1;
  const min = Math.min(a, v) - span * 0.35, max = Math.max(b, v) + span * 0.35;
  const at = (x) => `${((x - min) / (max - min)) * 100}%`;
  return (
    <div className="rbar" role="img" aria-label={`${fmt(v, r.decimals)} ${r.unit}, usual range ${r.range}`}>
      <div className="rb-track">
        <span className="rb-zone" style={{ left: at(a), width: `${((b - a) / (max - min)) * 100}%` }} />
        <span className={"rb-dot " + r.position} style={{ left: at(v) }} />
      </div>
      <span className="rb-text small">{r.range}</span>
    </div>);
}

// All of one area's own measures together: latest value, usual range, and the date a change began.
export default function Overview({ ov }) {
  if (!ov || ov.rows.filter((r) => r.value != null).length === 0) return null;
  const rows = ov.rows.filter((r) => r.value != null).sort((x, y) => (y.changed - x.changed) || (x.context - y.context));
  return (
    <section className="overview" aria-label="All measures in this area">
      <div className="ov-sum">
        <div className="ov-stat"><b>{ov.rows.filter((r) => !r.context).length}</b><span>measures in this area</span></div>
        <div className={"ov-stat" + (ov.outside ? " warn" : "")}><b>{ov.outside}</b><span>outside the usual range ({ov.ranged} have a range)</span></div>
        <div className={"ov-stat" + (ov.changed ? " bad" : "")}><b>{ov.changed}</b><span>changed past their threshold</span></div>
      </div>
      <div className="ovwrap">
        <table className="ovtable">
          <thead><tr><th>Measure</th><th>Latest</th><th>Against the usual range</th><th>Change</th></tr></thead>
          <tbody>{rows.map((r) => {
            const [label, cls, icon] = POS[r.position] || POS["no data"];
            return (
              <tr key={r.key} className={r.changed ? "chg" : ""}>
                <th scope="row">{r.label}{r.context && <span className="ovctx" title="Listed for this disease at the kickoff. Shown for context; it does not create findings here."> also considered</span>}</th>
                <td className="ov-val">{r.value == null ? "—" : <>{fmt(r.value, r.decimals)} <span className="u">{r.unit}</span></>}</td>
                <td><div className="ov-pos"><span className={"chip tier " + cls}><i aria-hidden>{icon}</i> {label}</span><RangeBar r={r} /></div></td>
                <td>{r.changed
                  ? <div className="ov-chg"><span className="chip warn">Changed</span>{r.onset ? <span className="small"><b>{short(Date.parse(r.onset))}</b><br /><span className="muted">crossed its threshold</span></span> : <span className="muted small">see finding</span>}</div>
                  : <span className="muted small">No change</span>}</td>
              </tr>);
          })}</tbody>
        </table>
      </div>
      <p className="muted small">Changed measures are listed first. Steady values outside the range are counted here but are not findings.</p>
    </section>);
}
