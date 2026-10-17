import { fmt } from "../api";

export default function Coverage({ d }) {
  return (
    <section>
      <div className="tablewrap"><table>
        <thead><tr><th>Signal</th><th>Source sheet</th><th>Days with data</th><th>Earlier {d.windowDays} days</th><th>Recent {d.windowDays} days</th><th>Change</th><th>Result</th><th>Data flag</th></tr></thead>
        <tbody>{d.coverage.map((r) => (
          <tr key={r.signal}><td><b>{r.signal}</b></td><td>{r.sheet}</td><td>{Math.round((r.coverage ?? 0) * 100)}%</td><td>{r.nFirst}</td><td>{r.nLast}</td>
            <td>{r.change == null ? "—" : `${r.change > 0 ? "+" : ""}${fmt(r.change, r.decimals)} ${r.unit}`}</td>
            <td>{r.direction[0].toUpperCase() + r.direction.slice(1)}</td>
            <td><span className={"chip " + (r.flag === "Sufficient" ? "ok" : r.flag === "Limited" ? "warn" : "quiet")}>{r.flag}</span></td></tr>))}</tbody>
      </table></div>
      <p className="muted small">Data flag: Sufficient = at least 85% of days and 72 of the first and last 90 days; Limited = at least 60% and 45 days, shown with a badge; Insufficient = not reported as an insight. The flag describes how much data was available, not how certain the model is. Thresholds are placeholders pending calibration on real patients.</p>
    </section>
  );
}
