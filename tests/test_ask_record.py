from pranapulse.ask import answer_profile

REC = {"age": 34, "sex": "Female",
       "medications": [{"name": "Metformin", "detail": "PCOS", "start": "2025-06-01", "status": "Active"},
                      {"name": "Vitamin D", "detail": "", "start": "2026-01-15", "status": ""}],
       "history": [{"name": "Polycystic ovary syndrome", "date": "2024-03-12", "status": "Active"}]}


def test_medications_are_listed_from_the_record():
    t = answer_profile("What medications is this patient on?", REC)
    assert "Metformin (for PCOS, since 2025-06-01, active)" in t and "Vitamin D (since 2026-01-15)" in t


def test_diagnoses_are_listed_from_the_record():
    t = answer_profile("Any previous diagnoses?", REC)
    assert "Polycystic ovary syndrome (2024-03-12, active)" in t


def test_empty_lists_say_so_plainly():
    assert answer_profile("which drugs are they taking", {"medications": []}) == "No medications are recorded for this patient."
    assert answer_profile("medical history", {"history": []}) == "No previous diagnoses or findings are recorded for this patient."


def test_questions_about_findings_are_not_taken_as_record_facts():
    for q in ("Does this mean I have a condition?", "Why was this flagged?", "What should I do next?"):
        assert answer_profile(q, REC) is None


def test_unsafe_characters_in_the_record_are_removed():
    t = answer_profile("medications", {"medications": [{"name": "Drug <script>x</script>", "detail": "", "start": "", "status": ""}]})
    assert "<" not in t and ">" not in t


def test_assistant_answers_medications_through_the_api():
    from fastapi.testclient import TestClient

    from api.main import app
    from tests.test_context import LAB_CSV, MEDS, up
    c = TestClient(app)
    assert c.post("/api/auth/register", json={"name": "T", "email": "ask-record@example.com", "password": "correct horse battery", "confirm": True}).status_code == 200
    up(c, "lab.csv", LAB_CSV.encode())
    up(c, "meds.csv", MEDS.encode())
    docs = c.get("/api/documents").json()
    doc = next(d for d in docs if d["id"] == "PC7001")
    r = c.post(f"/api/documents/{doc['key']}/ask", json={"question": "What medications is the patient on?", "history": []}).json()
    assert "Metformin" in r["text"] and r["source"] == "patient record"
