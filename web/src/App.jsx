import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "./api";
import Auth from "./components/Auth.jsx";
import Landing from "./components/Landing.jsx";
import Home from "./components/Home.jsx";
import Ask from "./components/Ask.jsx";
import Cohort from "./components/Cohort.jsx";
import Documents from "./components/Documents.jsx";
import Insights from "./components/Insights.jsx";
import Timeline from "./components/Timeline.jsx";
import Coverage from "./components/Coverage.jsx";
import Audit from "./components/Audit.jsx";

export default function App() {
  const [user, setUser] = useState(undefined);   // undefined = checking, null = signed out
  const [docs, setDocs] = useState([]);
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [tab, setTab] = useState("summary");
  const [busy, setBusy] = useState(null);
  const [error, setError] = useState(null);
  const [failed, setFailed] = useState({});
  const [flaggedOnly, setFlaggedOnly] = useState(false);
  const [q, setQ] = useState("");

  const fail = (e) => { if (e.status === 401) { setUser(null); setDocs([]); } else setError(e.message); };

  useEffect(() => { api.me().then(setUser).catch(() => setUser(null)); }, []);

  const refresh = useCallback(async () => {
    const rows = await api.documents();
    setDocs(rows);
    setSelected((cur) => (cur && rows.some((r) => r.key === cur) ? cur : (rows.find((r) => r.status === "Flagged") || rows[0])?.key || null));
  }, []);

  useEffect(() => { if (user) refresh().catch(fail); }, [user, refresh]);

  const run = async (label, fn) => {
    setError(null); setBusy(label);
    try { await fn(); await refresh(); } catch (e) { fail(e); } finally { setBusy(null); }
  };

  const loadDemo = () => run("Adding demo patients…", () => api.demo());

  const upload = async (fileList) => {
    const files = [...fileList].filter((f) => /\.xlsx$/i.test(f.name));
    if (!files.length) { setError("Choose .xlsx patient workbooks."); return; }
    const all = {};
    await run("Reading workbooks…", async () => {
      for (let i = 0; i < files.length; i += 10) {
        setBusy(`Reading workbooks… ${Math.min(i + 10, files.length)} of ${files.length}`);
        Object.assign(all, (await api.upload(files.slice(i, i + 10))).failed);
      }
    });
    setFailed(all);
  };

  const remove = (id) => run("Deleting…", () => api.remove(id));
  const removeAll = () => run("Deleting…", () => api.removeAll());

  useEffect(() => {
    if (!selected || !user) { setDetail(null); return; }
    let live = true;
    api.detail(selected).then((d) => live && setDetail(d)).catch((e) => live && fail(e));
    return () => { live = false; };
  }, [selected, user]);

  const signOut = async () => { await api.logout(); setUser(null); setDocs([]); setDetail(null); setSelected(null); setTab("summary"); };
  const deleteAccount = async () => {
    if (!confirm("Permanently delete your account and every document you uploaded?")) return;
    await api.deleteAccount().catch(() => {}); setUser(null); setDocs([]); setDetail(null); setSelected(null);
  };

  const visible = useMemo(
    () => docs.filter((p) => (!flaggedOnly || p.status === "Flagged") && (!q || p.id.toLowerCase().includes(q.toLowerCase()))),
    [docs, flaggedOnly, q]);

  const open = (key, to = "summary") => { setSelected(key); setTab(to); window.scrollTo({ top: 0 }); };

  if (user === undefined) return <div className="muted pad">Loading…</div>;
  if (user === null) return <Auth onDone={(u) => { setUser(u); setError(null); }} />;
  if (!docs.length) {
    return <Landing user={user} onDemo={loadDemo} onUpload={upload} onSignOut={signOut} busy={busy} error={error} failed={failed} />;
  }

  const TABS = [["summary", "My summary"], ["ask", "Ask a question"], ["timeline", "Trends"], ["insights", "Full findings"], ["coverage", "Data quality"],
    ["cohort", "All patients"], ["documents", "Files"],
    ...(user.role === "admin" ? [["audit", "Activity log"]] : [])];
  const needsPatient = ["summary", "ask", "insights", "timeline", "coverage"].includes(tab);

  return (
    <div className="shell">
      <aside className="rail">
        <div className="brand">🫀 <b>PranaPulse</b></div>
        <input className="search" placeholder="Search patient ID" value={q} onChange={(e) => setQ(e.target.value)} />
        <label className="check"><input type="checkbox" checked={flaggedOnly} onChange={(e) => setFlaggedOnly(e.target.checked)} /> Only patients with an insight</label>
        <div className="plist" role="listbox" aria-label="Patients">
          {visible.slice(0, 400).map((p) => (
            <button key={p.key} className={"pitem" + (p.key === selected ? " on" : "")} onClick={() => open(p.key, needsPatient ? tab : "summary")}>
              <span className={"dot " + (p.status === "Flagged" ? "flag" : "quiet")} /> {p.id}
              <span className="sub">{p.status === "Flagged" ? p.scenario : "Quiet"}</span>
            </button>
          ))}
          {visible.length > 400 && <div className="muted small pad">Showing first 400 of {visible.length}. Use search.</div>}
        </div>
        <div className="userbox">
          <div className="uname"><b>{user.name}</b><span className="muted small">{user.email} · {user.role}</span></div>
          <div className="railfoot">
            <button className="btn ghost small" onClick={signOut}>Sign out</button>
            <button className="btn ghost small" onClick={deleteAccount} title="Delete my account and data">Delete account</button>
          </div>
        </div>
      </aside>

      <main className="main">
        <div className="mobile-pick">
          <select value={selected || ""} onChange={(e) => open(e.target.value, needsPatient ? tab : "summary")}>
            {docs.map((p) => <option key={p.key} value={p.key}>{p.id} · {p.status}</option>)}
          </select>
          <button className="btn ghost small" onClick={signOut}>Sign out</button>
        </div>
        {busy && <div className="banner">{busy}</div>}
        {error && <div className="banner err" onClick={() => setError(null)}>{error}</div>}
        {Object.keys(failed).length > 0 && (
          <div className="banner err" onClick={() => setFailed({})}>Skipped: {Object.entries(failed).map(([f, w]) => `${f} (${w})`).join("; ")}</div>)}

        {detail && needsPatient && tab !== "summary" && (
          <header className="hero">
            <h1>Patient {detail.patient.id}</h1>
            <p>Changes against this patient's own baseline, connected to their history.</p>
            <div className="meta">{detail.patient.age ?? "—"} years · {detail.patient.sex ?? "—"} · data {detail.patient.start} to {detail.patient.end} ({detail.patient.days} days)</div>
          </header>
        )}
        <nav className="tabs" role="tablist">
          {TABS.map(([k, label]) => <button key={k} role="tab" aria-selected={tab === k} className={tab === k ? "on" : ""} onClick={() => setTab(k)}>{label}</button>)}
        </nav>

        {tab === "cohort" && <Cohort patients={docs} onOpen={open} />}
        {tab === "documents" && <Documents docs={docs} onUpload={upload} onDemo={loadDemo} onOpen={open} onRemove={remove} onRemoveAll={removeAll} busy={busy} />}
        {tab === "audit" && <Audit />}
        {needsPatient && !detail && <div className="muted pad">Loading patient…</div>}
        {tab === "summary" && <Home user={user} docs={docs} selected={selected} detail={detail} onPick={(k) => open(k, "summary")} onFull={() => setTab("insights")} onTrends={() => setTab("timeline")} />}
        {tab === "ask" && selected && <div className="askpage"><Ask pkey={selected} area={null} title="Ask about your results" /></div>}
        {tab === "insights" && detail && <Insights pkey={selected} d={detail} onTimeline={() => setTab("timeline")} />}
        {tab === "timeline" && detail && <Timeline d={detail} />}
        {tab === "coverage" && detail && <Coverage d={detail} />}

        <footer className="foot">Prototype for academic use on synthetic / anonymised data. It highlights patterns that may be worth discussing with a healthcare provider. It does not diagnose or give medical advice.</footer>
      </main>
    </div>
  );
}
