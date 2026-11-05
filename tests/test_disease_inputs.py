"""Meeting 3 feedback: each disease area uses only its own measures, and the usual range is shown as context."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from _patients import patients  # noqa: E402

from pranapulse import ask, reference as ref  # noqa: E402
from pranapulse.detect import disease_input_problems  # noqa: E402
from pranapulse.explain import check_language  # noqa: E402

DEMO = list(patients(None, 5))


@pytest.mark.parametrize("name,insights,_", DEMO, ids=[d[0] for d in DEMO])
def test_no_finding_uses_a_measure_from_another_disease(name, insights, _):
    assert disease_input_problems(insights) == []


def test_hba1c_never_belongs_to_cardiovascular_and_ldl_never_to_metabolic():
    assert "HbA1c" not in ref.AREAS["Cardiovascular / hypertension"].labs
    assert "Fasting glucose" not in ref.AREAS["Cardiovascular / hypertension"].labs
    assert "LDL cholesterol" not in ref.AREAS["Metabolic health"].labs
    assert "weight" not in ref.AREAS["Cardiovascular / hypertension"].signals
    assert "sbp" not in ref.AREAS["Metabolic health"].signals


def test_the_guard_catches_a_measure_in_the_wrong_area():
    insights = next(i for _, i, _ in DEMO if any(x.signals for x in i))
    ins = next(x for x in insights if x.signals)
    bad_area = "Metabolic health" if ins.scenario != "Metabolic health" else "Cardiovascular / hypertension"
    ins.scenario = bad_area
    ins.signals = [k for k in ("sbp", "weight") if k not in ref.AREAS[bad_area].signals]
    assert disease_input_problems([ins])


@pytest.mark.parametrize("name,insights,_", DEMO, ids=[d[0] for d in DEMO])
def test_every_finding_says_where_it_sits_against_the_usual_range(name, insights, _):
    for ins in insights:
        assert ins.tier in (ref.TIER_OUT, ref.TIER_IN, ref.TIER_NONE)
        for e in ins.evidence:
            assert e["reference_range"] and e["range_position"]


def test_range_helpers():
    assert ref.position(135, ref.RANGES["sbp"]) == "above"
    assert ref.position(80, ref.RANGES["sbp"]) == "below"
    assert ref.position(110, ref.RANGES["sbp"]) == "within"
    assert ref.position(80, ref.RANGES["weight"]) is None
    assert ref.tier(["within", None]) == ref.TIER_IN
    assert ref.tier(["within", "above"]) == ref.TIER_OUT
    assert ref.tier([None]) == ref.TIER_NONE


def test_an_improving_measure_is_never_reported_as_a_finding():
    for _, insights, _ in DEMO:
        for ins in insights:
            assert "improv" not in ins.title.lower()


def test_assistant_only_sees_measures_from_the_area_being_discussed():
    res = DEMO[0][2]
    picked = ask._pick(res, "tell me more", area="Metabolic health")
    assert picked and all(r.key in ref.AREAS["Metabolic health"].signals for r in picked)
    picked = ask._pick(res, "tell me more", area="Cardiovascular / hypertension")
    assert picked and all(r.key in ref.AREAS["Cardiovascular / hypertension"].signals for r in picked)


def test_area_is_inferred_from_the_question_when_none_is_chosen():
    assert ask.infer_area("how is my blood pressure") == "Cardiovascular / hypertension"
    assert ask.infer_area("how is my sleep") == "Metabolic health"
    assert ask.infer_area("is my cycle regular") == "Women's health (PCOS)"
    assert ask.infer_area("how is my weight and blood pressure") is None
    assert ask.infer_area("anything", "Metabolic health") == "Metabolic health"


def test_range_question_has_a_safe_answer():
    text = ask.answer_template("What is the usual range?", [])
    assert not check_language(text)


def test_attention_level_is_rule_based_and_never_a_diagnosis():
    for _, insights, _ in DEMO:
        by_area = ref.attention_by_area(insights)
        assert set(by_area) == set(ref.AREAS)
        for sc, a in by_area.items():
            assert a["level"] in (ref.ATT_NONE, ref.ATT_WATCH, ref.ATT_DISCUSS)
            assert "does not name a condition" in a["note"]
            banned = [m for m in check_language(a["level"] + " " + a["reason"] + " " + a["note"]) if not m.startswith("must")]
            assert not banned
            if not any(i.scenario == sc for i in insights):
                assert a["level"] == ref.ATT_NONE


def test_attention_rules():
    class F:  # a minimal finding
        def __init__(self, tier, flag="Sufficient"): self.tier, self.flag = tier, flag
    assert ref.attention([])[0] == ref.ATT_NONE
    assert ref.attention([F(ref.TIER_OUT)])[0] == ref.ATT_DISCUSS
    assert ref.attention([F(ref.TIER_OUT, "Limited")])[0] == ref.ATT_WATCH
    assert ref.attention([F(ref.TIER_IN)])[0] == ref.ATT_WATCH
    assert ref.attention([F(ref.TIER_NONE)])[0] == ref.ATT_WATCH
    assert ref.attention([F(ref.TIER_IN), F(ref.TIER_NONE)])[0] == ref.ATT_DISCUSS
