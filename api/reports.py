"""Lab reports uploaded ONE document at a time.

Each report (PDF, CSV or XLSX) is read, its values are stored in the database, and the findings for a
person are rebuilt from the stored values - never from the uploaded file. A second report for the same
person adds to the history; an exact repeat is not counted twice.
"""
import hashlib
import math

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from pranapulse.detect import detect
from pranapulse.loader import Patient
from pranapulse.readings import MEASURES, VITALS, WEARABLE, kind, parse_readings
from pranapulse.reports import ReportError, parse_report, quality

from . import auth
from .db import db

router = APIRouter()
SUFFIX = " (uploaded reports).xlsx"   # marks the workbook that is rebuilt from the stored lab results and daily readings
LEGACY_SUFFIX = " (lab reports).xlsx"  # the name used before daily readings could be uploaded


def built_patient(filename: str):
    """The patient ID when the document is a record rebuilt from uploaded reports, otherwise None."""
    for s in (SUFFIX, LEGACY_SUFFIX):
        if filename.endswith(s):
            return filename[:-len(s)]
    return None
MAX_FILE = 5 * 1024 * 1024
SAME = 1e-6


def _num(x):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(x) or math.isinf(x) else round(x, 4)


def is_workbook(filename: str, data: bytes) -> bool:
    """A full patient workbook has a 'Patient Profile' sheet; any other PDF, CSV or XLSX is treated as one lab report."""
    if not filename.lower().endswith((".xlsx", ".xlsm")):
        return False
    try:
        import io
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(data), read_only=True)
        return "Patient Profile" in wb.sheetnames
    except Exception:
        return True      # let the workbook loader report why the file cannot be read


def _store_lab(user, filename: str, data: bytes):
    """Read one lab report and add its values. Returns a plain-language result for the person uploading it."""
    if len(data) > MAX_FILE:
        return {"status": "rejected", "why": "file is larger than 5 MB"}
    sha = hashlib.sha256(data).hexdigest()
    with db() as con:
        if con.execute("SELECT 1 FROM lab_reports WHERE user_id = ? AND sha256 = ?", (user["id"], sha)).fetchone():
            return {"status": "duplicate", "why": "this exact file was already uploaded"}
    try:
        rep = parse_report(filename, data)
    except ReportError as exc:
        return {"status": "rejected", "why": str(exc)}
    added, same, conflicts, missing = 0, 0, [], []
    with db() as con:
        cur = con.execute(
            "INSERT INTO lab_reports(user_id, patient_id, collected, filename, sha256, size, age, sex) VALUES (?,?,?,?,?,?,?,?)",
            (user["id"], rep.patient_id, rep.collected, filename[:200], sha, len(data), rep.age, rep.sex))
        rid = cur.lastrowid
        for r in rep.rows:
            old = con.execute("SELECT id, value FROM lab_values WHERE user_id = ? AND patient_id = ? AND collected = ? AND test = ?",
                              (user["id"], rep.patient_id, rep.collected, r.test)).fetchone()
            if old is None:
                con.execute("INSERT INTO lab_values(report_id, user_id, patient_id, collected, test, value, unit, ref_low, ref_high, converted_from) "
                            "VALUES (?,?,?,?,?,?,?,?,?,?)",
                            (rid, user["id"], rep.patient_id, rep.collected, r.test, r.value, r.unit, r.ref_low, r.ref_high, r.converted_from))
                added += 1
                if r.value is None:
                    missing.append(r.test)
            elif old["value"] is None and r.value is not None:      # a later report fills a blank
                con.execute("UPDATE lab_values SET report_id=?, value=?, unit=?, ref_low=?, ref_high=?, converted_from=? WHERE id = ?",
                            (rid, r.value, r.unit, r.ref_low, r.ref_high, r.converted_from, old["id"]))
                added += 1
            elif r.value is None or abs(old["value"] - r.value) <= SAME + 0.006:   # converted values differ by rounding only
                same += 1
            else:
                conflicts.append(f"{r.test} on {rep.collected}: stored {old['value']:g}, this report says {r.value:g}. The stored value was kept.")
        con.execute("UPDATE lab_reports SET added = ? WHERE id = ?", (added, rid))
        if added == 0 and not conflicts:   # nothing new: do not keep a second copy of the same results
            con.execute("DELETE FROM lab_reports WHERE id = ?", (rid,))
            return {"status": "duplicate", "patient": rep.patient_id, "date": rep.collected,
                    "why": "the results for this person and date are already stored; nothing was added twice"}
    out = {"status": "added", "patient": rep.patient_id, "date": rep.collected, "added": added, "already_stored": same,
           "missing": missing, "conflicts": conflicts, "unrecognised": rep.unrecognised}
    if conflicts:
        out["status"] = "conflict" if added == 0 else "added"
    return out


