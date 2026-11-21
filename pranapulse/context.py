"""Everything in a person's record that is not a lab value or a daily reading: medications, diagnoses and earlier
findings, menstrual cycle log and clinical notes - plus FHIR bundles, which can hold all of it at once.

These feed the same places as in the full patient workbooks (Medication History, Medical History, Women Health), so
the analysis can use them as context and the women's health (PCOS) pattern can run on uploaded records.
Nothing here is scored or interpreted: each item is read as written, or reported as left out.
"""
import re
from dataclasses import dataclass, field

import pandas as pd

from . import intake
from .readings import _key, measure_of, convert, MEASURES
from .reports import ReportError, canonical, CANON

ISO = re.compile(r"\d{4}-\d{2}-\d{2}")
PID = re.compile(r"Patient\s*ID\s*[:\-]?\s*([A-Za-z0-9_\-]+)", re.I)
MED_COLS = ("medication", "medicine", "drug", "drugname", "medicationname", "medications")
HISTORY_COLS = ("finding", "findingevent", "diagnosis", "diagnoses", "condition", "problem", "event", "previousfinding")
CYCLE_COLS = ("cyclelength", "cycledays", "periodlength", "lengthofcycle")


@dataclass
class Context:
    patient_id: str
    kind: str                                   # medications | history | cycles | notes | fhir | clinical
    meds: list = field(default_factory=list)    # dict(name, indication, start, end, status, dose)
    history: list = field(default_factory=list) # dict(date, event, status)
    cycles: list = field(default_factory=list)  # dict(start, length)
    note: str = ""
    skipped: list = field(default_factory=list)
    age: float | None = None
    sex: str | None = None
    date: str | None = None
    ocr: bool = False
    labs: list = field(default_factory=list)      # FHIR only: (date, Row)
    readings: list = field(default_factory=list)  # FHIR only: (day, measure, value)


# ------------------------------------------------------------------ tables
def _date(x):
    t = pd.to_datetime(x, errors="coerce")
    return None if pd.isna(t) else t.strftime("%Y-%m-%d")


def _txt(x):
    return "" if x is None or (isinstance(x, float) and x != x) else str(x).strip()


def _one_patient(df, cols):
    c = next((cols[k] for k in ("patientid", "patient", "id", "participantid") if k in cols), None)
    pids = df[c].dropna().astype(str).str.strip().unique() if c else []
    if len(pids) != 1:
        raise ReportError("The file must name exactly one Patient ID.")
    return pids[0], c


def table_kind(df):
    cols = {_key(c) for c in df.columns}
    if cols & set(CYCLE_COLS) or (("cycle" in cols or "periodstart" in cols or "cyclestart" in cols) and "length" in cols):
        return "cycles"
    if cols & set(MED_COLS) and not cols & {"result", "metric"}:
        return "medications"
    if cols & set(HISTORY_COLS) and not cols & {"result", "metric", "value", "test", "testname"}:
        return "history"
    return None


def parse_table(df, kind):
    cols = {_key(c): c for c in df.columns}
    pid, c_pid = _one_patient(df, cols)
    ctx = Context(pid, kind)
    g = lambda r, *names: next((_txt(r[cols[n]]) for n in names if n in cols), "")
    for _, r in df.iterrows():
        if kind == "medications":
            name = g(r, *MED_COLS)
            if not name:
                continue
            start = _date(g(r, "startdate", "start", "started", "from", "date")) or None
            if not start:
                ctx.skipped.append(f"{name} has no start date; left out")
                continue
            ctx.meds.append({"name": name, "dose": g(r, "dose", "dosage"), "indication": g(r, "indication", "reason", "for", "condition"),
                             "start": start, "end": _date(g(r, "enddate", "end", "stopped", "to")), "status": g(r, "status") or "Active"})
        elif kind == "history":
            ev = g(r, *HISTORY_COLS)
            if not ev:
                continue
            when = _date(g(r, "date", "diagnosed", "diagnosisdate", "onset", "onsetdate", "recorded"))
            if not when:
                ctx.skipped.append(f"{ev} has no date; left out")
                continue
            ctx.history.append({"date": when, "event": ev, "status": g(r, "status") or "Active"})
        elif kind == "cycles":
            ln = pd.to_numeric(g(r, *CYCLE_COLS, "length"), errors="coerce")
            when = _date(g(r, "startdate", "start", "periodstart", "cyclestart", "date"))
            if pd.isna(ln) or not when:
                ctx.skipped.append("a cycle row without a start date or length was left out")
                continue
            ctx.cycles.append({"start": when, "length": float(ln)})
    if not (ctx.meds or ctx.history or ctx.cycles):
        raise ReportError("Nothing could be read from this file" + (": " + "; ".join(ctx.skipped[:3]) if ctx.skipped else "."))
    return ctx


