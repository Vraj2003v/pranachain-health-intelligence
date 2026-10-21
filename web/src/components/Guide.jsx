import { useEffect } from "react";
import { createPortal } from "react-dom";

const TERMS = [
  ["Baseline", "Your own usual level. We average your first 90 days and compare later readings with that, never with other people."],
  ["Weekly average", "The average of the readings in a week. It smooths out normal ups and downs so the trend is easier to see."],
  ["Usual day-to-day variation", "How much your readings normally bounce around. A change is only highlighted when it is clearly bigger than that."],
  ["Projection", "The trend carried forward 8 weeks in a straight line, with a shaded range. It shows what could happen if nothing changes. It is not a prediction."],
  ["95% range", "The shaded band around the projection. Real readings would usually land inside it."],
  ["Data: sufficient / limited", "Sufficient means most days have readings. Limited means some days are missing, so a finding could be less reliable."],
  ["HbA1c", "A blood test that reflects average blood sugar over about three months."],
  ["HRV", "Heart-rate variability: the small changes in time between heartbeats."],
  ["Changes found / No clear change", "Whether anything moved clearly beyond your own usual range. It is not a diagnosis."],
];

export default function Guide({ onClose }) {
  useEffect(() => {
    const k = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, [onClose]);
  // Rendered on <body>: the glass sidebar would otherwise trap a fixed-position dialog inside itself.
  return createPortal(
    <div className="scrim" onClick={onClose}>
      <section className="guide" role="dialog" aria-label="Plain-language guide" onClick={(e) => e.stopPropagation()}>
        <div className="askhead"><h2>Plain-language guide</h2>
          <button className="iconbtn" onClick={onClose} aria-label="Close guide" title="Close">✕</button></div>
        <p className="muted small">PranaPulse highlights patterns that may be worth discussing with a healthcare provider. It does not diagnose or give medical advice.</p>
        <dl>{TERMS.map(([t, d]) => <div key={t}><dt>{t}</dt><dd>{d}</dd></div>)}</dl>
      </section>
    </div>,
    document.body
  );
}
