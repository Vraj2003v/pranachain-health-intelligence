# Architecture Notes

Living doc — updated as decisions get made at each checkpoint. This first pass is based on the
structure documented in the PranaChain kickoff brief, before we've opened an actual workbook.
Sections marked **(pending real data)** need revisiting once someone has inspected `PC0001.xlsx` —
the brief describes what each sheet *should* contain, not confirmed column names or formats.

## 1. Source Data Shape

Each patient workbook (`PC####.xlsx`) has 9 sheets, per the brief:

| Sheet | Grain | Expected contents |
|---|---|---|
| Patient Profile | 1 row/patient | ID, age, sex, height, weight, BMI |
| Medical History | 1 row/event | Conditions, diagnoses, procedures, dates |
| Medication History | 1 row/medication | Name, indication, start/end dates, status |
| Lab Results | 1 row/test/date | Dated HbA1c, glucose, lipids, hormones |
| Vitals Daily | 1 row/day (365) | BP, HR, SpO2, weight, BMI, temperature |
| Wearable Daily | 1 row/day (365) | Steps, activity, sleep, resting HR, HRV, calories |
| Women's Health | 1 row/cycle or event | Cycle timing, symptoms, PCOS-related signals |
| Clinical Notes | 1 row/note | Synthetic report text/summaries |
| Medication Adherence | 1 row/day or dose | Adherence status over time |

**(pending real data)** Confirm exact column names, date formats, units, and how missing values
are represented (blank vs. `NaN` vs. sentinel) once a workbook is opened.

## 2. Data Model — Normalizing Into One Shape

Plan: parse all 9 sheets per patient into a single long-format table so ongoing signals and
historical context live side by side instead of in separate silos:

```
patient_id | date | domain | signal_name | value | unit | source_sheet
```

- `domain` distinguishes clinical-context rows (from Medical History, Medication History, Lab
  Results) from ongoing-layer rows (Vitals Daily, Wearable Daily, Women's Health, Adherence) —
  this is the join key for Section 3 below.
- Clinical events without a natural daily grain (a diagnosis, a medication start) get a single
  `date` = the event date, so they sit on the same timeline as daily vitals.
- `source_sheet` is kept so any insight can cite exactly which sheet a data point came from —
  needed for the explainability requirement (Section 4).

## 3. Connecting Clinical Context to Ongoing Data

The brief's core ask: don't analyze historical context and daily signals separately. Plan:

1. For each patient, build a timeline of clinical "reference points" (diagnoses, borderline labs,
   medication changes) from the historical sheets.
2. For each reference point, define a lookback/lookahead window (e.g. ±90 days) over the ongoing
   daily signals (vitals, wearables, adherence).
3. Flag when ongoing signals move in a clinically relevant direction relative to a reference point
   within that window (e.g. borderline HbA1c + falling activity + rising weight + worsening sleep
   over the following months — the brief's worked example).

**(pending real data)** Window sizes and "clinically relevant direction" thresholds need real
values from a sample workbook, not guesses.

## 4. Pattern / Anomaly Detection — Approach Options

Not yet decided; options on the table per the brief's "Your Approach Is Up to You" guidance:

- Statistical/time-series (rolling trends, change-point detection) — simplest, most explainable
- ML-based anomaly detection (e.g. isolation forest on engineered features)
- LLM-based multi-signal reasoning over the structured timeline
- Hybrid: statistical detection + LLM explanation layer

Decision deferred to Discovery checkpoint once the team has looked at real data volume/noise.

## 5. Explainability

Every surfaced insight must show: what changed, which signals/rows support it (traceable via
`source_sheet`), how it relates to a clinical reference point, and an explicit non-diagnostic
framing ("this pattern may be worth discussing with a provider," not a diagnosis).

## 6. Responsible AI / Uncertainty

**Confidence tiers.** Every insight carries one of three qualitative confidence levels, derived
from how much of the expected signal set was actually available and how far it deviates from the
patient's own baseline — never a bare unexplained probability:

| Tier | When it applies | How it's surfaced |
|---|---|---|
| High | All expected signals present, deviation clearly outside the patient's historical range | Shown as a normal insight |
| Moderate | Some signals missing/sparse, or deviation is borderline | Shown with a visible "limited signal" badge and which signals were unavailable |
| Insufficient | Too little data to support a pattern claim | Not surfaced as an insight at all — logged internally, not shown to the clinician/patient as a finding |

Missing or sparse data is never silently dropped or backfilled to force a confident-looking
result — it either downgrades the tier or suppresses the insight entirely.

**Language guardrails — the "no diagnosis" boundary.** Every insight's copy goes through the
same filter before it can be shown:

- Allowed framing: "this pattern may be worth discussing with a provider," "N of the last M
  {signal} readings were outside your usual range," "worth a check-in based on recent trends."
- Disallowed: naming or implying a specific condition/diagnosis, prescriptive medical
  instructions ("stop taking X," "you have Y"), and unqualified certainty language ("this means,"
  "you are experiencing") in place of "this pattern," "may indicate."
- Every insight must cite the specific `source_sheet` rows/signals behind it (Section 2/5) —
  no insight ships without a traceable evidence trail a clinician could audit.

**Review checkpoint.** Before the Prototype demo, run every example insight copy the team has
drafted against this checklist (confidence tier assigned correctly, no disallowed language,
evidence cited) rather than deciding case-by-case at build time.

## 7. UX / Interface

Not yet designed. Needs: a way to see a patient's timeline, the flagged insight(s), and the
supporting evidence without reading raw model output. Revisit after Prototype checkpoint.
