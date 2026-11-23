"""PCOS is shown from the provided dataset, not only from uploaded files.

The dataset is not stored in the repository. Point PRANAPULSE_DATASET at the folder that holds the patient workbooks
(for example PC0466.xlsx) and these tests run; without it they are skipped.
"""
import os
from pathlib import Path

import pytest

from pranapulse.detect import detect
from pranapulse.loader import load_patient

FOLDER = os.environ.get("PRANAPULSE_DATASET")
PATIENT = os.environ.get("PRANAPULSE_PCOS_PATIENT", "PC0466")
needs_dataset = pytest.mark.skipif(not FOLDER or not (Path(FOLDER or ".") / f"{PATIENT}.xlsx").exists(),
                                   reason="set PRANAPULSE_DATASET to the folder with the patient workbooks")


@needs_dataset
def test_pcos_patient_gets_an_irregular_cycle_finding_with_history():
    ins, _, _ = detect(load_patient(Path(FOLDER) / f"{PATIENT}.xlsx"))
    cyc = [i for i in ins if i.kind == "cycle"]
    assert cyc, [(i.kind, i.title) for i in ins]
    assert cyc[0].scenario == "Women's health (PCOS)"
    assert any("pcos" in x.lower() or "polycystic" in x.lower() for x in cyc[0].context)


@needs_dataset
def test_cycle_finding_wording_is_safe_and_has_evidence():
    ins, _, _ = detect(load_patient(Path(FOLDER) / f"{PATIENT}.xlsx"))
    c = [i for i in ins if i.kind == "cycle"][0]
    assert "healthcare provider" in c.narrative and "diagnos" not in c.narrative.lower()
    assert c.evidence and c.evidence[0]["signal"] == "Cycle length"
