"""Read ONE lab report (PDF with text, CSV or XLSX) into a clean list of results.

A report is one document for one person on one collection date. Different labs write the same test
differently ("Hemoglobin A1c", "A1C"; mmol/mol or %), so every row is mapped to the standard test name
and unit that the rest of PranaPulse uses. Nothing here guesses: a row that cannot be read is reported,
not invented. Scanned images need OCR and are not supported yet.
"""
import io
import re
from dataclasses import dataclass, field

import pandas as pd

# standard name -> (unit, low, high); the same names and units as the patient workbooks
CANON = {
    "Platelets": ("x10^9/L", 150, 450), "Total cholesterol": ("mg/dL", None, 200), "WBC": ("x10^9/L", 4.0, 11.0),
    "HDL cholesterol": ("mg/dL", 40, None), "eGFR": ("mL/min/1.73m²", 60, None), "Creatinine": ("mg/dL", 0.7, 1.3),
    "LDL cholesterol": ("mg/dL", None, 100), "AST": ("U/L", 10, 40), "Fasting glucose": ("mg/dL", 70, 99),
    "Hemoglobin": ("g/dL", 13.0, 17.0), "Vitamin B12": ("pg/mL", 200, 900), "HbA1c": ("%", 4.0, 5.6),
    "Vitamin D": ("ng/mL", 30, 100), "Triglycerides": ("mg/dL", None, 150), "ALT": ("U/L", 7, 56),
}

ALIASES = {
    "hba1c": "HbA1c", "hemoglobin a1c": "HbA1c", "haemoglobin a1c": "HbA1c", "a1c": "HbA1c", "glycated hemoglobin": "HbA1c",
    "glycosylated hemoglobin": "HbA1c", "glucose, fasting": "Fasting glucose", "fasting glucose": "Fasting glucose",
    "fasting blood glucose": "Fasting glucose", "glucose (fasting)": "Fasting glucose", "fbg": "Fasting glucose",
    "total cholesterol": "Total cholesterol", "cholesterol, total": "Total cholesterol", "cholesterol": "Total cholesterol",
    "ldl cholesterol": "LDL cholesterol", "ldl": "LDL cholesterol", "ldl-c": "LDL cholesterol", "cholesterol, ldl": "LDL cholesterol",
    "hdl cholesterol": "HDL cholesterol", "hdl": "HDL cholesterol", "hdl-c": "HDL cholesterol", "cholesterol, hdl": "HDL cholesterol",
    "triglycerides": "Triglycerides", "tg": "Triglycerides", "triglyceride": "Triglycerides",
    "hemoglobin": "Hemoglobin", "haemoglobin": "Hemoglobin", "hgb": "Hemoglobin", "hb": "Hemoglobin",
    "wbc": "WBC", "white blood cells": "WBC", "white blood cell count": "WBC", "platelets": "Platelets", "platelet count": "Platelets",
    "egfr": "eGFR", "creatinine": "Creatinine", "creatinine, serum": "Creatinine", "serum creatinine": "Creatinine",
    "alt": "ALT", "sgpt": "ALT", "ast": "AST", "sgot": "AST", "vitamin b12": "Vitamin B12", "b12": "Vitamin B12",
    "vitamin d": "Vitamin D", "vitamin d, 25-oh": "Vitamin D", "25-oh vitamin d": "Vitamin D", "25-hydroxyvitamin d": "Vitamin D",
}

# (standard test, unit as written) -> function that converts the value to the standard unit
CONVERT = {
    ("HbA1c", "mmol/mol"): lambda v: v / 10.929 + 2.15,
    ("Fasting glucose", "mmol/l"): lambda v: v * 18.016,
    ("Total cholesterol", "mmol/l"): lambda v: v * 38.67,
    ("LDL cholesterol", "mmol/l"): lambda v: v * 38.67,
    ("HDL cholesterol", "mmol/l"): lambda v: v * 38.67,
    ("Triglycerides", "mmol/l"): lambda v: v * 88.57,
    ("Creatinine", "umol/l"): lambda v: v / 88.4,
    ("Creatinine", "µmol/l"): lambda v: v / 88.4,
    ("Hemoglobin", "g/l"): lambda v: v / 10,
}

