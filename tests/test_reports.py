"""Lab reports uploaded one document at a time: parsing, storing, merging, data quality, findings from the database.

The files in tests/fake_reports are synthetic (made from the demo patient PC0433); see its README.txt.
"""
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api.main import app
from pranapulse.reports import ReportError, parse_report

FR = Path(__file__).parent / "fake_reports"
PW = "correct horse battery"

# .xlsx files are git-ignored in this repo, so the XLSX copies are made from the CSV reports when the tests start
(FR / "xlsx").mkdir(exist_ok=True)
for _csv in (FR / "csv").glob("*.csv"):
    pd.read_csv(_csv).to_excel(FR / "xlsx" / (_csv.stem + ".xlsx"), index=False)
_n = [0]


def client():
    _n[0] += 1
    c = TestClient(app)
    c.post("/api/auth/register", json={"name": "T", "email": f"rep{_n[0]}@example.com", "password": PW, "confirm": True})
    return c


def up(c, rel):
    p = FR / rel
    r = c.post("/api/reports", files=[("files", (p.name, p.read_bytes()))]).json()
    return r["results"][p.name]


def values(rep):
    return {r.test: r.value for r in rep.rows}


@pytest.mark.parametrize("date", ["2025-09-19", "2026-02-14", "2026-05-10", "2026-06-06"])
def test_pdf_csv_and_xlsx_give_the_same_values(date):
    got = [parse_report(f"x.{ext}", (FR / ext / f"PC0433_lab_{date}.{ext}").read_bytes()) for ext in ("pdf", "csv", "xlsx")]
    assert all(g.patient_id == "PC0433" and g.collected == date for g in got)
    assert values(got[0]) == values(got[1]) == values(got[2])


def test_other_names_and_units_are_mapped_to_standard():
    rep = parse_report("a.pdf", (FR / "edge_cases/03_other_names_and_units_2026-06-06.pdf").read_bytes())
    v = values(rep)
    assert v["Fasting glucose"] == 126.1 and "Total cholesterol" in v
    a1c = next(r for r in rep.rows if r.test == "HbA1c")
    assert a1c.unit == "%" and abs(a1c.value - 6.16) < 0.05 and a1c.converted_from == "44 mmol/mol"


def test_unreadable_files_are_rejected_with_a_reason():
    with pytest.raises(ReportError):
        parse_report("x.pdf", b"not a pdf")
    with pytest.raises(ReportError):
        parse_report("x.txt", b"hello")
    with pytest.raises(ReportError):
        parse_report("x.csv", b"Test,Result\nHbA1c,6\n")      # no patient id or date


def test_history_builds_up_in_any_order_and_dates_match_the_workbook_findings():
    c = client()
    for rel in ["pdf/PC0433_lab_2026-06-06.pdf", "csv/PC0433_lab_2025-09-19.csv", "xlsx/PC0433_lab_2026-02-14.xlsx", "pdf/PC0433_lab_2026-05-10.pdf"]:
        assert up(c, rel)["status"] == "added"
    assert c.get("/api/reports").json()["patients"][0]["values_n"] == 51
    d = c.get("/api/patients/PC0433/from-reports").json()
    assert d["source"] == "database" and d["patient"]["reports"] == 4
    on = {o["key"]: o["date"] for i in d["insights"] for o in i["onsets"]}
    assert on == {"HbA1c": "2026-02-14", "Fasting glucose": "2026-06-06"}
    assert d["history"]["HbA1c"]["points"][0] == {"d": "2025-09-19", "v": 5.65}


def test_repeats_are_not_counted_twice():
    c = client()
    assert up(c, "pdf/PC0433_lab_2026-02-14.pdf")["status"] == "added"
    assert up(c, "pdf/PC0433_lab_2026-02-14.pdf")["status"] == "duplicate"          # same file
    assert up(c, "edge_cases/01_duplicate_of_2026-02-14.pdf")["status"] == "duplicate"   # same results, another file
    assert up(c, "csv/PC0433_lab_2026-02-14.csv")["status"] == "duplicate"           # same results, another format
    assert c.get("/api/reports").json()["patients"][0]["values_n"] == 12


def test_a_blank_result_is_flagged_and_a_later_report_fills_it():
    c = client()
    r = up(c, "edge_cases/02_missing_HbA1c_2026-05-10.pdf")
    assert r["status"] == "added" and r["missing"] == ["HbA1c"]
    q = c.get("/api/patients/PC0433/from-reports").json()
    assert [n["kind"] for n in q["quality"]] == ["missing"] and "HbA1c" not in q["history"]
    assert up(c, "pdf/PC0433_lab_2026-05-10.pdf")["status"] == "added"          # now has the value
    q = c.get("/api/patients/PC0433/from-reports").json()
    assert q["history"]["HbA1c"]["points"] == [{"d": "2026-05-10", "v": 6.07}] and not q["quality"]


def test_gaps_between_reports_and_unit_conversions_are_noted():
    c = client()
    up(c, "pdf/PC0433_lab_2025-09-19.pdf")
    up(c, "edge_cases/03_other_names_and_units_2026-06-06.pdf")
    kinds = [n["kind"] for n in c.get("/api/patients/PC0433/from-reports").json()["quality"]]
    assert "gap" in kinds and "converted" in kinds


