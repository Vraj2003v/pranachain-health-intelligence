"""Disease areas, their own measures, and the usual (reference) ranges.

Added after Meeting 3 (2 Nov 2026). The business partner asked for two things:
  1. each disease area looks only at the measures that relate to it, and
  2. the biological reference range is the base, with the person's own variation checked against it.

This file is the single place that says which measures belong to which area, and what the usual range is.
The ranges are general adult reference values and are meant to be confirmed with the partner.
Measures with no universal range (weight, steps, HRV) stay on the personal baseline only; the app says so.
Lab tests use the reference range printed on the patient's own Lab Results sheet.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Area:
    scenario: str          # the name stored on every finding
    short: str             # the disease name shown in the app
    signals: tuple         # daily measures that may feed this area
    labs: tuple            # lab tests that may feed this area
    cycle: bool = False    # uses the cycle-length rule


AREAS = {
    "Cardiovascular / hypertension": Area("Cardiovascular / hypertension", "Cardiovascular",
                                          ("sbp", "dbp", "rhr", "hrv", "steps"), ("LDL cholesterol",)),
    "Metabolic health": Area("Metabolic health", "Metabolic",
                             ("weight", "steps", "sleep"), ("HbA1c", "Fasting glucose")),
    "Women's health (PCOS)": Area("Women's health (PCOS)", "Women's health", (), (), cycle=True),
}


@dataclass(frozen=True)
class Range:
    low: float | None
    high: float | None
    unit: str
    source: str


# Usual adult ranges for the daily measures. None means there is no universal range.
RANGES = {
    "sbp": Range(90, 120, "mmHg", "usual adult resting blood pressure"),
    "dbp": Range(60, 80, "mmHg", "usual adult resting blood pressure"),
    "rhr": Range(60, 100, "bpm", "usual adult resting heart rate"),
    "sleep": Range(7, 9, "h", "usual adult sleep"),
    "weight": None,   # depends on height, so no universal range
    "steps": None,    # no clinical reference range
    "hrv": None,      # depends on age and device
}
CYCLE_RANGE = Range(21, 35, "days", "usual cycle length")


def area_of(key: str) -> str:
    """The area a lone measure is reported under (steps belong to both areas; metabolic is used when reporting alone)."""
    return "Cardiovascular / hypertension" if key in ("sbp", "dbp", "rhr", "hrv") else "Metabolic health"


def allowed_signals(scenario: str) -> tuple:
    return AREAS[scenario].signals if scenario in AREAS else ()


def position(value, rng):
    """'above', 'below' or 'within' the range; None when there is no range or no value."""
    if rng is None or value is None or value != value:
        return None
    if rng.high is not None and value > rng.high:
        return "above"
    if rng.low is not None and value < rng.low:
        return "below"
    return "within"


def text(rng) -> str:
    if rng is None:
        return "no usual range (personal baseline only)"
    if rng.low is not None and rng.high is not None:
        return f"{rng.low:g}–{rng.high:g} {rng.unit}"
    if rng.high is not None:
        return f"up to {rng.high:g} {rng.unit}"
    return f"at least {rng.low:g} {rng.unit}"


def lab_range(lab_low, lab_high, unit) -> Range | None:
    lo = None if lab_low != lab_low else lab_low
    hi = None if lab_high != lab_high else lab_high
    return Range(lo, hi, str(unit), "range printed on the lab result") if (lo is not None or hi is not None) else None


TIER_OUT = "Outside the usual range"
TIER_IN = "Within the usual range, worth watching"
TIER_NONE = "Personal baseline only"


def tier(positions):
    """Overall position of a finding. positions: list of 'above'/'below'/'within'/None for its measures."""
    known = [p for p in positions if p]
    if any(p in ("above", "below") for p in known):
        return TIER_OUT
    if known:
        return TIER_IN
    return TIER_NONE
