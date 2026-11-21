import { useEffect, useState } from "react";
import { api, fmt } from "../api";

// The values ONE document added to the person's record. No score: the analysis runs on the combined record.
function Contents({ c }) {
  const labs = c.rows.filter((r) => r.kind === "lab");
  const readings = c.rows.filter((r) => r.kind === "readings");
  const meds = c.rows.filter((r) => r.kind === "medication");
  const hist = c.rows.filter((r) => r.kind === "history");
  const cyc = c.rows.filter((r) => r.kind === "cycle");
  const note = c.rows.find((r) => r.kind === "note");
  if (c.rows.length === 0) return <p className="note">No values could be read from this document.</p>;
  return (
    <div className="riskview">
      <p className="muted small">These values were read from this document and added to {c.document.patient_id}'s record. Nothing already stored was replaced. The analysis looks at the whole record together, not at this document alone.</p>
      {c.document.ocr ? <p className="note">This document was read from a scan or photo with OCR. Please check the values against the original.</p> : null}
      {meds.length > 0 && <div className="tablewrap"><table>
        <thead><tr><th>Medication</th><th>Dose</th><th>For</th><th>Started</th><th>Status</th></tr></thead>
        <tbody>{meds.map((r) => <tr key={r.name + r.date}><td><b>{r.name}</b></td><td>{r.dose || "—"}</td><td>{r.detail || "—"}</td><td>{r.date}</td><td>{r.end ? `${r.status}, to ${r.end}` : r.status}</td></tr>)}</tbody>
      </table></div>}
      {hist.length > 0 && <div className="tablewrap"><table>
        <thead><tr><th>Diagnosis or finding</th><th>Date</th><th>Status</th></tr></thead>
        <tbody>{hist.map((r) => <tr key={r.name + r.date}><td><b>{r.name}</b></td><td>{r.date}</td><td>{r.status}</td></tr>)}</tbody>
      </table></div>}
      {cyc.length > 0 && <div className="tablewrap"><table>
        <thead><tr><th>Cycle start</th><th>Cycle length</th></tr></thead>
        <tbody>{cyc.map((r) => <tr key={r.date}><td>{r.date}</td><td>{r.value} days</td></tr>)}</tbody>
      </table></div>}
      {note && <div><b>Clinical note</b><p className="small" style={{ whiteSpace: "pre-wrap" }}>{note.detail}</p></div>}
      {labs.length > 0 && <div className="tablewrap"><table>
        <thead><tr><th>Test</th><th>Result</th><th>Date</th><th>Usual range on the report</th></tr></thead>
        <tbody>{labs.map((r) => <tr key={r.name}><td><b>{r.name}</b></td><td>{fmt(r.value, Math.abs(r.value) < 10 ? 2 : 1)} {r.unit}</td><td>{r.when}</td><td>{r.range ? `${r.range} ${r.unit}` : "—"}</td></tr>)}</tbody>
      </table></div>}
      {readings.length > 0 && <div className="tablewrap"><table>
        <thead><tr><th>Measure</th><th>Days added</th><th>Period</th><th>Average</th><th>Lowest to highest</th></tr></thead>
        <tbody>{readings.map((r) => <tr key={r.name}><td><b>{r.name}</b></td><td>{r.days}</td><td>{r.from} to {r.to}</td><td>{fmt(r.mean, 1)} {r.unit}</td><td>{fmt(r.low, 1)} to {fmt(r.high, 1)} {r.unit}</td></tr>)}</tbody>
      </table></div>}
    </div>);
}

// The combined record for one person. Shown only for people built from uploaded documents.
export function PatientRecord({ id }) {
  const [r, setR] = useState(null);
  useEffect(() => { setR(null); api.patientRecord(id).then(setR).catch(() => setR(null)); }, [id]);
  if (!r) return null;
  return (
    <section className="dpanel recordpanel" aria-label="Record built from uploaded documents">
      <h3 className="h">Record built from the uploaded documents</h3>
      <p className="muted small">{[r.lab_reports > 0 && `${r.lab_reports} lab report${r.lab_reports === 1 ? "" : "s"}`, r.reading_files > 0 && `${r.reading_files} readings file${r.reading_files === 1 ? "" : "s"}`, r.documents > 0 && `${r.documents} other document${r.documents === 1 ? "" : "s"}`].filter(Boolean).join(", ")} combined into one record. The findings above are worked out from this whole record, comparing recent weeks with the person's own earlier values.</p>
      <div className="recgrid">
        {r.tests.map((t) => <div key={t.name}><b>{t.name}</b><div className="muted small">{t.results} result{t.results === 1 ? "" : "s"}, {t.first === t.last ? t.first : `${t.first} to ${t.last}`}</div></div>)}
        {r.measures.map((m) => <div key={m.name}><b>{m.name}</b><div className="muted small">{m.days} days, {m.first} to {m.last}</div></div>)}
        {r.medications.length > 0 && <div><b>Medications</b><div className="muted small">{r.medications.map((m) => m.name).join(", ")}</div></div>}
        {r.history.length > 0 && <div><b>Diagnoses and findings</b><div className="muted small">{r.history.map((h) => h.name).join(", ")}</div></div>}
        {r.cycles.count > 0 && <div><b>Cycle log</b><div className="muted small">{r.cycles.count} cycles, {r.cycles.first} to {r.cycles.last}</div></div>}
        {r.notes > 0 && <div><b>Clinical notes</b><div className="muted small">{r.notes} note{r.notes === 1 ? "" : "s"}</div></div>}
      </div>
      {r.missing.length > 0 && <p className="muted small"><b>Not added yet:</b> {r.missing.join(" ")}</p>}
    </section>);
}

// The list of individual uploaded documents; each shows what it added to the record.
export function Reports({ refresh }) {
  const [list, setList] = useState(null);
  const [open, setOpen] = useState(null);
  const [c, setC] = useState(null);
  const [err, setErr] = useState("");
  useEffect(() => { api.reports().then((x) => setList(x.reports)).catch(() => setList([])); }, [refresh]);
  const show = (rep) => {
    const k = rep.kind + rep.id;
    if (open === k) { setOpen(null); return; }
    setOpen(k); setC(null); setErr("");
    api.reportContents(rep.kind, rep.id).then(setC).catch((e) => setErr(e.message));
  };
  if (!list || list.length === 0) return null;
  return (
    <section className="reports">
      <h3 className="h">Uploaded documents</h3>
      <p className="muted small">Each document is read when it is uploaded and its values are added to the person's record. Open one to see what it added.</p>
      <div className="tablewrap"><table>
        <thead><tr><th>Report</th><th>Patient</th><th>Type</th><th>Date</th><th></th></tr></thead>
        <tbody>{list.slice(0, 300).map((rep) => {
          const k = rep.kind + rep.id;
          return [
            <tr key={k}><td><b>{rep.filename}</b></td><td>{rep.patient_id}</td><td>{rep.kind === "lab" ? "Lab results" : rep.kind === "readings" ? "Daily readings" : ({ medications: "Medications", history: "Diagnoses and findings", cycles: "Cycle log", clinical: "Clinical document", fhir: "FHIR record" })[rep.what] || "Record"}</td><td>{rep.collected}</td>
              <td className="actionscell"><button className="btn ghost small" aria-expanded={open === k} onClick={() => show(rep)}>{open === k ? "Hide" : "What it added"}</button></td></tr>,
            open === k && <tr key={k + "r"}><td colSpan={5}>{err ? <p className="note">{err}</p> : c ? <Contents c={c} /> : <p className="muted small">Reading the report…</p>}</td></tr>,
          ];
        })}</tbody>
      </table></div>
    </section>);
}
