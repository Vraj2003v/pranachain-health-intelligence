"""Fabricated patients in the same workbook layout as the real data, for demos and tests.

Everything here is invented by this script; none of it comes from the PranaChain dataset.
"""
import io

import numpy as np
import pandas as pd

START = pd.Timestamp("2025-09-01")
DAYS = 365
EPOCH = pd.Timestamp("1899-12-30")


def _ramp(rng, a, b, noise, n=DAYS):
    base = np.linspace(a, b, n)
    return base + rng.normal(0, noise, n)


def _dates(values, style):
    values = pd.to_datetime(pd.Series(values))
    if style == "serial":
        return ((values - EPOCH).dt.days).astype(int)
    if style == "text":
        return values.dt.strftime("%Y-%m-%d")
    return values


PERSONAS = {
    "A": dict(label="Demo A — several measures drifting the wrong way", id="DEMO-A", age=52, sex="Female", style="serial",
              weight=(88, 92.5), steps=(7000, 5200), sleep=(7.0, 6.2), sbp=(124, 125), rhr=(66, 67), hrv=(40, 39),
              hba1c=(5.9, 6.3), glucose=(104, 112), history=["Borderline glycemic markers"], meds=[("Metformin XR", "Metabolic management")],
              wear_missing=0.04, cycles="regular"),
    "B": dict(label="Demo B — stable, nothing to flag", id="DEMO-B", age=45, sex="Male", style="datetime",
              weight=(79, 79.2), steps=(8200, 8300), sleep=(7.2, 7.2), sbp=(118, 118), rhr=(62, 62), hrv=(46, 46),
              hba1c=(5.3, 5.3), glucose=(92, 93), history=[], meds=[], wear_missing=0.03, cycles=None),
    "C": dict(label="Demo C — same drift as A, but much data missing", id="DEMO-C", age=58, sex="Female", style="text",
              weight=(88, 92.5), steps=(7000, 5200), sleep=(7.0, 6.2), sbp=(124, 125), rhr=(66, 67), hrv=(40, 39),
              hba1c=(5.9, 6.3), glucose=(104, 112), history=["Borderline glycemic markers"], meds=[("Metformin XR", "Metabolic management")],
              wear_missing=0.45, cycles=None, lab_dates=2),
    "D": dict(label="Demo D — blood pressure and heart rate rising", id="DEMO-D", age=61, sex="Male", style="serial",
              weight=(84, 84.5), steps=(6500, 6100), sleep=(6.8, 6.7), sbp=(124, 136), dbp=(78, 86), rhr=(66, 73), hrv=(42, 34),
              hba1c=(5.6, 5.6), glucose=(98, 99), history=["Hypertension"], meds=[("Amlodipine", "Blood pressure management")],
              wear_missing=0.04, cycles=None),
    "E": dict(label="Demo E — irregular cycles", id="DEMO-E", age=29, sex="Female", style="datetime",
              weight=(70, 70.3), steps=(8000, 8100), sleep=(7.1, 7.0), sbp=(112, 112), rhr=(64, 64), hrv=(48, 48),
              hba1c=(5.2, 5.2), glucose=(90, 91), history=["PCOS"], meds=[], wear_missing=0.03, cycles="irregular"),
}