# ------------------------------------------------------------------ text (PDF, scan, Word, TXT)
SECTIONS = {
    "medications": ("medications", "current medications", "medication list", "medication history", "medicines", "drugs"),
    "history": ("diagnoses", "diagnosis", "problem list", "medical history", "past medical history", "history", "previous findings", "conditions", "findings"),
    "cycles": ("cycle log", "menstrual history", "menstrual cycles", "cycles", "menstrual cycle log"),
    "notes": ("notes", "clinical notes", "assessment", "plan", "assessment and plan", "summary", "impression", "history of present illness"),
}
HEAD = {w: k for k, ws in SECTIONS.items() for w in ws}
BULLET = re.compile(r"^[\s\-*•·●▪\d.)]+")


def _heading(line):
    t = re.sub(r"[:\s]+$", "", line.strip().lower())
    if t in HEAD:
        return HEAD[t]
    return "other" if line.strip().endswith(":") and len(t.split()) <= 4 and not PID.search(line) and not ISO.search(line) else None


def sections_of(text):
    out, cur = {}, None
    for line in text.splitlines():
        if not line.strip():
            continue
        h = _heading(line)
        if h:
            cur = h
            out.setdefault(h, [])
            continue
        if cur and cur != "other":
            out[cur].append(line.strip())
    return out


def looks_clinical(text):
    return bool(PID.search(text)) and bool(set(sections_of(text)) - {"other"})


def _med_line(line, doc_date):
    s = BULLET.sub("", line).strip()
    if not s:
        return None
    dates = ISO.findall(s)
    start = end = None
    m = re.search(r"(?:since|started|start|from|begun)\s*:?\s*(\d{4}-\d{2}-\d{2})", s, re.I)
    start = m.group(1) if m else (dates[0] if dates else doc_date)
    m = re.search(r"(?:until|stopped|ended|to|discontinued)\s*:?\s*(\d{4}-\d{2}-\d{2})", s, re.I)
    end = m.group(1) if m else None
    head = re.split(r"\s[-–—]\s|,|;|\(|\sfor\s|\ssince\s|\sstarted\s", s)[0].strip()
    toks = head.split()
    k = next((i for i, t in enumerate(toks) if re.match(r"^\d", t)), len(toks))
    name = " ".join(toks[:k]).strip() or head
    dose = " ".join(toks[k:]).strip()
    ind = re.search(r"\bfor\s+([A-Za-z][A-Za-z ]+?)(?:\s*(?:[,;(]|[-–—]\s|since|from|started|until|stopped)|$)", s, re.I)
    status = "Discontinued" if re.search(r"stopped|discontinued|ended", s, re.I) else "Active"
    return {"name": name, "dose": dose, "indication": ind.group(1).strip() if ind else "", "start": start, "end": end, "status": status}


