"""One command that checks every demo path and prints a pass/fail table to paste into docs/results/demo-rehearsal.md.

    python scripts/demo_check.py [dataset-folder] [PCOS-patient-id]

Checks: the built-in demo patients, the cardiovascular upload set, and (when a dataset folder is given) a PCOS patient.
"""
import io
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pranapulse.demo_data import all_demo_workbooks      # noqa: E402
from pranapulse.detect import detect                     # noqa: E402
from pranapulse.loader import load_patient               # noqa: E402


def insights_of(source):
    return detect(load_patient(source))[0]


def check_demo_patients():
    out = {}
    for name, data in all_demo_workbooks().items():
        out[name[5]] = [(i.kind, i.scenario) for i in insights_of(io.BytesIO(data if isinstance(data, bytes) else data.getvalue()))]
    kinds = lambda k: {s for _, s in out.get(k, [])}
    return [("Demo A shows a metabolic pattern", any(k == "pattern" and "Metabolic" in s for k, s in out.get("A", []))),
            ("Demo B (stable) shows nothing", not out.get("B")),
            ("Demo D shows a cardiovascular finding", any("Cardiovascular" in s for s in kinds("D"))),
            ("Demo E shows an irregular-cycle finding", any(k == "cycle" for k, _ in out.get("E", [])))]


def check_cardio_upload():
    from api.reports import patient_from_database
    from fastapi.testclient import TestClient
    from api.main import app
    from scripts.make_cardio_demo import PID, main
    c = TestClient(app)
    c.post("/api/auth/register", json={"name": "Check", "email": f"demo-check-{__import__('uuid').uuid4().hex[:8]}@example.com", "password": "correct horse battery", "confirm": True})
    with tempfile.TemporaryDirectory() as d:
        for f in main(Path(d)):
            c.post("/api/documents", files=[("files", (f, (Path(d) / f).read_bytes()))])
    me = {"id": c.get("/api/auth/me").json()["id"]}
    ins = detect(patient_from_database(me, PID))[0]
    return [("Cardio upload set merges into one record", patient_from_database(me, PID) is not None),
            ("Cardio upload set gives a cardiovascular pattern", any(i.kind == "pattern" and "Cardiovascular" in i.scenario for i in ins))]


def check_dataset_pcos(folder, pid):
    f = Path(folder) / f"{pid}.xlsx"
    if not f.exists():
        return [(f"PCOS dataset patient {pid} found in {folder}", False)]
    ins = insights_of(f)
    return [(f"{pid} shows an irregular-cycle finding", any(i.kind == "cycle" for i in ins)),
            (f"{pid} finding cites PCOS from the history", any(i.kind == "cycle" and any("pcos" in x.lower() or "polycystic" in x.lower() for x in i.context) for i in ins))]


if __name__ == "__main__":
    rows = check_demo_patients() + check_cardio_upload()
    if len(sys.argv) > 1:
        rows += check_dataset_pcos(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "PC0466")
    print("| Check | Result |\n|---|---|")
    for name, ok in rows:
        print(f"| {name} | {'pass' if ok else 'FAIL'} |")
    sys.exit(0 if all(ok for _, ok in rows) else 1)
