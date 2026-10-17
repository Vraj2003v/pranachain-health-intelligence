const j = async (r) => {
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || `Request failed (${r.status})`);
  return r.json();
};

export const api = {
  newSession: () => fetch("/api/session", { method: "POST" }).then(j),
  demo: (sid) => fetch(`/api/session/${sid}/demo`, { method: "POST" }).then(j),
  upload: (sid, files) => {
    const fd = new FormData();
    files.forEach((f) => fd.append("files", f));
    return fetch(`/api/session/${sid}/upload`, { method: "POST", body: fd }).then(j);
  },
  clear: (sid) => fetch(`/api/session/${sid}`, { method: "DELETE" }).then(j),
  patients: (sid) => fetch(`/api/session/${sid}/patients`).then(j),
  patient: (sid, key) => fetch(`/api/session/${sid}/patients/${encodeURIComponent(key)}`).then(j),
  explain: (sid, i, key) => fetch(`/api/session/${sid}/explain/${i}/${encodeURIComponent(key)}`, { method: "POST" }).then(j),
  health: () => fetch("/api/health").then(j),
};

export const fmt = (v, d = 1) => (v == null ? "—" : Number(v).toLocaleString(undefined, { minimumFractionDigits: d, maximumFractionDigits: d }));
export const shortDate = (s) => new Date(s + "T00:00:00").toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
