"""PranaPulse API: sign in, store patient workbooks in a database, get explainable insights as JSON.
Serves the React app from web/dist.

Run with:  uvicorn api.main:app --port 8000
"""
import hashlib
import io
import json
import math
from functools import lru_cache
from pathlib import Path

import pandas as pd
from fastapi import Depends, FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from pranapulse import ask as ask_mod, forecast, llm
from pranapulse.demo_data import all_demo_workbooks
from pranapulse.detect import detect
from pranapulse.loader import load_patient
from pranapulse.signals import SIGNALS, WINDOW_DAYS

from . import auth
from .db import db, init

app = FastAPI(title="PranaPulse API")
DIST = Path(__file__).resolve().parent.parent / "web" / "dist"
MAX_FILE = 5 * 1024 * 1024
init()


def num(x):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(x) or math.isinf(x) else round(x, 4)


def day(ts):
    return None if ts is None or pd.isna(ts) else pd.Timestamp(ts).strftime("%Y-%m-%d")


# ------------------------------------------------------------------ accounts
class Register(BaseModel):
    name: str
    email: str
    password: str
    confirm: bool = False


class Login(BaseModel):
    email: str
    password: str


def public(u):
    return {"id": u["id"], "name": u["name"], "email": u["email"], "role": u["role"]}


@app.post("/api/auth/register")
def register(body: Register, request: Request, response: Response):
    email = body.email.strip().lower()
    if not auth.EMAIL.match(email):
        raise HTTPException(400, "Enter a valid email address.")
    if len(body.password) < 8:
        raise HTTPException(400, "Use a password of at least 8 characters.")
    if not body.name.strip():
        raise HTTPException(400, "Enter your name.")
    if not body.confirm:
        raise HTTPException(400, "Please confirm that you will only use synthetic or anonymised data.")
    pw_hash, salt = auth.hash_password(body.password)
    with db() as con:
        if con.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
            raise HTTPException(409, "An account with this email already exists.")
        first = con.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0
        cur = con.execute("INSERT INTO users(email, name, role, pw_hash, salt, consent_at) VALUES (?,?,?,?,?,datetime('now'))",
                          (email, body.name.strip(), "admin" if first else "clinician", pw_hash, salt))
        user = {"id": cur.lastrowid, "name": body.name.strip(), "email": email, "role": "admin" if first else "clinician"}
    auth.start_session(response, request, user["id"])
    auth.log(user, "register", f"role={user['role']}")
    return public(user)


@app.post("/api/auth/login")
def login(body: Login, request: Request, response: Response):
    email = body.email.strip().lower()
    if auth.throttled(email):
        raise HTTPException(429, "Too many failed attempts. Try again in 15 minutes.")
    with db() as con:
        row = con.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if not row or not auth.verify_password(body.password, row["pw_hash"], row["salt"]):
        auth.note_failure(email)
        auth.log(None, "login_failed", email)
        raise HTTPException(401, "Email or password is incorrect.")
    auth.clear_failures(email)
    auth.start_session(response, request, row["id"])
    user = {"id": row["id"], "name": row["name"], "email": row["email"], "role": row["role"]}
    auth.log(user, "login")
    return public(user)


@app.post("/api/auth/logout")
def logout(request: Request, response: Response):
    auth.end_session(response, request)
    return {"ok": True}


@app.get("/api/auth/me")
def me(user=Depends(auth.current_user)):
    return public(user)


@app.delete("/api/auth/account")
def delete_account(request: Request, response: Response, user=Depends(auth.current_user)):
    auth.log(user, "account_deleted")
    with db() as con:
        con.execute("DELETE FROM users WHERE id = ?", (user["id"],))
    auth.end_session(response, request)
    return {"ok": True}


@app.get("/api/audit")
def audit(user=Depends(auth.current_user)):
    if user["role"] != "admin":
        raise HTTPException(403, "Only an administrator can view the audit log.")
    with db() as con:
        rows = con.execute("SELECT at, email, action, detail FROM audit ORDER BY id DESC LIMIT 200").fetchall()
    return [dict(r) for r in rows]


@app.get("/api/health")
def health():
    return {"ok": True, "llm": llm.available()}


# ------------------------------------------------------------------ documents (stored workbooks)
@lru_cache(maxsize=64)
def analysed(doc_id: int, sha: str):
    with db() as con:
        blob = con.execute("SELECT blob FROM documents WHERE id = ?", (doc_id,)).fetchone()["blob"]
    p = load_patient(io.BytesIO(blob))
    return (p, *detect(p))


