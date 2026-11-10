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
    # Measures the kickoff lists for this disease that are shown in the overview as context only. They do not feed findings
    # or the attention level, so finding IDs and the 900-workbook counts are unchanged.
    context_signals: tuple = ()
    context_labs: tuple = ()


AREAS = {
    "Cardiovascular / hypertension": Area("Cardiovascular / hypertension", "Cardiovascular",
                                          ("sbp", "dbp", "rhr", "hrv", "steps"), ("LDL cholesterol",),
                                          context_signals=("sleep", "weight"), context_labs=("Total cholesterol", "HDL cholesterol")),
    "Metabolic health": Area("Metabolic health", "Metabolic",
                             ("weight", "steps", "sleep"), ("HbA1c", "Fasting glucose"),
                             context_labs=("Total cholesterol", "LDL cholesterol", "HDL cholesterol", "Triglycerides")),
    "Women's health (PCOS)": Area("Women's health (PCOS)", "Women's health", (), (), cycle=True,
                                  context_signals=("weight", "sleep", "steps")),
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


# Added after the Meeting 3 follow-up: a plain "attention level" for each disease area.
# It is a rule on the findings already shown (not a trained model, not a probability and not a diagnosis).
ATT_NONE = "No clear change"
ATT_WATCH = "Worth watching"
ATT_DISCUSS = "Worth discussing with a healthcare provider"
ATT_NOTE = "A rule-based screening level from the findings shown. It does not name a condition and is not a measure of likelihood."


_RANK = {ATT_NONE: 0, ATT_WATCH: 1, ATT_DISCUSS: 2}
# Measures outside their usual range lift an area to "worth watching". Only a finding (a change) can lift it to "worth discussing".
# To let a number of steady out-of-range measures reach "worth discussing" too, set this to that number. It is left off because in the
# 1,000 synthetic journeys nearly every patient is above range on blood pressure and below on sleep, so a count would flag almost everyone.
OUTSIDE_FOR_DISCUSS = None


def overview(scenario, insights, results, labs, cycles):
    """All of one area's own measures together (Meeting 3: look at every measure of the disease, not only the ones that changed).

    Returns {rows, ranged, outside, changed, text}. Each row is one measure with its latest value, where it sits against the
    usual range, and whether a finding in this area involves it. A value that stays outside the range without changing is
    counted here, so it is not lost just because no change was found.
    """
    area = AREAS[scenario]
    mine = [i for i in insights if i.scenario == scenario]
    used = {k for i in mine for k in i.signals}
    used_labs = {e["signal"] for i in mine for e in i.evidence if e.get("source") == "Lab Results"}
    rows = []

    def row(key, label, value, unit, dec, rng, changed, usable=True, context=False):
        pos = position(value, rng) if usable else None
        rows.append({"key": key, "label": label, "value": None if not usable or value is None else round(float(value), 4),
                     "unit": unit, "decimals": dec, "range": text(rng) if rng else "no usual range",
                     "position": pos or ("no range" if usable and value is not None else "no data"), "changed": bool(changed),
                     "context": context})

    for k in area.signals:
        r = results.get(k)
        if r is None:
            continue
        row(k, r.label, r.mean_last, r.unit, r.decimals, RANGES.get(k), k in used, usable=r.flag != "Insufficient")
    for test in area.labs:
        sub = labs[labs.test == test].sort_values("date") if labs is not None and len(labs) else None
        if sub is None or sub.empty:
            continue
        last = sub.iloc[-1]
        v = float(last.result)
        row(test, test, v, str(last.unit), 2 if abs(v) < 10 else 1, lab_range(last.ref_low, last.ref_high, last.unit), test in used_labs)
    if area.cycle and cycles is not None and len(cycles) >= 4:
        row("cycle", "Cycle length", float(cycles.cycle_length.mean()), "days", 0, CYCLE_RANGE, bool(mine))

    every = {k for i in insights for k in i.signals}
    every_labs = {e["signal"] for i in insights for e in i.evidence if e.get("source") == "Lab Results"}
    for k in area.context_signals:
        r = results.get(k)
        if r is not None:
            row(k, r.label, r.mean_last, r.unit, r.decimals, RANGES.get(k), k in every, usable=r.flag != "Insufficient", context=True)
    for test in area.context_labs:
        sub = labs[labs.test == test].sort_values("date") if labs is not None and len(labs) else None
        if sub is None or sub.empty:
            continue
        last = sub.iloc[-1]
        v = float(last.result)
        row(test, test, v, str(last.unit), 2 if abs(v) < 10 else 1, lab_range(last.ref_low, last.ref_high, last.unit), test in every_labs, context=True)

    core = [r for r in rows if not r["context"]]
    ranged = [r for r in core if r["position"] in ("above", "below", "within")]
    outside = [r for r in ranged if r["position"] in ("above", "below")]
    changed = [r for r in core if r["changed"]]
    if not core:
        line = "No readings for this area in this file."
    else:
        line = (f"{len(outside)} of {len(ranged)} measures with a usual range are outside it. "
                f"{len(changed)} of {len(core)} measures changed.")
    return {"rows": rows, "ranged": len(ranged), "outside": len(outside), "changed": len(changed), "text": line}


def overview_by_area(insights, results, labs, cycles):
    return {sc: overview(sc, insights, results, labs, cycles) for sc in AREAS}


def attention(insights, ov=None):
    """Attention level for one disease area. Returns (level, reason).

    Uses the area's findings and, when given, the overview of all its measures (see overview()).
    """
    if not insights:
        level, why = ATT_NONE, "No finding in this area."
    else:
        outside = [i for i in insights if i.tier == TIER_OUT and i.flag == "Sufficient"]
        if outside:
            level, why = ATT_DISCUSS, f"{len(outside)} finding(s) outside the usual range, with enough data behind them."
        elif len(insights) >= 2:
            level, why = ATT_DISCUSS, f"{len(insights)} separate findings in this area."
        else:
            level, why = ATT_WATCH, "One finding, either within the usual range, on the personal baseline only, or with limited data."
    if ov and ov["outside"]:
        n = ov["outside"]
        l2 = ATT_DISCUSS if OUTSIDE_FOR_DISCUSS and n >= OUTSIDE_FOR_DISCUSS else ATT_WATCH
        w2 = f"{n} of {ov['ranged']} measures with a usual range are outside it."
        if _RANK[l2] > _RANK[level]:
            level, why = l2, w2
        elif _RANK[l2] == _RANK[level]:
            why = why + " " + w2
    return level, why


def attention_by_area(insights, ov=None):
    """{scenario: {level, reason, note}} for every disease area. ov is overview_by_area() when available."""
    out = {}
    for sc in AREAS:
        level, why = attention([i for i in insights if i.scenario == sc], (ov or {}).get(sc))
        out[sc] = {"level": level, "reason": why, "note": ATT_NOTE}
    return out
