import { useState } from "react";
import { api, fmt } from "../api";

const ICON = { pattern: "🔗", single: "📈", cycle: "🗓️", recent: "🕒" };
const KIND = { pattern: "Pattern across measures", single: "Single measure", cycle: "Cycle timing", recent: "Latest vs 90-day baseline" };
const EVID = [["id", "ID"], ["signal", "Signal"], ["source", "Source sheet"], ["first_window", "Earlier period"], ["last_window", "Recent period"],
  ["first_mean", "Earlier value"], ["last_mean", "Recent value"], ["days_with_data", "Days with data"], ["size_vs_own_variation", "Change vs usual variation"], ["trend_p", "Trend p-value"]];

function Card({ pkey, i, ins, onTimeline }) {
  const [text, setText] = useState(null);
  const [note, setNote] = useState(null);
  const [busy, setBusy] = useState(false);
  const explain = async () => {
    setBusy(true); setNote(null);
    try {
      const r = await api.explain(i, pkey);
      setText(r.text); setNote(r.source === "local model" ? "Wording by local model (checked against the wording rules)" : r.note || "Standard wording (local model off or reply rejected)");
    } catch (e) { setNote(e.message); } finally { setBusy(false); }
  };
  return (
    <article className="card">
      <h2>{ICON[ins.kind]} {ins.title}</h2>
      <p className="muted small" title="Finding ID and the evidence rows that support it">{ins.id} · evidence {ins.evidence.map((e) => e.id).join(", ")}</p>
      <div className="chips">
        <span className="chip kind">{ins.scenario}</span><span className="chip kind">{KIND[ins.kind]}</span>
        <span className={"chip " + (ins.flag === "Limited" ? "warn" : "ok")}>● {ins.flag === "Limited" ? "Limited data" : "Data sufficient"}</span>
        {ins.flag === "Limited" && <span className="muted small">some expected data was missing</span>}
      </div>
      <p className="lead">{text || ins.summary}</p>
      {note && <p className="muted small">{note}</p>}
      {ins.tiles.length > 0 && (
        <div className="tiles">
          {ins.tiles.map((t) => (
            <div className="tile" key={t.label}>
              <div className="l">{t.label}</div>
              <div className="v">{fmt(t.value, t.decimals)} <span className="u">{t.unit}</span></div>
              <div className="d">{t.diff > 0 ? "↑" : "↓"} {t.diff > 0 ? "+" : ""}{fmt(t.diff, t.decimals)} vs earlier 90 days</div>
            </div>))}
        </div>)}
      <ul>{ins.bullets.map((b) => <li key={b}>{b}</li>)}</ul>
      {ins.context.length > 0 && (
        <p className="ctx"><b>Connects to:</b> {ins.context.slice(0, 3).map((c) => c.split(" — ")[0]).join(" · ")}</p>)}
      {ins.closing && <div className="note">{ins.closing}</div>}
      <div className="actions">
        {ins.forecastKey && <button className="btn small" onClick={onTimeline}>See trend line and projection</button>}
        <button className="btn ghost small" disabled={busy} onClick={explain}>{busy ? "Rewriting…" : "Explain with local model"}</button>
      </div>
      <details><summary>Why was this flagged? Supporting evidence</summary>
        <div className="tablewrap"><table><thead><tr>{EVID.map(([, l]) => <th key={l}>{l}</th>)}</tr></thead>
          <tbody>{ins.evidence.map((e, n) => <tr key={n}>{EVID.map(([k]) => <td key={k}>{e[k] ?? "—"}</td>)}</tr>)}</tbody></table></div>
      </details>
      {ins.context.length > 0 && <details><summary>History this connects to (with source)</summary><ul>{ins.context.map((c) => <li key={c}>{c}</li>)}</ul></details>}
      {ins.asks.length > 0 && <details><summary>What additional data would improve understanding</summary><ul>{ins.asks.map((c) => <li key={c}>{c}</li>)}</ul></details>}
    </article>
  );
}

const SECTIONS = [
  { scenario: "Cardiovascular / hypertension", icon: "🩺", title: "Cardiovascular",
    watches: "Blood pressure, resting heart rate, HRV and LDL cholesterol",
    why: "Changes in these measures can matter for heart and blood-vessel health, so they are worth discussing with a healthcare provider alongside the patient's history." },
  { scenario: "Metabolic health", icon: "⚖️", title: "Metabolic",
    watches: "Weight, activity, sleep, HbA1c and fasting glucose",
    why: "Shifts in these measures can relate to how the body handles blood sugar and weight, so they are worth discussing with a healthcare provider alongside the patient's history." },
  { scenario: "Women's health (PCOS)", icon: "🌸", title: "Women's health",
    watches: "Cycle length and regularity, with related history",
    why: "Irregular cycle timing can relate to hormonal conditions, so it is worth discussing with a healthcare provider alongside the patient's history." },
];

export default function Insights({ pkey, d, onTimeline }) {
  const indexed = d.insights.map((ins, i) => ({ ins, i }));
  const other = indexed.filter(({ ins }) => !SECTIONS.some((s) => s.scenario === ins.scenario));
  return (
    <section>
      <p className="muted small">Results are grouped under the three areas we focus on. Each section shows what moved, the evidence, and why it may matter.</p>
      {SECTIONS.map((sec) => {
        const items = indexed.filter(({ ins }) => ins.scenario === sec.scenario);
        return (
          <div key={sec.scenario} className={"dsec" + (items.length ? " found" : "")}>
            <div className="dhead">
              <h2>{sec.icon} {sec.title}</h2>
              <span className={"chip " + (items.length ? "warn" : "ok")}>{items.length ? `Changes found (${items.length})` : "No clear change"}</span>
            </div>
            <p className="muted small"><b>What we look at:</b> {sec.watches}</p>
            {items.length > 0 && <p className="impact"><b>Why it may matter:</b> {sec.why}</p>}
            {items.length === 0 && <p className="muted small">Nothing in this area moved beyond this patient's own usual range.</p>}
            {items.map(({ ins, i }) => <Card key={i} pkey={pkey} i={i} ins={ins} onTimeline={onTimeline} />)}
          </div>);
      })}
      {other.map(({ ins, i }) => <Card key={i} pkey={pkey} i={i} ins={ins} onTimeline={onTimeline} />)}
      {d.held.length > 0 && <details className="card"><summary>Held back (not shown as insights)</summary><ul>{d.held.map((h) => <li key={h}>{h}</li>)}</ul></details>}
      {d.positives.length > 0 && <details className="card"><summary>Positive changes</summary><ul>{d.positives.map((h) => <li key={h}>{h}</li>)}</ul></details>}
    </section>
  );
}