def store(user, filename, data, is_demo=0):
    """Validate, analyse and save one workbook. Returns (document id, None) or (None, reason)."""
    if len(data) > MAX_FILE:
        return None, "file is larger than 5 MB"
    sha = hashlib.sha256(data).hexdigest()
    with db() as con:
        if con.execute("SELECT 1 FROM documents WHERE user_id = ? AND sha256 = ?", (user["id"], sha)).fetchone():
            return None, "already uploaded"
    try:
        p = load_patient(io.BytesIO(data))
        ins, held, _ = detect(p)
    except Exception as exc:   # a workbook that does not match the layout
        return None, str(exc)[:160]
    top = ins[0] if ins else None
    with db() as con:
        cur = con.execute("INSERT INTO documents(user_id, filename, sha256, size, blob, is_demo) VALUES (?,?,?,?,?,?)",
                          (user["id"], filename[:200], sha, len(data), data, is_demo))
        con.execute("INSERT INTO results VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (cur.lastrowid, p.patient_id, num(p.profile.get("Age")), p.profile.get("Sex"),
                     "Flagged" if top else "Quiet", top.title if top else "Nothing beyond usual variation",
                     top.flag if top else None, top.scenario if top else None, json.dumps([i.kind for i in ins]),
                     len(held), len(ins)))
    return cur.lastrowid, None


@app.get("/api/documents")
def documents(user=Depends(auth.current_user)):
    with db() as con:
        rows = con.execute(
            "SELECT d.id, d.filename, d.size, d.uploaded_at, d.is_demo, r.* FROM documents d JOIN results r ON r.document_id = d.id "
            "WHERE d.user_id = ? ORDER BY d.id", (user["id"],)).fetchall()
    return [{"key": str(r["id"]), "id": r["patient_id"], "filename": r["filename"], "size": r["size"], "uploaded": r["uploaded_at"],
             "demo": bool(r["is_demo"]), "age": r["age"], "sex": r["sex"], "status": r["status"], "found": r["found"],
             "flag": r["flag"], "scenario": r["scenario"], "held": r["held"], "insights": r["insights"]} for r in rows]


@app.post("/api/documents")
async def upload(files: list[UploadFile] = File(...), user=Depends(auth.current_user)):
    added, failed = 0, {}
    for f in files:
        _, why = store(user, f.filename or "workbook.xlsx", await f.read())
        if why:
            failed[f.filename] = why
        else:
            added += 1
    auth.log(user, "upload", f"{added} added, {len(failed)} skipped")
    return {"added": added, "failed": failed}


@app.post("/api/documents/demo")
def load_demo(user=Depends(auth.current_user)):
    with db() as con:
        if con.execute("SELECT 1 FROM documents WHERE user_id = ? AND is_demo = 1", (user["id"],)).fetchone():
            return {"added": 0}
    added = sum(1 for name, data in all_demo_workbooks().items() if store(user, f"{name}.xlsx", data, 1)[0])
    auth.log(user, "load_demo", f"{added} added")
    return {"added": added}


def owned(doc_id: int, user):
    with db() as con:
        row = con.execute("SELECT id, filename, sha256 FROM documents WHERE id = ? AND user_id = ?", (doc_id, user["id"])).fetchone()
    if not row:
        raise HTTPException(404, "Document not found")
    return row


@app.delete("/api/documents/{doc_id}")
def delete_document(doc_id: int, user=Depends(auth.current_user)):
    row = owned(doc_id, user)
    with db() as con:
        con.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    auth.log(user, "delete_document", row["filename"])
    return {"ok": True}


@app.delete("/api/documents")
def delete_all(user=Depends(auth.current_user)):
    with db() as con:
        n = con.execute("DELETE FROM documents WHERE user_id = ?", (user["id"],)).rowcount
    auth.log(user, "delete_all_documents", f"{n} removed")
    return {"removed": n}


@app.get("/api/documents/{doc_id}/file")
def download(doc_id: int, user=Depends(auth.current_user)):
    row = owned(doc_id, user)
    with db() as con:
        blob = con.execute("SELECT blob FROM documents WHERE id = ?", (doc_id,)).fetchone()["blob"]
    auth.log(user, "download_document", row["filename"])
    return Response(blob, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f'attachment; filename="{row["filename"]}"'})


def series_block(p, results, key):
    sig = SIGNALS[key]
    s = p.daily[sig.column]
    wk = forecast.weekly_means(s)
    rows = {}
    for d, v in s.items():
        rows[day(d)] = {"d": day(d), "v": num(v)}
    for d, v in wk.items():
        rows.setdefault(day(d), {"d": day(d)})["w"] = num(v)
    proj = forecast.project(s)
    if proj is not None:
        for r in proj.itertuples():
            rows[day(r.date)] = {"d": day(r.date), "p": num(r.mean), "band": [num(r.low), num(r.high)]}
        last = wk.index[-1]
        rows.setdefault(day(last), {"d": day(last)})["p"] = num(wk.iloc[-1])
    r = results.get(key)
    out = {"key": key, "label": sig.label, "unit": sig.unit, "decimals": sig.decimals,
           "rows": sorted(rows.values(), key=lambda x: x["d"]), "hasProjection": proj is not None}
    if r is not None:
        out["windows"] = {"first": [day(r.window_first[0]), day(r.window_first[1])], "last": [day(r.window_last[0]), day(r.window_last[1])],
                          "meanFirst": num(r.mean_first), "meanLast": num(r.mean_last)}
    return out


