"""Single-document risk factors and the rule-based screening score."""
import io

import pytest
from fastapi.testclient import TestClient

from pranapulse.risk import assess, judge, severity


def test_severity_bands():
    assert severity(0.0) == 1 and severity(0.099) == 1
    assert severity(0.10) == 2 and severity(0.249) == 2
    assert severity(0.25) == 3 and severity(1.5) == 3


def test_judge_direction_and_distance():
    assert judge(130, 90, 120) == ("above", pytest.approx(10 / 120))
    assert judge(80, 90, 120) == ("below", pytest.approx(10 / 90))
    assert judge(100, 90, 120) == ("within", 0.0)
    assert judge(None, 90, 120)[0] is None
    assert judge(5, None, None)[0] == "within"   # no range: nothing to compare


def lab(test, v, hi=None, lo=None, unit="x"):
    return {"test": test, "value": v, "unit": unit, "ref_low": lo, "ref_high": hi}


def test_risk_direction_matters():
    # low LDL is not a risk factor; low HDL is
    r = assess([lab("LDL cholesterol", 1.0, hi=3.0), lab("HDL cholesterol", 0.8, lo=1.0)])
    assert [f["label"] for f in r["factors"]] == ["HDL cholesterol"]
    assert r["factors"][0]["severity"] == 2 and r["factors"][0]["distance_pct"] == 20.0


def test_area_levels_and_method():
    r = assess([lab("HbA1c", 5.8, hi=5.7)])                       # 1.75% past: mild, 1 point
    met = next(a for a in r["areas"] if a["short"] == "Metabolic")
    assert (met["level"], met["points"]) == ("Moderate", 1)
    r = assess([lab("HbA1c", 7.5, hi=5.7)])                       # 31% past: marked -> High on its own
    assert next(a for a in r["areas"] if a["short"] == "Metabolic")["level"] == "High"
    r = assess([lab("HbA1c", 5.0, hi=5.7)])
    assert next(a for a in r["areas"] if a["short"] == "Metabolic")["level"] == "Low"
    assert "not a diagnosis" in r["method"]


def test_areas_not_covered_have_no_level_and_other_results_are_not_scored():
    r = assess([lab("ALT", 90, hi=40, lo=7)])
    assert all(a["level"] is None for a in r["areas"])            # nothing from the three areas in this document
    assert r["factors"] == [] and r["other_outside"][0]["label"] == "ALT"


def test_readings_use_document_mean():
    r = assess(readings=[{"measure": "Systolic BP", "value": 135}, {"measure": "Steps", "value": 1000}])
    assert [f["label"] for f in r["factors"]] == ["Systolic BP"]
    cv = next(a for a in r["areas"] if a["short"] == "Cardiovascular")
    assert cv["checked"] == 1 and cv["level"] == "Moderate"      # 12.5% past the limit = moderate = 2 points


def test_missing_and_nan_values_are_skipped():
    r = assess([lab("HbA1c", None, hi=5.7), lab("LDL cholesterol", float("nan"), hi=3)])
    assert r["checked"] == []


def _client(tmp_path, monkeypatch):
    monkeypatch.setenv("PRANAPULSE_DB", str(tmp_path / "t.db"))
    import importlib
    from api import db as dbm
    importlib.reload(dbm)
    from api import main
    importlib.reload(main)
    return TestClient(main.app)


def test_endpoints_one_document_and_patient(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    assert c.post("/api/auth/register", json={"name": "T", "email": "r@test.local", "password": "testpass123", "confirm": True}).status_code == 200
    csv = ("Patient ID,Test,Result,Unit,Reference Low,Reference High,Collected\n"
           "PX0001,LDL cholesterol,4.2,mmol/L,,3.0,2026-01-10\nPX0001,HbA1c,5.4,%,4,5.7,2026-01-10\nPX0001,ALT,80,U/L,7,40,2026-01-10\n")
    r = c.post("/api/reports", files=[("files", ("PX0001_lab_2026-01-10.csv", csv.encode()))]).json()
    listing = c.get("/api/reports").json()["reports"]
    rep = next(x for x in listing if x["kind"] == "lab")
    one = c.get(f"/api/reports/lab/{rep['id']}/risk")
    assert one.status_code == 200
    body = one.json()
    assert [f["label"] for f in body["factors"]] == ["LDL cholesterol"] and body["factors"][0]["severity"] == 3
    assert body["other_outside"][0]["label"] == "ALT"
    assert c.get("/api/reports/lab/9999/risk").status_code == 404 and c.get(f"/api/reports/bogus/{rep['id']}/risk").status_code == 404
    pat = c.get("/api/patients/PX0001/risk").json()
    assert next(a for a in pat["areas"] if a["short"] == "Cardiovascular")["level"] == "High"
    assert c.get("/api/patients/NOPE/risk").status_code == 404
