import { useState } from "react";
import Ask from "./Ask.jsx";

export default function ChatDock({ pkey, onAction }) {
  const [open, setOpen] = useState(false);
  if (!pkey) return null;
  return (
    <div className="dock">
      {open && (
        <div className="dockpanel" role="dialog" aria-label="Assistant">
          <button className="dockclose" aria-label="Close assistant" onClick={() => setOpen(false)}>×</button>
          <Ask pkey={pkey} area={null} title="Assistant" compact onAction={(a) => { onAction(a); }} />
        </div>)}
      <button className="dockbtn" aria-expanded={open} onClick={() => setOpen(!open)}>
        <span aria-hidden>💬</span> {open ? "Hide assistant" : "Ask the assistant"}
      </button>
    </div>
  );
}
