"""Read ONE report of daily readings (blood pressure, heart rate, weight, steps, sleep ...) into clean daily values.

A readings report is one document for one person with one row per day (wide: Date, Systolic, Diastolic, ...)
or one row per reading (long: Date, Metric, Value). It can be a CSV, an XLSX or a PDF with a text table.
Every column is mapped to the standard measure used by the patient workbooks, converted to the standard unit,
and checked for plausible values. Nothing is guessed: a column or value that cannot be read is reported, not invented.
Lab results (Test / Result / Unit) are read by pranapulse.reports instead; kind() tells the two apart.
"""
import io
import re
from dataclasses import dataclass, field

import pandas as pd

from .reports import ReportError

# standard measure -> (workbook sheet, unit, plausible low, plausible high, how several readings in one day are combined)
MEASURES = {
    "Systolic BP": ("Vitals Daily", "mmHg", 50, 260, "mean"),
    "Diastolic BP": ("Vitals Daily", "mmHg", 30, 160, "mean"),
    "Resting HR": ("Vitals Daily", "bpm", 25, 220, "mean"),
    "Weight kg": ("Vitals Daily", "kg", 20, 350, "mean"),
    "BMI": ("Vitals Daily", "kg/m²", 8, 80, "mean"),
    "SpO2 %": ("Vitals Daily", "%", 50, 100, "mean"),
    "Temp C": ("Vitals Daily", "°C", 30, 43, "mean"),
    "Respiratory Rate": ("Vitals Daily", "/min", 4, 60, "mean"),
    "Steps": ("Wearable Daily", "steps", 0, 100000, "sum"),
    "Sleep Hours": ("Wearable Daily", "h", 0, 24, "mean"),
    "Active Minutes": ("Wearable Daily", "min", 0, 1440, "sum"),
    "HRV ms": ("Wearable Daily", "ms", 1, 400, "mean"),
    "Calories kcal": ("Wearable Daily", "kcal", 0, 15000, "sum"),
    "Sedentary Hours": ("Wearable Daily", "h", 0, 24, "mean"),
    "Stress Score 1-10": ("Wearable Daily", "score", 0, 10, "mean"),
}
VITALS = [m for m, v in MEASURES.items() if v[0] == "Vitals Daily"]
WEARABLE = [m for m, v in MEASURES.items() if v[0] == "Wearable Daily"]

