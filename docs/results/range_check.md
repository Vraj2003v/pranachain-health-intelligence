# Usual-range and disease-input check (900 workbooks)

Run: `python scripts/range_check.py <folder of workbooks> 900 docs/results/range_check.csv`

| | Count |
|---|---|
| Workbooks | 900 |
| Patients with a finding | 85 (9.4%) |
| Findings | 89 |
| Outside the usual range | 66 |
| Within the usual range, worth watching | 2 |
| Personal baseline only (no single usual range) | 21 |
| Findings using a measure from the wrong disease area | 0 |

By area: Metabolic 62, Women's health 21, Cardiovascular 6.

The usual range does not change which findings appear (same 85 patients as before); it adds a tag and evidence columns.
