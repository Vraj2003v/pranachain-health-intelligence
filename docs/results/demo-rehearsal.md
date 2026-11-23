# Demo rehearsal results

Run before each rehearsal and paste the table the script prints. Do not edit the results by hand.

```
python scripts/make_cardio_demo.py          # writes demo-files/cardio/ (upload these in the app to show the cardiovascular pattern)
python scripts/demo_check.py <dataset-folder> PC0466
python -m pytest -q
```

Set `PRANAPULSE_DATASET=<dataset-folder>` before `pytest` to include the PCOS dataset tests (`tests/test_dataset_pcos.py`).

| Date | Who ran it | Check table | Full test suite | Notes |
|---|---|---|---|---|
| 22 Nov 2026 | Harsh Jayeshkumar Patel | 8 of 8 pass (table below) | 276 passed, 2 failed, 1 skipped (full suite, run earlier on 22 Nov) | `tests/test_dataset_pcos.py` with PRANAPULSE_DATASET set: 2 passed. The 2 full-suite failures are the OCR tests in `tests/test_context.py`: the local Tesseract install is missing `eng.traineddata`, so it is a laptop setup issue, not code. |

Check table, 22 Nov 2026 (dataset patient PC0466):

| Check | Result |
|---|---|
| Demo A shows a metabolic pattern | pass |
| Demo B (stable) shows nothing | pass |
| Demo D shows a cardiovascular finding | pass |
| Demo E shows an irregular-cycle finding | pass |
| Cardio upload set merges into one record | pass |
| Cardio upload set gives a cardiovascular pattern | pass |
| PC0466 shows an irregular-cycle finding | pass |
| PC0466 finding cites PCOS from the history | pass |
