"""Validate the three disease sections: do the findings agree with what the record already says, and with known patterns?

Run:  python scripts/validate_scenarios.py data/raw            (all .xlsx workbooks in the folder)
      python scripts/validate_scenarios.py data/raw 100        (first 100)
Writes docs/results/validation_summary.md and docs/results/validation_results.csv.

Two checks, both on synthetic data (neither is a measure of clinical accuracy):

1. History consistency (all workbooks). The detector never uses the Medical History or Medication sheets to decide
   what to report; they only add context to the wording. So we can ask: among people whose recorded history relates
   to a section, how many get a finding in that section, compared with people whose history does not?
   A good detector reports more often for the first group.

2. Known patterns (the five demo patients). Each demo patient is built with a known pattern (or none), so we can count
   true positives, false positives and missed patterns per section and give precision, recall and F1.
"""
import csv
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pranapulse.demo_data import all_demo_workbooks    # noqa: E402
from pranapulse.detect import SCENARIO, detect         # noqa: E402
from pranapulse.loader import load_patient             # noqa: E402
from pranapulse import detect as detect_mod            # noqa: E402
from pranapulse.signals import CLUSTERS, RECENT_MIN_EFFECT  # noqa: E402

SECTIONS = [SCENARIO["cardio"], SCENARIO["metabolic"], SCENARIO["cycle"]]
HISTORY_WORDS = {
    SCENARIO["cardio"]: CLUSTERS["cardio"]["context"],
    SCENARIO["metabolic"]: CLUSTERS["metabolic"]["context"],
    SCENARIO["cycle"]: ["pcos", "polycystic", "thyroid", "cycle"],
}
# What each fabricated demo patient was built to show (see pranapulse/demo_data.py).
DEMO_TRUTH = {
    "Demo A": {SCENARIO["metabolic"]}, "Demo B": set(), "Demo C": {SCENARIO["metabolic"]},
    "Demo D": {SCENARIO["cardio"]}, "Demo E": {SCENARIO["cycle"]},
}
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "results"


def related_history(p, words):
    """True if the Medical History or Medication sheet mentions any of the words."""
    texts = [str(e).lower() for e in p.history.event] + [f"{m} {i}".lower() for m, i in zip(p.meds.medication, p.meds.indication)]
    return any(w in t for w in words for t in texts)


def run(p, threshold):
    """Findings for one patient with the recent-change threshold set to `threshold`."""
    old = detect_mod.RECENT_MIN_EFFECT
    detect_mod.RECENT_MIN_EFFECT = threshold
    try:
        ins, _, _ = detect(p)
    finally:
        detect_mod.RECENT_MIN_EFFECT = old
    return {i.scenario for i in ins}, ins


def pct(a, b):
    return f"{100 * a / b:.0f}%" if b else "n/a"


THRESHOLDS = [RECENT_MIN_EFFECT, 0.8]     # the value in signals.py now, and the value under discussion


def history_table(rows_by_thr, n):
    out = []
    for thr, (tally, any_flag, limited) in rows_by_thr.items():
        out += [
            f"### Recent-change threshold {thr} x the baseline's own variation",
            "",
            "| Section | With related history: people | With a finding | Without related history: people | With a finding |",
            "|---|---|---|---|---|",
        ]
        for s in SECTIONS:
            h, nh = tally[s]["hist"], tally[s]["nohist"]
            out.append(f"| {s} | {h[0]} | {h[1]} ({pct(h[1], h[0])}) | {nh[0]} | {nh[1]} ({pct(nh[1], nh[0])}) |")
        out += ["", f"{any_flag} of {n} people ({pct(any_flag, n)}) have at least one finding; {limited} have a finding based on limited data.", ""]
    return out


def main(folder, limit=None):
    files = sorted(Path(folder).rglob("*.xlsx"))
    if limit:
        files = files[:limit]
    thr_list = list(dict.fromkeys(THRESHOLDS))
    by_thr = {t: ({s: {"hist": [0, 0], "nohist": [0, 0]} for s in SECTIONS}, 0, 0) for t in thr_list}
    by_thr = {t: [v[0], 0, 0] for t, v in by_thr.items()}
    rows = []
    for f in files:
        p = load_patient(str(f))
        row = {"patient": f.stem}
        has = {s: related_history(p, HISTORY_WORDS[s]) for s in SECTIONS}
        for t in thr_list:
            found, ins = run(p, t)
            tally = by_thr[t][0]
            by_thr[t][1] += bool(found)
            by_thr[t][2] += any(i.flag == "Limited" for i in ins)
            for s in SECTIONS:
                c = tally[s]["hist" if has[s] else "nohist"]
                c[0] += 1
                c[1] += s in found
                row[f"{s} | finding at {t}"] = "yes" if s in found else "no"
        for s in SECTIONS:
            row[f"{s} | related history"] = "yes" if has[s] else "no"
        rows.append(row)

    demo = {}
    for name, data in all_demo_workbooks().items():
        demo[name[:6]] = run(load_patient(io.BytesIO(data if isinstance(data, bytes) else data.getvalue())), RECENT_MIN_EFFECT)[0]
    per = {}
    for s in SECTIONS:
        tp = sum(1 for k, t in DEMO_TRUTH.items() if s in t and s in demo[k])
        fp = sum(1 for k, t in DEMO_TRUTH.items() if s not in t and s in demo[k])
        fn = sum(1 for k, t in DEMO_TRUTH.items() if s in t and s not in demo[k])
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        per[s] = (tp, fp, fn, prec, rec, 2 * prec * rec / (prec + rec) if prec + rec else 0.0)

    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "validation_results.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    n = len(rows)
    md = [
        "# Validation of the three disease sections",
        "",
        f"Run on {n} synthetic workbooks. Neither check measures clinical accuracy: the data is synthetic, and the detector "
        "never reads the Medical History or Medication sheets to decide what to report (they only add context to the wording).",
        "",
        "## 1. History consistency",
        "Share of people who get a finding in a section, split by whether their recorded history relates to that section "
        "(a history event or a medication indication that mentions the section's keywords, see `HISTORY_WORDS` in `scripts/validate_scenarios.py`). "
        "A section that reports more often for people whose history relates to it agrees with the record. "
        "A small or zero difference means the section does not separate people well and needs refinement.",
        "",
        *history_table(by_thr, n),
        "## 2. Known patterns (five demo patients)",
        "",
        "| Section | True positives | False positives | Missed | Precision | Recall | F1 |",
        "|---|---|---|---|---|---|---|",
    ]
    for s, (tp, fp, fn, pr, rc, f1) in per.items():
        md.append(f"| {s} | {tp} | {fp} | {fn} | {pr:.2f} | {rc:.2f} | {f1:.2f} |")
    md += [
        "",
        "Demo B is built to be stable, so any finding for it counts as a false positive. Five patients is a small test; "
        "it shows the detector finds the patterns we built in, not how it behaves on real people.",
        "",
        "## What this does not show",
        "- It does not show that a finding is medically correct or that the history caused it.",
        "- Most people in this dataset have a glycemic or metformin entry in their record, so the metabolic history split is weak by construction.",
        "- The thresholds are placeholders (see `pranapulse/signals.py`); the numbers change when they change.",
    ]
    (OUT / "validation_summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: python scripts/validate_scenarios.py <folder with .xlsx workbooks> [limit]")
    sys.exit(main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else None))
