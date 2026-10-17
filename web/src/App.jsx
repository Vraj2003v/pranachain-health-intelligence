import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "./api";
import Landing from "./components/Landing.jsx";
import Cohort from "./components/Cohort.jsx";
import Insights from "./components/Insights.jsx";
import Timeline from "./components/Timeline.jsx";
import Coverage from "./components/Coverage.jsx";

const TABS = [["cohort", "Cohort"], ["insights", "Insights"], ["timeline", "Timeline & projection"], ["coverage", "Data coverage"]];

export default function App() {
  const [sid, setSid] = useState(null);
  const [patients, setPatients] = useState([]);
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [tab, setTab] = useState("cohort");
  const [busy, setBusy] = useState(null);
  const [error, setError] = useState(null);
  const [failed, setFailed] = useState({});
  const [flaggedOnly, setFlaggedOnly] = useState(false);
  const [q, setQ] = useState("");

  useEffect(() => { api.newSession().then((r) => setSid(r.session)).catch((e) => setError(e.message)); }, []);

  const refresh = useCallback(async (id = sid) => {
    const rows = await api.patients(id);
    setPatients(rows);
    setSelected((cur) => (cur && rows.some((r) => r.key === cur) ? cur : (rows.find((r) => r.status === "Flagged") || rows[0])?.key || null));
  }, [sid]);

  const loadDemo = async () => {
    setError(null); setBusy("Loading demo patients…");
    try { await api.demo(sid); await refresh(); } catch (e) { setError(e.message); } finally { setBusy(null); }
  };

  const upload = async (fileList) => {
    const files = [...fileList].filter((f) => /\.xlsx$/i.test(f.name));
    if (!files.length) { setError("Choose .xlsx patient workbooks."); return; }
    setError(null);
    const allFailed = {};
    try {
      for (let i = 0; i < files.length; i += 10) {
        setBusy(`Reading workbooks… ${Math.min(i + 10, files.length)} of ${files.length}`);
        Object.assign(allFailed, (await api.upload(sid, files.slice(i, i + 10))).failed);
      }
      setFailed(allFailed);
      await refresh();
    } catch (e) { setError(e.message); } finally { setBusy(null); }
  };

  const clear = async () => { await api.clear(sid); setPatients([]); setSelected(null); setDetail(null); setFailed({}); setTab("cohort"); };

  useEffect(() => {
    if (!selected || !sid) { setDetail(null); return; }
    let live = true;
    api.patient(sid, selected).then((d) => live && setDetail(d)).catch((e) => live && setError(e.message));
    return () => { live = false; };
  }, [selected, sid]);

  const visible = useMemo(
    () => patients.filter((p) => (!flaggedOnly || p.status === "Flagged") && (!q || p.id.toLowerCase().includes(q.toLowerCase()))),
    [patients, flaggedOnly, q]);

  const open = (key, to = "insights") => { setSelected(key); setTab(to); window.scrollTo({ top: 0 }); };

  if (!patients.length) {
    return <Landing onDemo={loadDemo} onUpload={upload} busy={busy} error={error} failed={failed} ready={!!sid} />;
  }

  return (
    <div className="shell">
      <aside className="rail">
        <div className="brand">🫀 <b>PranaPulse</b></div>
        <input className="search" placeholder="Search patient ID" value={q} onChange={(e) => setQ(e.target.value)} />
        <label className="check"><input type="checkbox" checked={flaggedOnly} onChange={(e) => setFlaggedOnly(e.target.checked)} /> Only patients with an insight</label>
        <div className="plist" role="listbox" aria-label="Patients">
          {visible.slice(0, 400).map((p) => (
            <button key={p.key} className={"pitem" + (p.key === selected ? " on" : "")} onClick={() => open(p.key, tab === "cohort" ? "insights" : tab)}>
              <span className={"dot " + (p.status === "Flagged" ? "flag" : "quiet")} /> {p.id}
              <span className="sub">{p.status === "Flagged" ? p.scenario : "Quiet"}</span>
            </button>
          ))}
          {visible.length > 400 && <div className="muted small pad">Showing first 400 of {visible.length}. Use search.</div>}
        </div>
        <div className="railfoot">
          <label className="btn ghost small">Add workbooks<input type="file" accept=".xlsx" multiple hidden onChange={(e) => upload(e.target.files)} /></label>
          <button className="btn ghost small" onClick={clear}>Clear all</button>
        </div>
      </aside>

      <main className="main">
        <div className="mobile-pick">
          <select value={selected || ""} onChange={(e) => open(e.target.value, tab === "cohort" ? "insights" : tab)}>
            {patients.map((p) => <option key={p.key} value={p.key}>{p.id} · {p.status}</option>)}
          </select>
        </div>
        {busy && <div className="banner">{busy}</div>}
        {error && <div className="banner err" onClick={() => setError(null)}>{error}</div>}
        {Object.keys(failed).length > 0 && <div className="banner err">Could not read: {Object.entries(failed).map(([f, w]) => `${f} (${w})`).join("; ")}</div>}

        {detail && (
          <header className="hero">
            <h1>Patient {detail.patient.id}</h1>
            <p>Changes against this patient's own baseline, connected to their history.</p>
            <div className="meta">{detail.patient.age ?? "—"} years · {detail.patient.sex ?? "—"} · data {detail.patient.start} to {detail.patient.end} ({detail.patient.days} days)</div>
          </header>
        )}
        <nav className="tabs" role="tablist">
          {TABS.map(([k, label]) => <button key={k} role="tab" aria-selected={tab === k} className={tab === k ? "on" : ""} onClick={() => setTab(k)}>{label}</button>)}
        </nav>

        {tab === "cohort" && <Cohort patients={patients} onOpen={open} />}
        {tab !== "cohort" && !detail && <div className="muted pad">Loading patient…</div>}
        {tab === "insights" && detail && <Insights sid={sid} pkey={selected} d={detail} onTimeline={() => setTab("timeline")} />}
        {tab === "timeline" && detail && <Timeline d={detail} />}
        {tab === "coverage" && detail && <Coverage d={detail} />}

        <footer className="foot">Prototype for academic use on synthetic / anonymised data. It highlights patterns that may be worth discussing with a healthcare provider. It does not diagnose or give medical advice.</footer>
      </main>
    </div>
  );
}
