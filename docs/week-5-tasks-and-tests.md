# Week 5: tasks and test guide (Monday 9 November 2026)

Group 11, PranaPulse. Week 9 progress evaluation: Tuesday 10 November, 12:00 to 12:20, 300 Ouellette Avenue.
This page records the tasks due on 9 November, how each one is checked, and how to run every test.

## 1. Tasks due on 9 November

Source: "Next steps before the final meeting" in `docs/meeting-3-feedback.md`.

### 1.1 Review and merge `feedback-m3`; confirm the usual ranges with the partner
Owners: Vraj, Bhavya.

| Part | Status | Evidence |
|---|---|---|
| Review and merge `feedback-m3` | Done | Pull request #54 merged on 4 Nov |
| Follow-up changes merged on top | Done | #55 sign-in buttons, #56 attention level, #57 summary follows the measure tab, #58 trimmed area view, #59 cycle chart |
| Overview of all of an area's measures | Built and tested; merge when ready | See section 3 |
| Usual ranges confirmed by the partner | Open | Needs Abhishek's answer |

The ranges the app shows as context (general adult values; the range tag never decides whether a finding appears):

| Measure | Usual range |
|---|---|
| Systolic BP | 90–120 mmHg |
| Diastolic BP | 60–80 mmHg |
| Resting heart rate | 60–100 bpm |
| Sleep | 7–9 h |
| Cycle length | 21–35 days |
| Weight, daily steps, HRV | none (own baseline only) |
| Lab results | the range printed on the lab sheet |

Questions for Abhishek:
1. Do you agree with these ranges, or should a different source be used?
2. The app gives a rule-based attention level and an overview of each disease area's measures. It does not predict disease or give a risk score (the kickoff says no black-box risk score and no diagnosis). Is that enough?

### 1.2 Re-check the disease lists against the kickoff
Owner: Bhavya. Check: the list for each disease matches the kickoff document.

| Disease area | Kickoff lists (ongoing and clinical) | Feeds findings | Shown in the overview as context ("also considered") |
|---|---|---|---|
| Cardiovascular | blood pressure, resting heart rate, activity, sleep, weight; BP history, cholesterol | systolic BP, diastolic BP, resting heart rate, HRV, steps, LDL | sleep, weight, total and HDL cholesterol |
| Metabolic | activity, sleep, weight, glucose; HbA1c, glucose, lipids, weight/BMI | weight, steps, sleep, HbA1c, fasting glucose | total, LDL, HDL cholesterol and triglycerides |
| Women's health | cycle patterns, weight, sleep, activity | cycle length | weight, sleep, steps |

Every measure the kickoff lists now appears in the overview of its disease. Context measures do not create findings and are not counted in "outside the usual range" or in the attention level, so finding IDs, the attention levels and the 900-workbook counts are unchanged. To make one of them feed findings, move it from `context_signals`/`context_labs` to `signals`/`labs` in `pranapulse/reference.py`; that changes the counts, so re-run `scripts\range_check.py` and agree it with Bhavya first.

How to check: open `pranapulse/reference.py` (`AREAS`), compare with the table above, then run `python -m pytest tests\test_disease_inputs.py -q`. Changing a list changes which findings appear, so re-run `python scripts\range_check.py <folder of workbooks>` and record the counts.
Rule agreed in Meeting 3: a disease uses only its own measures (HbA1c and glucose never feed cardiovascular, LDL never feeds metabolic).

## 2. Test guide

### 2.1 How to run (PowerShell, project folder, virtual environment on)

| Purpose | Command | Time |
|---|---|---|
| Quick check before a pull request | `python -m pytest tests\test_disease_inputs.py tests\test_api.py -q` | about 15 s |
| Findings, IDs, sections, thresholds | `python -m pytest tests\test_evidence_ids.py tests\test_sections.py tests\test_threshold.py tests\test_prototype.py tests\test_clean_reply.py -q` | about 1 min |
| Everything | `python -m pytest -q` | about 23 min |
| Skip the slow assistant tests | `python -m pytest -q --ignore=tests\test_assistant_safety.py` | much faster |

### 2.2 What each test file checks

| File | Tests | What it checks |
|---|---|---|
| `tests/test_disease_inputs.py` | 23 | Each finding uses only its own disease's measures; kickoff context measures are shown but never feed findings or attention; HbA1c/glucose never belong to cardiovascular and LDL never to metabolic; usual-range tags; attention level rules and wording; overview uses only an area's own measures; a steady out-of-range value is counted but is not a finding; insufficient data is never counted as outside |
| `tests/test_api.py` | 11 | Sign-in required; sign-up rules (the first account is the administrator; the role choice never grants administrator); wrong password and sign-out; demo patients and the detail endpoint; users cannot see each other's files; bad files are reported and deletion works; the activity log is administrator-only; assistant answers pass the wording check and stay private |
| `tests/test_assistant_safety.py` | 135 | The assistant never diagnoses, gives doses or treatment, or adds numbers; safety questions get the fixed safe answer |
| `tests/test_evidence_ids.py` | 6 | Every finding has an ID (F1, F2, ...) and every evidence row an ID (E1, E2, ...) |
| `tests/test_sections.py` | 6 | Each disease section is traceable: right section, evidence, safe wording, 90-day baseline |
| `tests/test_threshold.py` | 3 | The recent-change check flags a clear move of the latest 14 days and stays quiet otherwise |
| `tests/test_prototype.py` | 10 | Core detection on the demo patients: a drifting patient gets one pattern with history, a stable patient stays quiet, missing data downgrades the flag, cardiovascular and cycle patterns, every narrative passes the wording guardrails, the AI reply is used only when it passes the checks; date formats load |
| `tests/test_clean_reply.py` | 1 | Lead-in phrases are stripped from assistant replies |
| Total | 195 | |

