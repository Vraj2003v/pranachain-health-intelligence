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
import Explore from "./components/Explore.jsx";
import Tools from "./components/Tools.jsx";
import ChatDock from "./components/ChatDock.jsx";
import Audit from "./components/Audit.jsx";
import { viewFor } from "./roles.js";

export default function App() {
  const [user, setUser] = useState(undefined);   // undefined = checking, null = signed out
  const [docs, setDocs] = useState([]);
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [tab, setTab] = useState("summary");
  const [busy, setBusy] = useState(null);
  const [error, setError] = useState(null);
  const [failed, setFailed] = useState({});
  const [focus, setFocus] = useState(null);   // measure(s) chosen by the assistant
  const [flaggedOnly, setFlaggedOnly] = useState(false);
  const [q, setQ] = useState("");

  const fail = (e) => { if (e.status === 401) { setUser(null); setDocs([]); } else setError(e.message); };

  useEffect(() => { api.me().then((u) => { setUser(u); setTab(viewFor(u.role).home); }).catch(() => setUser(null)); }, []);

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

  const signOut = async () => { await api.logout(); setUser(null); setDocs([]); setDetail(null); setSelected(null); };
  const deleteAccount = async () => {
    if (!confirm("Permanently delete your account and every document you uploaded?")) return;
    await api.deleteAccount().catch(() => {}); setUser(null); setDocs([]); setDetail(null); setSelected(null);
  };

  const visible = useMemo(
    () => docs.filter((p) => (!flaggedOnly || p.status === "Flagged") && (!q || p.id.toLowerCase().includes(q.toLowerCase()))),
    [docs, flaggedOnly, q]);

  const home = viewFor(user?.role);
  const landing = home.tabs.includes("summary") ? "summary" : "insights";
  const open = (key, to = landing) => { setSelected(key); setTab(to); window.scrollTo({ top: 0 }); };

  const act = (a) => { setFocus({ key: a.key, keys: a.keys || (a.key ? [a.key] : null) }); setTab(a.tab); window.scrollTo({ top: 0 }); };

  if (user === undefined) return <div className="muted pad">Loading…</div>;
  if (user === null) return <Auth onDone={(u) => { setUser(u); setTab(viewFor(u.role).home); setError(null); }} />;
  if (!docs.length) {
    return <Landing user={user} onDemo={loadDemo} onUpload={upload} onSignOut={signOut} busy={busy} error={error} failed={failed} />;
  }

  const view = viewFor(user.role);
  const TABS = view.tabList;
  const shown = view.tabs.includes(tab) ? tab : view.home;
  const needsPatient = ["summary", "ask", "insights", "timeline", "explore", "coverage"].includes(shown);

  return (
    <div className="shell">
      <aside className="rail">
        <div className="brandrow"><div className="brand">🫀 <b>PranaPulse</b></div><Tools /></div>
        {view.rail && <>
        <input className="search" placeholder="Search patient ID" value={q} onChange={(e) => setQ(e.target.value)} />
        <label className="check"><input type="checkbox" checked={flaggedOnly} onChange={(e) => setFlaggedOnly(e.target.checked)} /> Only patients with an insight</label>
        <div className="plist" role="listbox" aria-label="Patients">
          {visible.slice(0, 400).map((p) => (
            <button key={p.key} className={"pitem" + (p.key === selected ? " on" : "")} onClick={() => open(p.key, needsPatient ? shown : landing)}>
              <span className={"dot " + (p.status === "Flagged" ? "flag" : "quiet")} /> {p.id}
              <span className="sub">{p.status === "Flagged" ? p.scenario : "Quiet"}</span>
            </button>
          ))}
          {visible.length > 400 && <div className="muted small pad">Showing first 400 of {visible.length}. Use search.</div>}
        </div>
        </>}
        <div className="userbox">
          <div className="uname"><b>{user.name}</b><span className="muted small">{user.email} · {{ patient: "Patient", clinician: "Healthcare provider", researcher: "Researcher", admin: "Administrator" }[user.role] || user.role}</span></div>
          <div className="railfoot">
            <button className="btn ghost small" onClick={signOut}>Sign out</button>
            <button className="btn ghost small" onClick={deleteAccount} title="Delete my account and data">Delete account</button>
          </div>
        </div>
      </aside>

      <main className="main">
        <div className="mobile-pick">
          <Tools />
          {view.rail && <select value={selected || ""} onChange={(e) => open(e.target.value, needsPatient ? shown : landing)}>
            {docs.map((p) => <option key={p.key} value={p.key}>{p.id} · {p.status}</option>)}
          </select>}
          <button className="btn ghost small" onClick={signOut}>Sign out</button>
        </div>
        {busy && <div className="banner">{busy}</div>}
        {error && <div className="banner err" onClick={() => setError(null)}>{error}</div>}
        {Object.keys(failed).length > 0 && (
          <div className="banner err" onClick={() => setFailed({})}>Skipped: {Object.entries(failed).map(([f, w]) => `${f} (${w})`).join("; ")}</div>)}

        {detail && needsPatient && shown !== "summary" && (
          <header className="hero">
            <h1>Patient {detail.patient.id}</h1>
            <p>Changes against this patient's own baseline, connected to their history.</p>
            <div className="meta">{detail.patient.age ?? "—"} years · {detail.patient.sex ?? "—"} · data {detail.patient.start} to {detail.patient.end} ({detail.patient.days} days)</div>
          </header>
        )}
        <nav className="tabs" role="tablist">
          {TABS.map(([k, label]) => <button key={k} role="tab" aria-selected={shown === k} className={shown === k ? "on" : ""} onClick={() => setTab(k)}>{label}</button>)}
        </nav>

        {shown === "cohort" && <Cohort patients={docs} onOpen={open} />}
        {shown === "documents" && <Documents docs={docs} onUpload={upload} onDemo={loadDemo} onOpen={open} onRemove={remove} onRemoveAll={removeAll} busy={busy} />}
        {shown === "audit" && <Audit />}
        {needsPatient && !detail && <div className="muted pad">Loading patient…</div>}
        {shown === "summary" && <Home user={user} canFull={view.tabs.includes("insights")} docs={docs} selected={selected} detail={detail} onPick={(k) => open(k, landing)} onFull={() => setTab("insights")} onTrends={() => setTab("timeline")} />}
        {shown === "ask" && selected && <div className="askpage"><Ask pkey={selected} area={null} title="Ask about your results" onAction={act} /></div>}
        {shown === "insights" && detail && <Insights pkey={selected} d={detail} onTimeline={() => setTab("timeline")} />}
        {shown === "timeline" && detail && <Timeline key={focus?.key || "t"} d={detail} initialKey={focus?.key} />}
        {shown === "explore" && detail && <Explore key={(focus?.keys || []).join()} d={detail} initial={focus?.keys} />}
        {shown === "coverage" && detail && <Coverage d={detail} />}

        <ChatDock pkey={selected} onAction={act} />
        <footer className="foot">Prototype for academic use on synthetic / anonymised data. It highlights patterns that may be worth discussing with a healthcare provider. It does not diagnose or give medical advice.</footer>
      </main>
    </div>
  );
}