def test_a_different_patient_is_kept_apart_and_users_do_not_share():
    c, other = client(), client()
    up(c, "pdf/PC0433_lab_2026-02-14.pdf")
    up(c, "edge_cases/04_wrong_patient_PC9999.pdf")
    assert [p["patient_id"] for p in c.get("/api/reports").json()["patients"]] == ["PC0433", "PC9999"]
    assert other.get("/api/reports").json()["patients"] == []
    assert other.get("/api/patients/PC0433/from-reports").status_code == 404


def test_a_conflicting_value_keeps_the_stored_one():
    c = client()
    up(c, "csv/PC0433_lab_2026-02-14.csv")
    bad = (FR / "csv/PC0433_lab_2026-02-14.csv").read_text().replace("6.29", "7.5").encode()
    r = c.post("/api/reports", files=[("files", ("changed.csv", bad))]).json()["results"]["changed.csv"]
    assert r["status"] == "conflict" and "HbA1c" in r["conflicts"][0]
    assert c.get("/api/patients/PC0433/from-reports").json()["history"]["HbA1c"]["points"][0]["v"] == 6.29


def test_removing_a_report_removes_its_values():
    c = client()
    up(c, "pdf/PC0433_lab_2026-02-14.pdf")
    rid = c.get("/api/reports").json()["reports"][0]["id"]
    assert c.delete(f"/api/reports/{rid}").status_code == 200
    assert c.get("/api/reports").json()["patients"] == []


def test_requires_sign_in():
    assert TestClient(app).post("/api/reports", files=[("files", ("a.csv", b"x"))]).status_code == 401


# ---- the normal upload box: lab reports show up as an ordinary patient, like a workbook
def up_docs(c, *rels):
    files = [("files", ((FR / r).name, (FR / r).read_bytes())) for r in rels]
    return c.post("/api/documents", files=files).json()


def test_lab_reports_become_one_normal_patient_with_dated_findings():
    c = client()
    r = up_docs(c, "pdf/PC0433_lab_2026-06-06.pdf", "csv/PC0433_lab_2025-09-19.csv", "xlsx/PC0433_lab_2026-02-14.xlsx", "pdf/PC0433_lab_2026-05-10.pdf")
    assert r["added"] == 4 and r["failed"] == {}
    docs = c.get("/api/documents").json()
    assert len(docs) == 1 and docs[0]["id"] == "PC0433" and docs[0]["status"] == "Flagged"
    d = c.get(f"/api/documents/{docs[0]['key']}/detail").json()
    assert {o["key"]: o["date"] for i in d["insights"] for o in i["onsets"]} == {"HbA1c": "2026-02-14", "Fasting glucose": "2026-06-06"}
    assert d["labs"]["HbA1c"]["points"][0] == {"d": "2025-09-19", "v": 5.65}
    assert c.get(f"/api/documents/{docs[0]['key']}/file").status_code == 200


def test_another_report_updates_the_same_patient_and_repeats_are_skipped():
    c = client()
    up_docs(c, "pdf/PC0433_lab_2025-09-19.pdf", "pdf/PC0433_lab_2026-02-14.pdf")
    first = c.get("/api/documents").json()
    assert len(first) == 1 and first[0]["status"] == "Quiet"          # one pair of results is not yet a change
    r = up_docs(c, "pdf/PC0433_lab_2026-02-14.pdf", "pdf/PC0433_lab_2026-06-06.pdf", "pdf/PC0433_lab_2026-05-10.pdf")
    assert r["added"] == 2 and list(r["failed"]) == ["PC0433_lab_2026-02-14.pdf"]
    docs = c.get("/api/documents").json()
    assert len(docs) == 1 and docs[0]["status"] == "Flagged"


def test_notes_for_blank_and_unreadable_files_and_workbooks_still_work():
    from pranapulse.demo_data import make_workbook
    c = client()
    r = up_docs(c, "edge_cases/02_missing_HbA1c_2026-05-10.pdf")
    assert any("HbA1c is blank" in n for n in r["notes"])
    bad = c.post("/api/documents", files=[("files", ("bad.pdf", b"nope"))]).json()
    assert "bad.pdf" in bad["failed"]
    wb = c.post("/api/documents", files=[("files", ("wb.xlsx", make_workbook("A")))]).json()
    assert wb["added"] == 1
    assert {d["id"] for d in c.get("/api/documents").json()} == {"PC0433", "DEMO-A"}


def test_deleting_the_lab_patient_removes_its_reports():
    c = client()
    up_docs(c, "pdf/PC0433_lab_2026-02-14.pdf")
    key = c.get("/api/documents").json()[0]["key"]
    assert c.delete(f"/api/documents/{key}").status_code == 200
    assert c.get("/api/reports").json() == {"patients": [], "reports": []}


def test_lab_only_patient_detail_has_no_nan():
    """A patient built only from lab reports has no sex/vitals; the detail screen must still return valid JSON."""
    c = client()
    for rel in sorted((FR / "pdf").glob("*.pdf"))[:2]:
        c.post("/api/documents", files=[("files", (rel.name, rel.read_bytes()))])
    for d in c.get("/api/documents").json():
        r = c.get(f"/api/documents/{d['key']}/detail")
        assert r.status_code == 200, d["id"]


def test_unit_spelling_variants_are_accepted():
    from pranapulse.reports import _row
    unrec = []
    row = _row("WBC", "6.1", "10^9/L", "4.0-11.0", unrec)
    assert row and row.value == 6.1 and not unrec
