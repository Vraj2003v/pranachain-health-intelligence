"""Reports of daily readings (blood pressure, heart rate, weight, steps, sleep ...) uploaded one document at a time.

All data here is synthetic. The round-trip test cuts a demo patient's year into separate reports in four layouts
(wide CSV, wide XLSX with other headers, long CSV, PDF tables), uploads them in a shuffled order, and checks that the
daily series rebuilt from the database equals the original workbook's.
"""
import importlib.util
import io
import random
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.reports import patient_from_database
from pranapulse.demo_data import all_demo_workbooks
from pranapulse.loader import load_patient
from pranapulse.readings import kind, parse_readings
from pranapulse.reports import ReportError

PW = "correct horse battery"
_n = [0]


def client():
    _n[0] += 1
    c = TestClient(app)
    c.post("/api/auth/register", json={"name": "T", "email": f"read{_n[0]}@example.com", "password": PW, "confirm": True})
    return c


def csv_bytes(df):
    return df.to_csv(index=False).encode()


def upload(c, name, data):
    r = c.post("/api/documents", files=[("files", (name, data))]).json()
    return r


def pdf_table(df, pid="PC9001", rows_per_page=None):
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4))
    data = [list(df.columns)] + [["" if pd.isna(v) else str(v) for v in r] for r in df.itertuples(index=False)]
    doc.build([Paragraph(f"Patient ID: {pid}", getSampleStyleSheet()["Normal"]), Spacer(1, 8), Table(data, repeatRows=1)])
    return buf.getvalue()


def test_wide_csv_with_other_headers_and_units():
    df = pd.DataFrame({"Patient ID": "PC9001", "Date": ["2026-03-01", "2026-03-02"], "SBP": [128, 131], "DBP": [82, 84], "Pulse": [66, 70],
                       "Weight (lb)": [180.0, 181.0], "Sleep (min)": [420, 450], "Steps": [8000, 9100], "Mood": ["ok", "ok"]})
    rep = parse_readings("a.csv", csv_bytes(df))
    assert rep.patient_id == "PC9001" and rep.dates == ["2026-03-01", "2026-03-02"]
    assert rep.days[("2026-03-01", "Systolic BP")] == 128 and rep.days[("2026-03-02", "Resting HR")] == 70
    assert abs(rep.days[("2026-03-01", "Weight kg")] - 81.6466) < 0.001            # lb converted to kg
    assert rep.days[("2026-03-01", "Sleep Hours")] == 7.0 and rep.days[("2026-03-02", "Sleep Hours")] == 7.5   # minutes to hours
    assert rep.unrecognised == ["Mood"]


def test_long_csv_with_an_empty_unit_column():
    df = pd.DataFrame({"Patient ID": "PC9001", "Date": ["2026-03-01", "2026-03-01"], "Metric": ["Systolic BP", "Heart rate"], "Value": [120, 64], "Unit": [None, None]})
    assert kind("a.csv", csv_bytes(df)) == "readings"
    rep = parse_readings("a.csv", csv_bytes(df))
    assert rep.days == {("2026-03-01", "Systolic BP"): 120, ("2026-03-01", "Resting HR"): 64}


def test_implausible_values_and_several_readings_in_a_day():
    df = pd.DataFrame({"Patient ID": "PC9001", "Date": ["2026-03-01", "2026-03-01", "2026-03-02"], "Systolic BP": [120, 130, 400], "Steps": [3000, 4000, 100]})
    rep = parse_readings("a.csv", csv_bytes(df))
    assert rep.days[("2026-03-01", "Systolic BP")] == 125 and rep.days[("2026-03-01", "Steps")] == 7000       # averaged / added
    assert ("2026-03-02", "Systolic BP") not in rep.days and any("400" in s for s in rep.skipped)
    assert any("averaged" in s for s in rep.combined) and any("added together" in s for s in rep.combined)


def test_pdf_table_over_two_pages_with_blank_cells():
    """A 45-row table breaks onto a second page that repeats the header; blank cells must not shift values into other columns."""
    days = pd.date_range("2026-03-01", periods=45).strftime("%Y-%m-%d")
    df = pd.DataFrame({"Date": days, "Systolic BP": [120 + i for i in range(45)], "Diastolic BP": [80 + (i % 5) for i in range(45)],
                       "Resting HR": [60 + (i % 7) for i in range(45)]})
    df.loc[3, "Systolic BP"] = None
    rep = parse_readings("a.pdf", pdf_table(df))
    assert len(rep.dates) == 45
    assert ("2026-03-04", "Systolic BP") not in rep.days and rep.days[("2026-03-04", "Diastolic BP")] == 83
    assert rep.days[("2026-04-14", "Systolic BP")] == 164 and rep.days[("2026-04-14", "Resting HR")] == 60 + (44 % 7)


