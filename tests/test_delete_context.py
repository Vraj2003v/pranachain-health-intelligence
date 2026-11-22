"""Deleting documents must also remove medications, diagnoses, cycles and notes that came from uploaded files."""
import uuid

from fastapi.testclient import TestClient

from api.main import app
from tests.test_context import CLINICAL, CYCLES, LAB_CSV, MEDS, up


def _client():
    c = TestClient(app)
    assert c.post("/api/auth/register", json={"name": "T", "email": f"del-{uuid.uuid4().hex[:8]}@example.com",
                                              "password": "correct horse battery", "confirm": True}).status_code == 200
    return c


def _load(c):
    for name, data in (("lab.csv", LAB_CSV), ("cycles.csv", CYCLES), ("meds.csv", MEDS), ("summary.txt", CLINICAL)):
        assert up(c, name, data.encode())["added"] == 1


def test_delete_all_removes_the_context_records_too():
    c = _client()
    _load(c)
    assert c.get("/api/patients/PC7001/record").json()["cycles"]["count"] == 8
    c.delete("/api/documents")
    assert c.get("/api/patients/PC7001/record").status_code == 404
    _load_again = up(c, "lab.csv", LAB_CSV.encode())          # a new upload must not bring the old records back
    rec = c.get("/api/patients/PC7001/record").json()
    assert rec["cycles"]["count"] == 0 and rec["medications"] == [] and rec["notes"] == 0


def test_deleting_the_built_record_removes_the_context_records_too():
    c = _client()
    _load(c)
    docs = c.get("/api/documents").json()
    doc = next(d for d in docs if "PC7001" in str(d.get("filename") or d.get("name") or d))
    c.delete(f"/api/documents/{doc['key']}")
    assert c.get("/api/patients/PC7001/record").status_code == 404
