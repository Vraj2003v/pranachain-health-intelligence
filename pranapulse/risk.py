"""Risk factors from ONE document, and a plain rule-based screening score.

A patient uploads a document (a lab report, or a report of daily readings). This module looks at the values in that
document only and answers two questions:
  1. Which results are outside their usual range, in which direction, by how much, and which health area they relate to?
  2. What is the screening level for each area?

Everything here is a written rule. It is not a trained model, not a probability, and not a diagnosis.

Severity (how far past the nearest limit of the usual range the value is):
    less than 10%   -> mild      (1 point)
    10% up to 25%   -> moderate  (2 points)
    25% or more     -> marked    (3 points)
Screening level for an area, from the points of the risk factors found in it:
    0 points                      -> Low
    1 to 3 points, none marked    -> Moderate
    4 or more points, or any one marked factor -> High
The usual ranges are general adult reference values (to be confirmed with the business partner). A lab result uses the
reference range printed on its own report. A measure with no usual range is not scored.
"""
from .reference import AREAS, RANGES

CV, MET, WOM = "Cardiovascular / hypertension", "Metabolic health", "Women's health (PCOS)"

# rule key -> (area, which side is a risk, factor name). Lab tests use the printed name.
LAB_RULES = {
    "LDL cholesterol": (CV, "high", "High LDL cholesterol"),
    "Total cholesterol": (CV, "high", "High total cholesterol"),
    "HDL cholesterol": (CV, "low", "Low HDL cholesterol"),
    "Triglycerides": (MET, "high", "High triglycerides"),
    "HbA1c": (MET, "high", "High HbA1c (long-term blood sugar)"),
    "Fasting glucose": (MET, "high", "High fasting glucose"),
}
# daily measures (standard names from pranapulse.readings) -> (area, side, factor name, usual range low, high, unit)
READING_RULES = {
    "Systolic BP": (CV, "high", "High systolic blood pressure", RANGES["sbp"].low, RANGES["sbp"].high, "mmHg"),
    "Diastolic BP": (CV, "high", "High diastolic blood pressure", RANGES["dbp"].low, RANGES["dbp"].high, "mmHg"),
    "Resting HR": (CV, "high", "High resting heart rate", RANGES["rhr"].low, RANGES["rhr"].high, "bpm"),
    "BMI": (MET, "high", "High body mass index", 18.5, 24.9, "kg/m²"),
    "Sleep Hours": (MET, "low", "Short sleep", RANGES["sleep"].low, RANGES["sleep"].high, "h"),
}
SEVERITY = {1: "mild", 2: "moderate", 3: "marked"}
AREA_SHORT = {CV: "Cardiovascular", MET: "Metabolic", WOM: "Women's health"}
METHOD = ("Each result outside its usual range in a risk direction is a risk factor: mild (under 10% past the limit) = 1 point, "
          "moderate (10% to 25%) = 2, marked (25% or more) = 3. An area is Low with 0 points, Moderate with 1 to 3 points, "
          "and High with 4 or more points or any marked factor. This is a screening rule on the values in this document. "
          "It is not a diagnosis, not a probability, and not a trained model.")


def _num(x):
    return None if x is None or x != x else float(x)


def severity(distance):
    return 1 if distance < 0.10 else 2 if distance < 0.25 else 3


def judge(value, low, high):
    """('above'|'below'|'within', distance past the nearest limit as a fraction of that limit)."""
    value, low, high = _num(value), _num(low), _num(high)
    if value is None:
        return None, 0.0
    if high is not None and value > high:
        return "above", (value - high) / abs(high) if high else 0.0
    if low is not None and value < low:
        return "below", (low - value) / abs(low) if low else 0.0
    return "within", 0.0


def _range_text(low, high, unit):
    low, high = _num(low), _num(high)
    if low is not None and high is not None:
        return f"{low:g}–{high:g} {unit}".strip()
    if high is not None:
        return f"up to {high:g} {unit}".strip()
    if low is not None:
        return f"at least {low:g} {unit}".strip()
    return "no usual range"


def assess(labs=(), readings=()):
    """labs: dicts with test, value, unit, ref_low, ref_high. readings: dicts with measure, value (the document's mean).

    Returns the full picture for one document (or one person's latest values): every checked result, the risk factors,
    results outside the range that belong to none of the three areas, and the screening level per area.
    """
    checked, factors, other = [], [], []
    for r in labs:
        test, value, unit = r["test"], _num(r.get("value")), r.get("unit") or ""
        if value is None:
            continue
        rule = LAB_RULES.get(test)
        pos, dist = judge(value, r.get("ref_low"), r.get("ref_high"))
        item = {"label": test, "value": round(value, 4), "unit": unit, "range": _range_text(r.get("ref_low"), r.get("ref_high"), unit),
                "position": pos or "no range", "area": rule[0] if rule else None, "source": "lab"}
        if pos is None or (_num(r.get("ref_low")) is None and _num(r.get("ref_high")) is None):
            item["position"] = "no range"
        checked.append(item)
        _file(item, rule, pos, dist, factors, other)
    for r in readings:
        m, value = r["measure"], _num(r.get("value"))
        rule = READING_RULES.get(m)
        if value is None or rule is None:
            continue
        pos, dist = judge(value, rule[3], rule[4])
        item = {"label": m, "value": round(value, 2), "unit": rule[5], "range": _range_text(rule[3], rule[4], rule[5]),
                "position": pos, "area": rule[0], "source": "readings"}
        checked.append(item)
        _file(item, rule, pos, dist, factors, other)
    factors.sort(key=lambda f: (-f["severity"], f["label"]))
    areas = []
    for scen in (CV, MET, WOM):
        mine = [c for c in checked if c["area"] == scen]
        fs = [f for f in factors if f["area"] == scen]
        pts = sum(f["severity"] for f in fs)
        level = None if not mine else "High" if pts >= 4 or any(f["severity"] == 3 for f in fs) else "Moderate" if pts >= 1 else "Low"
        areas.append({"area": scen, "short": AREA_SHORT[scen], "level": level, "points": pts, "checked": len(mine),
                      "factors": [f["label"] for f in fs]})
    return {"checked": checked, "factors": factors, "other_outside": other, "areas": areas, "method": METHOD}


def _file(item, rule, pos, dist, factors, other):
    if pos not in ("above", "below"):
        return
    if rule is None:
        other.append({**item, "note": "Outside its range, but not one of the three scored health areas."})
        return
    side = rule[1]
    if (side == "high" and pos != "above") or (side == "low" and pos != "below"):
        return
    sev = severity(dist)
    name = rule[2]
    factors.append({**item, "factor": name, "distance_pct": round(dist * 100, 1), "severity": sev, "severity_label": SEVERITY[sev],
                    "text": f"{item['label']} is {item['value']:g} {item['unit']}, {pos} the usual range ({item['range']}), "
                            f"{dist * 100:.0f}% past the limit: {SEVERITY[sev]}."})
