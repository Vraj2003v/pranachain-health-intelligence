# Local model comparison

Run by: Bhavya. Date: 31 Oct 2026. Patients: 3 (PC0001 to PC0003), 4 chat questions each, 12 answers per model.
Commands: `python scripts/compare_models.py --models <model> --folder data/raw --patients 3 --out <file>.csv`, run once per model. Results: `docs/results/model_comparison.csv`.

| Model | Accepted by checks | Avg seconds | Faithful (1-5) | Tone (1-5) |
|---|---|---|---|---|
| llama3.1:8b | 11/12 (91%) | 49.0 | 4.33 | 4.58 |
| llama3.2:3b | 9/12 (75%) | 12.8 | 4.00 | 4.42 |
| qwen2.5:7b | not run | | | |

Faithful and Tone were scored by hand on a 1 to 5 scale.

## Recommendation
Default model: llama3.2:3b for the live demo; llama3.1:8b where accuracy matters more than speed. Reasons: the 8B passed more checks (91% vs 75%) and scored slightly higher on faithfulness (4.33 vs 4.00), but it was about four times slower (49 s vs 13 s per answer on this laptop). The 3B is fast enough for a live demo, but gave the weakest answers: twice it said there was "no data available" for a patient who has 12 months of data.
Context from our own runs: on the demo laptop the 8B model took about 20 s per answer (57 s on the first request) and the 3B model was faster; the 3B model is what we use for the live demo (`PRANAPULSE_MODEL=llama3.2:3b`).

## Limits of this comparison
- qwen2.5:7b was not run: the laptop ran out of memory and time with three models loaded.
- Only 3 patients, none with a flagged finding, so all 24 answers are chat questions. Explaining a flagged insight was not tested.
- The question "How much data is behind this?" gave the weakest answers for both models and needs a better prompt.

## Threshold
`python scripts/threshold_check.py <folder> 1.5 1.0 0.8` on all 900 workbooks:

| Threshold | Patients flagged |
|---|---|
| 1.5 | 0 |
| 1.0 | 2 |
| 0.8 | 28 |

Recommended: 0.8, because 1.5 flags nobody (so the recent-change check would never show anything) and 1.0 flags only 2 of 900, while 0.8 flags 28 (about 3%) and matches the 0.8 effect size the first-vs-last check already uses. The team confirms the final value at the meeting.
