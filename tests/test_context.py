"""More kinds of data: Word, text, JSON, old Excel, scans and photos (OCR), FHIR bundles, and the record types that are
not lab values or daily readings (medications, diagnoses, cycle log, clinical notes). All data here is synthetic."""
import io
import json
import shutil

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.reports import patient_from_database, workbook_from_database
from pranapulse.detect import detect
from pranapulse.loader import load_patient

PW = "correct horse battery"
_n = [0]


def client():
    _n[0] += 1
    c = TestClient(app)
    r = c.post("/api/auth/register", json={"name": "T", "email": f"ctx{_n[0]}@example.com", "password": PW, "confirm": True})
    c.user = r.json()
    return c


def up(c, name, data):
    return c.post("/api/documents", files=[("files", (name, data))]).json()


def user_of(c):
    from api import auth
    return {"id": c.get("/api/auth/me").json()["id"]}


LAB_TXT = """Patient ID: PC7001
Age: 29
Sex: Female
Collection date: 2026-02-10

Test            Result   Unit     Reference Range
HbA1c           5.4      %        4.0-5.6
Fasting glucose 92       mg/dL    70-99
"""

LAB_CSV = "Patient ID,Date,Test,Result,Unit,Reference Range\nPC7001,2026-01-05,HbA1c,5.2,%,4.0-5.6\nPC7001,2026-01-05,Fasting glucose,88,mg/dL,70-99\n"
CYCLES = "Patient ID,Start Date,Cycle Length\n" + "\n".join(f"PC7001,2026-{m:02d}-01,{n}" for m, n in zip(range(1, 9), [26, 41, 29, 48, 27, 52, 31, 45])) + "\n"
MEDS = "Patient ID,Medication,Dose,Indication,Start Date,Status\nPC7001,Metformin,500 mg,PCOS,2025-06-01,Active\n"
CLINICAL = """Clinical summary
Patient ID: PC7001
Visit date: 2026-02-10

Diagnoses:
- Polycystic ovary syndrome (2024-03-12)
- Seasonal allergy, resolved

Medications:
- Metformin 500 mg twice daily for PCOS since 2025-06-01
- Vitamin D 1000 IU for low vitamin D started 2026-01-15

Notes:
Patient reports irregular periods for two years.
"""


def test_text_file_is_read_as_a_lab_report():
    c = client()
    r = up(c, "lab.txt", LAB_TXT.encode())
    assert r["added"] == 1, r


def test_word_document_with_a_table_is_read_as_a_lab_report():
    from docx import Document
    d = Document()
    d.add_paragraph("Patient ID: PC7001")
    d.add_paragraph("Collection date: 2026-02-10")
    t = d.add_table(rows=3, cols=4)
    for i, row in enumerate([("Test", "Result", "Unit", "Reference Range"), ("HbA1c", "5.4", "%", "4.0-5.6"), ("Fasting glucose", "92", "mg/dL", "70-99")]):
        for j, v in enumerate(row):
            t.cell(i, j).text = v
    b = io.BytesIO(); d.save(b)
    c = client()
    assert up(c, "lab.docx", b.getvalue())["added"] == 1


def test_json_records_are_read_as_a_lab_report():
    rows = [{"Patient ID": "PC7001", "Date": "2026-02-10", "Test": "HbA1c", "Result": 5.4, "Unit": "%", "Reference Range": "4.0-5.6"}]
    c = client()
    assert up(c, "lab.json", json.dumps(rows).encode())["added"] == 1


def test_old_excel_xls_is_read():
    pytest.importorskip("xlwt")
    pytest.importorskip("xlrd")
    import xlwt
    wb = xlwt.Workbook()
    ws = wb.add_sheet("Labs")
    for i, line in enumerate(LAB_CSV.strip().splitlines()):
        for j, v in enumerate(line.split(",")):
            ws.write(i, j, v)
    b = io.BytesIO()
    wb.save(b)
    c = client()
    assert up(c, "lab.xls", b.getvalue())["added"] == 1


needs_ocr = pytest.mark.skipif(shutil.which("tesseract") is None, reason="Tesseract is not installed")


def _image_of(text):
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.load_default(size=28)
    lines = text.splitlines()
    img = Image.new("RGB", (1300, 60 + 44 * len(lines)), "white")
    dr = ImageDraw.Draw(img)
    for i, line in enumerate(lines):
        dr.text((30, 20 + 44 * i), line, fill="black", font=font)
    return img


@needs_ocr
def test_photo_of_a_report_is_read_with_ocr_and_flagged():
    b = io.BytesIO(); _image_of(LAB_TXT).save(b, "PNG")
    c = client()
    r = c.post("/api/documents", files=[("files", ("scan.png", b.getvalue()))]).json()
    assert r["added"] == 1, r
    p = patient_from_database(user_of(c), "PC7001")
    assert set(p.labs.test) == {"HbA1c", "Fasting glucose"}
    assert any("scan" in n.lower() or "check" in n.lower() for n in r["notes"])


@needs_ocr
def test_scanned_pdf_is_read_with_ocr():
    b = io.BytesIO(); _image_of(LAB_TXT).save(b, "PDF")
    c = client()
    assert up(c, "scan.pdf", b.getvalue())["added"] == 1


def test_image_without_ocr_engine_gives_a_clear_message(monkeypatch):
    from pranapulse import intake
    from pranapulse.reports import ReportError
    monkeypatch.setattr(intake, "_ocr_image", lambda img: (_ for _ in ()).throw(ReportError(intake.OCR_MISSING)))
    b = io.BytesIO(); _image_of("x").save(b, "PNG")
    c = client()
    r = up(c, "scan.png", b.getvalue())
    assert r["added"] == 0 and "OCR" in list(r["failed"].values())[0]


