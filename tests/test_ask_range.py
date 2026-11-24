"""'What is the usual range?' answers only with measures that are in the record, not with a generic or unrelated measure."""
from types import SimpleNamespace as NS

from pranapulse.ask import answer

LABS = [{"test": "HbA1c", "value": 6.1, "unit": "%", "low": 4.0, "high": 5.6},
        {"test": "Fasting glucose", "value": 107.0, "unit": "mg/dL", "low": 70.0, "high": 99.0},
        {"test": "LDL cholesterol", "value": 150.0, "unit": "mg/dL", "low": None, "high": 100.0}]


def test_metabolic_area_lists_only_its_labs_and_no_sleep():
    text, source, *_ = answer("What is the usual range?", [], "Metabolic health", use_model=False, results={}, profile={"labs": LABS})
    assert source == "patient record"
    assert "HbA1c 4–5.6 %" in text and "Fasting glucose 70–99 mg/dL" in text and "above it" in text
    assert "Sleep" not in text and "LDL" not in text


def test_a_named_lab_gets_only_its_own_range():
    text, *_ = answer("What is the normal range for HbA1c?", [], None, use_model=False, results={}, profile={"labs": LABS})
    assert "HbA1c" in text and "Fasting" not in text


def test_nothing_in_the_record_falls_back_to_the_standard_answer():
    text, source, *_ = answer("What is the usual range?", [], "Metabolic health", use_model=False, results={}, profile={"labs": []})
    assert source == "template" and "usual adult range" in text


def test_a_lab_the_record_does_not_have_is_said_not_swapped_for_another_measure():
    text, source, *_ = answer("What is the usual range for HbA1c?", [], None, use_model=False, results={}, profile={"labs": [LABS[2]]})
    assert source == "patient record" and "HbA1c is not in this record" in text and "Sleep" not in text and "LDL" not in text


def test_a_reading_with_no_values_is_left_out():
    nan = float("nan")
    res = {"sleep": NS(label="Sleep", mean_last=nan, decimals=1), "resting_hr": NS(label="Resting heart rate", mean_last=73.0, decimals=0)}
    text, *_ = answer("What is the usual range?", [], None, use_model=False, results=res, profile={"labs": []})
    assert "nan" not in text.lower() and "None" not in text
