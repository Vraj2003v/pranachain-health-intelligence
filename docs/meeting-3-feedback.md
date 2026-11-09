# Meeting 3 feedback and our response (2 Nov 2026)

Group 11, PranaPulse. Business partner: Abhishek Chakrala. GA: Sheetal.

## What we presented
- Recap of the three points from Meeting 2: 90-day baseline, three disease sections, friendlier interface.
- Live demo (workbook PC0062), local assistant (3B model about 13 s per answer, 8B about 40–50 s), five demo workbooks, 172 automated tests.
- Record agreement across 900 workbooks, the 250-answer safety test, and the 1.5 threshold (nobody flagged at 1.5 or 1.2, 26 of 900 at 0.8).

## Feedback
| Topic | What the partner said | Our reading |
|---|---|---|
| **Inputs per disease (main point)** | Each disease should be judged only on its own measures, the four or five listed at the kickoff. A change in an unrelated measure (for example HbA1c for cardiovascular) should not be an input. He called missing the right inputs "a big red flag" because disease prediction is the agenda. | Make each area's measure list explicit and enforce it, including for the assistant. |
| **Reference ranges** | Use the biological reference range as the base, then check the person's day-to-day variation against it. Lower is sometimes good, and a variation-only rule would flag it. | Keep the personal baseline as the check for change; add the usual range as context and show where the recent readings sit. Improvements are never findings. |
| **Labels** | Use the exact disease names in the interface instead of "sugar and weight". | Areas renamed to Cardiovascular, Metabolic, Women's health. |
| **Evidence** | Asked whether a flag shows the evidence behind it. | Yes (last reading, comparison with earlier days, evidence IDs E1…). Usual range now added to the evidence rows. |
| **Safety wording** | Answers should stay vague and explain, never "you will get" a disease. Our disclaimer covers it. | No change needed; kept the "may be worth discussing with a healthcare provider" wording. |
| **Testing** | Fine-tune the criteria for prediction rather than review every test run. | New automated tests for the disease inputs and the usual-range tags. |
| **Interface** | "Looking good". | Kept; phone and interactivity improved (below). |

Open point to confirm at the final meeting: he used the words "predict" and "probability". Our design shows changes and evidence, with no diagnosis and no risk score. Ask whether he expects a risk level or only a "worth discussing" finding.

## What we changed (this branch, `feedback-m3`)
**Detection and assistant**
- `pranapulse/reference.py` (new): one table of which measures belong to each disease area, and the usual range for each measure. Lab tests use the range printed on the patient's lab result; cycle length uses 21–35 days. Weight, steps and HRV have no single usual range and are compared with the personal baseline only.
- `pranapulse/detect.py`: every finding gets a usual-range tag (**Outside the usual range**, **Within the usual range, worth watching**, **Personal baseline only**); evidence rows carry the usual range and where the recent value sits; `disease_input_problems()` reports any finding that uses a measure from another disease area.
- `pranapulse/ask.py`, `pranapulse/llm.py`: the model now only sees readings from the disease area being discussed (it used to get the biggest changes across all measures). The area is taken from the screen or inferred from the question. New answer for "What is the usual range?". Single-measure answers state the usual range.
- Detection thresholds and the flagging rule are **unchanged** (1.5 recent check, 0.8 first-vs-last), so the 900-workbook counts stay the same.

**Interface**
- Disease names as titles, with each area's measures listed under it.
- Trends: **3 months / 6 months / Full year**, a green usual-range band with a **Show usual range** toggle, and a line saying where the recent average sits.
- Full findings: jump buttons with counts, usual-range tags on findings, tiles and evidence rows.
- Phone: bottom tab bar, swipeable measure buttons, larger touch targets, two-column tiles.
- "Ask a question" tab removed; the assistant is the 💬 button (earlier this week).

## Results
| Check | Result |
|---|---|
| Automated tests | 189 pass (172 earlier, plus 17 for disease inputs and usual-range tags) |
| 900 workbooks, patients with a finding | 85 of 900 (9.4%), same as before the change |
| 900 workbooks, findings | 89: 66 outside the usual range, 2 within it (worth watching), 21 personal baseline only |
| 900 workbooks, findings using a measure from the wrong disease | 0 |
| Interface | Checked at 390 px (phone) and 1440 px (desktop); screenshots in `docs/ui-review-screens/m3-*.png` |

Details: `docs/results/range_check.csv` and `scripts/range_check.py`.

