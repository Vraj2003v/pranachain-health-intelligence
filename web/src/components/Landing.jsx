import { useRef, useState } from "react";

export default function Landing({ user, onDemo, onUpload, onSignOut, busy, error, failed }) {
  const input = useRef();
  const [over, setOver] = useState(false);
  return (
    <div className="landing">
      <header className="hero big">
        <h1>🫀 Welcome, {user.name.split(" ")[0]}</h1>
        <p>Add patient workbooks to see what changed, the evidence, and the history it connects to.</p>
        <div className="meta">Signed in as {user.email} · {user.role} · <a href="#" style={{ color: "#fff" }} onClick={(e) => { e.preventDefault(); onSignOut(); }}>Sign out</a></div>
      </header>
      <div className="steps">
        <div className="step"><b>1 · Load</b><br />Drop in patient workbooks, or add the fabricated demo patients. They are saved to your account.</div>
        <div className="step"><b>2 · Compare</b><br />Each patient is compared with their own earlier self, never a population average.</div>
        <div className="step"><b>3 · Explain</b><br />See what changed, the evidence, the history it connects to, and a trend projection.</div>
      </div>
      <div className={"drop" + (over ? " over" : "")}
        onDragOver={(e) => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)}
        onDrop={(e) => { e.preventDefault(); setOver(false); onUpload(e.dataTransfer.files); }}>
        <p><b>Drop patient workbooks (.xlsx) here</b></p>
        <p className="muted">or choose files from your device. You can select many at once.</p>
        <div className="row">
          <button className="btn" disabled={!!busy} onClick={() => input.current.click()}>Upload workbooks</button>
          <button className="btn ghost" disabled={!!busy} onClick={onDemo}>Try demo patients</button>
        </div>
        <input ref={input} type="file" accept=".xlsx" multiple hidden onChange={(e) => onUpload(e.target.files)} />
      </div>
      {busy && <div className="banner">{busy}</div>}
      {error && <div className="banner err">{error}</div>}
      {Object.keys(failed).length > 0 && <div className="banner err">Skipped: {Object.entries(failed).map(([f, w]) => `${f} (${w})`).join("; ")}</div>}
      <footer className="foot">Prototype for academic use on synthetic / anonymised data. It does not diagnose or give medical advice.</footer>
    </div>
  );
}
