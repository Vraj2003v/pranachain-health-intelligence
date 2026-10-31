"""Every finding has an ID (F1, F2, ...) and every evidence row has an ID (E1, E2, ...), so a result can be traced."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from _patients import patients  # noqa: E402

DEMO = list(patients(None, 5))


@pytest.mark.parametrize("name,insights,_", DEMO, ids=[d[0] for d in DEMO])
def test_findings_and_evidence_have_unique_ordered_ids(name, insights, _):
    assert [i.insight_id for i in insights] == [f"F{n}" for n in range(1, len(insights) + 1)]
    ids = [e["id"] for i in insights for e in i.evidence]
    assert ids == [f"E{n}" for n in range(1, len(ids) + 1)]
    assert len(set(ids)) == len(ids)


def test_ids_are_the_same_on_every_run():
    first = [[e["id"] for e in i.evidence] for _, ins, _r in patients(None, 5) for i in ins]
    again = [[e["id"] for e in i.evidence] for _, ins, _r in patients(None, 5) for i in ins]
    assert first == again
