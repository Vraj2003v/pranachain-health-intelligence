"""Check that every disease section the app shows is built correctly and can be traced to the readings.

Run:  python scripts/verify_sections.py                  (the five demo patients)
      python scripts/verify_sections.py data/raw 900     (a folder of .xlsx workbooks, first N files)
Writes docs/results/section_checks.csv (one row per flagged section) and prints a summary per section.
A check that fails is listed with the patient, so it can be fixed or explained before meeting 3.

Checks for each flagged section:
  1. it belongs to one of the three sections (cardiovascular, metabolic, women's health)
  2. it has evidence rows (what was compared, with the dates)
  3. the wording check passes (no diagnosis, no dose, no risk score)
  4. recent-change findings: baseline window is the 90 days before the latest 14 days,
     and the averages in the sentence match the evidence table
  5. the data-sufficiency flag agrees with the number of days with data
  6. cycle findings: at least 4 cycles were used
"""
import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _patients import patients                         # noqa: E402
from pranapulse.detect import SCENARIO                 # noqa: E402
from pranapulse.explain import check_language          # noqa: E402
from pranapulse.signals import RECENT_DAYS, WINDOW_DAYS  # noqa: E402

SECTIONS = set(SCENARIO.values())

def days(win):
    """'01 Jan 2026 to 31 Mar 2026' -> number of days in the window."""
    import pandas as pd
    a, b = [pd.Timestamp(x.strip()) for x in win.split(" to ")]
    return (b - a).days + 1


def check(ins):
    """Return a list of problems for one insight (empty = all checks passed)."""
    bad = []
    if ins.scenario not in SECTIONS:
        bad.append(f"not in a known section: {ins.scenario!r}")
    if not ins.evidence:
        bad.append("no evidence rows")
    problems = check_language(ins.narrative)
    if problems:
        bad.append("wording check: " + "; ".join(problems))
    if ins.kind == "recent" and ins.evidence:
        e = ins.evidence[0]
        if days(e["first_window"]) != WINDOW_DAYS:
            bad.append(f"baseline window is {days(e['first_window'])} days, expected {WINDOW_DAYS}")
        if days(e["last_window"]) != RECENT_DAYS:
            bad.append(f"recent window is {days(e['last_window'])} days, expected {RECENT_DAYS}")
        for mean in (e["first_mean"], e["last_mean"]):
            if mean.split()[0] not in ins.narrative:
                bad.append(f"average {mean} is in the table but not in the sentence")
        n_base, n_rec = [int(x) for x in re.findall(r"\d+", e["days_with_data"])]
        should = "Sufficient" if n_base >= 72 and n_rec >= 11 else "Limited"
        if ins.flag != should:
            bad.append(f"flag is {ins.flag} but {n_base} baseline and {n_rec} recent days give {should}")
    if ins.kind == "cycle" and ins.evidence:
        n = int(re.findall(r"\d+", ins.evidence[0]["days_with_data"])[0])
        if n < 4:
            bad.append(f"only {n} cycles used")
    return bad


def main(folder=None, limit=10):
    rows, per_section, patients_seen = [], {s: {"patients": 0, "ok": 0, "failed": 0} for s in sorted(SECTIONS)}, 0
    for name, insights, _ in patients(folder, limit):
        patients_seen += 1
        seen = set()
        for ins in insights:
            problems = check(ins)
            sec = ins.scenario if ins.scenario in SECTIONS else "(none)"
            stats = per_section.setdefault(sec, {"patients": 0, "ok": 0, "failed": 0})
            if sec not in seen:
                stats["patients"] += 1
                seen.add(sec)
            stats["failed" if problems else "ok"] += 1
            rows.append({"patient": name, "section": sec, "kind": ins.kind, "title": ins.title, "flag": ins.flag,
                         "result": "FAIL" if problems else "pass", "problems": " | ".join(problems)})

    out = Path(__file__).resolve().parent.parent / "docs" / "results" / "section_checks.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["patient", "section", "kind", "title", "flag", "result", "problems"])
        w.writeheader()
        w.writerows(rows)

    print(f"{patients_seen} patients checked; {len(rows)} flagged sections written to {out}")
    print(f"{'Section':32} {'Patients':>8} {'Passed':>7} {'Failed':>7}")
    for sec, s in per_section.items():
        print(f"{sec:32} {s['patients']:>8} {s['ok']:>7} {s['failed']:>7}")
    fails = [r for r in rows if r["result"] == "FAIL"]
    for r in fails:
        print("FAIL", r["patient"], "-", r["section"], "-", r["problems"])
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else None, int(sys.argv[2]) if len(sys.argv) > 2 else 10))
