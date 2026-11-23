"""Make the cardiovascular demo files: a synthetic patient (PC8101) whose blood pressure, heart rate and recovery drift
the wrong way over six months while LDL cholesterol rises, with a history of hypertension. All data is synthetic.

Run:  python scripts/make_cardio_demo.py            (writes demo-files/cardio/)
Upload the files in any order from the app; the cardiovascular pattern should appear.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PID = "PC8101"
OUT = Path(__file__).resolve().parent.parent / "demo-files" / "cardio"

LAB_ROWS = [("2026-01-12", "LDL cholesterol", 118), ("2026-03-16", "LDL cholesterol", 134), ("2026-06-22", "LDL cholesterol", 152)]


def readings(seed=11, days=181):
    rng = np.random.default_rng(seed)
    d = pd.date_range("2026-01-01", periods=days)
    t = np.linspace(0, 1, days)
    return pd.DataFrame({
        "Patient ID": PID, "Date": d.strftime("%Y-%m-%d"),
        "Systolic BP": np.round(124 + 18 * t + rng.normal(0, 2.2, days)),
        "Diastolic BP": np.round(79 + 11 * t + rng.normal(0, 1.8, days)),
        "Resting HR": np.round(66 + 9 * t + rng.normal(0, 1.5, days)),
        "HRV ms": np.round(52 - 14 * t + rng.normal(0, 2.5, days)),
        "Steps": np.round(8600 - 3000 * t + rng.normal(0, 600, days)),
    })


def main(out=OUT):
    out.mkdir(parents=True, exist_ok=True)
    r = readings()
    r.iloc[:91].to_csv(out / "daily_readings_jan_to_mar.csv", index=False)
    r.iloc[91:].to_csv(out / "daily_readings_apr_to_jun.csv", index=False)
    for date, test, value in LAB_ROWS:            # a lab report holds one collection date, so one file per draw
        pd.DataFrame({"Patient ID": PID, "Date": [date], "Test": [test], "Result": [value], "Unit": "mg/dL",
                      "Reference Range": "0-100"}).to_csv(out / f"lipid_panel_{date}.csv", index=False)
    (out / "clinic_summary.txt").write_text(
        f"Clinic summary\nPatient ID: {PID}\nAge: 58\nSex: Male\nVisit date: 2026-06-22\n\n"
        "Diagnoses:\n- Hypertension (2021-05-03)\n- High cholesterol (2024-02-14)\n\n"
        "Medications:\n- Amlodipine 5 mg daily for hypertension since 2021-06-01\n\n"
        "Notes:\nHome blood pressure has been creeping up since the spring.\n")
    return sorted(p.name for p in out.iterdir())


if __name__ == "__main__":
    print("\n".join(main(Path(sys.argv[1]) if len(sys.argv) > 1 else OUT)))