def test_cycle_log_medications_and_clinical_note_become_part_of_the_record_and_pcos_pattern_runs():
    c = client()
    assert up(c, "lab.csv", LAB_CSV.encode())["added"] == 1
    assert up(c, "cycles.csv", CYCLES.encode())["added"] == 1
    assert up(c, "meds.csv", MEDS.encode())["added"] == 1
    r = up(c, "summary.txt", CLINICAL.encode())
    assert r["added"] == 1, r
    u = user_of(c)
    p = patient_from_database(u, "PC7001")
    assert len(p.cycles) == 8 and len(p.meds) == 2 and len(p.history) == 2   # Metformin appears in two files: stored once
    ins, _, _ = detect(p)
    cyc = [i for i in ins if i.kind == "cycle"]
    assert cyc and any("PCOS" in x or "Polycystic" in x or "polycystic" in x for x in cyc[0].context), cyc
    # the rebuilt workbook carries the same sheets and loads like any patient workbook
    q = load_patient(io.BytesIO(workbook_from_database(u, "PC7001")))
    assert len(q.cycles) == 8 and len(q.meds) == 2 and len(q.history) == 2
    rec = c.get("/api/patients/PC7001/record").json()
    assert len(rec["medications"]) == 2 and rec["cycles"]["count"] == 8 and rec["notes"] == 1
    assert not any("Medications" in m for m in rec["missing"])


def test_same_context_file_twice_is_not_stored_twice():
    c = client()
    up(c, "lab.csv", LAB_CSV.encode())
    up(c, "meds.csv", MEDS.encode())
    r = up(c, "meds2.csv", MEDS.encode() + b"")
    assert r["added"] == 0
    assert len(patient_from_database(user_of(c), "PC7001").meds) == 1


def test_list_and_contents_for_a_context_document():
    c = client()
    up(c, "lab.csv", LAB_CSV.encode())
    up(c, "meds.csv", MEDS.encode())
    lst = c.get("/api/reports").json()["reports"]
    ctx = [x for x in lst if x["kind"] == "context"]
    assert len(ctx) == 1
    rows = c.get(f"/api/reports/context/{ctx[0]['id']}/contents").json()["rows"]
    assert rows[0]["name"] == "Metformin" and rows[0]["dose"] == "500 mg"
    assert c.delete(f"/api/reports/context/{ctx[0]['id']}").json() == {"ok": True}
    assert len(patient_from_database(user_of(c), "PC7001").meds) == 0


FHIR = {
    "resourceType": "Bundle", "type": "collection", "entry": [
        {"resource": {"resourceType": "Patient", "id": "PC7002", "gender": "female", "birthDate": "1990-04-01"}},
        {"resource": {"resourceType": "Observation", "subject": {"reference": "Patient/PC7002"}, "effectiveDateTime": "2026-02-10",
                      "code": {"coding": [{"system": "http://loinc.org", "code": "4548-4", "display": "Hemoglobin A1c"}]},
                      "valueQuantity": {"value": 5.8, "unit": "%"}}},
        {"resource": {"resourceType": "Observation", "subject": {"reference": "Patient/PC7002"}, "effectiveDateTime": "2026-02-10",
                      "code": {"text": "Fasting glucose"}, "valueQuantity": {"value": 5.5, "unit": "mmol/L"}}},
        {"resource": {"resourceType": "Observation", "subject": {"reference": "Patient/PC7002"}, "effectiveDateTime": "2026-02-11",
                      "code": {"coding": [{"code": "85354-9"}]},
                      "component": [{"code": {"coding": [{"code": "8480-6"}]}, "valueQuantity": {"value": 142, "unit": "mmHg"}},
                                    {"code": {"coding": [{"code": "8462-4"}]}, "valueQuantity": {"value": 91, "unit": "mmHg"}}]}},
        {"resource": {"resourceType": "Condition", "subject": {"reference": "Patient/PC7002"}, "code": {"text": "Hypertension"},
                      "onsetDateTime": "2023-05-01", "clinicalStatus": {"coding": [{"code": "active"}]}}},
        {"resource": {"resourceType": "MedicationRequest", "subject": {"reference": "Patient/PC7002"}, "status": "active",
                      "medicationCodeableConcept": {"text": "Amlodipine"}, "authoredOn": "2025-01-10", "reasonCode": [{"text": "Hypertension"}]}},
    ]}


def test_fhir_bundle_adds_labs_vitals_conditions_and_medications():
    c = client()
    r = up(c, "bundle.json", json.dumps(FHIR).encode())
    assert r["added"] == 1, r
    p = patient_from_database(user_of(c), "PC7002")
    assert set(p.labs.test) == {"HbA1c", "Fasting glucose"}
    assert round(float(p.labs[p.labs.test == "Fasting glucose"].result.iloc[0]), 0) == 99          # 5.5 mmol/L converted
    assert float(p.daily["Systolic BP"].dropna().iloc[0]) == 142 and float(p.daily["Diastolic BP"].dropna().iloc[0]) == 91
    assert list(p.history.event) == ["Hypertension"] and list(p.meds.medication) == ["Amlodipine"]
    assert p.profile["Sex"] == "Female" and p.profile["Age"] == 35
    assert up(c, "bundle-again.json", json.dumps(FHIR).encode())["added"] == 0


def test_a_file_with_nothing_readable_is_rejected_plainly():
    c = client()
    r = up(c, "empty.txt", b"hello there, nothing useful here")
    assert r["added"] == 0 and r["failed"]