def make_workbook(key: str, seed: int = 7) -> bytes:
    sp = PERSONAS[key]
    rng = np.random.default_rng(seed + ord(key))
    days = pd.date_range(START, periods=DAYS)
    st = sp["style"]

    sbp = _ramp(rng, *sp["sbp"], 4)
    dbp = _ramp(rng, *sp.get("dbp", (sp["sbp"][0] * 0.64, sp["sbp"][1] * 0.64)), 3)
    weight = _ramp(rng, *sp["weight"], 0.35)
    vit = pd.DataFrame({
        "Date": _dates(days, st), "Systolic BP": sbp.round(), "Diastolic BP": dbp.round(),
        "Resting HR": _ramp(rng, *sp["rhr"], 3).round(), "Weight kg": weight.round(1),
        "BMI": (weight / 1.68 ** 2).round(1), "SpO2 %": rng.normal(97, 0.6, DAYS).round(1),
        "Temp C": rng.normal(36.7, 0.15, DAYS).round(1), "Respiratory Rate": rng.normal(11.5, 0.7, DAYS).round(1)})
    vit.loc[rng.random(DAYS) < 0.03, ["Systolic BP", "Diastolic BP"]] = np.nan

    wea = pd.DataFrame({
        "Date": _dates(days, st), "Steps": _ramp(rng, *sp["steps"], 900).clip(500).round(),
        "Sleep Hours": _ramp(rng, *sp["sleep"], 0.7).clip(3, 10).round(1),
        "Active Minutes": rng.normal(45, 8, DAYS).clip(0).round(), "Resting HR": vit["Resting HR"],
        "HRV ms": _ramp(rng, *sp["hrv"], 5).clip(5).round(), "Calories kcal": rng.normal(1900, 120, DAYS).round(),
        "Sedentary Hours": rng.normal(9.5, 1.0, DAYS).round(1), "Stress Score 1-10": rng.normal(5, 1, DAYS).clip(1, 10).round(1)})
    gone = rng.random(DAYS) < sp["wear_missing"]
    wea.loc[gone, wea.columns[1:]] = np.nan

    lab_dates = pd.to_datetime(["2025-09-10", "2025-12-10", "2026-03-10", "2026-06-10", "2026-08-20"])
    if sp.get("lab_dates"):
        lab_dates = lab_dates[[0, -1]][: sp["lab_dates"]]
    k = np.linspace(0, 1, len(lab_dates))
    rows = []
    for i, d in enumerate(lab_dates):
        rows += [
            (d, "HbA1c", round(sp["hba1c"][0] + (sp["hba1c"][1] - sp["hba1c"][0]) * k[i], 2), "%", "4.0–5.6"),
            (d, "Fasting glucose", round(sp["glucose"][0] + (sp["glucose"][1] - sp["glucose"][0]) * k[i], 1), "mg/dL", "70–99"),
            (d, "LDL cholesterol", round(rng.normal(100, 6), 1), "mg/dL", "0–100"),
            (d, "TSH", round(rng.normal(1.8, 0.2), 2), "mIU/L", "0.4–4.0")]
    labs = pd.DataFrame(rows, columns=["Date", "Test Name", "Result", "Unit", "Reference Range"])
    labs["Date"] = _dates(labs["Date"], st)

    hist = [(pd.Timestamp("2024-02-10"), "Annual preventive assessment", "Completed", "Routine history updated")]
    hist += [(pd.Timestamp("2025-03-12"), h, "Monitoring", "Follow-up planned") for h in sp["history"]]
    mh = pd.DataFrame(hist, columns=["Date", "Finding / Event", "Status", "Notes"])
    mh["Date"] = _dates(mh["Date"], st)

    meds = pd.DataFrame(
        [(m, "10 mg", "Once daily", "Oral", pd.Timestamp("2025-03-20"), pd.NaT, "Active", ind, "Tolerated", "Started after review")
         for m, ind in sp["meds"]],
        columns=["Medication", "Dose", "Frequency", "Route", "Start Date", "End Date", "Status", "Indication",
                 "Tolerance / Adverse Effect", "Change Rationale"])
    meds["Start Date"] = _dates(meds["Start Date"], st) if len(meds) else meds["Start Date"]

    if sp["cycles"]:
        gaps = rng.normal(29, 1.5, 13) if sp["cycles"] == "regular" else rng.choice([24, 33, 41, 48, 29, 55], 13)
        starts = START + pd.to_timedelta(np.cumsum(np.r_[0, gaps[:-1]]), unit="D")
        women = pd.DataFrame({"Cycle": range(1, 14), "Start Date": _dates(starts, st), "Cycle Length": gaps.round(),
                              "Bleeding Days": rng.integers(3, 7, 13), "Symptoms": "Mild cramps", "Severity": "Mild"})
    else:
        women = pd.DataFrame({"Cycle": ["—"], "Start Date": [np.nan], "Cycle Length": [np.nan], "Bleeding Days": [np.nan],
                              "Symptoms": ["Not applicable"], "Severity": [np.nan]})

    profile = pd.DataFrame({"Field": ["Patient ID", "Age", "Sex", "Height (cm)", "Data Window"],
                            "Value": [sp["id"], sp["age"], sp["sex"], 168, "2025-09-01 to 2026-08-31"]})
    blank = lambda cols: pd.DataFrame(columns=cols)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        for name, df in [("Patient Profile", profile), ("Medical History", mh), ("Medication History", meds),
                         ("Lab Results", labs), ("Vitals Daily", vit), ("Wearable Daily", wea),
                         ("Habits Weekly", blank(["Week"])), ("Symptoms Timeline", blank(["Date", "Symptom"])),
                         ("Encounters & Notes", blank(["Date", "Encounter"])),
                         ("Medication Adherence", blank(["Month"])), ("Women Health", women)]:
            df.to_excel(xw, sheet_name=name, index=False)
    return buf.getvalue()


def all_demo_workbooks():
    return {PERSONAS[k]["label"]: make_workbook(k) for k in PERSONAS}
