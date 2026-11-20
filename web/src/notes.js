// Many reports repeat the same note ("Ferritin not recognised" in every file). Show one line per kind, with a count.
export function summariseNotes(notes) {
  const left = new Map(), blank = new Map(), other = [];
  for (const n of notes) {
    let m = n.match(/^(.*?): not recognised and left out: (.+)$/);
    if (m) { const k = m[2]; left.set(k, (left.get(k) || new Set()).add(m[1])); continue; }
    m = n.match(/^(.*?): (.+) is blank in the report$/);
    if (m) { const k = m[2]; blank.set(k, (blank.get(k) || new Set()).add(m[1])); continue; }
    other.push(n);
  }
  const list = (map) => [...map].sort((a, b) => b[1].size - a[1].size).map(([k, s]) => `${k} (${s.size})`).join(", ");
  const lines = [];
  if (left.size) lines.push(`Left out, name or unit not recognised (number of reports): ${list(left)}`);
  if (blank.size) lines.push(`Blank results (number of reports): ${list(blank)}`);
  lines.push(...other.slice(0, 5));
  if (other.length > 5) lines.push(`and ${other.length - 5} more notes`);
  return lines;
}
