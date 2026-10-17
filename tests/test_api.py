import io

from fastapi.testclient import TestClient

from api.main import app
from pranapulse.demo_data import make_workbook

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
PW = "correct horse battery"


def user(email, name="Test User", confirm=True):
    c = TestClient(app)
    r = c.post("/api/auth/register", json={"name": name, "email": email, "password": PW, "confirm": confirm})
    return c, r


def test_requires_sign_in():
    assert TestClient(app).get("/api/documents").status_code == 401


def test_register_rules_and_first_user_is_admin():
    c, r = user("first@example.com")
    assert r.status_code == 200 and r.json()["role"] == "admin"
    c2, r2 = user("second@example.com")
    assert r2.json()["role"] == "clinician"
    assert user("first@example.com")[1].status_code == 409
    assert user("x@example.com", confirm=False)[1].status_code == 400
    bad = TestClient(app).post("/api/auth/register", json={"name": "A", "email": "a@example.com", "password": "short", "confirm": True})
    assert bad.status_code == 400


def test_login_wrong_password_and_logout():
    user("login@example.com")
    c = TestClient(app)
    assert c.post("/api/auth/login", json={"email": "login@example.com", "password": "nope-nope-nope"}).status_code == 401
    assert c.post("/api/auth/login", json={"email": "login@example.com", "password": PW}).status_code == 200
    assert c.get("/api/auth/me").json()["email"] == "login@example.com"
    c.post("/api/auth/logout")
    assert c.get("/api/auth/me").status_code == 401


def test_demo_documents_scenarios_and_detail():
    c, _ = user("demo@example.com")
    assert c.post("/api/documents/demo").json()["added"] == 5
    assert c.post("/api/documents/demo").json()["added"] == 0   # duplicates are skipped
    rows = c.get("/api/documents").json()
    assert len(rows) == 5 and {r["status"] for r in rows} == {"Flagged", "Quiet"}
    assert {r["scenario"] for r in rows if r["scenario"]} == {
        "Metabolic health", "Cardiovascular / hypertension", "Women's health (PCOS)"}
    d = c.get(f"/api/documents/{rows[0]['key']}/detail").json()
    assert d["insights"][0]["context"] and d["series"]["weight"]["hasProjection"]
    assert any("band" in row for row in d["series"]["weight"]["rows"])


def test_users_cannot_see_each_others_documents():
    a, _ = user("a1@example.com")
    b, _ = user("b1@example.com")
    a.post("/api/documents", files=[("files", ("wb.xlsx", io.BytesIO(make_workbook("A")), XLSX))])
    key = a.get("/api/documents").json()[0]["key"]
    assert b.get("/api/documents").json() == []
    assert b.get(f"/api/documents/{key}/detail").status_code == 404
    assert b.delete(f"/api/documents/{key}").status_code == 404


def test_bad_file_reported_and_delete_works():
    c, _ = user("del@example.com")
    r = c.post("/api/documents", files=[("files", ("bad.xlsx", io.BytesIO(b"not a workbook"), XLSX)),
                                        ("files", ("ok.xlsx", io.BytesIO(make_workbook("B")), XLSX))]).json()
    assert r["added"] == 1 and "bad.xlsx" in r["failed"]
    key = c.get("/api/documents").json()[0]["key"]
    assert c.get(f"/api/documents/{key}/file").content[:2] == b"PK"
    assert c.delete(f"/api/documents/{key}").status_code == 200 and c.get("/api/documents").json() == []


def test_audit_log_admin_only_and_account_deletion():
    admin = TestClient(app)
    c, _ = user("plain@example.com")
    assert c.get("/api/audit").status_code == 403
    assert c.delete("/api/auth/account").status_code == 200
    assert c.get("/api/auth/me").status_code == 401
