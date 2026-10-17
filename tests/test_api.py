import io

from fastapi.testclient import TestClient

from api.main import app
from pranapulse.demo_data import make_workbook

client = TestClient(app)


def new():
    return client.post("/api/session").json()["session"]


def test_demo_session_lists_five_patients_with_scenarios():
    sid = new()
    assert client.post(f"/api/session/{sid}/demo").json()["patients"] == 5
    rows = client.get(f"/api/session/{sid}/patients").json()
    assert len(rows) == 5 and {r["status"] for r in rows} == {"Flagged", "Quiet"}
    assert {r["scenario"] for r in rows if r["scenario"]} == {
        "Metabolic health", "Cardiovascular / hypertension", "Women's health (PCOS)"}


def test_upload_detail_has_projection_and_history():
    sid = new()
    f = ("wb.xlsx", io.BytesIO(make_workbook("A")),
         "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    r = client.post(f"/api/session/{sid}/upload", files=[("files", f)]).json()
    assert r["patients"] == 1 and not r["failed"]
    key = client.get(f"/api/session/{sid}/patients").json()[0]["key"]
    d = client.get(f"/api/session/{sid}/patients/{key}").json()
    assert d["insights"][0]["context"] and d["series"]["weight"]["hasProjection"]
    assert any("band" in row for row in d["series"]["weight"]["rows"])


def test_bad_file_is_reported_not_fatal():
    sid = new()
    f = ("bad.xlsx", io.BytesIO(b"not a workbook"), "application/octet-stream")
    r = client.post(f"/api/session/{sid}/upload", files=[("files", f)]).json()
    assert r["patients"] == 0 and "bad.xlsx" in r["failed"]
