import { useEffect, useState } from "react";
import Ask from "./Ask.jsx";

// Round glass button in the corner. Tapping it pops the assistant open; Escape or the close button dismisses it.
export default function ChatDock({ pkey, onAction }) {
  const [open, setOpen] = useState(false);
  useEffect(() => {
    if (!open) return;
    const k = (e) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, [open]);
  if (!pkey) return null;
  return (
    <>
      {open && <Ask pkey={pkey} area={null} bar open setOpen={setOpen} onAction={onAction} />}
      <button className={"chatfab" + (open ? " open" : "")} aria-expanded={open} aria-label={open ? "Close assistant" : "Open assistant"}
        onClick={() => setOpen(!open)}><span aria-hidden>{open ? "✕" : "💬"}</span></button>
    </>
  );
}
