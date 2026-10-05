# Verified Data Schema (Issue #6)

Based on a scan of all 900 workbooks in the shared Drive folder (Oct 5, 2026). Reproduce with
`python scripts/scan_dataset.py data/raw`. Raw data stays out of the repo (see `data/sample/README.md`).

## What is consistent
- 900 workbooks, one per patient. IDs run PC0001–PC1000 **except PC0201–PC0300, which is not in the shared folder.**
- Every workbook has the same 11 sheets: Patient Profile, Medical History, Medication History, Lab Results,
  Vitals Daily, Wearable Daily, Habits Weekly, Symptoms Timeline, Encounters & Notes, Medication Adherence, Women Health.
- Data window is 2025-09-01 to 2026-08-31 for every patient; Vitals Daily and Wearable Daily have 365 rows each.
- Patient Profile is a Field/Value list (ID, age, sex, height, blood group, allergies, family history, data window).
  Weight and BMI come from Vitals Daily, not the profile.
- Lab Results is long format (Date, Test Name, Result, Unit, Reference Range); 39 distinct tests; 4–7 lab dates per patient;
  every patient has HbA1c and fasting glucose.

## What is not consistent (the loader must handle it)
| Issue | Detail |
|---|---|
| Date formats | Excel serial numbers (PC0001–PC0200 and part of PC0401–PC0600), real datetimes (PC0301 onward), text dates (56 files in PC0401–PC0600). |
| Missing days | Vitals/wearable gaps are blank cells. Wearable gaps blank every column at once. PC0001–PC0200 and about 144 files in PC0401–PC0600 average about 48 missing wearable days and 36 missing BP days; the rest about 13 and 20. |
| Women Health | 597 patients have a single "Not applicable" row, including 170 women. Do not infer cycle data from sex. |
| Resting HR | Identical in Vitals and Wearable sheets for the first 344 files only. |
| Adherence | Monthly, estimated from refill estimates or self-report; the same medication and month can appear twice. |

## Scenarios are not labelled
There is no scenario column. Medical History findings are the best label: Borderline glycemic markers (344),
Hypertension (163), Hypothyroidism (124), Hyperlipidemia (107), Prediabetes (87), Type 2 diabetes (31),
PCOS (14, all female, mean cycle length about 41 days), plus iron deficiency, vitamin D insufficiency, migraine, GERD
and asthma. 103 patients have routine review only and can act as controls.

## Trends
Changes over the window are small on average. Roughly 37% of patients gain weight, 40% lose steps and 32% have rising
systolic BP, so worsening patients exist but each change is small.
