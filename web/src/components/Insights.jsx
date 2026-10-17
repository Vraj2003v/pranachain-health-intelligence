import { useState } from "react";
import { api, fmt } from "../api";

const ICON = { pattern: "🔗", single: "📈", cycle: "🗓️" };
const KIND = { pattern: "Pattern across measures", single: "Single measure", cycle: "Cycle timing" };
const EVID = [["signal", "Signal"], ["source", "Source sheet"], ["first_window", "Earlier period"], ["last_window", "Recent period"],
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

export default function Insights({ pkey, d, onTimeline }) {
  return (
    <section>
      {d.insights.length === 0 && (
        <div className="card ok-card"><h2>✅ Nothing flagged</h2>
          <p>No meaningful change was found against this patient's own baseline.</p>
          <p className="muted small">Staying quiet is intended: small day-to-day variation is not reported as an insight.</p></div>)}
      {d.insights.map((ins, i) => <Card key={i} pkey={pkey} i={i} ins={ins} onTimeline={onTimeline} />)}
      {d.held.length > 0 && <details className="card"><summary>Held back (not shown as insights)</summary><ul>{d.held.map((h) => <li key={h}>{h}</li>)}</ul></details>}
      {d.positives.length > 0 && <details className="card"><summary>Positive changes</summary><ul>{d.positives.map((h) => <li key={h}>{h}</li>)}</ul></details>}
    </section>
  );
}
