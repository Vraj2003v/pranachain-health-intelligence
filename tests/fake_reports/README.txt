SYNTHETIC TEST DATA - built from the demo patient PC0433. Not a real patient or lab.
pdf/, csv/, xlsx/: the same 4 lab reports (19 Sep 2025, 14 Feb 2026, 10 May 2026, 6 Jun 2026), one document per collection date, in 3 formats.
Test 1: upload the 4 reports one at a time in any order. The final history must equal EXPECTED_after_all_documents.csv.
Test 2: the findings must match the same patient uploaded as one workbook (HbA1c crossed 14 Feb 2026, fasting glucose 6 Jun 2026).
edge_cases/: duplicate, missing value, other names and units, wrong patient, out-of-order. Each file says the expected result at the bottom.
Note: the file with HbA1c in mmol/mol (44) converts to about 6.18 %, not exactly 6.16, because 44 is a rounded whole number.
