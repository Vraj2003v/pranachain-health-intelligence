"""Compare local models on insight explanations and chat questions.

Run (Ollama running, models pulled with `ollama pull <name>`):
    python scripts/compare_models.py --models llama3.1:8b llama3.2:3b qwen2.5:7b
    python scripts/compare_models.py --models llama3.2:3b --folder C:\\path\\to\\workbooks --patients 10
Writes model_comparison.csv (one row per answer) and prints a summary per model.
Fill Faithful (1-5) and Tone (1-5) by hand: does it use only the facts, and does it sound calm and clear?
"""
import argparse
import csv
import time
from pathlib import Path

from _patients import patients
from pranapulse import ask, llm
from pranapulse.explain import check_language

QUESTIONS = ["Why was this flagged?", "What does the baseline mean?", "How much data is behind this?", "How is my weight?",
             "How is my blood pressure?", "Compare weight and HbA1c.", "What changed most?", "What does the projection show?",
             "What should I ask my doctor?", "Explain this in simple words."]

ap = argparse.ArgumentParser()
ap.add_argument("--models", nargs="+", required=True)
ap.add_argument("--folder")
ap.add_argument("--patients", type=int, default=5)
ap.add_argument("--out", default="model_comparison.csv")
a = ap.parse_args()

cases = [(n, ins, res) for n, ins, res in patients(a.folder, a.patients)]
rows, summary = [], {}
for m in a.models:
    if not llm.available(m):
        print(f"SKIP {m}: not found. Run: ollama pull {m}")
        continue
    llm.DEFAULT_MODEL = m
    llm.available = lambda *x, **k: True     # we checked above
    ok = tot = 0
    secs = []
    for name, ins, res in cases:
        for i in [x for x in ins][:2]:        # up to 2 insights per patient
            t = time.time()
            text, src = llm.explain(i, model=m)
            dt = time.time() - t
            tot += 1; ok += src == "local model"; secs.append(dt)
            rows.append([m, name, "insight", i.title, text, src, "; ".join(check_language(text)) or "none", round(dt, 1), "", ""])
        for q in QUESTIONS[:max(1, 10 // max(len(cases), 1)) + 1]:
            t = time.time()
            text, src, *_ = ask.answer(q, ins, None, results=res)
            dt = time.time() - t
            tot += 1; ok += src == "local model"; secs.append(dt)
            rows.append([m, name, "chat", q, text, src, "; ".join(check_language(text)) or "none", round(dt, 1), "", ""])
    summary[m] = (ok, tot, sum(secs) / max(len(secs), 1))
with open(a.out, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["Model", "Patient", "Kind", "Prompt", "Answer", "Source", "Wording-check problems", "Seconds", "Faithful (1-5)", "Tone (1-5)"])
    w.writerows(rows)
print(f"\nWritten: {Path(a.out).resolve()}\n")
print(f"{'Model':<16}{'Accepted by checks':<22}{'Avg seconds'}")
for m, (ok, tot, avg) in summary.items():
    print(f"{m:<16}{ok}/{tot} ({100*ok//max(tot,1)}%)".ljust(38) + f"{avg:.1f}")
print("\n'Accepted' = the model's reply passed the wording and number checks. Rejected replies fall back to the template.")