def parse_text(text, ocr=False):
    pid = PID.search(text)
    if not pid:
        raise ReportError("No Patient ID found in the document.")
    d = re.search(r"(?:visit|encounter|report|document|note)?\s*date\s*[:\-]?\s*(\d{4}-\d{2}-\d{2})", text, re.I) or ISO.search(text)
    doc_date = (d.group(1) if d and d.lastindex else d.group(0)) if d else None
    age = re.search(r"Age\s*[:\-]?\s*(\d{1,3})", text)
    sx = re.search(r"Sex\s*[:\-]?\s*(Male|Female)", text, re.I)
    ctx = Context(pid.group(1), "clinical", age=float(age.group(1)) if age else None, sex=sx.group(1).title() if sx else None, date=doc_date, ocr=ocr)
    sec = sections_of(text)
    for line in sec.get("medications", []):
        m = _med_line(line, doc_date)
        if not m:
            continue
        if not m["start"]:
            ctx.skipped.append(f"{m['name']} has no start date; left out")
        else:
            ctx.meds.append(m)
    for line in sec.get("history", []):
        s = BULLET.sub("", line).strip()
        when = (ISO.findall(s) or [doc_date])[0]
        ev = re.sub(r"\(?\b(?:since|on|in)?\s*\d{4}-\d{2}-\d{2}\)?", "", s).strip(" -–—,;:()")
        if not ev:
            continue
        if not when:
            ctx.skipped.append(f"{ev} has no date; left out")
            continue
        status = "Resolved" if re.search(r"resolved|past|previous|history of", s, re.I) else "Active"
        ctx.history.append({"date": when, "event": ev, "status": status})
    for line in sec.get("cycles", []):
        m = re.search(r"(\d{4}-\d{2}-\d{2})\D{1,25}?(\d{2,3})\s*(?:days?|d)?\b", line)
        if m:
            ctx.cycles.append({"start": m.group(1), "length": float(m.group(2))})
        else:
            ctx.skipped.append("a cycle line without a start date and length was left out")
    ctx.note = "\n".join(sec.get("notes", []))[:20000]
    if not (ctx.meds or ctx.history or ctx.cycles or ctx.note):
        raise ReportError("Nothing could be read from the sections of this document.")
    return ctx


# ------------------------------------------------------------------ FHIR
LOINC = {
    "8480-6": "Systolic BP", "8462-4": "Diastolic BP", "8867-4": "Resting HR", "29463-7": "Weight kg", "39156-5": "BMI",
    "2708-6": "SpO2 %", "59408-5": "SpO2 %", "8310-5": "Temp C", "9279-1": "Respiratory Rate", "55423-8": "Steps",
    "4548-4": "HbA1c", "1558-6": "Fasting glucose", "2345-7": "Fasting glucose", "2339-0": "Fasting glucose", "2093-3": "Total cholesterol",
    "13457-7": "LDL cholesterol", "18262-6": "LDL cholesterol", "2089-1": "LDL cholesterol", "2085-9": "HDL cholesterol", "2571-8": "Triglycerides",
    "718-7": "Hemoglobin", "6690-2": "WBC", "777-3": "Platelets", "33914-3": "eGFR", "62238-1": "eGFR", "2160-0": "Creatinine",
    "1742-6": "ALT", "1920-8": "AST", "2132-9": "Vitamin B12", "1989-3": "Vitamin D", "62292-8": "Vitamin D",
}


def _concept(c):
    c = c or {}
    codes = [x.get("code") for x in c.get("coding", []) if x.get("code")]
    names = [c.get("text")] + [x.get("display") for x in c.get("coding", [])]
    return codes, [n for n in names if n]


def _std_name(c):
    codes, names = _concept(c)
    for k in codes:
        if k in LOINC:
            return LOINC[k]
    for n in names:
        if canonical(n) or measure_of(n):
            return canonical(n) or measure_of(n)
    return None


def _resources(obj):
    if obj.get("resourceType") == "Bundle":
        return [e.get("resource", {}) for e in obj.get("entry", []) if isinstance(e, dict)]
    return [obj]


