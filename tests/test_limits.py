"""Issue #85: every finding carries a Limits line that says what it cannot tell, built from the data flag and the reading counts."""
import uuid

from fastapi.testclient import TestClient

from api.main import app
from api.reports import patient_from_database
from pranapulse.detect import Insight, detect, limits_line
from pranapulse.explain import check_language
from scripts.make_cardio_demo import PID, main as make_files
from tests.test_context import up, user_of


def finding(flag="Sufficient", kind="pattern", evidence=None):
    ev = evidence if evidence is not None else [
        {"signal": "Systolic BP", "days_with_data": "88 of 90 (first), 90 of 90 (last)"},
        {"signal": "LDL cholesterol", "days_with_data": "3 results"}]
    return Insight(kind, "t", flag, [], ev, [], "n")


def test_reading_counts_are_listed_for_each_measure():
    t = limits_line(finding())
    assert "Systolic BP (88 of 90 days earlier, 90 of 90 recently)" in t and "LDL cholesterol (3 results)" in t
    same = limits_line(finding(evidence=[{"signal": "Weight", "days_with_data": "90 of 90 (first), 90 of 90 (last)"}]))
    assert "Weight (90 of 90 days in both windows)" in same


def test_limited_data_is_said_plainly():
    assert "Some expected readings were missing" in limits_line(finding("Limited"))
    assert "enough readings for each measure" in limits_line(finding("Sufficient"))


def test_recent_and_cycle_findings_say_what_they_look_at():
    rec = limits_line(finding(kind="recent", evidence=[{"signal": "Resting heart rate", "days_with_data": "88 baseline, 13 recent"}]))
    assert "88 baseline and 13 recent days" in rec and "latest 14 days" in rec
    assert "cycle start dates only" in limits_line(finding(kind="cycle", evidence=[{"signal": "Cycle length", "days_with_data": "9 cycles"}]))


def test_limits_never_names_a_condition_and_passes_the_wording_check():
    for f in (finding(), finding("Limited"), finding(kind="recent"), finding(kind="cycle"), finding(evidence=[])):
        t = limits_line(f)
        assert not check_language(t), check_language(t)
        assert "does not name or rule out any condition" in t


def test_every_finding_on_the_cardio_demo_has_limits_and_the_api_sends_it(tmp_path):
    c = TestClient(app)
    assert c.post("/api/auth/register", json={"name": "T", "email": f"limits-{uuid.uuid4().hex[:8]}@example.com",
                                              "password": "correct horse battery", "confirm": True}).status_code == 200
    for name in make_files(tmp_path):
        up(c, name, (tmp_path / name).read_bytes())
    ins = detect(patient_from_database(user_of(c), PID))[0]
    assert ins and all(i.limits.startswith("Based on ") for i in ins)
    doc = next(d for d in c.get("/api/documents").json() if d["id"] == PID)
    sent = c.get(f"/api/documents/{doc['key']}/detail").json()["insights"]
    assert sent and all(i["limits"] for i in sent)
