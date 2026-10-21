import { useEffect, useRef, useState } from "react";
import { api } from "../api";

const CHIPS = ["What changed the most?", "Why was this flagged?", "How is my weight?", "Compare weight and steps",
  "What does the baseline mean?", "Does this mean I have a condition?"];

export default function Ask({ pkey, area, title = "Ask about your results", onAction, compact = false, bar = false, open = true, setOpen = () => {} }) {
  const [msgs, setMsgs] = useState([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const end = useRef();
  const [ai, setAi] = useState(null);
  useEffect(() => { if (bar) api.health().then((h) => setAi(h)).catch(() => {}); }, [bar]);
  useEffect(() => { setMsgs([]); }, [pkey, area]);
  useEffect(() => { end.current?.scrollIntoView({ block: "nearest", behavior: "smooth" }); }, [msgs, busy]);

  const send = async (q) => {
    q = (q ?? text).trim();
    if (!q || busy) return;
    setOpen(true);
    const history = msgs.map((m) => ({ who: m.who, text: m.text, key: m.key }));
    setText(""); setMsgs((m) => [...m, { who: "me", text: q }]); setBusy(true);
    try {
      const r = await api.ask(pkey, q, area, history);
      setMsgs((m) => [...m, { who: "bot", text: r.text, key: r.key, action: r.action, follow: r.followups,
        note: r.source === "local model" ? "Wording by local model, checked against the wording rules" : null }]);
    } catch (e) {
      setMsgs((m) => [...m, { who: "bot", text: e.message, error: true }]);
    } finally { setBusy(false); }
  };

  const lastBot = [...msgs].reverse().find((m) => m.who === "bot" && m.follow);
  const chips = lastBot ? lastBot.follow : CHIPS;

  const thread = (
    <>
      <div className="thread" aria-live="polite">
        {msgs.length === 0 && <p className="muted small">Ask about any reading, compare two measures, or find what changed most. Answers use only your findings and never replace a healthcare provider.</p>}
        {msgs.map((m, i) => (
          <div key={i} className={"bubble " + m.who + (m.error ? " err" : "")}>
            {m.text}
            {m.action && onAction && <button type="button" className="actbtn" onClick={() => onAction(m.action)}>{m.action.label}</button>}
            {m.note && <span className="bnote">{m.note}</span>}
          </div>))}
        {busy && <div className="bubble bot typing" aria-label="Writing an answer"><i /><i /><i /></div>}
        <div ref={end} />
      </div>
      <div className="qchips">
        {chips.map((c) => <button key={c} type="button" className="qchip" disabled={busy} onClick={() => send(c)}>{c}</button>)}
      </div>
    </>
  );
  const form = (
    <form className="askrow" onSubmit={(e) => { e.preventDefault(); send(); }}>
      <input value={text} onChange={(e) => setText(e.target.value)} onFocus={() => bar && setOpen(true)} placeholder="Ask in your own words" maxLength={300} aria-label="Your question" />
      <button className="btn" disabled={busy || !text.trim()}>Ask</button>
    </form>
  );

  if (bar) {
    return (
      <section className="chatbar" aria-label="Assistant">
        {open && (
          <div className="barpanel">
            <div className="askhead">
              <h3>Assistant {ai && <span className={"chip " + (ai.llm ? "ok" : "quiet")} title={ai.llm ? `Local model ${ai.model} is rewording answers` : "Standard answers. Start Ollama to switch the AI on."}>{ai.llm ? `AI on · ${ai.model}` : "AI off · standard answers"}</span>}</h3>
              <span className="row">
                {msgs.length > 0 && <button type="button" className="btn ghost small" onClick={() => setMsgs([])}>New chat</button>}
                <button type="button" className="btn ghost small" onClick={() => setOpen(false)} aria-label="Minimise assistant">Minimise</button>
              </span>
            </div>
            {thread}
          </div>)}
        {form}
      </section>);
  }

  return (
    <section className={"ask" + (compact ? " compact" : "")} aria-label={title}>
      <div className="askhead"><h3>{title}</h3>
        {msgs.length > 0 && <button type="button" className="btn ghost small" onClick={() => setMsgs([])}>New chat</button>}</div>
      {thread}
      {form}
    </section>
  );
}
