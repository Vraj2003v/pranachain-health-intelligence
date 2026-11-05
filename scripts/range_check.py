"""Re-run every workbook in a folder with the Meeting 3 rules and report:
- how many patients have a finding (unchanged by the range layer),
- how the findings split across the usual-range tiers,
- how many findings use a measure from the wrong disease area (must be 0).

Usage: python scripts/range_check.py <folder> [limit] [out.csv]
"""
import csv
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _patients import patients  # noqa: E402
from pranapulse.detect import disease_input_problems  # noqa: E402

folder = sys.argv[1] if len(sys.argv) > 1 else None
limit = int(sys.argv[2]) if len(sys.argv) > 2 else 5
out = sys.argv[3] if len(sys.argv) > 3 else None

n = with_finding = 0
tiers, areas, problems = Counter(), Counter(), []
rows = []
for name, insights, _ in patients(folder, limit):
    n += 1
    with_finding += bool(insights)
    problems += [f"{name}: {p}" for p in disease_input_problems(insights)]
    for i in insights:
        tiers[i.tier] += 1
        areas[i.scenario] += 1
        rows.append([name, i.insight_id, i.scenario, i.kind, i.flag, i.tier, i.title])

print(f"workbooks: {n}")
print(f"patients with a finding: {with_finding} ({with_finding / max(n, 1):.1%})")
print(f"findings: {sum(tiers.values())}")
for t, c in tiers.most_common():
    print(f"  {t}: {c}")
for a, c in areas.most_common():
    print(f"  area {a}: {c}")
print(f"findings using a measure from the wrong disease area: {len(problems)}")
for p in problems[:10]:
    print("  ", p)
if out:
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["patient", "finding", "area", "kind", "data_flag", "range_tier", "title"])
        w.writerows(rows)
