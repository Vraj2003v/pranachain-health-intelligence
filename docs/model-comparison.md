# Local model comparison

Run by: Bhavya. Date: ____. Patients: ____.
Command: `python scripts/compare_models.py --models llama3.1:8b llama3.2:3b qwen2.5:7b --folder <folder> --patients 10`

| Model | Accepted by checks | Avg seconds | Faithful (1-5) | Tone (1-5) |
|---|---|---|---|---|
| llama3.1:8b | | | | |
| llama3.2:3b | | | | |
| qwen2.5:7b | | | | |

## Recommendation
Default model: ____. Reasons: ____.

## Threshold
`python scripts/threshold_check.py <folder> 1.5 1.0 0.8`

| Threshold | Patients flagged |
|---|---|
| 1.5 | |
| 1.0 | |
| 0.8 | |

Recommended: ____ because ____. Update `RECENT_MIN_EFFECT` in `pranapulse/signals.py` and its comment.
