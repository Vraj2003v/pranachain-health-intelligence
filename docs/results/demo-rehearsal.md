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
|  |  |  |  |  |
