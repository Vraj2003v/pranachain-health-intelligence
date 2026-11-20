"""Turn patient workbooks into separate, synthetic reports of DAILY READINGS (vitals and wearable data) for testing upload.

    python scripts/make_reading_reports.py --src path/to/workbooks --out readings_out PC0021 PC0433 ...

Each patient's year is cut into ~30-day windows. For every window two reports are written, one for the vitals measures
(blood pressure, heart rate, weight, BMI, SpO2, temperature, respiratory rate) and one for the wearable measures (steps,
sleep, active minutes, HRV, calories, sedentary hours, stress). The formats rotate so the reader meets different layouts,
column names and units: wide CSV, wide XLSX with other headers, long CSV (Date, Metric, Value, Unit) and PDF tables.
Weight in lb and sleep in minutes appear for some patients. Every report is labelled SYNTHETIC.
Also writes expected_findings.csv: the findings (with onset dates) found in the ORIGINAL workbook, which uploading
all the readings (and the lab reports) should reproduce.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from pranapulse.detect import detect
from pranapulse.loader import load_patient
from pranapulse.readings import VITALS, WEARABLE

S = getSampleStyleSheet()
WINDOW = 30
OTHER_HEADERS = {"Systolic BP": "SBP", "Diastolic BP": "DBP", "Resting HR": "Pulse", "Weight kg": "Weight (kg)", "BMI": "BMI",
                 "SpO2 %": "SpO2", "Temp C": "Temperature", "Respiratory Rate": "Resp rate", "Steps": "Step count",
                 "Sleep Hours": "Sleep (h)", "Active Minutes": "Active min", "HRV ms": "HRV", "Calories kcal": "Calories",
                 "Sedentary Hours": "Sedentary hours", "Stress Score 1-10": "Stress score"}


def table(window, measures, unit_variant):
    """DataFrame for one window: Date + one column per measure, with a unit variant (lb / minutes) where it applies."""
    df = pd.DataFrame({"Date": window.index.strftime("%Y-%m-%d")})
    for m in measures:
        name = m
        col = window[m].round(6).tolist()
        if unit_variant and m == "Weight kg":
            name, col = "Weight (lb)", (window[m] * 2.2046226218).round(6).tolist()
        if unit_variant and m == "Sleep Hours":
            name, col = "Sleep (min)", (window[m] * 60).round(4).tolist()
        df[name] = col
    return df


def write_pdf(path, pid, df, title):
    doc = SimpleDocTemplate(str(path), pagesize=landscape(A4), leftMargin=24, rightMargin=24, topMargin=24, bottomMargin=24)
    head = [Paragraph("SYNTHETIC TEST DATA - NOT A REAL PATIENT", S["Normal"]), Paragraph(f"{title} - Test Clinic (fictional)", S["Heading2"]),
            Paragraph(f"Patient ID: {pid}", S["Normal"]), Spacer(1, 10)]
    data = [list(df.columns)] + [["" if pd.isna(v) else (f"{v:.10g}" if not isinstance(v, str) else v) for v in row] for row in df.itertuples(index=False)]
    t = Table(data, repeatRows=1)
    t.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 7), ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                           ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke), ("ALIGN", (1, 0), (-1, -1), "CENTER")]))
    doc.build(head + [t])


def write_report(path_stem, pid, window, measures, variant, unit_variant, label):
    """Write one report; returns the file name. variant: 0 wide CSV, 1 wide XLSX with other headers, 2 long CSV, 3 PDF."""
    start = window.index[0].strftime("%Y-%m-%d")
    base = f"{pid}_{label}_{start}"
    if variant == 2:
        rows = []
        for m in measures:
            std = m
            for d, v in window[m].items():
                if pd.notna(v):
                    rows.append({"Patient ID": pid, "Date": d.strftime("%Y-%m-%d"), "Metric": m, "Value": round(float(v), 6), "Unit": ""})
        out = path_stem / f"{base}_long.csv"
        pd.DataFrame(rows).to_csv(out, index=False)
        return out.name
    df = table(window, measures, unit_variant)
    if variant == 1:
        df = df.rename(columns={c: OTHER_HEADERS.get(c, c) for c in df.columns})
    if variant == 3:
        out = path_stem / f"{base}.pdf"
        write_pdf(out, pid, df, "Vitals record" if label == "vitals" else "Wearable export")
        return out.name
    df.insert(0, "Patient ID", pid)
    if variant == 1:
        out = path_stem / f"{base}.xlsx"
        df.to_excel(out, index=False)
    else:
        out = path_stem / f"{base}.csv"
        df.to_csv(out, index=False)
    return out.name


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("patients", nargs="+")
    a = ap.parse_args()
    out = Path(a.out)
    expected = []
    for n, pid in enumerate(a.patients):
        p = load_patient(Path(a.src) / f"{pid}.xlsx")
        folder = out / pid
        folder.mkdir(parents=True, exist_ok=True)
        unit_variant = n % 2 == 1
        daily = p.daily.sort_index()
        windows = [daily.iloc[i:i + WINDOW] for i in range(0, len(daily), WINDOW)]
        for k, w in enumerate(windows):
            if len(w) < 3:
                continue
            write_report(folder, pid, w, [m for m in VITALS if m in w], (n + k) % 4, unit_variant, "vitals")
            write_report(folder, pid, w, [m for m in WEARABLE if m in w], (n + k + 1) % 4, unit_variant, "wearable")
        ins, held, _ = detect(p)
        expected.append({"patient": pid, "findings": " | ".join(f"{i.title} [{i.flag}]: " + "; ".join(f"{o['key']} {o['date']}" for o in i.onsets) for i in ins) or "none"})
        print(pid, len(list(folder.glob('*'))), "files,", len(ins), "findings")
    pd.DataFrame(expected).to_csv(out / "expected_findings.csv", index=False)


if __name__ == "__main__":
    main()
