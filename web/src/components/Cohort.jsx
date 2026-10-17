import { useMemo, useState } from "react";

const SCEN = ["Metabolic health", "Cardiovascular / hypertension", "Women's health (PCOS)"];

export default function Cohort({ patients, onOpen }) {
  const [scen, setScen] = useState("All");
  const [status, setStatus] = useState("All");
  const [flag, setFlag] = useState("Any");
  const [q, setQ] = useState("");
  const [sort, setSort] = useState({ k: "id", dir: 1 });

  const flagged = patients.filter((p) => p.status === "Flagged");
  const limited = flagged.filter((p) => p.flag === "Limited").length;
  const counts = Object.fromEntries(SCEN.map((s) => [s, flagged.filter((p) => p.scenario === s).length]));

  const rows = useMemo(() => {
    let r = patients.filter((p) =>
      (scen === "All" || p.scenario === scen) && (status === "All" || p.status === status) &&
      (flag === "Any" || p.flag === flag) && (!q || p.id.toLowerCase().includes(q.toLowerCase())));
    r = [...r].sort((a, b) => (String(a[sort.k] ?? "").localeCompare(String(b[sort.k] ?? ""), undefined, { numeric: true })) * sort.dir);
    return r;
  }, [patients, scen, status, flag, q, sort]);

  const th = (k, label) => (
    <th onClick={() => setSort((s) => ({ k, dir: s.k === k ? -s.dir : 1 }))} className="sortable">
      {label}{sort.k === k ? (sort.dir > 0 ? " ▲" : " ▼") : ""}
    </th>);

  const csv = () => {
    const head = ["Patient", "Age", "Sex", "Status", "Scenario", "What was found", "Data flag", "Held back"];
    const body = patients.map((p) => [p.id, p.age ?? "", p.sex ?? "", p.status, p.scenario ?? "", p.found, p.flag ?? "", p.held]);
    const text = [head, ...body].map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(",")).join("\n");
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([text], { type: "text/csv" }));
    a.download = "pranapulse_cohort.csv"; a.click();
  };

  return (
    <section>
      <div className="kpis">
        <div className="kpi"><div className="n">{patients.length}</div><div className="l">Patients loaded</div></div>
        <div className="kpi"><div className="n">{flagged.length}</div><div className="l">With an insight</div></div>
        <div className="kpi"><div className="n">{patients.length - flagged.length}</div><div className="l">Quiet (intended)</div></div>
        <div className="kpi"><div className="n">{limited}</div><div className="l">Limited-data insights</div></div>
      </div>

      <h3 className="h">The three validation scenarios</h3>
      <div className="scen">
        {SCEN.map((s) => (
          <button key={s} className={"scard" + (scen === s ? " on" : "")} onClick={() => setScen(scen === s ? "All" : s)}>
            <span className="n">{counts[s]}</span><span>{s}</span>
          </button>))}
      </div>

      <div className="filters">
        <select value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="All">All patients</option><option value="Flagged">With an insight</option><option value="Quiet">Quiet</option>
        </select>
        <select value={flag} onChange={(e) => setFlag(e.target.value)}>
          <option value="Any">Any data flag</option><option value="Sufficient">Data sufficient</option><option value="Limited">Limited data</option>
        </select>
        <input placeholder="Search patient ID" value={q} onChange={(e) => setQ(e.target.value)} />
        <button className="btn ghost small" onClick={csv}>Download CSV</button>
      </div>

      <div className="tablewrap">
        <table>
          <thead><tr>{th("id", "Patient")}{th("age", "Age")}{th("sex", "Sex")}{th("status", "Status")}{th("scenario", "Scenario")}{th("found", "What was found")}{th("flag", "Data flag")}{th("held", "Held back")}</tr></thead>
          <tbody>
            {rows.slice(0, 300).map((p) => (
              <tr key={p.key} onClick={() => onOpen(p.key)} className="click">
                <td><b>{p.id}</b></td><td>{p.age ?? "—"}</td><td>{p.sex ?? "—"}</td>
                <td><span className={"chip " + (p.status === "Flagged" ? "warn" : "quiet")}>{p.status}</span></td>
                <td>{p.scenario ?? "—"}</td><td>{p.found}</td>
                <td>{p.flag ? <span className={"chip " + (p.flag === "Limited" ? "warn" : "ok")}>{p.flag === "Limited" ? "Limited data" : "Data sufficient"}</span> : "—"}</td>
                <td>{p.held}</td>
              </tr>))}
          </tbody>
        </table>
      </div>
      <p className="muted small">Showing {Math.min(rows.length, 300)} of {rows.length}. Select a patient to open their insights. Quiet is intended: ordinary day-to-day variation is not reported.</p>
    </section>
  );
}