## Limits to state honestly
- The usual ranges are general adult values (blood pressure 90–120 / 60–80 mmHg, resting heart rate 60–100 bpm, sleep 7–9 h). Ask the partner to confirm them.
- Before this change, detection already grouped measures by area. The part that did mix areas was the assistant's list of readings; that is fixed and tested.
- The range tag is context; it does not change which findings appear. We have no labelled outcomes to show that a range-based rule is more accurate.
- The two-lane/persistence detection idea (lower thresholds with guards) is still an experiment and is not part of this branch.

## Next steps before the final meeting
| Task | Owner | Done by (proposed) | How it is checked |
|---|---|---|---|
| Review and merge `feedback-m3`; confirm usual ranges with the partner | Vraj, Bhavya | Nov 9 | Ranges table signed off; 189 tests pass |
| Re-check disease lists against the kickoff document | Bhavya | Nov 9 | List per disease matches the kickoff |
| Patient and clinician wording check on the new labels and tags | Krish | Nov 11 | Notes on anything hard to find |
| Re-run the full 250-answer safety test with the model, incl. measures the patient does not have; improve the "how much data is behind this" prompt | Harsh | Nov 11 | Table of safe, unclear, unsafe counts |
| Persistence rule and larger minimum change for steps, then re-test at lower thresholds | Vraj, Bhavya | Nov 12 | 900-workbook counts at 1.5, 1.0, 0.8 |
| Update slides, demo script and logs | All | Nov 14 | Deck matches the code and results |


## Follow-up: attention level per disease (5 Nov 2026)
Abhishek spoke about "predicting" disease risk. We have no outcome data to train or validate a risk model, so we added a plain, rule-based **attention level** for each disease area instead. It is not a diagnosis and not a probability.

| Level | When it is shown |
|---|---|
| No clear change | The area has no finding |
| Worth watching | One finding that is within the usual range, on the personal baseline only, or has limited data |
| Worth discussing with a healthcare provider | A finding outside the usual range with enough data, or two or more findings in the area |

- Code: `attention()` and `attention_by_area()` in `pranapulse/reference.py`; returned as `attention` by the detail endpoint; shown on the Home area cards and in Full findings.
- Demo patients: A (metabolic) and D (cardiovascular) and E (cycle) show "Worth discussing"; B shows no change; C has the same drift as A but limited data, so it shows "Worth watching".
- Tests: `test_attention_rules` and `test_attention_level_is_rule_based_and_never_a_diagnosis`.
- Open question for the final meeting: does he expect a risk level, and are these three levels enough?


## Follow-up: all of a disease's own measures together (5 Nov 2026)
Abhishek asked whether the cardiovascular result considers all of that disease's parameters, not only the ones that changed. The kickoff lists each area's inputs, and he said each disease should use only its own.

- **Overview per area.** Each disease area now lists all of its own measures with the latest value, the usual range, where the value sits (above, within, below, or own baseline only) and whether a finding involves it. Cardiovascular: systolic and diastolic BP, resting heart rate, HRV, steps, LDL. Metabolic: weight, steps, sleep, HbA1c, fasting glucose. Women's health: cycle length.
- **Steady values count.** A value that stays outside its usual range without changing is counted in the overview ("3 of 4 measures with a usual range are outside it"). It is not a numbered finding, so finding IDs (F1, F2) and the 900-workbook finding counts do not change.
- **Attention level.** Findings decide "worth discussing", as before. Measures outside their range lift an area with no finding to "worth watching". `OUTSIDE_FOR_DISCUSS` in `pranapulse/reference.py` is left off: in the synthetic journeys almost every patient is above range on blood pressure and below on sleep, so a count would flag nearly everyone.
- **Screens.** Measure tabs that have a finding show an amber dot, and the area opens on that tab.
- Code: `overview()` and `overview_by_area()` in `pranapulse/reference.py`; returned as `overview` by the detail endpoint; `Overview.jsx` on the interface.
- Tests: `test_overview_uses_only_the_areas_own_measures`, `test_a_steady_value_outside_the_range_is_counted_without_being_a_finding`, `test_insufficient_data_is_not_counted_as_outside`.
- Kickoff lists: the measures the kickoff lists for each disease but that are not finding inputs (sleep and weight for cardiovascular, lipids for metabolic, weight, sleep and steps for women's health) now appear in that disease's overview, marked "also considered". They create no findings and are not counted in the attention level, so finding counts are unchanged. Bhavya confirms whether any should become finding inputs.
- No risk score or trained model: the kickoff says not to build a black-box risk score or a diagnosis.
