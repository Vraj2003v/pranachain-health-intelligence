const j = async (r) => {
  if (!r.ok) {
    const e = new Error((await r.json().catch(() => ({}))).detail || `Request failed (${r.status})`);
    e.status = r.status;
    throw e;
  }
  return r.json();
};
const post = (url, body) => fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }).then(j);

export const api = {
  me: () => fetch("/api/auth/me").then(j),
  register: (b) => post("/api/auth/register", b),
  login: (b) => post("/api/auth/login", b),
  logout: () => fetch("/api/auth/logout", { method: "POST" }).then(j),
  deleteAccount: () => fetch("/api/auth/account", { method: "DELETE" }).then(j),
  documents: () => fetch("/api/documents").then(j),
  upload: (files) => {
    const fd = new FormData();
    files.forEach((f) => fd.append("files", f));
    return fetch("/api/documents", { method: "POST", body: fd }).then(j);
  },
  demo: () => fetch("/api/documents/demo", { method: "POST" }).then(j),
  remove: (id) => fetch(`/api/documents/${id}`, { method: "DELETE" }).then(j),
  removeAll: () => fetch("/api/documents", { method: "DELETE" }).then(j),
  detail: (id) => fetch(`/api/documents/${id}/detail`).then(j),
  explain: (i, id) => fetch(`/api/documents/${id}/explain/${i}`, { method: "POST" }).then(j),
  audit: () => fetch("/api/audit").then(j),
  health: () => fetch("/api/health").then(j),
};

export const fmt = (v, d = 1) => (v == null ? "—" : Number(v).toLocaleString(undefined, { minimumFractionDigits: d, maximumFractionDigits: d }));
export const shortDate = (s) => new Date(s + "T00:00:00").toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
export const stamp = (s) => new Date(s.replace(" ", "T") + "Z").toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
export const kb = (n) => (n < 1024 * 1024 ? `${Math.max(1, Math.round(n / 1024))} KB` : `${(n / 1024 / 1024).toFixed(1)} MB`);