def workbook_from_database(user, patient_id: str):
    """The stored lab results and daily readings of one person as an ordinary patient workbook, so every screen that reads
    workbooks (graphs, findings, chat, download) works on it. It is rebuilt from the database after every upload or removal;
    the database stays the source of truth."""
    import io
    p = patient_from_database(user, patient_id)
    if p is None:
        return None
    stamps = list(p.labs.date) + list(p.daily.index)
    days = pd.date_range(min(stamps), max(stamps))
    nan = float("nan")
    vit = pd.DataFrame({"Date": days, **{c: nan for c in ["Systolic BP", "Diastolic BP", "Resting HR", "Weight kg", "BMI", "SpO2 %", "Temp C", "Respiratory Rate"]}})
    wea = pd.DataFrame({"Date": days, **{c: nan for c in ["Steps", "Sleep Hours", "Active Minutes", "Resting HR", "HRV ms", "Calories kcal", "Sedentary Hours", "Stress Score 1-10"]}})
    for frame, cols in ((vit, VITALS), (wea, [c for c in WEARABLE])):
        for c in cols:
            if c in p.daily:
                frame[c] = frame["Date"].map(p.daily[c].dropna().to_dict())
    labs = pd.DataFrame({"Date": p.labs.date.dt.strftime("%Y-%m-%d"), "Test Name": p.labs.test, "Result": p.labs.result, "Unit": p.labs.unit,
                         "Reference Range": [_range_text(r.ref_low, r.ref_high) for r in p.labs.itertuples()]})
    empty = lambda cols: pd.DataFrame({c: [] for c in cols})
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as w:
        pd.DataFrame({"Field": ["Patient ID", "Age", "Sex"], "Value": [patient_id, p.profile.get("Age"), p.profile.get("Sex")]}).to_excel(w, sheet_name="Patient Profile", index=False)
        vit.to_excel(w, sheet_name="Vitals Daily", index=False)
        wea.to_excel(w, sheet_name="Wearable Daily", index=False)
        (labs if len(labs) else empty(["Date", "Test Name", "Result", "Unit", "Reference Range"])).to_excel(w, sheet_name="Lab Results", index=False)
        empty(["Date", "Encounter / Type", "Finding / Event", "Status", "Notes"]).to_excel(w, sheet_name="Medical History", index=False)
        empty(["Medication ID", "Medication", "Dose", "Frequency", "Route", "Start Date", "End Date", "Status", "Indication",
               "Tolerance / Adverse Effect", "Change Rationale"]).to_excel(w, sheet_name="Medication History", index=False)
        empty(["Cycle", "Start Date", "Cycle Length", "Bleeding Days", "Symptoms", "Severity"]).to_excel(w, sheet_name="Women Health", index=False)
    return out.getvalue()


def _range_text(lo, hi):
    lo, hi = _num(lo), _num(hi)
    if lo is not None and hi is not None:
        return f"{lo:g}–{hi:g}"
    if hi is not None:
        return f"<{hi:g}"
    if lo is not None:
        return f">{lo:g}"
    return ""


def sync_documents(user, patient_ids):
    """Keep one normal patient document per person who has uploaded reports, rebuilt from the database."""
    from .main import store            # late import: main imports this module
    for pid in set(patient_ids):
        with db() as con:
            for suffix in (SUFFIX, LEGACY_SUFFIX):
                con.execute("DELETE FROM documents WHERE user_id = ? AND filename = ?", (user["id"], pid + suffix))
        data = workbook_from_database(user, pid)
        if data is not None:
            store(user, pid + SUFFIX, data)


@router.post("/api/reports")
async def upload_reports(files: list[UploadFile] = File(...), user=Depends(auth.current_user)):
    results = {}
    for f in files:
        name = f.filename or "report"
        results[name] = store_report(user, name, await f.read())
    ok = sum(1 for r in results.values() if r["status"] == "added")
    sync_documents(user, [r["patient"] for r in results.values() if r["status"] == "added"])
    auth.log(user, "upload_reports", f"{ok} added of {len(files)}")
    return {"added": ok, "results": results}


def _patients(user):
    with db() as con:
        labs = {r["patient_id"]: dict(r) for r in con.execute(
            "SELECT patient_id, COUNT(DISTINCT collected) AS reports, MIN(collected) AS first, MAX(collected) AS last, "
            "COUNT(*) AS values_n FROM lab_values WHERE user_id = ? GROUP BY patient_id", (user["id"],))}
        daily = {r["patient_id"]: dict(r) for r in con.execute(
            "SELECT patient_id, COUNT(DISTINCT day) AS days, MIN(day) AS first, MAX(day) AS last "
            "FROM daily_values WHERE user_id = ? GROUP BY patient_id", (user["id"],))}
    out = []
    for pid in sorted(set(labs) | set(daily)):
        a, b = labs.get(pid), daily.get(pid)
        out.append({"patient_id": pid, "reports": a["reports"] if a else 0, "values_n": a["values_n"] if a else 0,
                    "days": b["days"] if b else 0,
                    "first": min(x["first"] for x in (a, b) if x), "last": max(x["last"] for x in (a, b) if x)})
    return out