### 2.3 Last known results

| Run | Result | Date |
|---|---|---|
| Full suite on the merged Meeting 3 work | 189 passed in 1365 s | 4 Nov |
| `test_disease_inputs.py` and `test_api.py` with the overview change | 33 passed | 5 Nov |
| `test_evidence_ids.py`, `test_prototype.py`, `test_clean_reply.py` with the overview change | 17 passed | 5 Nov |
| Full suite after #55 to #59 and the overview change (195 tests) | **Not run yet.** Run once before the evaluation and record the number here | |

### 2.4 Checks on the 900 workbooks (not part of pytest)

| Script | What it does | Last result |
|---|---|---|
| `python scripts\range_check.py <folder>` | Findings per patient, tier counts, findings using the wrong disease's measure | 85 of 900 patients with a finding (9.4%); 89 findings; 0 from the wrong disease |
| `python scripts\threshold_check.py <folder> 1.5 1.0 0.8` | How many patients the recent-change check flags at each threshold | Re-test due 12 Nov |
| `python scripts\verify_sections.py <folder>` | Section checks for every finding | `docs/results/section_checks.csv` |
| `python scripts\assistant_test.py` | 250 assistant answers on the demo patients (needs the local model) | `docs/safety-test-results.md` |
| `python scripts\validate_scenarios.py` | The three validation scenarios | `docs/results/validation_summary.md` |

### 2.5 Is a patient flagged correctly?
Run `python scripts\show_flags.py "C:\path\to\PC0062.xlsx"`. It prints the findings, the attention level and overview of each area, every daily measure with its first and last 90-day mean, change, change divided by the patient's own variation, trend p-value, usual range and flagged yes or no, then the labs against the lab-sheet range.
A measure is flagged when its change is at least 0.8 times the patient's own day-to-day variation and the trend p is at most 0.01.
Hand check (5 minutes): in Excel take the first and last 90 days of one measure, use `=AVERAGE(...)` for each and `=STDEV(...)` over the first window; the change divided by that value should match the "x var" column.

Workbooks worth opening (all in the `Data` folder):

| Workbook | Shows |
|---|---|
| PC0062, PC0106, PC0132 | Weight and systolic BP (Metabolic and Cardiovascular) |
| PC0466 | HbA1c and glucose shifting together, and irregular cycles (two areas) |
| PC0995 | HbA1c and glucose shifting together (one combined finding) |
| PC0082 | Weight and HbA1c together |
| PC0036, PC0180, PC0188 | Systolic BP only |
| PC0303, PC0313, PC0423 | Irregular cycles only |
| PC0001 | No finding |

No workbook in the 900 has findings in all three areas.

### 2.6 Interface checklist (desktop 1440 px and phone 390 px)
- [ ] Sign in and Create account buttons are equal width.
- [ ] Open a patient, then each disease card. The attention line, "All measures" table and the measure card appear.
- [ ] Click each measure tab. The card above the graph changes: a finding for that measure, or "no clear change" with its value and range position. A dot marks a tab with a finding.
- [ ] Women's health: cycle bars show their values; amber bars are outside 21–35 days.
- [ ] Every page opens (My summary, Trends, Compare, Full findings, Data quality, My files, Activity log). No page scrolls sideways; no "undefined" or "NaN" text.
- [ ] Assistant: ask "Why was this flagged?" and "Do I have diabetes?" (the second must get the fixed safe answer).

Last automated sweep (5 Nov): four patients, desktop and phone, every page, area card and measure tab: no console errors, no failed requests, no broken text.

## 3. What changed in the overview patch

- Each disease area lists its own measures with the latest value, usual range, position (above, within, below, own baseline only) and whether a finding involves it. A steady value outside its range is counted in the overview but is not a numbered finding, so finding IDs and the 900-workbook finding counts are unchanged.
- Attention level: findings decide "worth discussing". Measures outside their range lift an area with no finding to "worth watching". `OUTSIDE_FOR_DISCUSS` in `pranapulse/reference.py` is left off because in the synthetic data nearly every patient is above range on blood pressure and below on sleep, so a count would flag almost everyone.
- Measure tabs that have a finding show an amber dot; the area opens on that tab.
- Result on the 900 workbooks: cardiovascular 111 no clear change, 786 worth watching, 3 worth discussing; metabolic 141, 722, 37; women's health 879 no clear change, 21 worth discussing.

## 4. Before the evaluation (10 November)
- [ ] Decide which version to demo (`main` at #59, or with the overview change) and tell the team.
- [ ] Run the full suite once and record the number in section 2.3.
- [ ] Each person prepares a one-minute statement of their own work and can open their pull request or branch.
- [ ] Update `docs/demo-script.md` for the overview table and the tab dots.
- [ ] Start the app, load the demo patients, ask the assistant one warm-up question.
- [ ] Keep screenshots or a short recording as a backup.
- [ ] Update `docs/progress_log/log.json` and the Evidence Trail (due 14 Nov).
