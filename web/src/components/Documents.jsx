import { useRef } from "react";
import { kb, stamp } from "../api";
import { Reports } from "./RecordView.jsx";

export default function Documents({ docs, onUpload, onDemo, onOpen, onRemove, onRemoveAll, busy }) {
  const input = useRef();
  return (
    <section>
      <div className="row between" style={{ marginBottom: 12 }}>
        <div><h3 className="h" style={{ margin: 0 }}>Patient documents</h3>
          <p className="muted small" style={{ margin: 0 }}>Workbooks and reports you uploaded (lab results, vitals, wearable data) are stored in the database, analysed, and kept private to your account. Reports added one at a time are combined into one record per person.</p></div>
        <div className="row">
          <button className="btn small" disabled={!!busy} onClick={() => input.current.click()}>Upload files</button>
          <button className="btn ghost small" disabled={!!busy} onClick={onDemo}>Add demo patients</button>
          <button className="btn ghost small" disabled={!docs.length} onClick={() => confirm("Delete all your uploaded documents?") && onRemoveAll()}>Delete all</button>
        </div>
        <input ref={input} type="file" accept=".xlsx,.pdf,.csv" multiple hidden onChange={(e) => { onUpload(e.target.files); e.target.value = ""; }} />
      </div>
      <div className="tablewrap">
        <table>
          <thead><tr><th>Document</th><th>Patient</th><th>Uploaded</th><th>Size</th><th>Status</th><th>Source</th><th></th></tr></thead>
          <tbody>
            {docs.slice(0, 300).map((d) => (
              <tr key={d.key}>
                <td><b>{d.filename}</b></td><td>{d.id}</td><td>{stamp(d.uploaded)}</td><td>{kb(d.size)}</td>
                <td><span className={"chip " + (d.status === "Flagged" ? "warn" : "quiet")}>{d.status}</span></td>
                <td>{d.demo ? "Fabricated demo" : /\((uploaded|lab) reports\)\.xlsx$/.test(d.filename) ? "Uploaded reports" : "Uploaded"}</td>
                <td className="actionscell">
                  <button className="btn ghost small" onClick={() => onOpen(d.key)}>Open</button>
                  <a className="btn ghost small" href={`/api/documents/${d.key}/file`}>Download</a>
                  <button className="btn ghost small" onClick={() => confirm(`Delete ${d.filename}?`) && onRemove(d.key)}>Delete</button>
                </td>
              </tr>))}
          </tbody>
        </table>
      </div>
      <Reports refresh={docs.length + ":" + (docs[0]?.uploaded || "")} />
      {docs.length > 300 && <p className="muted small">Showing first 300 of {docs.length}.</p>}
    </section>
  );
}