def test_bad_readings_reports_are_rejected_with_a_reason():
    with pytest.raises(ReportError):
        parse_readings("a.csv", csv_bytes(pd.DataFrame({"Date": ["2026-03-01"], "Systolic BP": [120]})))                 # no patient id
    with pytest.raises(ReportError):
        parse_readings("a.csv", csv_bytes(pd.DataFrame({"Patient ID": ["P"], "Date": ["2026-03-01"], "Colour": ["red"]})))   # nothing recognised
    with pytest.raises(ReportError):
        parse_readings("a.pdf", b"not a pdf")


def test_readings_and_lab_reports_build_one_patient_and_repeats_are_not_counted_twice():
    c = client()
    df = pd.DataFrame({"Patient ID": "PC9002", "Date": ["2026-03-01", "2026-03-02", "2026-03-03"], "Systolic BP": [120, 125, 130]})
    r = upload(c, "v1.csv", csv_bytes(df))
    assert r["added"] == 1 and not r["failed"]
    assert upload(c, "v1.csv", csv_bytes(df))["failed"]["v1.csv"] == "this exact file was already uploaded"
    df2 = df.copy()
    df2["Resting HR"] = [60, 61, 62]
    assert upload(c, "v2.csv", csv_bytes(df2))["added"] == 1                                              # new measure, same days: added
    again = upload(c, "v3.csv", csv_bytes(df2.assign(Note="x")))
    assert "already stored" in again["failed"]["v3.csv"]
    df3 = df.copy()
    df3.loc[0, "Systolic BP"] = 150
    conflict = upload(c, "v4.csv", csv_bytes(df3))
    assert "stored 120, this report says 150" in conflict["failed"]["v4.csv"]
    lab = pd.DataFrame({"Patient ID": "PC9002", "Collected": "2026-03-02", "Test": ["HbA1c"], "Result": [5.4], "Unit": ["%"]})
    assert upload(c, "lab.csv", csv_bytes(lab))["added"] == 1
    docs = c.get("/api/documents").json()
    assert len(docs) == 1 and docs[0]["filename"] == "PC9002 (uploaded reports).xlsx"
    assert c.get(f"/api/documents/{docs[0]['key']}/detail").status_code == 200
    listing = c.get("/api/reports").json()
    assert listing["patients"][0]["days"] == 3 and {r["kind"] for r in listing["reports"]} == {"lab", "readings"}


def test_deleting_the_rebuilt_record_removes_its_reports():
    c = client()
    upload(c, "v1.csv", csv_bytes(pd.DataFrame({"Patient ID": "PC9003", "Date": ["2026-03-01"], "Steps": [5000]})))
    doc = c.get("/api/documents").json()[0]
    assert c.delete(f"/api/documents/{doc['key']}").status_code == 200
    assert c.get("/api/reports").json() == {"patients": [], "reports": []}


def _generator():
    spec = importlib.util.spec_from_file_location("make_reading_reports", Path(__file__).resolve().parent.parent / "scripts" / "make_reading_reports.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_round_trip_reports_in_all_layouts_rebuild_the_original_daily_series(tmp_path):
    gen = _generator()
    key, wb = next(iter(all_demo_workbooks().items())) if isinstance(all_demo_workbooks(), dict) else all_demo_workbooks()[0]
    original = load_patient(io.BytesIO(wb))
    daily = original.daily.sort_index()
    pid = original.patient_id
    files = []
    for k, i in enumerate(range(0, len(daily), 30)):
        w = daily.iloc[i:i + 30]
        if len(w) < 3:
            continue
        for label, measures, shift in (("vitals", gen.VITALS, 0), ("wearable", gen.WEARABLE, 1)):
            files.append(gen.write_report(tmp_path, pid, w, [m for m in measures if m in w], (k + shift) % 4, k % 2 == 1, label))
    assert {Path(f).suffix for f in files} == {".csv", ".xlsx", ".pdf"}
    random.Random(5).shuffle(files)
    c = client()
    for name in files:
        r = upload(c, name, (tmp_path / name).read_bytes())
        assert r["added"] == 1 and not r["failed"], (name, r)
    with __import__("api.db", fromlist=["db"]).db() as con:
        user = dict(con.execute("SELECT * FROM users WHERE email = ?", (f"read{_n[0]}@example.com",)).fetchone())
    rebuilt = patient_from_database(user, pid).daily
    for col in rebuilt.columns:
        a, b = original.daily[col].reindex(rebuilt.index), rebuilt[col]
        assert (a.notna() == b.notna()).all(), col
        both = a.notna() & b.notna()
        assert ((a[both] - b[both]).abs() < 1e-3).all(), col