@router.get("/api/reports")
def list_reports(user=Depends(auth.current_user)):
    with db() as con:
        files = [dict(r, kind="lab") for r in con.execute(
            "SELECT id, patient_id, collected, filename, size, added, uploaded_at FROM lab_reports WHERE user_id = ? ORDER BY collected, id", (user["id"],))]
        files += [dict(r, kind="readings") for r in con.execute(
            "SELECT id, patient_id, first_day || ' to ' || last_day AS collected, filename, size, added, uploaded_at FROM reading_files "
            "WHERE user_id = ? ORDER BY first_day, id", (user["id"],))]
    return {"patients": _patients(user), "reports": files}


@router.delete("/api/reports/{report_id}")
def delete_report(report_id: int, user=Depends(auth.current_user)):
    with db() as con:
        row = con.execute("SELECT filename FROM lab_reports WHERE id = ? AND user_id = ?", (report_id, user["id"])).fetchone()
        if not row:
            raise HTTPException(404, "Report not found")
        pid = con.execute("SELECT patient_id FROM lab_reports WHERE id = ?", (report_id,)).fetchone()["patient_id"]
        con.execute("DELETE FROM lab_reports WHERE id = ?", (report_id,))
    sync_documents(user, [pid])
    auth.log(user, "delete_report", row["filename"])
    return {"ok": True}


def patient_from_database(user, patient_id: str):
    """Rebuild one person from the stored values: lab history (blank results are left out) and daily readings."""
    with db() as con:
        vals = con.execute("SELECT collected, test, value, unit, ref_low, ref_high FROM lab_values "
                           "WHERE user_id = ? AND patient_id = ? AND value IS NOT NULL ORDER BY collected", (user["id"], patient_id)).fetchall()
        daily_rows = con.execute("SELECT day, measure, value FROM daily_values WHERE user_id = ? AND patient_id = ?", (user["id"], patient_id)).fetchall()
        meta = con.execute("SELECT age, sex FROM lab_reports WHERE user_id = ? AND patient_id = ? AND (age IS NOT NULL OR sex IS NOT NULL) "
                           "ORDER BY collected DESC LIMIT 1", (user["id"], patient_id)).fetchone() or \
            con.execute("SELECT age, sex FROM reading_files WHERE user_id = ? AND patient_id = ? AND (age IS NOT NULL OR sex IS NOT NULL) "
                        "ORDER BY id DESC LIMIT 1", (user["id"], patient_id)).fetchone()
    if not vals and not daily_rows:
        return None
    cols = ["date", "test", "result", "unit", "ref_low", "ref_high"]
    if vals:
        labs = pd.DataFrame([dict(v) for v in vals]).rename(columns={"collected": "date", "value": "result"})
        labs["date"] = pd.to_datetime(labs["date"])
        labs = labs[cols].sort_values("date")
    else:
        labs = pd.DataFrame({c: [] for c in cols})
        labs["date"] = pd.to_datetime(labs["date"])
    names = list(MEASURES)
    if daily_rows:
        d = pd.DataFrame([dict(r) for r in daily_rows])
        d["day"] = pd.to_datetime(d["day"])
        daily = d.pivot(index="day", columns="measure", values="value").reindex(columns=names).sort_index()
        daily.index.name = "Date"
    else:
        daily = pd.DataFrame(index=pd.DatetimeIndex([], name="Date"), columns=names, dtype=float)
    profile = {"Patient ID": patient_id, "Age": meta["age"] if meta else None, "Sex": meta["sex"] if meta else None}
    empty_hist = pd.DataFrame({"date": pd.to_datetime([]), "event": [], "status": []})
    empty_meds = pd.DataFrame({"medication": [], "indication": [], "start": pd.to_datetime([]), "end": pd.to_datetime([]), "status": []})
    empty_cyc = pd.DataFrame({"start": pd.to_datetime([]), "cycle_length": []})
    return Patient(patient_id, profile, daily, labs, empty_hist, empty_meds, empty_cyc)