DATE = re.compile(r"(\d{4}-\d{2}-\d{2})")
RANGE = re.compile(r"^[<>≤≥]?\d[\d.]*([–-]\d[\d.]*)?$")
NUMBER = re.compile(r"^-?\d+(?:\.\d+)?$")


class ReportError(ValueError):
    """The document cannot be read as a lab report; the message says why, in plain words."""


@dataclass
class Row:
    test: str
    value: float | None          # None = the result is blank in the document
    unit: str
    ref_low: float | None
    ref_high: float | None
    converted_from: str = ""     # e.g. "44 mmol/mol" when the value was converted to the standard unit


@dataclass
class Report:
    patient_id: str
    collected: str               # YYYY-MM-DD
    rows: list[Row]
    age: float | None = None
    sex: str | None = None
    unrecognised: list[str] = field(default_factory=list)


def canonical(name: str):
    return ALIASES.get(re.sub(r"\s+", " ", str(name).strip().lower()))


def _unit_key(u):
    return re.sub(r"\s+", "", str(u).lower()).replace("×", "x").replace("^", "").replace("10e9", "109").replace("x109", "109").replace("109/l", "109/l")


def _num(x):
    try:
        v = float(str(x).replace(",", "").strip())
    except (TypeError, ValueError):
        return None
    return None if pd.isna(v) else v


def _range(text):
    nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", str(text))]
    t = str(text)
    if len(nums) >= 2:
        return nums[0], nums[1]
    if len(nums) == 1 and ("<" in t or "≤" in t):
        return None, nums[0]
    if len(nums) == 1 and (">" in t or "≥" in t):
        return nums[0], None
    return None, None


def _row(name, value, unit, rng, unrecognised):
    test = canonical(name)
    if test is None:
        unrecognised.append(str(name).strip())
        return None
    std_unit, lo, hi = CANON[test]
    unit = str(unit or "").strip()
    v = _num(value)
    if v is None:
        return Row(test, None, std_unit, lo, hi)
    if unit and _unit_key(unit) != _unit_key(std_unit):
        fn = CONVERT.get((test, unit.lower()))
        if fn is None:
            unrecognised.append(f"{str(name).strip()} (unit {unit})")
            return None
        return Row(test, round(fn(v), 2), std_unit, lo, hi, f"{v:g} {unit}")
    r_lo, r_hi = _range(rng)
    return Row(test, v, std_unit, r_lo if r_lo is not None else lo, r_hi if r_hi is not None else hi)


def _from_table(df: pd.DataFrame):
    cols = {re.sub(r"[^a-z]", "", str(c).lower()): c for c in df.columns}
    need = lambda *names: next((cols[n] for n in names if n in cols), None)
    c_test, c_val = need("test", "testname", "name", "analyte", "parameter"), need("result", "value")
    c_unit, c_rng = need("unit", "units"), need("referencerange", "referenceinterval", "reference", "range")
    c_date, c_pid = need("date", "collectiondate", "collected"), need("patientid", "patient", "id")
    if c_test is None or c_val is None:
        raise ReportError("Could not find the Test and Result columns.")
    pid = df[c_pid].dropna().astype(str).unique() if c_pid else []
    dates = pd.to_datetime(df[c_date], errors="coerce").dropna().dt.strftime("%Y-%m-%d").unique() if c_date else []
    return df, c_test, c_val, c_unit, c_rng, list(pid), list(dates)


def _parse_table(df):
    df, c_test, c_val, c_unit, c_rng, pids, dates = _from_table(df)
    if len(pids) != 1:
        raise ReportError("The report must name exactly one Patient ID.")
    if len(dates) != 1:
        raise ReportError("The report must have exactly one collection date.")
    unrec, rows = [], []
    for _, r in df.iterrows():
        if pd.isna(r[c_test]):
            continue
        row = _row(r[c_test], r[c_val], r[c_unit] if c_unit else "", r[c_rng] if c_rng else "", unrec)
        if row:
            rows.append(row)
    return Report(pids[0].strip(), dates[0], rows, unrecognised=unrec)


