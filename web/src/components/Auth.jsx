import { useState } from "react";
import { api } from "../api";

const LAST = "pranapulse.lastEmail";
const lastEmail = () => { try { return localStorage.getItem(LAST) || ""; } catch { return ""; } };
const saveEmail = (v) => { try { localStorage.setItem(LAST, v); } catch { /* storage may be blocked */ } };

const ROLES = [["patient", "Patient", "See my own readings and ask questions"],
  ["clinician", "Healthcare provider", "Review patients and the evidence"],
  ["researcher", "Researcher or student", "Explore the method on demo data"]];

export default function Auth({ onDone }) {
  const [mode, setMode] = useState("login");
  const [f, setF] = useState({ name: "", email: lastEmail(), password: "", again: "", confirm: false, role: "patient" });
  const [err, setErr] = useState(null);
  const [busy, setBusy] = useState(false);
  const [show, setShow] = useState(false);
  const [caps, setCaps] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value });
  const reg = mode === "register";

  const longEnough = f.password.length >= 8;
  const matches = f.password.length > 0 && f.password === f.again;
  const ready = reg ? f.name.trim() && f.email && longEnough && matches && f.confirm : f.email && f.password;

  const switchMode = (m) => { setErr(null); setMode(m); };
  const submit = async (e) => {
    e.preventDefault(); setErr(null);
    if (reg && !matches) { setErr("The two passwords do not match."); return; }
    setBusy(true);
    try {
      const u = reg ? await api.register({ name: f.name, email: f.email, password: f.password, confirm: f.confirm, role: f.role })
                    : await api.login({ email: f.email, password: f.password });
      saveEmail(f.email); onDone(u);
    } catch (x) { setErr(x.message); } finally { setBusy(false); }
  };
  const keys = (e) => setCaps(e.getModifierState && e.getModifierState("CapsLock"));

  return (
    <div className="authwrap">
      <form className="authcard" onSubmit={submit} noValidate>
        <div className="authbrand">🫀 PranaPulse</div>
        <div className="seg" role="tablist">
          <button type="button" role="tab" aria-selected={!reg} className={!reg ? "on" : ""} onClick={() => switchMode("login")}>Sign in</button>
          <button type="button" role="tab" aria-selected={reg} className={reg ? "on" : ""} onClick={() => switchMode("register")}>Create account</button>
        </div>
        <h2>{reg ? "Create your account" : "Welcome back"}</h2>
        <p className="muted small">{reg ? "The first account created becomes the administrator." : "Sign in to see your patients and findings."}</p>
        {reg && <label>Full name<input value={f.name} onChange={set("name")} autoComplete="name" autoFocus required /></label>}
        {reg && (
          <fieldset className="roles"><legend>I am a</legend>
            {ROLES.map(([k, t, d]) => (
              <label key={k} className={"role" + (f.role === k ? " on" : "")}>
                <input type="radio" name="role" value={k} checked={f.role === k} onChange={set("role")} />
                <span><b>{t}</b><span className="muted small">{d}</span></span>
              </label>))}
          </fieldset>)}
        <label>Email<input type="email" value={f.email} onChange={set("email")} autoComplete="email" autoFocus={!reg && !f.email} required /></label>
        <label>Password
          <span className="pwrow">
            <input type={show ? "text" : "password"} value={f.password} onChange={set("password")} onKeyUp={keys} onKeyDown={keys}
              autoComplete={reg ? "new-password" : "current-password"} autoFocus={!reg && !!f.email} required />
            <button type="button" className="btn ghost small" onClick={() => setShow(!show)} aria-pressed={show}>{show ? "Hide" : "Show"}</button>
          </span>
        </label>
        {caps && <p className="small warn-text">Caps Lock is on.</p>}
        {reg && (
          <>
            <label>Repeat password<input type={show ? "text" : "password"} value={f.again} onChange={set("again")} autoComplete="new-password" required /></label>
            <ul className="rules small">
              <li className={longEnough ? "met" : ""}>{longEnough ? "✓" : "○"} At least 8 characters</li>
              <li className={matches ? "met" : ""}>{matches ? "✓" : "○"} Both passwords match</li>
            </ul>
            <label className="check"><input type="checkbox" checked={f.confirm} onChange={set("confirm")} />
              I confirm I will only upload synthetic or anonymised data, and I understand this tool highlights patterns to discuss with a healthcare provider and does not diagnose.</label>
          </>)}
        {err && <div className="banner err" role="alert">{err}</div>}
        <button className="btn" disabled={busy || !ready}>{busy ? "Please wait…" : reg ? "Create account" : "Sign in"}</button>
        <p className="small center muted">{reg ? "Already registered? " : "New here? "}
          <a href="#" onClick={(e) => { e.preventDefault(); switchMode(reg ? "login" : "register"); }}>{reg ? "Sign in" : "Create an account"}</a></p>
        <p className="small center muted">Forgot your password? There is no email reset yet, so ask the administrator to remove your account, then register again.</p>
      </form>
    </div>
  );
}
