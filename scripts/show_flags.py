"""Show what the app flags for one workbook, and why, from the command line.

Usage:  python scripts/show_flags.py path\\to\\PC0062.xlsx

Prints (1) the findings, (2) every daily measure with the numbers the rule uses, (3) the latest lab
results against the range printed on the lab sheet. Use it next to the app when you check a flag by hand.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pranapulse import reference as ref                       # noqa: E402
from pranapulse.detect import detect                          # noqa: E402
from pranapulse.loader import load_patient                    # noqa: E402
from pranapulse.signals import MAX_TREND_P, MIN_EFFECT        # noqa: E402

if len(sys.argv) < 2:
    sys.exit("Usage: python scripts/show_flags.py <workbook.xlsx>")

p = load_patient(sys.argv[1])
insights, _, results = detect(p)

print(f"Patient {p.patient_id}: {len(insights)} finding(s)")
for i in insights:
    print(f"  {i.insight_id}  [{i.scenario}]  {i.title}  | {i.tier} | data: {i.flag}")
if not insights:
    print("  (none)")
ov = ref.overview_by_area(insights, results, p.labs, p.cycles)
att = ref.attention_by_area(insights, ov)
print("\nAttention level per disease area")
for sc, a in att.items():
    print(f"  {ref.AREAS[sc].short:15} {a['level']}  ({a['reason']})")
    print(f"  {'':15} {ov[sc]['text']}")

flagged = {k for i in insights for k in i.signals}
print(f"\nDaily measures (rule: change >= {MIN_EFFECT} x own variation and trend p <= {MAX_TREND_P})")
print(f"{'measure':14}{'first 90d':>10}{'last 90d':>10}{'change':>9}{'x var':>7}{'trend p':>9}  {'usual range':16}{'position':>9}  flagged")
for k, r in results.items():
    rng = ref.RANGES.get(k)
    pos = ref.position(r.mean_last, rng) or "no range"
    d = r.decimals
    print(f"{r.label[:13]:14}{r.mean_first:10.{d}f}{r.mean_last:10.{d}f}{r.diff:9.{d}f}{abs(r.effect):7.2f}{r.trend_p:9.4f}  "
          f"{ref.text(rng)[:16]:16}{pos:>9}  {'YES' if k in flagged else 'no'}")

wanted = [t for a in ref.AREAS.values() for t in a.labs]
print("\nLabs used by the disease areas (latest result vs the range on the lab sheet)")
print(f"{'test':18}{'date':12}{'result':>9}  {'range':14}{'position':>9}  flagged")
for t in wanted:
    rows = p.labs[p.labs.test == t].sort_values("date")
    if rows.empty:
        print(f"{t:18}(no result in this workbook)")
        continue
    r = rows.iloc[-1]
    rng = ref.lab_range(r.ref_low, r.ref_high, r.unit)
    pos = ref.position(r.result, rng) or "no range"
    hit = any(e.get("signal") == t for i in insights for e in i.evidence)
    print(f"{t:18}{str(r.date)[:10]:12}{r.result:9.2f}  {ref.text(rng)[:14]:14}{pos:>9}  {'YES' if hit else 'no'}")
print("\nNote: a value outside its usual range is only flagged when it also changed against the person's own baseline.")
