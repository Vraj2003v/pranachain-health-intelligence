"""The cardiovascular demo files (scripts/make_cardio_demo.py) upload as separate documents, merge into one record,
and produce a cardiovascular pattern that uses blood pressure, heart rate, a lipid result and the hypertension history."""
import random
import uuid
from pathlib import Path

from api.reports import patient_from_database
from pranapulse.detect import detect
from fastapi.testclient import TestClient

from api.main import app
from tests.test_context import up, user_of
from scripts.make_cardio_demo import PID, main as make_files


def client():
    c = TestClient(app)          # its own account each time (importing test_context's counter twice makes two accounts share an email)
    assert c.post("/api/auth/register", json={"name": "T", "email": f"cardio-{uuid.uuid4().hex[:8]}@example.com",
                                              "password": "correct horse battery", "confirm": True}).status_code == 200
    return c


def _upload_all(tmp_path, seed=0):
    files = make_files(tmp_path)
    random.Random(seed).shuffle(files)
    c = client()
    for name in files:
        r = up(c, name, (tmp_path / name).read_bytes())
        assert r["added"] == 1, (name, r)
    return c, patient_from_database(user_of(c), PID)


def test_files_merge_into_one_record(tmp_path):
    _, p = _upload_all(tmp_path)
    assert len(p.daily) == 181 and len(p.labs) == 3 and len(p.meds) == 1 and len(p.history) == 2


def test_cardiovascular_pattern_is_found_with_labs_and_history(tmp_path):
    _, p = _upload_all(tmp_path)
    ins, _, _ = detect(p)
    pat = [i for i in ins if i.kind == "pattern" and "Cardiovascular" in i.scenario]
    assert pat, [(i.kind, i.title) for i in ins]
    ev = {e["signal"] for e in pat[0].evidence}
    assert "LDL cholesterol" in ev and {"Systolic BP", "Resting heart rate"} & ev
    assert any("ypertension" in x for x in pat[0].context)


def test_upload_order_does_not_change_the_result(tmp_path):
    a = detect(_upload_all(tmp_path / "a", 1)[1])[0]
    b = detect(_upload_all(tmp_path / "b", 2)[1])[0]
    assert [(i.kind, i.title, i.flag) for i in a] == [(i.kind, i.title, i.flag) for i in b]


def test_no_diagnosis_wording_in_the_cardiovascular_finding(tmp_path):
    _, p = _upload_all(tmp_path)
    for i in detect(p)[0]:
        assert "you have" not in i.narrative.lower() and "diagnos" not in i.narrative.lower()