@app.get("/api/documents/{doc_id}/detail")
def patient_detail(doc_id: int, user=Depends(auth.current_user)):
    row = owned(doc_id, user)
    p, ins, held, results = analysed(doc_id, row["sha256"])
    auth.log(user, "view_patient", p.patient_id)
    start, end = p.window
    marks = [{"date": day(r.date), "text": str(r.event)} for r in p.history.itertuples()]
    marks += [{"date": day(r.start), "text": f"{r.medication} started"} for r in p.meds.itertuples() if pd.notna(r.start)]
    for m in marks:
        m["before"] = m["date"] < day(start)
    labs = {}
    for t in sorted(p.labs.test.unique()):
        rows = p.labs[p.labs.test == t]
        labs[t] = {"unit": str(rows.unit.iloc[0]), "refLow": num(rows.ref_low.iloc[0]), "refHigh": num(rows.ref_high.iloc[0]),
                   "points": [{"d": day(r.date), "v": num(r.result)} for r in rows.itertuples()]}
    coverage = [{"signal": r.label, "sheet": r.sheet, "coverage": num(r.coverage), "nFirst": r.n_first, "nLast": r.n_last,
                 "change": num(r.diff), "unit": r.unit, "decimals": r.decimals, "direction": r.direction, "flag": r.flag}
                for r in results.values()]
    positives = [f"{r.label} moved from {r.mean_first:,.{r.decimals}f} to {r.mean_last:,.{r.decimals}f} {r.unit}"
                 for r in results.values() if r.direction == "improving" and r.flag != "Insufficient"]
    tiles = lambda i: [{"label": results[k].label, "value": num(results[k].mean_last), "diff": num(results[k].diff),
                        "unit": results[k].unit, "decimals": results[k].decimals} for k in i.signals if k in results]
    return {
        "patient": {"id": p.patient_id, "age": num(p.profile.get("Age")), "sex": p.profile.get("Sex"), "start": day(start),
                    "end": day(end), "days": len(p.daily)},
        "insights": [{"kind": i.kind, "title": i.title, "flag": i.flag, "scenario": i.scenario, "summary": i.summary,
                      "bullets": i.bullets, "closing": i.closing, "context": i.context, "asks": i.asks,
                      "evidence": [{k: (v if isinstance(v, str) else num(v)) for k, v in e.items()} for e in i.evidence],
                      "forecastKey": i.forecast_key, "signals": i.signals, "tiles": tiles(i)} for i in ins],
        "held": held, "positives": positives, "coverage": coverage, "windowDays": WINDOW_DAYS,
        "series": {k: series_block(p, results, k) for k in SIGNALS}, "markers": marks, "labs": labs,
        "cycles": [{"d": day(r.start), "v": num(r.cycle_length)} for r in p.cycles.itertuples()],
    }


@app.post("/api/documents/{doc_id}/explain/{index}")
def explain(doc_id: int, index: int, user=Depends(auth.current_user)):
    row = owned(doc_id, user)
    ins = analysed(doc_id, row["sha256"])[1]
    if index >= len(ins):
        raise HTTPException(404, "Unknown insight")
    if not llm.available():
        return {"text": ins[index].summary, "source": "template", "note": "Local model not running."}
    text, source = llm.explain(ins[index])
    auth.log(user, "explain_local_model", row["filename"])
    return {"text": text, "source": source}


class Ask(BaseModel):
    question: str
    area: str | None = None


@app.get("/api/ask/suggestions")
def suggestions(user=Depends(auth.current_user)):
    return {"questions": ask_mod.SUGGESTED}


@app.post("/api/documents/{doc_id}/ask")
def ask(doc_id: int, body: Ask, user=Depends(auth.current_user)):
    row = owned(doc_id, user)
    q = body.question.strip()[:300]
    if not q:
        raise HTTPException(400, "Type a question first.")
    text, source = ask_mod.answer(q, analysed(doc_id, row["sha256"])[1], body.area)
    auth.log(user, "ask_question", row["filename"])
    return {"text": text, "source": source}


if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        f = DIST / path
        return FileResponse(f if path and f.is_file() else DIST / "index.html")
