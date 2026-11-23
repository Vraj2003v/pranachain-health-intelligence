"""Issue #95 part 2: Clinical Notes and Medication Adherence are read as context only and never change what is detected."""
import dataclasses
import io

import numpy as np
import pandas as pd

from api.main import record_context
from pranapulse.detect import detect
from pranapulse.loader import load_patient


def workbook(with_context=True):
    days = pd.date_range("2026-01-01", periods=120)
    rng = np.random.default_rng(7)
    sheets = {
        "Patient Profile": pd.DataFrame({"Field": ["Patient ID", "Age", "Sex"], "Value": ["PC0001", 41, "Male"]}),
        "Vitals Daily": pd.DataFrame({"Date": days, "Systolic BP": 118 + np.arange(120) * 0.1 + rng.normal(0, 2, 120),
                                      "Diastolic BP": 76 + rng.normal(0, 2, 120), "Resting HR": 64 + rng.normal(0, 1.5, 120)}),
        "Wearable Daily": pd.DataFrame({"Date": days, "Steps": 8000 - np.arange(120) * 20 + rng.normal(0, 300, 120),
                                        "Sleep Hours": 7 + rng.normal(0, 0.4, 120)}),
        "Lab Results": pd.DataFrame({"Date": ["2026-01-10", "2026-04-10"], "Test Name": ["LDL cholesterol"] * 2, "Result": [118, 96],
                                     "Unit": ["mg/dL"] * 2, "Reference Range": ["0–100"] * 2}),
        "Medical History": pd.DataFrame({"Date": ["2025-05-01"], "Encounter / Type": ["Visit"], "Finding / Event": ["Annual check"], "Status": ["Resolved"], "Notes": [""]}),
        "Medication History": pd.DataFrame({"Medication ID": ["MED-02", "MED-02", "MED-03"], "Medication": ["Metformin", "Metformin XR", "Atorvastatin"],
                                            "Indication": ["x", "x", "y"], "Start Date": ["2025-10-01", "2026-02-01", "2026-03-01"],
                                            "End Date": [None, None, None], "Status": ["Active"] * 3}),
        "Women Health": pd.DataFrame({"Cycle": [], "Start Date": [], "Cycle Length": []}),
    }
    if with_context:
        sheets["Encounters & Notes"] = pd.DataFrame({"Date": ["2026-02-01", "2026-03-15"], "Encounter": ["Primary care", "Follow-up"],
                                                     "Clinical Note": ["Results reviewed.", "Medication plan updated."]})
        sheets["Medication Adherence"] = pd.DataFrame({"Month": ["2026-02-01", "2026-03-01", "2026-03-01"], "Medication ID": ["MED-02", "MED-02", "MED-03"],
                                                       "Estimated Adherence %": [88, 90, 99], "Approx Missed Doses": [4, 3, 0],
                                                       "Source": ["Refill estimate", "Refill estimate", "Self-report"]})
    buf = io.BytesIO()
    with pd.ExcelWriter(buf) as w:
        for name, df in sheets.items():
            df.to_excel(w, sheet_name=name, index=False)
    buf.seek(0)
    return buf


def findings(p):
    insights, held, results = detect(p)
    return [dataclasses.asdict(i) for i in insights], held, {k: dataclasses.astuple(v) if dataclasses.is_dataclass(v) else v for k, v in results.items()}


def test_notes_and_adherence_are_read():
    p = load_patient(workbook())
    assert list(p.encounters.encounter) == ["Primary care", "Follow-up"] and p.encounters.note.iloc[0] == "Results reviewed."
    assert list(p.adherence.adherence) == [88, 99, 90]  # sorted by month, then medication name
    assert set(p.adherence.medication) == {"Metformin XR", "Atorvastatin"}  # the id is shown as its latest medication name


def test_context_never_changes_what_is_detected():
    with_sheets, without = load_patient(workbook(True)), load_patient(workbook(False))
    assert len(without.encounters) == 0 and len(without.adherence) == 0
    a, b = findings(with_sheets), findings(without)
    assert a[0] and a == b


def test_missing_or_renamed_sheets_give_empty_context():
    buf = workbook(True)
    sheets = pd.read_excel(buf, sheet_name=None)
    sheets["Encounters & Notes"] = sheets["Encounters & Notes"].rename(columns={"Clinical Note": "Text"})
    del sheets["Medication Adherence"]
    out = io.BytesIO()
    with pd.ExcelWriter(out) as w:
        for name, df in sheets.items():
            df.to_excel(w, sheet_name=name, index=False)
    out.seek(0)
    p = load_patient(out)
    assert len(p.encounters) == 0 and len(p.adherence) == 0
    assert record_context(p) == {"notes": [], "adherence": []}


def test_record_context_is_plain_values_for_the_api():
    rc = record_context(load_patient(workbook()))
    assert rc["notes"][0] == {"date": "2026-02-01", "encounter": "Primary care", "note": "Results reviewed."}
    assert rc["adherence"][0] == {"month": "2026-02", "medication": "Metformin XR", "adherence": 88.0, "missed": 4.0, "source": "Refill estimate"}
