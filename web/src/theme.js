// Light / dark / automatic. The choice is remembered in this browser only.
const KEY = "pranapulse.theme";
const read = () => { try { return localStorage.getItem(KEY); } catch { return null; } };
export const getTheme = () => (read() === "light" || read() === "dark" ? read() : "auto");
export const applyTheme = (t) => {
  const el = document.documentElement;
  if (t === "light" || t === "dark") el.setAttribute("data-theme", t); else el.removeAttribute("data-theme");
  try { if (t === "auto") localStorage.removeItem(KEY); else localStorage.setItem(KEY, t); } catch { /* storage may be blocked */ }
};
export const nextTheme = (t) => ({ auto: "light", light: "dark", dark: "auto" }[t]);

// Text size: 100% / 112% / 125%, remembered in this browser only.
const SKEY = "pranapulse.size";
export const getSize = () => { try { return localStorage.getItem(SKEY) || "normal"; } catch { return "normal"; } };
export const applySize = (z) => {
  const el = document.documentElement;
  if (z === "normal") el.removeAttribute("data-size"); else el.setAttribute("data-size", z);
  try { localStorage.setItem(SKEY, z); } catch { /* storage may be blocked */ }
};
export const nextSize = (z) => ({ normal: "large", large: "xlarge", xlarge: "normal" }[z]);
