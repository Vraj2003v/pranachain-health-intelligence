import { useEffect, useRef, useState } from "react";
import { api } from "../api";

const CHIPS = ["Why was this flagged?", "What does the baseline mean?", "How much data is behind this?",
  "What does the projection show?", "What should I do next?", "Does this mean I have a condition?"];

export default function Ask({ pkey, area, title = "Ask about your results" }) {
  const [msgs, setMsgs] = useState([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const end = useRef();
  useEffect(() => { setMsgs([]); }, [pkey, area]);
  useEffect(() => { end.current?.scrollIntoView({ block: "nearest", behavior: "smooth" }); }, [msgs, busy]);

  const send = async (q) => {
    q = (q ?? text).trim();
    if (!q || busy) return;
    setText(""); setMsgs((m) => [...m, { who: "me", text: q }]); setBusy(true);
    try {
      const r = await api.ask(pkey, q, area);
      setMsgs((m) => [...m, { who: "bot", text: r.text, note: r.source === "local model" ? "Wording by local model, checked against the wording rules" : null }]);
    } catch (e) {
      setMsgs((m) => [...m, { who: "bot", text: e.message, error: true }]);
    } finally { setBusy(false); }
  };

  return (
    <section className="ask" aria-label={title}>
      <h3>{title}</h3>
      <div className="thread" aria-live="polite">
        {msgs.length === 0 && <p className="muted small">Pick a question or type your own. Answers use only your findings and never replace a healthcare provider.</p>}
        {msgs.map((m, i) => (
          <div key={i} className={"bubble " + m.who + (m.error ? " err" : "")}>
            {m.text}{m.note && <span className="bnote">{m.note}</span>}
          </div>))}
        {busy && <div className="bubble bot typing" aria-label="Writing an answer"><i /><i /><i /></div>}
        <div ref={end} />
      </div>
      <div className="qchips">
        {CHIPS.map((c) => <button key={c} type="button" className="qchip" disabled={busy} onClick={() => send(c)}>{c}</button>)}
      </div>
      <form className="askrow" onSubmit={(e) => { e.preventDefault(); send(); }}>
        <input value={text} onChange={(e) => setText(e.target.value)} placeholder="Ask in your own words" maxLength={300} aria-label="Your question" />
        <button className="btn" disabled={busy || !text.trim()}>Ask</button>
      </form>
    </section>
  );
}
