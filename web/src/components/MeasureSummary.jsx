import { fmt } from "../api";

const tierClass = (t) => (t.startsWith("Outside") ? "out" : t.startsWith("Within") ? "in" : "none");
const rangeLine = (t) => (t.position === "no range" ? "Compared with your own baseline only"
  : t.position === "within" ? `Within the usual range (${t.range})` : `${t.position === "above" ? "Above" : "Below"} the usual range (${t.range})`);

function Finding({ ins }) {
  return (
    <div className="finding">
      <h3>{ins.title}</h3>
      {ins.tier && <p className="tierline"><span className={"chip tier " + tierClass(ins.tier)}>{ins.tier}</span></p>}
      {ins.tiles.length > 0 && (
        <div className="tiles">{ins.tiles.map((t) => (
          <div className="tile" key={t.label}><div className="l">{t.label}</div>
            <div className="v">{Number(t.value).toLocaleString(undefined, { maximumFractionDigits: t.decimals })} <span className="u">{t.unit}</span></div>
            <div className="d">{t.diff > 0 ? "up" : "down"} {Math.abs(t.diff).toLocaleString(undefined, { maximumFractionDigits: t.decimals })} compared with your first 90 days</div>
            <div className={"rng " + (t.position === "within" ? "in" : t.position === "no range" ? "none" : "out")}>{rangeLine(t)}</div></div>))}
        </div>)}
      <ul>{ins.bullets.map((b) => <li key={b}>{b}</li>)}</ul>
      {ins.context.length > 0 && <p className="ctx"><b>Connects to your history:</b> {ins.context.slice(0, 3).map((c) => c.split(" — ")[0]).join(" · ")}</p>}
      <p className="muted small">Data: {ins.flag === "Limited" ? "limited, some readings were missing" : "sufficient"}.</p>
    </div>);
}

// Shown when the selected measure has no finding of its own: its numbers, plainly.
function Quiet({ s, cov }) {
  const w = s.windows, dec = s.decimals;
  if (!w || w.meanFirst == null || w.meanLast == null)
    return (
      <div className="finding">
        <h3>{s.label}: not enough readings to compare</h3>
        <p className="muted">There are too few {s.label.toLowerCase()} readings in the first or last 90 days to compare them.</p>
      </div>);
  const diff = w.meanLast - w.meanFirst, r = s.range;
  const pos = !r ? "no range" : r.high != null && w.meanLast > r.high ? "above" : r.low != null && w.meanLast < r.low ? "below" : "within";
  const flat = Math.abs(diff) < Math.pow(10, -dec) / 2;
  return (
    <div className="finding">
      <h3>{s.label}: no clear change</h3>
      <div className="tiles">
        <div className="tile"><div className="l">{s.label}</div>
          <div className="v">{fmt(w.meanLast, dec)} <span className="u">{s.unit}</span></div>
          <div className="d">{flat ? "the same as" : (diff > 0 ? "up " : "down ") + fmt(Math.abs(diff), dec) + " compared with"} your first 90 days</div>
          <div className={"rng " + (pos === "within" ? "in" : pos === "no range" ? "none" : "out")}>
            {rangeLine({ position: pos, range: r?.text })}</div></div>
      </div>
      <ul>
        <li>{s.label} averaged {fmt(w.meanFirst, dec)} {s.unit} in your first 90 days and {fmt(w.meanLast, dec)} {s.unit} in your last 90 days.</li>
        <li>This difference is small next to your usual day-to-day variation, so it is not shown as a finding.</li>
        {(pos === "above" || pos === "below") && <li>The last 90 days sit {pos} the usual range. A value that stays steady outside the range is not shown as a finding, because findings look at change. You can raise it with a healthcare provider.</li>}
      </ul>
      <p className="muted small">Data: {cov?.flag === "Limited" ? "limited, some readings were missing" : cov?.flag === "Insufficient" ? "insufficient" : "sufficient"}.</p>
    </div>);
}

// The summary follows the measure picked on the chart tabs.
export default function MeasureSummary({ d, area, sel }) {
  const inArea = d.insights.filter((i) => i.scenario === area.scenario);
  const mine = inArea.filter((i) => i.signals.includes(sel));
  const others = inArea.filter((i) => !i.signals.includes(sel));
  const s = d.series[sel];
  const cov = s && d.coverage.find((c) => c.signal === s.label);
  const label = (i) => (i.signals.map((k) => d.series[k]?.label).filter(Boolean).join(", ") || i.title);
  return (
    <div aria-live="polite">
      {s && (mine.length ? mine.map((i) => <Finding key={i.id} ins={i} />) : <Quiet s={s} cov={cov} />)}
      {others.length > 0 && s && <p className="muted small">Also found in this area: {others.map(label).join("; ")}. Pick that measure below to see it.</p>}
      {/* findings that do not belong to any chart tab (for example lab results) always stay visible */}
      {!s && inArea.map((i) => <Finding key={i.id} ins={i} />)}
    </div>);
}
