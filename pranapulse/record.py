"""What each uploaded document adds to a person's record, and what the combined record holds.

A document is NOT analysed on its own and is NOT given a score. Each one is read, its values are stored against the
person, and the analysis (pranapulse.detect) runs later on the combined record: historical measurements together with
the ongoing readings, looking for patterns and changes over time. This module only describes the record so a person can
see what was extracted and what is still missing.
"""
from .reference import RANGES

MISSING_NOTE = {
    "medications": "Medication history is not part of the uploaded record yet.",
    "history": "Previous diagnoses and clinical findings are not part of the uploaded record yet.",
    "cycles": "Cycle data is not part of the uploaded record yet, so the women's health (PCOS) scenario cannot run on uploads.",
}


def _num(x):
    return None if x is None or x != x else float(x)


def contents(labs=(), readings=()):
    """The values one document contributed, as plain rows. labs: test, value, unit, ref_low, ref_high, collected.
    readings: measure, days, first_day, last_day, mean, low, high, unit."""
    rows = []
    for r in labs:
        v = _num(r.get("value"))
        if v is None:
            continue
        lo, hi = _num(r.get("ref_low")), _num(r.get("ref_high"))
        rng = f"{lo:g}–{hi:g}" if lo is not None and hi is not None else f"up to {hi:g}" if hi is not None else f"at least {lo:g}" if lo is not None else ""
        rows.append({"kind": "lab", "name": r["test"], "value": round(v, 4), "unit": r.get("unit") or "", "when": r.get("collected") or "", "range": rng})
    for r in readings:
        rows.append({"kind": "readings", "name": r["measure"], "days": r["days"], "from": r["first_day"], "to": r["last_day"],
                     "mean": round(r["mean"], 2), "low": round(r["low"], 2), "high": round(r["high"], 2), "unit": r.get("unit") or ""})
    return rows


def summarise(labs=(), readings=(), reports=0, files=0):
    """The combined record for one person: which tests and measures it holds, over what period, and what is missing."""
    tests = {}
    for r in labs:
        t = tests.setdefault(r["test"], {"name": r["test"], "unit": r.get("unit") or "", "results": 0, "first": r["collected"], "last": r["collected"]})
        t["results"] += 1
        t["first"], t["last"] = min(t["first"], r["collected"]), max(t["last"], r["collected"])
    measures = [{"name": r["measure"], "days": r["days"], "first": r["first_day"], "last": r["last_day"], "unit": r.get("unit") or ""} for r in readings]
    return {"lab_reports": reports, "reading_files": files, "tests": sorted(tests.values(), key=lambda t: t["name"]),
            "measures": sorted(measures, key=lambda m: m["name"]), "missing": list(MISSING_NOTE.values())}
