// One line per skipped file, with the reason in plain words. Files that were already uploaded are counted, not listed.
export function groupSkipped(failed) {
  const dup = [], other = [];
  for (const [file, why] of Object.entries(failed || {})) {
    if (/already uploaded|nothing was added twice/i.test(why)) dup.push(file);
    else other.push([file, why]);
  }
  return { dup, other };
}

export default function Skipped({ failed, onClose }) {
  const { dup, other } = groupSkipped(failed);
  if (dup.length === 0 && other.length === 0) return null;
  return (
    <div className="banner err" role="status" onClick={onClose}>
      <b>{other.length + dup.length} file{other.length + dup.length === 1 ? " was" : "s were"} not added</b>{onClose ? " (click to close)" : ""}
      {dup.length > 0 && <p className="small">{dup.length} already in the record, so nothing was added twice.</p>}
      {other.length > 0 && <ul className="notes">{other.map(([f, w]) => <li key={f}><b>{f}</b>: {w}</li>)}</ul>}
    </div>);
}
