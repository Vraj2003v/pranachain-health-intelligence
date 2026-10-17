import { useState } from "react";
import { api } from "../api";

export default function Auth({ onDone }) {
  const [mode, setMode] = useState("login");
  const [f, setF] = useState({ name: "", email: "", password: "", confirm: false });
  const [err, setErr] = useState(null);
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value });

  const submit = async (e) => {
    e.preventDefault(); setErr(null); setBusy(true);
    try { onDone(mode === "login" ? await api.login({ email: f.email, password: f.password }) : await api.register(f)); }
    catch (x) { setErr(x.message); } finally { setBusy(false); }
  };

  return (
    <div className="authwrap">
      <div className="authside">
        <h1>🫀 PranaPulse</h1>
        <p>Explainable changes in a patient's health, connected to their history.</p>
        <ul>
          <li>Each patient is compared with their own earlier self</li>
          <li>Every insight shows its evidence and the history it connects to</li>
          <li>Missing data is flagged openly, never hidden</li>
          <li>It never diagnoses and never gives a risk score</li>
        </ul>
        <div className="meta">Beyond the Record · Group 11 · COMP8967</div>
      </div>
      <form className="authcard" onSubmit={submit}>
        <h2>{mode === "login" ? "Sign in" : "Create your account"}</h2>
        <p className="muted small">{mode === "login" ? "Use the account you created for this app." : "The first account created becomes the administrator."}</p>
        {mode === "register" && <label>Full name<input value={f.name} onChange={set("name")} autoComplete="name" required /></label>}
        <label>Email<input type="email" value={f.email} onChange={set("email")} autoComplete="email" required /></label>
        <label>Password<input type="password" value={f.password} onChange={set("password")} minLength={mode === "register" ? 8 : 1}
          autoComplete={mode === "login" ? "current-password" : "new-password"} required /></label>
        {mode === "register" && <p className="muted small">At least 8 characters.</p>}
        {mode === "register" && (
          <label className="check"><input type="checkbox" checked={f.confirm} onChange={set("confirm")} />
            I confirm I will only upload synthetic or anonymised data, and I understand this tool highlights patterns to discuss with a healthcare provider and does not diagnose.</label>)}
        {err && <div className="banner err">{err}</div>}
        <button className="btn" disabled={busy}>{busy ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}</button>
        <p className="small center">
          {mode === "login" ? "New here? " : "Already have an account? "}
          <a href="#" onClick={(e) => { e.preventDefault(); setErr(null); setMode(mode === "login" ? "register" : "login"); }}>
            {mode === "login" ? "Create an account" : "Sign in"}</a>
        </p>
      </form>
    </div>
  );
}
