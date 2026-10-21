import { useState } from "react";
import Guide from "./Guide.jsx";
import ThemeToggle from "./ThemeToggle.jsx";


// Small symbol buttons: colour theme, text size and the plain-language guide.
export default function Tools() {
  const [guide, setGuide] = useState(false);
  return (
    <span className="tools">
      <button type="button" className="themebtn" onClick={() => setGuide(true)} aria-label="Open plain-language guide" title="What do these words mean?"><b>?</b></button>
      <ThemeToggle />
      {guide && <Guide onClose={() => setGuide(false)} />}
    </span>
  );
}
