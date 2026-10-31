# Local model comparison

Run by: Bhavya. Date: ____. Patients: ____.
Command: `python scripts/compare_models.py --models llama3.1:8b llama3.2:3b qwen2.5:7b --folder <folder> --patients 10`

The model table needs the three models to be run on your computer, so it is left for you to fill in from the script output. Score Faithful and Tone by hand.

| Model | Accepted by checks | Avg seconds | Faithful (1-5) | Tone (1-5) |
|---|---|---|---|---|
| llama3.1:8b | | | | |
| llama3.2:3b | | | | |
| qwen2.5:7b | | | | |

## Recommendation
Default model: ____. Reasons: ____.
Context from our own runs: on the demo laptop the 8B model took about 20 s per answer (57 s on the first request) and the 3B model was faster; the 3B model is what we use for the live demo (`PRANAPULSE_MODEL=llama3.2:3b`).

## Threshold
`python scripts/threshold_check.py <folder> 1.5 1.0 0.8` on all 900 workbooks:

| Threshold | Patients flagged |
|---|---|
| 1.5 | 0 |
| 1.0 | 2 |
| 0.8 | 28 |

Recommended: 0.8, because 1.5 flags nobody (so the recent-change check would never show anything) and 1.0 flags only 2 of 900, while 0.8 flags 28 (about 3%) and matches the 0.8 effect size the first-vs-last check already uses. The team confirms the final value at the meeting.
To apply it: in `pranapulse/signals.py` change `RECENT_MIN_EFFECT = 1.5` to `0.8` and update its comment to "0.8 x the baseline's own daily variation"; then run `python -m pytest` (tests/test_threshold.py uses the constant) and `python scripts/verify_sections.py data/raw 900`.
