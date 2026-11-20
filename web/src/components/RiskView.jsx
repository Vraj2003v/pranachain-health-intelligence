import { useEffect, useState } from "react";
import { api, fmt } from "../api";

const LEVEL = { Low: "in", Moderate: "mid", High: "out" };
const SEV = { mild: "mid", moderate: "mid", marked: "out" };

// The screening levels and risk factors found in one document, or in one person's latest values.
export function RiskView({ r, title }) {
  const person = r.document?.kind === "patient";
  const outside = r.checked.filter((c) => c.position === "above" || c.position === "below").length;
  const within = r.checked.filter((c) => c.position === "within").length;
  return (
    <div className="riskview">
      {title && <h3 className="h">{title}</h3>}
      <div className="risk-areas">
        {r.areas.map((a) => (
          <div key={a.area} className={"risk-area " + (a.level ? LEVEL[a.level] : "none")}>
            <div className="ra-name">{a.short}</div>
            <div className="ra-level">{a.level ?? "Not covered"}</div>
            <div className="muted small">{a.level
              ? `${a.points} point${a.points === 1 ? "" : "s"} · ${a.checked} measure${a.checked === 1 ? "" : "s"} checked`
              : `no measure for this area in ${person ? "the latest results" : "this document"}`}</div>
          </div>))}
      </div>
      {r.factors.length > 0 ? (
        <div className="tablewrap"><table>
          <thead><tr><th>Risk factor</th><th>Value</th><th>Usual range</th><th>Direction</th><th>Past the limit</th><th>Severity</th><th>Area</th></tr></thead>
          <tbody>{r.factors.map((f) => (
            <tr key={f.label}>
              <td><b>{f.factor}</b></td>
              <td>{fmt(f.value, Math.abs(f.value) < 10 ? 2 : 1)} {f.unit}</td>
              <td>{f.range}</td>
              <td>{f.position === "above" ? "▲ Above" : "▼ Below"}</td>
              <td>{f.distance_pct}%</td>
              <td><span className={"chip tier " + SEV[f.severity_label]}>{f.severity_label}</span></td>
              <td>{r.areas.find((a) => a.area === f.area)?.short}</td>
            </tr>))}</tbody>
        </table></div>
      ) : <p className="note">No risk factors were found in {person ? "the latest results" : "this document"}{r.checked.length ? `: all ${within} scored result${within === 1 ? "" : "s"} sit within the usual range.` : ". It has no results that can be scored."}</p>}
      {r.other_outside.length > 0 && (
        <p className="muted small"><b>Also outside their range, not scored:</b> {r.other_outside.map((o) => `${o.label} ${o.position === "above" ? "▲" : "▼"} ${fmt(o.value, 1)} ${o.unit}`).join("; ")}. These do not belong to the three health areas.</p>)}
      <p className="muted small">{r.checked.length} result{r.checked.length === 1 ? "" : "s"} checked: {within} within the usual range, {outside} outside.</p>
      {person && <p className="muted small">This looks at where the latest values sit against their usual ranges. The attention level above is about change over time, so the two can differ.</p>}
      <details className="howto"><summary>How the screening level is worked out</summary><p className="small">{r.method}</p></details>
      <p className="muted small"><b>Screening level, not a diagnosis.</b> It is a written rule on the values in {person ? "the latest results" : "this document"} and should be read by a healthcare provider.</p>
    </div>);
}

// One person, all uploaded documents together. Shown only for people built from uploaded reports.
export function PatientRisk({ id }) {
  const [r, setR] = useState(null);
  useEffect(() => { setR(null); api.patientRisk(id).then(setR).catch(() => setR(null)); }, [id]);
  if (!r) return null;
  return <section className="dpanel riskpanel" aria-label="Screening levels"><RiskView r={r} title="Screening levels from the uploaded reports" /></section>;
}

// The list of individual uploaded reports; each can be opened to see its own risk factors.
export function Reports({ refresh }) {
  const [list, setList] = useState(null);
  const [open, setOpen] = useState(null);
  const [risk, setRisk] = useState(null);
  const [err, setErr] = useState("");
  useEffect(() => { api.reports().then((x) => setList(x.reports)).catch(() => setList([])); }, [refresh]);
  const show = (rep) => {
    const k = rep.kind + rep.id;
    if (open === k) { setOpen(null); return; }
    setOpen(k); setRisk(null); setErr("");
    api.reportRisk(rep.kind, rep.id).then(setRisk).catch((e) => setErr(e.message));
  };
  if (!list || list.length === 0) return null;
  return (
    <section className="reports">
      <h3 className="h">Uploaded reports</h3>
      <p className="muted small">Each report is read on its own. Open one to see which results are outside their usual range and what that means for each health area.</p>
      <div className="tablewrap"><table>
        <thead><tr><th>Report</th><th>Patient</th><th>Type</th><th>Date</th><th></th></tr></thead>
        <tbody>{list.slice(0, 300).map((rep) => {
          const k = rep.kind + rep.id;
          return [
            <tr key={k}><td><b>{rep.filename}</b></td><td>{rep.patient_id}</td><td>{rep.kind === "lab" ? "Lab results" : "Daily readings"}</td><td>{rep.collected}</td>
              <td className="actionscell"><button className="btn ghost small" aria-expanded={open === k} onClick={() => show(rep)}>{open === k ? "Hide risk factors" : "Risk factors"}</button></td></tr>,
            open === k && <tr key={k + "r"}><td colSpan={5}>{err ? <p className="note">{err}</p> : risk ? <RiskView r={risk} /> : <p className="muted small">Reading the report…</p>}</td></tr>,
          ];
        })}</tbody>
      </table></div>
    </section>);
}