def _parse_pdf(data: bytes):
    try:
        from pypdf import PdfReader
        pages = PdfReader(io.BytesIO(data)).pages
        text = "\n".join((pg.extract_text(extraction_mode="layout") or "") for pg in pages)
    except Exception as exc:
        raise ReportError(f"Could not read the PDF ({str(exc)[:80]}).")
    if len(text.strip()) < 20:
        raise ReportError("The PDF has no readable text (it may be a scan). Scans need OCR, which is not supported yet.")
    pid = re.search(r"Patient\s*ID\s*[:\-]?\s*([A-Za-z0-9_\-]+)", text)
    date = re.search(r"(?:Collection|Collected|Sample)\s*date\s*[:\-]?\s*(\d{4}-\d{2}-\d{2})", text, re.I) or DATE.search(text)
    if not pid:
        raise ReportError("No Patient ID found in the report.")
    if not date:
        raise ReportError("No collection date (YYYY-MM-DD) found in the report.")
    age = re.search(r"Age\s*[:\-]?\s*(\d{1,3})", text)
    sex = re.search(r"Sex\s*[:\-]?\s*(Male|Female)", text, re.I)
    unrec, rows = [], []
    in_table = False
    for line in text.splitlines():
        tok = line.split()
        if not in_table:
            in_table = [t.lower() for t in tok[:3]] == ["test", "result", "unit"]
            continue
        if not tok:   # a blank line ends the results table; what follows is notes
            if rows or unrec:
                break
            continue
        if len(tok) < 3 or not RANGE.match(tok[-1]):
            continue
        rng, unit, rest = tok[-1], tok[-2], tok[:-2]
        if rest and NUMBER.match(rest[-1]):
            value, name = rest[-1], " ".join(rest[:-1])
        else:
            value, name = None, " ".join(rest)
        if not name or name.lower() in ("test", "result"):
            continue
        row = _row(name, value, unit, rng, unrec)
        if row:
            rows.append(row)
    if not rows and not unrec:
        raise ReportError("No test results found in the report.")
    return Report(pid.group(1), date.group(1), rows, float(age.group(1)) if age else None, sex.group(1).title() if sex else None, unrec)


def parse_report(filename: str, data: bytes) -> Report:
    name = filename.lower()
    try:
        if name.endswith(".pdf"):
            rep = _parse_pdf(data)
        elif name.endswith(".csv"):
            rep = _parse_table(pd.read_csv(io.BytesIO(data)))
        elif name.endswith((".xlsx", ".xlsm")):
            rep = _parse_table(pd.read_excel(io.BytesIO(data)))
        else:
            raise ReportError("Use a PDF, CSV or XLSX lab report.")
    except ReportError:
        raise
    except Exception as exc:
        raise ReportError(f"Could not read the file ({str(exc)[:80]}).")
    if not rep.rows:
        raise ReportError("None of the tests in this report are recognised: " + ", ".join(rep.unrecognised[:6]))
    return rep


# ---------------------------------------------------------------- data quality over many reports
GAP_DAYS = 200


def quality(reports, values, conflicts):
    """reports: [(collected, filename)], values: rows with value possibly None -> plain-language notes."""
    notes = []
    for v in values:
        if v["value"] is None:
            notes.append({"kind": "missing", "date": v["collected"], "test": v["test"],
                          "text": f"{v['test']} is blank in the report of {v['collected']}."})
    for c in conflicts:
        notes.append({"kind": "conflict", **c})
    dates = sorted({d for d, _ in reports})
    for a, b in zip(dates, dates[1:]):
        days = (pd.Timestamp(b) - pd.Timestamp(a)).days
        if days > GAP_DAYS:
            notes.append({"kind": "gap", "date": a, "text": f"No report between {a} and {b} ({days} days)."})
    for v in values:
        if v.get("converted_from"):
            notes.append({"kind": "converted", "date": v["collected"], "test": v["test"],
                          "text": f"{v['test']} on {v['collected']} was {v['converted_from']}; converted to {v['unit']}."})
    return notes
