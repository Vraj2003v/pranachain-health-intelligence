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


def _steps_patient(drop_days, drop=1800.0):
    """150 days of steady steps; the last `drop_days` days are `drop` lower."""
    from types import SimpleNamespace
    import numpy as np
    import pandas as pd
    days = pd.date_range("2026-03-01", periods=150, freq="D")
    rng = np.random.default_rng(3)
    s = pd.Series(8000 + rng.normal(0, 300, 150), index=days)
    s.iloc[-drop_days:] -= drop
    return SimpleNamespace(daily=pd.DataFrame({"Steps": s}), window=(days[0], days[-1]))


def test_a_change_in_only_the_latest_week_is_not_flagged():
    # persistence: a one-week dip is not enough, the change has to hold in both of the latest two weeks
    assert detect.recent_check(_steps_patient(7), "steps") is None


def test_a_change_that_holds_for_two_weeks_is_flagged():
    hit = detect.recent_check(_steps_patient(14), "steps")
    assert hit and hit["diff"] < -1000


def test_steps_need_a_larger_minimum_change():
    assert SIGNALS["steps"].min_abs >= 1000
    # a 900-step drop is below the minimum, even if it holds for two weeks
    assert detect.recent_check(_steps_patient(14, drop=900.0), "steps") is None


def test_persistence_share_is_a_fraction_of_the_threshold():
    from pranapulse.signals import RECENT_PERSIST_SHARE
    assert 0.5 <= RECENT_PERSIST_SHARE <= 1.0
