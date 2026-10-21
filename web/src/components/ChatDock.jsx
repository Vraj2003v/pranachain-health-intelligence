import { useState } from "react";
import Ask from "./Ask.jsx";

// Chat bar fixed to the bottom of the screen: type at any time, the conversation opens above it.
export default function ChatDock({ pkey, onAction }) {
  const [open, setOpen] = useState(false);
  if (!pkey) return null;
  return <Ask pkey={pkey} area={null} bar open={open} setOpen={setOpen} onAction={onAction} />;
}
