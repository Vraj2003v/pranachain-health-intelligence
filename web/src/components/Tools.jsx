import { useState } from "react";
import { applySize, getSize, nextSize } from "../theme.js";
import Guide from "./Guide.jsx";
import ThemeToggle from "./ThemeToggle.jsx";

const SIZE = { normal: "A", large: "A+", xlarge: "A++" };

// Small symbol buttons: colour theme, text size and the plain-language guide.
export default function Tools() {
  const [size, setSize] = useState(getSize());
  const [guide, setGuide] = useState(false);
  return (
    <span className="tools">
      <button type="button" className="themebtn" onClick={() => { const n = nextSize(size); applySize(n); setSize(n); }}
        aria-label={`Text size: ${SIZE[size]}. Click to change.`} title="Text size"><b>{SIZE[size]}</b></button>
      <button type="button" className="themebtn" onClick={() => setGuide(true)} aria-label="Open plain-language guide" title="What do these words mean?"><b>?</b></button>
      <ThemeToggle />
      {guide && <Guide onClose={() => setGuide(false)} />}
    </span>
  );
}
