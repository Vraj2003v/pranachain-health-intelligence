import { useEffect, useState } from "react";
import { api, stamp } from "../api";

export default function Audit() {
  const [rows, setRows] = useState(null);
  const [err, setErr] = useState(null);
  useEffect(() => { api.audit().then(setRows).catch((e) => setErr(e.message)); }, []);
  if (err) return <div className="banner err">{err}</div>;
  if (!rows) return <div className="muted pad">Loading…</div>;
  return (
    <section>
      <p className="muted small">Who did what, newest first (last 200 events). Only administrators can see this.</p>
      <div className="tablewrap"><table>
        <thead><tr><th>When</th><th>User</th><th>Action</th><th>Detail</th></tr></thead>
        <tbody>{rows.map((r, i) => <tr key={i}><td>{stamp(r.at)}</td><td>{r.email ?? "—"}</td><td>{r.action}</td><td style={{ whiteSpace: "normal" }}>{r.detail}</td></tr>)}</tbody>
      </table></div>
    </section>
  );
}
