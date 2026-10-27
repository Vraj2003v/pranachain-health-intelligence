"""Each disease section shown in the app must be traceable: right section, evidence, safe wording, 90-day baseline."""
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from _patients import patients  # noqa: E402

spec = importlib.util.spec_from_file_location("verify_sections", ROOT / "scripts" / "verify_sections.py")
verify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify)

DEMO = list(patients(None, 5))


@pytest.mark.parametrize("name,insights,_", DEMO, ids=[d[0] for d in DEMO])
def test_every_flagged_section_passes_its_checks(name, insights, _):
    for ins in insights:
        assert verify.check(ins) == [], (name, ins.title, verify.check(ins))


def test_all_three_sections_appear_in_the_demo_patients():
    sections = {ins.scenario for _, insights, _ in DEMO for ins in insights}
    assert sections == {"Metabolic health", "Cardiovascular / hypertension", "Women's health (PCOS)"}