def parse_fhir(obj):
    from .reports import Row, _row
    res = _resources(obj)
    pat = next((r for r in res if r.get("resourceType") == "Patient"), {})
    pid = pat.get("id") or next((i.get("value") for i in pat.get("identifier", []) if i.get("value")), None)
    if not pid:
        for r in res:
            ref = (r.get("subject") or r.get("patient") or {}).get("reference", "")
            if ref.startswith("Patient/"):
                pid = ref.split("/", 1)[1]
                break
    if not pid:
        raise ReportError("No patient found in the FHIR file.")
    sex = {"male": "Male", "female": "Female"}.get(str(pat.get("gender", "")).lower())
    ctx = Context(str(pid), "fhir", sex=sex)
    seen_dates = []
    for r in res:
        t = r.get("resourceType")
        if t == "Observation":
            when = _date(r.get("effectiveDateTime") or (r.get("effectivePeriod") or {}).get("start") or r.get("issued"))
            if not when:
                ctx.skipped.append("an observation without a date was left out")
                continue
            parts = [(r.get("code"), r.get("valueQuantity"), r.get("referenceRange"))]
            for comp in r.get("component", []):
                parts.append((comp.get("code"), comp.get("valueQuantity"), comp.get("referenceRange")))
            for code, q, rng in parts:
                if not q or q.get("value") is None:
                    continue
                name = _std_name(code)
                if name is None:
                    ctx.skipped.append(f"{(_concept(code)[1] or ['an observation'])[0]} is not a recognised test or measure; left out")
                    continue
                unit = q.get("unit") or q.get("code") or ""
                if name in CANON:
                    unrec = []
                    lo = hi = ""
                    if rng:
                        lo, hi = (rng[0].get("low") or {}).get("value"), (rng[0].get("high") or {}).get("value")
                    rg = (f"{lo}-{hi}" if lo is not None and hi is not None else f"<{hi}" if hi is not None else f">{lo}" if lo is not None else "")
                    row = _row(name, q["value"], unit, rg, unrec)
                    if row:
                        ctx.labs.append((when, row))
                        seen_dates.append(when)
                    else:
                        ctx.skipped.extend(unrec)
                elif name in MEASURES:
                    v, ok = convert(name, float(q["value"]), unit)
                    if ok:
                        ctx.readings.append((when, name, v))
                        seen_dates.append(when)
                    else:
                        ctx.skipped.append(f"{name} in unit {unit} is not recognised; left out")
        elif t == "Condition":
            ev = (_concept(r.get("code"))[1] or [None])[0]
            when = _date(r.get("onsetDateTime") or r.get("recordedDate"))
            st = ((r.get("clinicalStatus") or {}).get("coding") or [{}])[0].get("code", "active").title()
            if ev and when:
                ctx.history.append({"date": when, "event": ev, "status": st})
            elif ev:
                ctx.skipped.append(f"{ev} has no date; left out")
        elif t in ("MedicationRequest", "MedicationStatement"):
            nm = (_concept(r.get("medicationCodeableConcept"))[1] or [None])[0]
            when = _date(r.get("authoredOn") or (r.get("effectivePeriod") or {}).get("start") or r.get("effectiveDateTime"))
            if nm and when:
                reason = (_concept((r.get("reasonCode") or [{}])[0])[1] or [""])[0]
                ctx.meds.append({"name": nm, "dose": "", "indication": reason, "start": when,
                                 "end": _date((r.get("effectivePeriod") or {}).get("end")), "status": str(r.get("status", "active")).title()})
            elif nm:
                ctx.skipped.append(f"{nm} has no start date; left out")
    if pat.get("birthDate") and seen_dates:
        b, last = pd.to_datetime(pat["birthDate"], errors="coerce"), pd.to_datetime(max(seen_dates))
        if not pd.isna(b):
            ctx.age = float((last - b).days // 365)
    if not (ctx.labs or ctx.readings or ctx.meds or ctx.history):
        raise ReportError("No recognised tests, readings, medications or conditions in the FHIR file.")
    return ctx


# ------------------------------------------------------------------ routing
def classify(filename, data):
    """-> 'fhir' | 'medications' | 'history' | 'cycles' | 'clinical' | None (None: a lab report or daily readings)."""
    e = intake.ext(filename)
    try:
        if e == ".json":
            obj = intake.load_json(data)
            if intake.is_fhir(obj):
                return "fhir"
        if e in intake.TABLE_EXT:
            return table_kind(intake.table_of(filename, data).head(200))
        if e in intake.TEXT_EXT or e in intake.IMAGE_EXT:
            pages, _ = intake.text_pages(filename, data)
            text = "\n".join(pages)
            if re.search(r"Test\s+Result\s+Unit", text):
                return None
            return "clinical" if looks_clinical(text) and not _has_readings_table(text) else None
    except ReportError:
        return None
    return None


def _has_readings_table(text):
    from .readings import _pdf_header
    return bool(_pdf_header(text))


def parse_context(filename, data):
    e = intake.ext(filename)
    if e == ".json":
        obj = intake.load_json(data)
        if intake.is_fhir(obj):
            return parse_fhir(obj)
    if e in intake.TABLE_EXT:
        df = intake.table_of(filename, data)
        return parse_table(df, table_kind(df))
    pages, ocr = intake.text_pages(filename, data)
    return parse_text("\n".join(pages), ocr)
