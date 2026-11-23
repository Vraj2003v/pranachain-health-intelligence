"""Issue #95 part 1: each pattern shows how many of its lab results are outside the range printed on the report."""
import uuid
from types import SimpleNamespace

import pandas as pd
from fastapi.testclient import TestClient

from api.main import app
from api.reports import patient_from_database
from pranapulse.detect import detect, labs_out_of_range
from scripts.make_cardio_demo import PID, main as make_files
from tests.test_context import up, user_of


def patient(rows):
    labs = pd.DataFrame(rows, columns=["date", "test", "result", "unit", "ref_low", "ref_high"])
    labs["date"] = pd.to_datetime(labs["date"])
    return SimpleNamespace(labs=labs)


def test_counts_results_outside_the_printed_range():
    p = patient([("2026-01-12", "LDL cholesterol", 118, "mg/dL", 0, 100),
                 ("2026-03-16", "LDL cholesterol", 95, "mg/dL", 0, 100),
                 ("2026-06-22", "LDL cholesterol", 152, "mg/dL", 0, 100)])
    out = labs_out_of_range(p, ["LDL cholesterol"])
    assert (out["out"], out["checked"]) == (2, 3)
    assert [i["value"] for i in out["items"]] == ["118 mg/dL", "152 mg/dL"] and out["items"][0]["position"] == "above"
    assert out["text"] == "2 of 3 lab results for this pattern are outside the range printed on the report."


def test_below_the_range_counts_and_other_tests_are_ignored():
    p = patient([("2026-01-01", "HbA1c", 3.9, "%", 4.0, 5.6), ("2026-01-01", "TSH", 9.0, "mIU/L", 0.4, 4.0)])
    out = labs_out_of_range(p, ["HbA1c", "Fasting glucose"])
    assert (out["out"], out["checked"]) == (1, 1) and out["items"][0]["position"] == "below"


def test_results_without_a_printed_range_are_not_counted():
    p = patient([("2026-01-01", "LDL cholesterol", 160, "mg/dL", float("nan"), float("nan"))])
    assert labs_out_of_range(p, ["LDL cholesterol"]) == {}


def test_cardio_demo_pattern_shows_its_labs_out_of_range_through_the_api(tmp_path):
    c = TestClient(app)
    assert c.post("/api/auth/register", json={"name": "T", "email": f"labs-{uuid.uuid4().hex[:8]}@example.com",
                                              "password": "correct horse battery", "confirm": True}).status_code == 200
    for name in make_files(tmp_path):
        up(c, name, (tmp_path / name).read_bytes())
    pat = [i for i in detect(patient_from_database(user_of(c), PID))[0] if i.kind == "pattern"]
    assert pat and (pat[0].labs_out["out"], pat[0].labs_out["checked"]) == (3, 3)   # LDL 118, 134, 152 against 0-100
    doc = next(d for d in c.get("/api/documents").json() if d["id"] == PID)
    sent = [i for i in c.get(f"/api/documents/{doc['key']}/detail").json()["insights"] if i["kind"] == "pattern"]
    assert sent[0]["labsOut"]["out"] == 3
