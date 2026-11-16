# History consistency check (900 workbooks)
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
| Cardiovascular / hypertension | 394 | 13 (3%) | 506 | 10 (2%) |
| Metabolic health | 555 | 40 (7%) | 345 | 22 (6%) |
| Women's health (PCOS) | 146 | 21 (14%) | 754 | 0 (0%) |

101 of 900 people (11%) have at least one finding; 5 have a finding based on limited data.

## How to read it
- **Women's health:** 21 of 146 people (14%) whose history relates to PCOS or cycles get a finding, against 0 of 754 (0%) without. This is the clearest agreement with the record.
- **Metabolic health:** 7% against 6%. Almost everyone in this dataset has a glycemic or metformin entry (555 of 900), so this split is weak by construction.
- **Cardiovascular:** 1% against 1% at 1.5; 3% against 2% at 0.8. The section is too quiet to separate people at 1.5.
- This does not show that a finding is medically correct or that the history caused it. The detector never reads the history sheets to decide what to report.

Command: `python scripts/validate_scenarios.py data/raw 900`. Counts include the persistence rule from the threshold re-test (`docs/results/threshold_retest.md`).