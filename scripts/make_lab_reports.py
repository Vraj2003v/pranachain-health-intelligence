"""Turn patient workbooks into separate, synthetic lab reports (one per collection date) for testing document upload.

    python scripts/make_lab_reports.py --src path/to/workbooks --out reports_out PC0021 PC0433 ...

Each report is labelled SYNTHETIC. Three layouts rotate across patients so the parser meets different test names,
units and column names: A clean PDF, B PDF with other names and SI units, C CSV with other headers.
Also writes expected.csv: the lab-based changes (with dates) found in the original workbook.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from pranapulse.detect import detect
from pranapulse.loader import load_patient

S = getSampleStyleSheet()
OTHER_NAMES = {"HbA1c": "Hemoglobin A1c", "Fasting glucose": "Glucose, fasting", "Total cholesterol": "Cholesterol, total",
               "LDL cholesterol": "LDL-C", "HDL cholesterol": "HDL-C", "WBC": "White blood cells", "Platelets": "Platelet count",
               "Creatinine": "Creatinine, serum", "Vitamin D": "25-OH Vitamin D", "Hemoglobin": "Hgb"}
# standard unit -> (SI unit, factor from standard to SI)
SI = {("HbA1c", "%"): ("mmol/mol", lambda v: round((v - 2.15) * 10.929)), ("Fasting glucose", "mg/dL"): ("mmol/L", lambda v: round(v / 18.016, 2)),
      ("Total cholesterol", "mg/dL"): ("mmol/L", lambda v: round(v / 38.67, 2)), ("Creatinine", "mg/dL"): ("umol/L", lambda v: round(v * 88.4, 1))}


def rng(lo, hi):
    if pd.notna(lo) and pd.notna(hi):
        return f"{lo:g}–{hi:g}"
    return f"<{hi:g}" if pd.notna(hi) else (f">{lo:g}" if pd.notna(lo) else "")


def rows_for(labs, layout):
    out = []
    for r in labs.itertuples():
        name, val, unit = r.test, r.result, r.unit
        if layout in ("B",):
            name = OTHER_NAMES.get(name, name)
            if (r.test, unit) in SI:
                unit, f = SI[(r.test, unit)]
                val = f(val)
        out.append([name, f"{val:g}", unit, rng(r.ref_low, r.ref_high)])
    return out


def pdf(path, pid, date, age, sex, rows, lab="Test Lab (fictional)"):
    d = SimpleDocTemplate(str(path), pagesize=A4, topMargin=40, bottomMargin=40)
    el = [Paragraph("<b>SYNTHETIC TEST DATA - NOT A REAL PATIENT OR LAB</b>", S["Title"]), Paragraph(f"Laboratory Report - {lab}", S["Heading2"]),
          Paragraph(f"Patient ID: {pid}<br/>Age: {age:g} &nbsp; Sex: {sex}<br/>Collection date: {date}", S["Normal"]), Spacer(1, 12)]
    t = Table([["Test", "Result", "Unit", "Reference range"]] + rows, colWidths=[170, 70, 80, 120])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey), ("GRID", (0, 0), (-1, -1), .4, colors.grey), ("FONTSIZE", (0, 0), (-1, -1), 10)]))
    d.build(el + [t])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("patients", nargs="+")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    expected = []
    for n, pid in enumerate(a.patients):
        p = load_patient(Path(a.src) / f"{pid}.xlsx")
        layout = "ABC"[n % 3]
        age, sex = float(p.profile.get("Age") or 0), p.profile.get("Sex") or "Unknown"
        folder = out / pid
        folder.mkdir(exist_ok=True)
        for date, labs in p.labs.groupby(p.labs.date.dt.strftime("%Y-%m-%d")):
            base = folder / f"{pid}_lab_{date}"
            if layout == "C":
                df = pd.DataFrame(rows_for(labs, "A"), columns=["Analyte", "Value", "Units", "Reference Interval"])
                df.insert(0, "Patient", pid)
                df.insert(1, "Collected", date)
                df.to_csv(str(base) + ".csv", index=False)
            else:
                pdf(str(base) + ".pdf", pid, date, age, sex, rows_for(labs, layout), "Test Lab B (fictional)" if layout == "B" else "Test Lab (fictional)")
        ins, _, _ = detect(p)
        lab_on = [(o["label"], o["date"]) for i in ins for o in i.onsets if o.get("kind") == "lab"]
        expected.append({"patient": pid, "layout": layout, "reports": p.labs.date.nunique(), "lab_changes": "; ".join(f"{l} {d}" for l, d in sorted(lab_on)) or "none"})
    pd.DataFrame(expected).to_csv(out / "expected.csv", index=False)
    print(f"{len(expected)} patients written to {out}")


if __name__ == "__main__":
    main()
