# Validation of the three disease sections

Run on 900 synthetic workbooks. Neither check measures clinical accuracy: the data is synthetic, and the detector never reads the Medical History or Medication sheets to decide what to report (they only add context to the wording).

## 1. History consistency
Share of people who get a finding in a section, split by whether their recorded history relates to that section (a history event or a medication indication that mentions the section's keywords, see `HISTORY_WORDS` in `scripts/validate_scenarios.py`). A section that reports more often for people whose history relates to it agrees with the record. A small or zero difference means the section does not separate people well and needs refinement.

### Recent-change threshold 1.5 x the baseline's own variation

| Section | With related history: people | With a finding | Without related history: people | With a finding |
|---|---|---|---|---|
| Cardiovascular / hypertension | 394 | 2 (1%) | 506 | 4 (1%) |
| Metabolic health | 555 | 40 (7%) | 345 | 22 (6%) |
| Women's health (PCOS) | 146 | 21 (14%) | 754 | 0 (0%) |

85 of 900 people (9%) have at least one finding; 5 have a finding based on limited data.

### Recent-change threshold 0.8 x the baseline's own variation

| Section | With related history: people | With a finding | Without related history: people | With a finding |
|---|---|---|---|---|
| Cardiovascular / hypertension | 394 | 13 (3%) | 506 | 18 (4%) |
| Metabolic health | 555 | 41 (7%) | 345 | 22 (6%) |
| Women's health (PCOS) | 146 | 21 (14%) | 754 | 0 (0%) |

110 of 900 people (12%) have at least one finding; 6 have a finding based on limited data.

## 2. Known patterns (five demo patients)

| Section | True positives | False positives | Missed | Precision | Recall | F1 |
|---|---|---|---|---|---|---|
| Cardiovascular / hypertension | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| Metabolic health | 2 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| Women's health (PCOS) | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 |

Demo B is built to be stable, so any finding for it counts as a false positive. Five patients is a small test; it shows the detector finds the patterns we built in, not how it behaves on real people.

## What this does not show
- It does not show that a finding is medically correct or that the history caused it.
- Most people in this dataset have a glycemic or metformin entry in their record, so the metabolic history split is weak by construction.
- The thresholds are placeholders (see `pranapulse/signals.py`); the numbers change when they change.
