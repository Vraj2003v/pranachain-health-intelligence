import { fmt } from "../api";

const POS = { above: ["Above", "out"], below: ["Below", "out"], within: ["Within", "in"], "no range": ["Own baseline only", "none"], "no data": ["Not enough data", "none"] };

// All of one area's own measures together: latest value, usual range, and whether a finding involves it.
export default function Overview({ ov }) {
  if (!ov || ov.rows.length === 0) return null;
  return (
    <section className="overview" aria-label="All measures in this area">
      <p className="ovtext"><b>All measures in this area.</b> {ov.text}</p>
      <div className="ovwrap">
        <table className="ovtable">
          <thead><tr><th>Measure</th><th>Latest</th><th>Usual range</th><th>Position</th><th>Changed</th></tr></thead>
          <tbody>{ov.rows.map((r) => {
            const [label, cls] = POS[r.position] || POS["no data"];
            return (
              <tr key={r.key}>
                <th scope="row">{r.label}{r.context && <span className="ovctx" title="Listed for this disease at the kickoff. Shown for context; it does not create findings here."> also considered</span>}</th>
                <td>{r.value == null ? "—" : `${fmt(r.value, r.decimals)} ${r.unit}`}</td>
                <td>{r.range}</td>
                <td><span className={"chip tier " + cls}>{label}</span></td>
                <td>{r.changed ? "Yes, see finding" : "No"}</td>
              </tr>);
          })}</tbody>
        </table>
      </div>
    </section>);
}
