"""PranaPulse API: upload patient workbooks, get explainable insights as JSON. Serves the React app from web/dist.

Run with:  uvicorn api.main:app --port 8000
"""
import io
import math
import uuid
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from pranapulse import forecast, llm
from pranapulse.demo_data import all_demo_workbooks
from pranapulse.detect import detect
from pranapulse.loader import load_patient
from pranapulse.signals import SIGNALS, WINDOW_DAYS

app = FastAPI(title="PranaPulse API")
SESSIONS: dict[str, dict] = {}   # session id -> {patient key -> (patient, insights, held, results)}
DIST = Path(__file__).resolve().parent.parent / "web" / "dist"


def num(x):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(x) or math.isinf(x) else round(x, 4)


def day(ts):
    return None if ts is None or pd.isna(ts) else pd.Timestamp(ts).strftime("%Y-%m-%d")


def session(sid):
    if sid not in SESSIONS:
        raise HTTPException(404, "Unknown session; reload the page.")
    return SESSIONS[sid]


def add(sess, name, data):
    p = load_patient(io.BytesIO(data))
    key = p.patient_id if p.patient_id not in sess else f"{p.patient_id} ({name})"
    sess[key] = (p, *detect(p))
    return key


def summary(key, entry):
    p, ins, held, _ = entry
    top = ins[0] if ins else None
    return {"key": key, "id": p.patient_id, "age": num(p.profile.get("Age")), "sex": p.profile.get("Sex"),
            "status": "Flagged" if top else "Quiet", "found": top.title if top else "Nothing beyond usual variation",
            "flag": top.flag if top else None, "scenario": top.scenario if top else None,
            "kinds": [i.kind for i in ins], "held": len(held), "insights": len(ins)}


@app.get("/api/health")
def health():
    return {"ok": True, "llm": llm.available()}


@app.post("/api/session")
def new_session():
    sid = uuid.uuid4().hex[:12]
    SESSIONS[sid] = {}
    return {"session": sid}


@app.post("/api/session/{sid}/demo")
def load_demo(sid: str):
    sess = session(sid)
    for name, data in all_demo_workbooks().items():
        add(sess, name, data)
    return {"patients": len(sess)}


@app.post("/api/session/{sid}/upload")
async def upload(sid: str, files: list[UploadFile] = File(...)):
    sess = session(sid)
    failed = {}
    for f in files:
        try:
            add(sess, f.filename, await f.read())
        except Exception as exc:   # a workbook that does not match the layout
            failed[f.filename] = str(exc)[:160]
    return {"patients": len(sess), "failed": failed}


@app.delete("/api/session/{sid}")
def clear(sid: str):
    SESSIONS[sid] = {}
    return {"patients": 0}


@app.get("/api/session/{sid}/patients")
def patients(sid: str):
    return [summary(k, v) for k, v in session(sid).items()]


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


@app.get("/api/session/{sid}/patients/{key:path}")
def patient_detail(sid: str, key: str):
    sess = session(sid)
    if key not in sess:
        raise HTTPException(404, "Unknown patient")
    p, ins, held, results = sess[key]
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


@app.post("/api/session/{sid}/explain/{index}/{key:path}")
def explain(sid: str, index: int, key: str):
    sess = session(sid)
    if key not in sess or index >= len(sess[key][1]):
        raise HTTPException(404, "Unknown insight")
    if not llm.available():
        return {"text": sess[key][1][index].summary, "source": "template", "note": "Local model not running."}
    text, source = llm.explain(sess[key][1][index])
    return {"text": text, "source": source}


if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        f = DIST / path
        return FileResponse(f if path and f.is_file() else DIST / "index.html")
