"""Documents add to ONE patient record; there is no per-document score."""
import importlib

import pytest
from fastapi.testclient import TestClient

from pranapulse.record import contents, summarise


def test_contents_lists_values_without_any_score():
    rows = contents(labs=[{"test": "HbA1c", "value": 5.9, "unit": "%", "ref_low": 4, "ref_high": 5.7, "collected": "2026-01-10"},
                          {"test": "ALT", "value": None, "unit": "U/L"}])
    assert rows == [{"kind": "lab", "name": "HbA1c", "value": 5.9, "unit": "%", "when": "2026-01-10", "range": "4–5.7"}]
    assert not any(k in rows[0] for k in ("level", "points", "severity", "score"))


def test_summarise_combines_documents_and_lists_what_is_missing():
    labs = [{"test": "LDL cholesterol", "unit": "mg/dL", "collected": "2025-09-10"}, {"test": "LDL cholesterol", "unit": "mg/dL", "collected": "2026-03-10"}]
    s = summarise(labs, [{"measure": "Systolic BP", "days": 30, "first_day": "2025-10-01", "last_day": "2025-10-30", "unit": "mmHg"}], reports=2, files=1)
    t = s["tests"][0]
    assert (t["results"], t["first"], t["last"]) == (2, "2025-09-10", "2026-03-10")
    assert s["measures"][0]["days"] == 30 and any("Medication" in m for m in s["missing"]) and any("Cycle" in m for m in s["missing"])


def _client(tmp_path, monkeypatch):
    monkeypatch.setenv("PRANAPULSE_DB", str(tmp_path / "t.db"))
    from api import db as dbm
    importlib.reload(dbm)
    from api import main
    importlib.reload(main)
    return TestClient(main.app)


def test_endpoints_second_document_adds_to_the_same_record(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    assert c.post("/api/auth/register", json={"name": "T", "email": "r@test.local", "password": "testpass123", "confirm": True}).status_code == 200
    lab = lambda d, v: ("Patient ID,Test,Result,Unit,Reference Low,Reference High,Collected\n"
                        f"PX0001,LDL cholesterol,{v},mmol/L,,3.0,{d}\nPX0001,HbA1c,5.4,%,4,5.7,{d}\n").encode()
    vit = b"Patient ID,Date,Systolic BP\nPX0001,2025-10-01,120\nPX0001,2025-10-02,124\n"
    for name, data in [("PX0001_lab_2026-01-10.csv", lab("2026-01-10", 3.4)), ("PX0001_lab_2026-04-10.csv", lab("2026-04-10", 3.9)),
                       ("PX0001_vitals_2025-10-01.csv", vit)]:
        assert c.post("/api/reports", files=[("files", (name, data))]).status_code == 200
    reps = c.get("/api/reports").json()["reports"]
    first = next(r for r in reps if r["kind"] == "lab")
    one = c.get(f"/api/reports/lab/{first['id']}/contents").json()
    assert {r["name"] for r in one["rows"]} == {"LDL cholesterol", "HbA1c"}
    vitals = next(r for r in reps if r["kind"] == "readings")
    assert c.get(f"/api/reports/readings/{vitals['id']}/contents").json()["rows"][0]["days"] == 2
    rec = c.get("/api/patients/PX0001/record").json()
    ldl = next(t for t in rec["tests"] if t["name"] == "LDL cholesterol")
    assert ldl["results"] == 2 and rec["lab_reports"] == 2 and rec["reading_files"] == 1   # both reports kept, nothing replaced
    assert c.get("/api/reports/lab/9999/contents").status_code == 404
    assert c.get("/api/reports/bogus/1/contents").status_code == 404
    assert c.get("/api/patients/NOPE/record").status_code == 404
    assert "json" not in c.get("/api/reports/lab/1/risk").headers["content-type"]   # the per-document score is gone (the app page answers instead)
