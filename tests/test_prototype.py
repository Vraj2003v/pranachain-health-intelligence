import io

import pandas as pd

from pranapulse.demo_data import PERSONAS, make_workbook
from pranapulse.detect import detect
from pranapulse.explain import check_language
from pranapulse.loader import load_patient, to_dates


def run(key):
    p = load_patient(io.BytesIO(make_workbook(key)))
    return detect(p)


def test_all_three_date_formats_load():
    for key in ("A", "B", "C"):  # serial numbers, real datetimes, text dates
        p = load_patient(io.BytesIO(make_workbook(key)))
        assert len(p.daily) == 365 and p.daily.index.min() == pd.Timestamp("2025-09-01")


def test_to_dates_serial():
    assert to_dates(pd.Series([45901])).iloc[0] == pd.Timestamp("2025-09-01")


def test_drifting_patient_gets_one_pattern_with_history():
    insights, held, _ = run("A")
    assert [i.kind for i in insights] == ["pattern"] and insights[0].flag == "Sufficient"
    assert any("Borderline glycemic" in c for c in insights[0].context)


def test_stable_patient_is_quiet():
    assert run("B")[0] == []


def test_missing_data_downgrades_flag():
    insights, _, _ = run("C")
    assert all(i.flag == "Limited" for i in insights)


def test_cardio_and_cycle_patterns():
    assert run("D")[0][0].scenario.startswith("Cardiovascular")
    assert run("E")[0][0].kind == "cycle"


def test_every_narrative_passes_guardrails():
    for key in PERSONAS:
        for i in run(key)[0]:
            assert check_language(i.narrative) == []


def test_guardrail_catches_bad_wording():
    assert check_language("You have diabetes and should go to the emergency room.")
    assert check_language("This pattern may be worth discussing with a provider.") == []


def test_llm_fallback_and_guardrail():
    from pranapulse import llm
    ins = run("A")[0][0]
    good = "These readings may have shifted, and it may be worth discussing with a healthcare provider."
    assert llm.explain(ins, generate=lambda *a: good) == (good, "local model")
    bad = "This is dangerous and you have a disease."
    assert llm.explain(ins, generate=lambda *a: bad)[1] == "template"

    def boom(*a):
        raise OSError("no server")
    assert llm.explain(ins, generate=boom)[1] == "template"
    assert llm.available(url="http://localhost:9") is False
