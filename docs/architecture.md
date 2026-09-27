# Architecture Notes (living doc)

Fill this in as decisions get made at each checkpoint. Suggested skeleton below.

## 1. Data Model

How each patient workbook's 9 sheets are parsed and normalized into a common longitudinal
representation (e.g. one long-format table keyed by patient_id, date, signal_name, value, source_sheet).

## 2. Connecting Clinical Context to Ongoing Data

How historical findings (a borderline lab value, a diagnosis, a medication start date) are linked
to the ongoing daily/weekly signals so the system can reason about them together instead of
analyzing each sheet independently.

## 3. Pattern / Anomaly Detection

Techniques under consideration (see slide "Your Approach Is Up to You"):
- Statistical/time-series methods (rolling trends, change-point detection)
- ML-based anomaly detection
- LLM-based multi-signal reasoning
- Hybrid approaches

## 4. Explainability

For every surfaced insight: what changed, what evidence supports it (which signals, over what
window), how it relates to clinical history, and what the model is *not* claiming (no diagnosis).

## 5. Responsible AI / Uncertainty

- How missing or sparse data is handled and communicated
- How confidence/uncertainty is represented to the end user
- Non-diagnostic framing and disclaimers

## 6. UX / Interface

What the dashboard/timeline looks like and how a patient or clinician reads an insight without
needing to interpret raw model output.

## Open Questions (from the brief)

- How will very different data types be normalized?
- How will time and historical context be represented?
- How will unsupported correlations be avoided?
- How will uncertainty be communicated?
- What happens when important data is missing?
