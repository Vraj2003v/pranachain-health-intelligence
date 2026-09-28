# PranaChain — Beyond the Record: AI Health Intelligence Challenge

**COMP8967 Internship Project | Business 2 | Group 11 | Fall 2026**
**University of Windsor × PranaChain**

## The Challenge

> Can AI identify meaningful changes in a person's health before they know what to look for?

Build the intelligence **layer** between a patient's clinical history (diagnoses, labs, medications) and
their continuously changing health data (vitals, wearables, lifestyle, cycle tracking) — surfacing
longitudinal, explainable insights rather than another score, alert, or report summary.

This is **not**:
- A PDF/medical-report summarizer
- A basic high/low vital threshold alert system
- Three isolated disease classifiers
- A black-box risk score with no explanation
- A production-ready clinical decision system or diagnostic tool

This **is**:
- A proof-of-concept health intelligence framework
- A way to combine historical clinical context with ongoing personal health data
- Longitudinal pattern and relationship detection, with supporting evidence
- A simple interface that makes the insight understandable to a patient or clinician
- Extensible to health areas beyond the three validation scenarios

## Validation Scenarios

The framework is built generically, then proven against three focused areas:

| # | Scenario | Clinical context | Ongoing layer |
|---|----------|------------------|---------------|
| 1 | Metabolic Health / Type 2 Diabetes Risk | HbA1c, glucose, lipids, medications, weight/BMI | Activity, sleep, weight trends, glucose |
| 2 | Cardiovascular / Hypertension Risk | BP history, cholesterol, medications, previous findings | Blood pressure, resting HR, activity, sleep, weight |
| 3 | PCOS / Women's Health | Cycle history, relevant labs, medications, previous findings | Cycle patterns, weight, sleep, activity, wearable/lifestyle data |

## What the AI Should Do

1. **Understand** — read and structure the available medical context
2. **Connect** — relate ongoing vitals, wearable, and lifestyle data back to that history
3. **Detect** — find trends, anomalies, and multi-signal patterns over time
4. **Explain** — show what changed, what evidence supports it, and why it may matter
5. **Ask** — identify missing or additional data that could improve understanding

**Worked example:** a previous report shows borderline HbA1c. Over the following months, activity
falls, weight rises, sleep worsens, and glucose trends upward. The AI should connect the changes to
the historical finding, show supporting evidence, and surface the pattern for attention — without
making a diagnosis.

## Dataset

1,000 synthetic patient journeys, one Excel workbook per patient, each spanning a 12-month
longitudinal window. Every workbook contains:

| Sheet | Contents |
|-------|----------|
| Patient Profile | Patient ID, age, sex, height, weight, BMI |
| Medical History | Conditions, diagnoses, procedures, historical events |
| Medication History | Medication, indication, dates, status |
| Lab Results | Dated HbA1c, glucose, lipids, hormones where relevant |
| Vitals Daily | 365 days of BP, HR, SpO2, weight, BMI, temperature |
| Wearable Daily | 365 days of steps, activity, sleep, resting HR, HRV, calories |
| Women's Health | Cycle timing, symptoms, PCOS-related signals (where relevant) |
| Clinical Notes | Synthetic summaries/reports providing context for newer data |
| Medication Adherence | Longitudinal adherence info for behavioral context |

> Data is a combination of real and synthetic records, intended only for academic
> prototyping/testing. Real patient data must never be committed to this repo —
> see `data/sample/README.md`.

## Deliverables

- **Working prototype** — end-to-end flow using synthetic/anonymized longitudinal health data
- **AI/data approach** — documented data structuring, connection over time, and reasoning choices
- **Explainable output** — contributing data, link to historical context, and uncertainty/limitations per insight
- **Validation** — tested against all three scenarios
- **User experience** — a simple dashboard, timeline, or interface that makes output understandable
- **Technical handoff** — source code, setup instructions, architecture, assumptions, limitations, and next steps

## Evaluation Criteria

1. **Insight Quality** — meaningful multi-signal patterns, not just threshold violations
2. **Context Connection** — does it correctly connect ongoing data with relevant medical history?
3. **Explainability** — can we see what changed, why it was surfaced, and what evidence was used?
4. **Technical Design** — is the architecture appropriate, extensible, and realistically implementable?
5. **Responsible AI** — uncertainty, missing data, privacy, and non-diagnostic boundaries
6. **User Experience** — can a patient or clinician understand the output without reading raw model results?

## Project Journey / Checkpoints

| Checkpoint | Focus |
|---|---|
| 1. Kickoff | Align on challenge, scope, and questions |
| 2. Discovery | Define data model, use cases, success criteria |
| 3. Prototype | Demonstrate first end-to-end insight flow |
| 4. Refinement | Improve reasoning, explainability, UX |
| 5. Final Pitch | Working demo, results, limitations, roadmap |

At each checkpoint: show what works, what doesn't yet work, what was learned, and what's decided next.

## Repository Structure

```
├── docs/                    # Architecture notes, checkpoint write-ups, decisions
├── data/
│   └── sample/              # Small anonymized/synthetic samples only (never real patient data)
└── requirements.txt         # Planned Python dependencies
```

Code folders (`src/`, `app/`, `tests/`, etc.) will be added once the data model and approach are
settled at the Discovery checkpoint, rather than committed empty ahead of time.

## Team — Group 11

- Harsh Jayeshkumar Patel (Team Leader)
- Vrajkumar Yaminkumar Patel
- Bhavya Ketan Patel
- Krishkumar Maheshbhai Patel

## Links

- Project Management: [GitHub Project board](https://github.com/users/Vraj2003v/projects/3/views/1)
- Course: COMP8967-1-R-2026F, Business 2
- Instructor/Coordinator: Sheetal (sheetal@uwindsor.ca)
