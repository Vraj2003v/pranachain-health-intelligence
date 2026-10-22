"""How many patients would the recent-change check flag at different thresholds?

Run:  python scripts/threshold_check.py data/raw          (or any folder of .xlsx workbooks)
      python scripts/threshold_check.py data/raw 1.5 1.0 0.8
Prints, for each threshold (in multiples of the patient's own daily variation), how many patients
have at least one measure whose latest 14 days sit that far from their previous 90-day average.
"""
import glob
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pranapulse import detect                          # noqa: E402
from pranapulse.loader import load_patient             # noqa: E402
from pranapulse.signals import SIGNALS                 # noqa: E402

folder = sys.argv[1] if len(sys.argv) > 1 else "data/raw"
thresholds = [float(x) for x in sys.argv[2:]] or [1.5, 1.0, 0.8]
files = sorted(glob.glob(str(Path(folder) / "*.xlsx")))
if not files:
    sys.exit(f"No .xlsx files in {folder}")
patients = []
for f in files:
    try:
        patients.append(load_patient(f))
    except Exception:
        pass
print(f"{len(patients)} patients read from {folder}")
for t in thresholds:
    detect.RECENT_MIN_EFFECT = t
    n = sum(1 for p in patients if any(detect.recent_check(p, k) for k in SIGNALS))
    print(f"  threshold {t}x: {n} patients flagged ({100 * n // max(len(patients), 1)}%)")
