import { useState } from "react";
import { applyTheme, getTheme, nextTheme } from "../theme.js";

const LABEL = { auto: ["🌓", "Auto"], light: ["☀️", "Light"], dark: ["🌙", "Dark"] };

export default function ThemeToggle({ floating = false }) {
  const [t, setT] = useState(getTheme());
  const go = () => { const n = nextTheme(t); applyTheme(n); setT(n); };
  return (
    <button type="button" className={"themebtn" + (floating ? " floating" : "")} onClick={go}
      aria-label={`Colour theme: ${LABEL[t][1]}. Click to change.`} title="Switch light / dark / auto">
      <span aria-hidden>{LABEL[t][0]}</span> {LABEL[t][1]}
    </button>
  );
}