@router.get("/api/patients/{patient_id}/from-reports")
def from_reports(patient_id: str, user=Depends(auth.current_user)):
    p = patient_from_database(user, patient_id)
    if p is None:
        raise HTTPException(404, "No reports are stored for this patient.")
    ins, held, _ = detect(p)
    with db() as con:
        reps = con.execute("SELECT collected, filename FROM lab_reports WHERE user_id = ? AND patient_id = ?", (user["id"], patient_id)).fetchall()
        allvals = [dict(v) for v in con.execute(
            "SELECT collected, test, value, unit, converted_from FROM lab_values WHERE user_id = ? AND patient_id = ?", (user["id"], patient_id))]
    history = {}
    for t in sorted(p.labs.test.unique()):
        rows = p.labs[p.labs.test == t]
        history[t] = {"unit": str(rows.unit.iloc[0]), "refLow": _num(rows.ref_low.iloc[0]), "refHigh": _num(rows.ref_high.iloc[0]),
                      "points": [{"d": r.date.strftime("%Y-%m-%d"), "v": _num(r.result)} for r in rows.itertuples()]}
    auth.log(user, "view_patient_from_reports", patient_id)
    return {
        "patient": {"id": patient_id, "age": _num(p.profile.get("Age")), "sex": (lambda v: None if v is None or v != v else str(v))(p.profile.get("Sex")), "reports": len({d for d, _ in reps}),
                    "first": min(list(p.labs.date) + list(p.daily.index)).strftime("%Y-%m-%d"),
                    "last": max(list(p.labs.date) + list(p.daily.index)).strftime("%Y-%m-%d"), "days": int(p.daily.notna().any(axis=1).sum())},
        "history": history,
        "quality": quality([(d, f) for d, f in reps], allvals, []),
        "insights": [{"id": i.insight_id, "kind": i.kind, "title": i.title, "flag": i.flag, "scenario": i.scenario, "summary": i.summary,
                      "bullets": i.bullets, "closing": i.closing, "onsets": i.onsets} for i in ins],
        "held": held, "source": "database",
    }


def store_report(user, filename: str, data: bytes):
    """Read ONE uploaded report, whatever it holds (lab results or daily readings), and add its values to the database."""
    if len(data) > MAX_FILE:
        return {"status": "rejected", "why": "file is larger than 5 MB"}
    sha = hashlib.sha256(data).hexdigest()
    with db() as con:
        if (con.execute("SELECT 1 FROM lab_reports WHERE user_id = ? AND sha256 = ?", (user["id"], sha)).fetchone()
                or con.execute("SELECT 1 FROM reading_files WHERE user_id = ? AND sha256 = ?", (user["id"], sha)).fetchone()):
            return {"status": "duplicate", "why": "this exact file was already uploaded"}
    if kind(filename, data) == "readings":
        return _store_readings(user, filename, data, sha)
    return _store_lab(user, filename, data)


def _store_readings(user, filename: str, data: bytes, sha: str):
    try:
        rep = parse_readings(filename, data)
    except ReportError as exc:
        return {"status": "rejected", "why": str(exc)}
    dates = rep.dates
    added, same, conflicts = 0, 0, []
    with db() as con:
        cur = con.execute(
            "INSERT INTO reading_files(user_id, patient_id, first_day, last_day, filename, sha256, size, age, sex) VALUES (?,?,?,?,?,?,?,?,?)",
            (user["id"], rep.patient_id, dates[0], dates[-1], filename[:200], sha, len(data), rep.age, rep.sex))
        fid = cur.lastrowid
        for (day, measure), v in sorted(rep.days.items()):
            old = con.execute("SELECT value FROM daily_values WHERE user_id = ? AND patient_id = ? AND day = ? AND measure = ?",
                              (user["id"], rep.patient_id, day, measure)).fetchone()
            if old is None:
                con.execute("INSERT INTO daily_values(file_id, user_id, patient_id, day, measure, value) VALUES (?,?,?,?,?,?)",
                            (fid, user["id"], rep.patient_id, day, measure, v))
                added += 1
            elif abs(old["value"] - v) <= 0.006:
                same += 1
            else:
                conflicts.append(f"{measure} on {day}: stored {old['value']:g}, this report says {v:g}. The stored value was kept.")
        con.execute("UPDATE reading_files SET added = ? WHERE id = ?", (added, fid))
        if added == 0 and not conflicts:
            con.execute("DELETE FROM reading_files WHERE id = ?", (fid,))
            return {"status": "duplicate", "patient": rep.patient_id, "date": dates[0],
                    "why": "the readings for this person and these days are already stored; nothing was added twice"}
    out = {"status": "added", "patient": rep.patient_id, "date": f"{dates[0]} to {dates[-1]}", "added": added, "already_stored": same,
           "missing": [], "conflicts": conflicts, "unrecognised": rep.unrecognised, "skipped": rep.skipped + rep.combined, "kind": "readings"}
    if conflicts and added == 0:
        out["status"] = "conflict"
    return out
