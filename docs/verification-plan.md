# How the three health sections are verified

The partner asked how the new sections will be checked. We check them at four levels. Each level has a command or a
checklist and a result we can show at the next meeting.

## Level 1: automatic checks on every finding (script)
`python scripts/verify_sections.py data/raw 900` checks each flagged section and writes `docs/results/section_checks.csv`.

For every finding it checks that:
1. it belongs to one of the three sections;
2. it has evidence rows with the dates compared;
3. its wording passes the wording check;
4. a recent-change finding uses the 90 days before the latest 14 days, and the averages in the sentence match the evidence table;
5. the data-sufficiency flag agrees with the number of days with data;
6. a cycle finding uses at least 4 cycles.

Results: 5 demo patients, 4 flagged sections, 0 failures. On all 900 workbooks: 89 flagged sections (62 metabolic, 21 women's health, 6 cardiovascular; 84 Sufficient, 5 Limited), 89 pass, 0 failures. See `docs/results/section_checks.csv`.

## Level 2: automated tests (pytest)
`python -m pytest` runs 165 tests, including `tests/test_sections.py` (each section on the demo patients),
`tests/test_threshold.py` (the recent-change threshold) and `tests/test_assistant_safety.py` (30 safety and 5 normal questions).

## Level 3: hand review (52 rows)
Result: each of the four of us checked flagged and no-finding workbooks against the Excel data (52 rows in all); every number and date matched. One minor wording issue (M1): the first and last windows are 91 days but the table says "of 90". Files: `docs/results/hand-review-<name>.csv`. The original plan was 50 workbooks; the plan text below is kept for reference.
Pick 50 workbooks: 15 flagged for cardiovascular, 15 for metabolic, 10 for women's health and 10 with no finding.
For each, open the workbook in Excel and check:
- [ ] the baseline and recent dates in the evidence table are right;
- [ ] the two averages match what Excel gives for the same dates;
- [ ] the data-sufficiency flag is reasonable for the missing days;
- [ ] the sentence says only what the numbers show (no diagnosis, no dose, no risk score);
- [ ] for the 10 with no finding: nothing obvious was missed.
Record each one in `docs/results/hand-review.csv` with columns: patient, section, all checks passed (yes/no), note.

## Level 4: the assistant
`python scripts/assistant_test.py` asks 30 safety questions and 20 normal questions on 10 patients. Every safety question
must get the fixed safe answer, and every normal answer must pass the wording and number checks.

## What counts as passing (proposed; the team confirms)
| Check | Pass |
|---|---|
| Automatic checks on 900 workbooks | 0 failures, or every failure explained |
| Wording check | 0 violations |
| Hand review of 50 | No number mismatches; at least 90% of findings judged reasonable |
| Safety questions | 30 of 30 get the safe answer |

## Who does what
| Level | Owner | Due |
|---|---|---|
| 1 and 2 | Harsh | Sun 1 Nov |
| 3 | Bhavya, Krish and Harsh (about 17 workbooks each) | Sun 1 Nov |
| 4 | Harsh | Sun 1 Nov |
| Write-up for the meeting | Krish | Mon 2 Nov |
