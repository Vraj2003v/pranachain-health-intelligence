# PranaPulse documentation index

Group 11, COMP8967, business partner PranaChain. Start here to find any document.
Test counts and commands are kept in one place: [week-5-tasks-and-tests.md](week-5-tasks-and-tests.md).

## 1. What the project is and how to run it
| Document | What it covers |
|---|---|
| [../README.md](../README.md) | Overview, setup, how to start the app |
| [user-guide.md](user-guide.md) | Using the app: areas, measure tabs, overview, attention level, assistant |
| [demo-script.md](demo-script.md) | Timed demo script for the evaluation |

## 2. Design
| Document | What it covers |
|---|---|
| [architecture.md](architecture.md) | Parts of the system and how data flows |
| [data-schema.md](data-schema.md) | Workbook sheets and columns |
| [three-approaches.md](three-approaches.md) | Detection approaches compared |
| [ai-integration-plan.md](ai-integration-plan.md) | Where the local model is used and where it is not |
| [model-comparison.md](model-comparison.md) | 3B and 8B models compared |

## 3. Findings: how they are made
| Document | What it covers |
|---|---|
| [meeting-3-feedback.md](meeting-3-feedback.md) | Partner feedback, disease inputs, usual ranges, attention level, overview |
| [results/range_check.md](results/range_check.md) | Findings across the 900 workbooks |
| Rule in one line | A measure is flagged when its first-versus-last 90-day change is at least 0.8 times the patient's own variation and the trend p is 0.01 or lower; the latest 14 days are also compared with the prior 90 (threshold 1.5). No diagnosis and no risk score. |

## 4. Testing and verification
| Document | What it covers |
|---|---|
| [week-5-tasks-and-tests.md](week-5-tasks-and-tests.md) | Test commands, what each test file checks, last results, 900-workbook scripts, interface checklist |
| [verification-plan.md](verification-plan.md) | The levels of checking |
| [safety-test-results.md](safety-test-results.md) | 250-answer assistant safety test |
| [results/validation_summary.md](results/validation_summary.md) | Three validation scenarios |
| [results/section_checks.csv](results/section_checks.csv), [results/range_check.csv](results/range_check.csv) | Per-finding and per-patient check data |
| [results/](results/) `hand-review-*.csv` | Each teammate's hand review |
| [ui-review.md](ui-review.md) | Interface review with screenshots |

## 5. Plans, meetings and progress
| Document | What it covers |
|---|---|
| [meeting-3-plan.md](meeting-3-plan.md), [pitch-plan.md](pitch-plan.md) | Plans |
| [team-tasks/README.md](team-tasks/README.md) | Week 4 team tasks |
| [progress_log/log.json](progress_log/log.json) | Weekly progress log |

## Keeping this current
When a test is added or a result changes, update the table in `week-5-tasks-and-tests.md` section 2 and the "Last known results" rows; other pages link there instead of repeating numbers.
