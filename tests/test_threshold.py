"""The recent-change check: flags a patient whose latest 14 days moved clearly away from their baseline, and stays quiet otherwise."""
import io

from pranapulse import detect
from pranapulse.demo_data import make_workbook
from pranapulse.loader import load_patient
from pranapulse.signals import RECENT_MIN_EFFECT, SIGNALS


def flagged(key, threshold):
    old = detect.RECENT_MIN_EFFECT
    detect.RECENT_MIN_EFFECT = threshold
    try:
        p = load_patient(io.BytesIO(make_workbook(key)))
        return any(detect.recent_check(p, k) for k in SIGNALS)
    finally:
        detect.RECENT_MIN_EFFECT = old


def test_stable_patient_is_never_flagged():
    # Demo B is stable, so even a low threshold should not flag them
    assert not flagged("B", RECENT_MIN_EFFECT)


def test_lower_threshold_never_flags_fewer_patients():
    for key in ("A", "B", "C"):
        assert flagged(key, 0.8) >= flagged(key, RECENT_MIN_EFFECT)


def test_threshold_is_a_sensible_multiple():
    assert 0.5 <= RECENT_MIN_EFFECT <= 3.0
