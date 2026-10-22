"""Shared helper: load patients from a folder of .xlsx files, or the built-in demo patients."""
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pranapulse.demo_data import all_demo_workbooks   # noqa: E402
from pranapulse.detect import detect                  # noqa: E402
from pranapulse.loader import load_patient            # noqa: E402


def patients(folder=None, limit=10):
    """Yield (name, insights, results). With no folder, the five demo patients are used."""
    if folder:
        files = sorted(Path(folder).glob("*.xlsx"))[:limit]
        sources = [(f.stem, str(f)) for f in files]
    else:
        sources = [(k, io.BytesIO(v if isinstance(v, bytes) else v.getvalue())) for k, v in list(all_demo_workbooks().items())[:limit]]
    for name, src in sources:
        p = load_patient(src)
        ins, _, results = detect(p)
        yield name, ins, results
