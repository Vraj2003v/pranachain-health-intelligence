import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import { applySize, applyTheme, getSize, getTheme } from "./theme.js";
import "./styles.css";

applyTheme(getTheme());
applySize(getSize());
createRoot(document.getElementById("root")).render(<App />);

// Light follows the pointer: the glass edge highlight and the colour field react to it.
if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
  let raf = 0;
  window.addEventListener("pointermove", (e) => {
    if (raf) return;
    raf = requestAnimationFrame(() => {
      raf = 0;
      const x = (e.clientX / window.innerWidth - 0.5) * 2, y = (e.clientY / window.innerHeight - 0.5) * 2;
      const r = document.documentElement.style;
      r.setProperty("--px", x.toFixed(3)); r.setProperty("--py", y.toFixed(3));
      r.setProperty("--pa", `${Math.round((Math.atan2(y, x) * 180) / Math.PI + 135)}deg`);
    });
  }, { passive: true });
}