_ALIASES = {
    "Systolic BP": "systolic sbp systolicbp systolicbloodpressure bpsystolic sys systolicpressure",
    "Diastolic BP": "diastolic dbp diastolicbp diastolicbloodpressure bpdiastolic dia diastolicpressure",
    "Resting HR": "restinghr restingheartrate heartrate hr pulse restingpulse rhr averageheartrate",
    "Weight kg": "weight weightkg bodyweight weightlb weightlbs bodymass",
    "BMI": "bmi bodymassindex",
    "SpO2 %": "spo2 oxygensaturation bloodoxygen o2saturation oxygen",
    "Temp C": "temp temperature bodytemperature bodytemp temperaturec",
    "Respiratory Rate": "respiratoryrate respirationrate breathingrate resprate rr",
    "Steps": "steps stepcount dailysteps totalsteps",
    "Sleep Hours": "sleep sleephours sleepduration sleeptime hoursofsleep sleepmin sleepminutes",
    "Active Minutes": "activeminutes activemin activitymin exerciseminutes activetime",
    "HRV ms": "hrv hrvms heartratevariability rmssd",
    "Calories kcal": "calories caloriesburned kcal caloriesout energyburned",
    "Sedentary Hours": "sedentaryhours sedentary sedentarytime",
    "Stress Score 1-10": "stress stressscore stresslevel",
}
ALIAS = {a: m for m, words in _ALIASES.items() for a in words.split()}
ALIAS.update({re.sub(r"[^a-z0-9]", "", m.lower()): m for m in MEASURES})    # the standard names themselves
DATE_COLS = ("date", "day", "datetime", "timestamp", "recordeddate", "measurementdate", "measured", "recorded")
PID_COLS = ("patientid", "patient", "id", "participantid")
METRIC_COLS = ("metric", "measure", "measurement", "signal", "readingtype", "type")
VALUE_COLS = ("value", "reading")
UNIT_COLS = ("unit", "units")
LAB_TEST_COLS = ("test", "testname", "analyte", "parameter", "name")
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _key(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def _split_header(h):
    """'Weight (lb)' -> ('Weight', 'lb')."""
    m = re.search(r"[(\[]([^)\]]*)[)\]]", str(h))
    return re.sub(r"[(\[][^)\]]*[)\]]", "", str(h)).strip(), (m.group(1).strip() if m else "")


def _unit_key(u):
    return re.sub(r"[\s°]", "", str(u or "").lower())


def measure_of(name, unit=""):
    """Standard measure for a column or row name, or None. The unit may also be written in the name ('weightlb')."""
    k = _key(name)
    m = ALIAS.get(k)
    if m:
        return m
    return None


def convert(measure, value, unit):
    """Convert to the standard unit. Returns (value, ok); ok is False when the unit is not understood."""
    u = _unit_key(unit)
    if not u:
        return value, True
    std = _unit_key(MEASURES[measure][1])
    if u == std or u in ("", "n/a"):
        return value, True
    table = {
        ("Weight kg", "lb"): lambda v: v * 0.45359237, ("Weight kg", "lbs"): lambda v: v * 0.45359237,
        ("Temp C", "f"): lambda v: (v - 32) * 5 / 9,
        ("Sleep Hours", "min"): lambda v: v / 60, ("Sleep Hours", "mins"): lambda v: v / 60, ("Sleep Hours", "minutes"): lambda v: v / 60,
        ("Sedentary Hours", "min"): lambda v: v / 60, ("Sedentary Hours", "minutes"): lambda v: v / 60,
        ("Active Minutes", "h"): lambda v: v * 60, ("Active Minutes", "hours"): lambda v: v * 60,
        ("Sleep Hours", "hours"): lambda v: v, ("Sleep Hours", "hrs"): lambda v: v, ("Sleep Hours", "hr"): lambda v: v,
        ("Weight kg", "kilograms"): lambda v: v, ("Resting HR", "beats/min"): lambda v: v, ("Resting HR", "bpm"): lambda v: v,
        ("SpO2 %", "percent"): lambda v: v, ("Temp C", "celsius"): lambda v: v, ("Steps", "count"): lambda v: v,
    }
    fn = table.get((measure, u))
    return (round(fn(value), 6), True) if fn else (value, False)


@dataclass
class Readings:
    patient_id: str
    days: dict                      # (YYYY-MM-DD, measure) -> value, one per day
    unrecognised: list = field(default_factory=list)    # columns or measures that could not be read
    skipped: list = field(default_factory=list)         # "Systolic BP on 2026-03-02 (400) is not plausible; left out"
    combined: list = field(default_factory=list)        # "Steps: 3 days had several readings; added together"
    age: float | None = None
    sex: str | None = None
    ocr: bool = False

    @property
    def dates(self):
        return sorted({d for d, _ in self.days})


def _text(x):
    return "" if x is None or (isinstance(x, float) and x != x) else str(x).strip()


def _num(x):
    try:
        v = float(str(x).replace(",", "").strip())
    except (TypeError, ValueError):
        return None
    return None if v != v else v


def _accumulate(items, rep_unrec, rep_skipped):
    """items: [(date, measure, value)] -> days dict with one value per day; implausible values are left out."""
    buckets = {}
    for d, m, v in items:
        _, _, lo, hi, _how = MEASURES[m]
        if not (lo <= v <= hi):
            rep_skipped.append(f"{m} on {d} ({v:g}) is not plausible; left out")
            continue
        buckets.setdefault((d, m), []).append(v)
    days, several = {}, {}
    for (d, m), vs in buckets.items():
        how = MEASURES[m][4]
        days[(d, m)] = round(sum(vs) if how == "sum" else sum(vs) / len(vs), 6)
        if len(vs) > 1:
            several[m] = several.get(m, 0) + 1
    return days, [f"{m}: {n} day(s) had several readings; {'added together' if MEASURES[m][4] == 'sum' else 'averaged'}"
                  for m, n in several.items()]


def _col(cols, names):
    return next((cols[n] for n in names if n in cols), None)


def _from_table(df):
    cols = {_key(c): c for c in df.columns}
    c_date, c_pid = _col(cols, DATE_COLS), _col(cols, PID_COLS)
    if c_date is None:
        raise ReportError("Could not find a Date column.")
    pids = df[c_pid].dropna().astype(str).str.strip().unique() if c_pid else []
    if len(pids) != 1:
        raise ReportError("The report must name exactly one Patient ID.")
    when = pd.to_datetime(df[c_date], errors="coerce")
    if when.notna().sum() == 0:
        raise ReportError("No readable dates in the Date column.")
    day = when.dt.strftime("%Y-%m-%d")
    unrec, items = [], []
    skipped_dates = int(when.isna().sum() - df[c_date].isna().sum())
    c_metric, c_value, c_unit = _col(cols, METRIC_COLS), _col(cols, VALUE_COLS), _col(cols, UNIT_COLS)
    if c_metric is not None and c_value is not None:           # long: one reading per row
        for i, row in df.iterrows():
            if pd.isna(day[i]):
                continue
            m = measure_of(row[c_metric])
            if m is None:
                unrec.append(str(row[c_metric]).strip())
                continue
            v = _num(row[c_value])
            if v is None:
                continue
            v, ok = convert(m, v, _text(row[c_unit]) if c_unit is not None else "")
            if not ok:
                unrec.append(f"{_text(row[c_metric])} (unit {_text(row[c_unit])})")
                continue
            items.append((day[i], m, v))
    else:                                                       # wide: one column per measure
        used = {c_date, c_pid}
        for c in df.columns:
            if c in used:
                continue
            base, unit = _split_header(c)
            m = measure_of(base) or measure_of(c)
            if m is None:
                if _key(c) not in ("age", "sex", "gender", "notes", "note", "comment", "comments"):
                    unrec.append(str(c).strip())
                continue
            u = unit or ("lb" if _key(c).endswith(("lb", "lbs")) and m == "Weight kg" else "")
            u = u or ("min" if _key(c).endswith(("min", "minutes")) and m in ("Sleep Hours", "Sedentary Hours") else "")
            bad_unit = False
            for i, raw in df[c].items():
                v = _num(raw)
                if v is None or pd.isna(day[i]):
                    continue
                v, ok = convert(m, v, u)
                if not ok:
                    bad_unit = True
                    break
                items.append((day[i], m, v))
            if bad_unit:
                items = [t for t in items if t[1] != m]
                unrec.append(f"{str(c).strip()} (unit not recognised)")
    age = _num(df[cols["age"]].dropna().iloc[0]) if "age" in cols and df[cols["age"]].notna().any() else None
    sx = next((str(df[cols[k]].dropna().iloc[0]).title() for k in ("sex", "gender") if k in cols and df[cols[k]].notna().any()), None)
    rep = Readings(pids[0], {}, unrec, [], [], age, sx if sx in ("Male", "Female") else None)
    rep.days, rep.combined = _accumulate(items, rep.unrecognised, rep.skipped)
    if skipped_dates:
        rep.skipped.append(f"{skipped_dates} row(s) with an unreadable date were left out")
    return rep


def _pdf_pages(data):
    try:
        from pypdf import PdfReader
        return [(pg.extract_text(extraction_mode="layout") or "") for pg in PdfReader(io.BytesIO(data)).pages]
    except Exception as exc:
        raise ReportError(f"Could not read the PDF ({str(exc)[:80]}).")


def _pdf_text(data):
    return "\n".join(_pdf_pages(data))


def _pdf_header(text):
    """The table header line: first word 'Date', and at least one column that names a known measure."""
    lines = text.splitlines()
    for n, line in enumerate(lines):
        words = [(m.start(), m.end(), m.group()) for m in re.finditer(r"\S+(?: \S+)*", line)]
        if words and _key(words[0][2]) in ("date", "day"):
            names = [w for w in words[1:]]
            if any(measure_of(_split_header(w[2])[0]) for w in names):
                return n, names, lines
    return None


def _columns(heads, unrec):
    cols = []
    for s_, e_, name in heads:
        base, unit = _split_header(name)
        m = measure_of(base)
        if m is None and name.strip() not in unrec:
            unrec.append(name.strip())
        cols.append((m, unit, (s_ + e_) / 2))
    return cols


def _parse_pages(pages):
    text = "\n".join(pages)
    pid = re.search(r"Patient\s*ID\s*[:\-]?\s*([A-Za-z0-9_\-]+)", text)
    if not pid:
        raise ReportError("No Patient ID found in the report.")
    if not _pdf_header(text):
        raise ReportError("No table of daily readings found in the report.")
    unrec, items, cols = [], [], None
    for page in pages:                       # column positions can differ from page to page, so each page uses its own header
        found = _pdf_header(page)
        lines = page.splitlines()
        start = 0
        if found:
            n, heads, lines = found
            cols, start = _columns(heads, unrec), n + 1
        if cols is None:
            continue
        for line in lines[start:]:
            toks = [(t.start(), t.end(), t.group()) for t in re.finditer(r"\S+", line)]
            if not toks or not ISO.match(toks[0][2]):    # blank lines, a repeated header or a note: skip
                continue
            day = toks[0][2]
            for s_, e_, tok in toks[1:]:
                v = _num(tok)
                if v is None:
                    continue
                mid = (s_ + e_) / 2
                m, unit, _ = min(cols, key=lambda c: abs(c[2] - mid))
                if m is None:
                    continue
                v, ok = convert(m, v, unit)
                if ok:
                    items.append((day, m, v))
    if not items:
        raise ReportError("No daily readings could be read from the table.")
    age = re.search(r"Age\s*[:\-]?\s*(\d{1,3})", text)
    sx = re.search(r"Sex\s*[:\-]?\s*(Male|Female)", text, re.I)
    rep = Readings(pid.group(1), {}, unrec, [], [], float(age.group(1)) if age else None, sx.group(1).title() if sx else None)
    rep.days, rep.combined = _accumulate(items, rep.unrecognised, rep.skipped)
    return rep


def parse_readings(filename: str, data: bytes) -> Readings:
    from . import intake
    e = intake.ext(filename)
    try:
        if e in intake.TEXT_EXT or e in intake.IMAGE_EXT:
            pages, ocr = intake.text_pages(filename, data)
            rep = _parse_pages(pages)
            rep.ocr = ocr
        elif e in intake.TABLE_EXT:
            rep = _from_table(intake.table_of(filename, data))
        else:
            raise ReportError("Use a PDF, image, Word, text, CSV, Excel or JSON file.")
    except ReportError:
        raise
    except Exception as exc:
        raise ReportError(f"Could not read the file ({str(exc)[:80]}).")
    if not rep.days:
        why = ", ".join(rep.unrecognised[:6]) or "no readable values"
        raise ReportError("None of the columns in this report are recognised as daily readings: " + why)
    return rep


def _kind_of_text(text):
    if re.search(r"Test\s+Result\s+Unit", text):
        return "lab"
    return "readings" if _pdf_header(text) else "lab"


def kind(filename: str, data: bytes) -> str:
    """'readings' when the document is a table of daily readings, otherwise 'lab' (which gives its own plain-language errors)."""
    from . import intake
    e = intake.ext(filename)
    try:
        if e in intake.TEXT_EXT or e in intake.IMAGE_EXT:
            pages, _ = intake.text_pages(filename, data)
            return _kind_of_text("\n".join(pages))
        if e in intake.TABLE_EXT:
            df = intake.table_of(filename, data).head(50)
            cols = {_key(c): c for c in df.columns}
            has_date = any(c in cols for c in DATE_COLS)
            if has_date and any(c in cols for c in METRIC_COLS) and any(c in cols for c in VALUE_COLS):
                return "readings"
            if any(c in cols for c in LAB_TEST_COLS) and ("result" in cols or "value" in cols):
                return "lab"
            if has_date and any(measure_of(_split_header(c)[0]) for c in df.columns):
                return "readings"
    except Exception:
        pass
    return "lab"
