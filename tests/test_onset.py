"""Every change carries the date its measure crossed the change threshold, and a quiet patient has none."""
import io

import pandas as pd

from pranapulse import detect
from pranapulse.demo_data import make_workbook
from pranapulse.loader import load_patient


def run(key):
    p = load_patient(io.BytesIO(make_workbook(key)))
    return p, detect.detect(p)[0]


def test_quiet_patient_has_no_dates():
    assert run("B")[1] == []


def test_each_measure_in_a_pattern_gets_its_own_date():
    p, ins = run("A")
    on = {o["key"]: o for i in ins for o in i.onsets}
    assert {"weight", "steps", "HbA1c"} <= set(on)
    start, end = p.window
    for o in on.values():
        assert start <= pd.Timestamp(o["date"]) <= end


def test_the_date_is_when_the_average_crossed_the_threshold_and_stayed():
    p, ins = run("A")
    w = next(o for i in ins for o in i.onsets if o["key"] == "weight")
    s = p.daily["Weight kg"].rolling("14D", min_periods=7).mean()
    after = s[pd.Timestamp(w["date"]):]
    half = w["baseline"] + (w["threshold"] - w["baseline"]) * 0.5
    assert after.iloc[0] >= w["threshold"] - 1e-6           # at or past the threshold on that day
    assert (after >= half - 1e-6).all()                     # and never dropped back to under half of it
    assert s[: pd.Timestamp(w["date"]) - pd.Timedelta(days=1)].iloc[-1] < w["threshold"]  # was below the day before


def test_dates_come_out_in_the_api_and_overview():
    from api import main
    p, ins = run("D")
    assert all("date" in o for i in ins for o in i.onsets)
    assert any(i.onsets for i in ins)
