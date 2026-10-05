"""Scan every patient workbook and write one summary row per patient.

Usage:  python scripts/scan_dataset.py data/raw data/processed/patient_summary.csv

Handles the three date formats found in the dataset (Excel serial numbers, real
datetimes, and text dates). Never writes anything into version control: the default
output folder is gitignored.
"""
import glob
import os
import sys
from multiprocessing import Pool

import numpy as np
import pandas as pd

EXCEL_EPOCH = pd.Timestamp("1899-12-30")


def to_date(value):
    """Convert an Excel serial number, a datetime, or a text date to a Timestamp."""
    if isinstance(value, pd.Timestamp):
        return value
    if isinstance(value, str):
        return pd.to_datetime(value, errors="coerce")
    return EXCEL_EPOCH + pd.to_timedelta(float(value), "D")


def yearly_change(series):
    """Approximate total change over the window from a straight-line fit."""
    s = series.dropna()
    if len(s) < 30:
        return np.nan
    return np.polyfit(np.arange(len(s)), s.values, 1)[0] * len(s)


def scan(path):
    try:
        sheets = pd.read_excel(path, sheet_name=None)
        profile = sheets["Patient Profile"].set_index("Field").Value.to_dict()
        labs, vitals, wear = sheets["Lab Results"], sheets["Vitals Daily"], sheets["Wearable Daily"]
        women = sheets["Women Health"]
        row = {
            "file": os.path.basename(path),
            "folder": os.path.basename(os.path.dirname(path)),
            "date_type": type(sheets["Medical History"].Date.iloc[0]).__name__,
            "age": profile.get("Age"),
            "sex": profile.get("Sex"),
            "findings": "|".join(sheets["Medical History"]["Finding / Event"].astype(str)),
            "medications": "|".join(sorted(set(sheets["Medication History"].Medication.astype(str)))),
            "lab_dates": labs.Date.nunique(),
            "bp_days_missing": int(vitals["Systolic BP"].isna().sum()),
            "wearable_days_missing": int(wear.Steps.isna().sum()),
            "sbp_change": yearly_change(vitals["Systolic BP"]),
            "weight_change_kg": yearly_change(vitals["Weight kg"]),
            "steps_change": yearly_change(wear.Steps),
            "sleep_change_h": yearly_change(wear["Sleep Hours"]),
            "cycles": int(women["Cycle Length"].notna().sum()),
            "cycle_length_mean": women["Cycle Length"].mean(),
            "cycle_length_sd": women["Cycle Length"].std(),
            "adherence_mean": sheets["Medication Adherence"]["Estimated Adherence %"].mean(),
        }
        hba1c = labs[labs["Test Name"] == "HbA1c"].sort_values("Date").Result
        row["hba1c_results"] = len(hba1c)
        row["hba1c_first"] = hba1c.iloc[0] if len(hba1c) else np.nan
        row["hba1c_last"] = hba1c.iloc[-1] if len(hba1c) else np.nan
        return row
    except Exception as exc:  # keep scanning; report the bad file in the output
        return {"file": os.path.basename(path), "error": str(exc)}


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "data/raw"
    out = sys.argv[2] if len(sys.argv) > 2 else "data/processed/patient_summary.csv"
    files = sorted(glob.glob(os.path.join(src, "**", "*.xlsx"), recursive=True))
    with Pool() as pool:
        rows = pool.map(scan, files, chunksize=10)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"Scanned {len(files)} workbooks -> {out}")
