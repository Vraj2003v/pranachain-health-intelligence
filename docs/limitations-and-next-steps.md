# Limitations and next steps

This page is part of the technical handoff asked for in the kickoff deliverables (see `README.md`). PranaPulse is a course prototype. It compares a person with their own earlier readings and shows where something has moved. This page lists what it does not do, what it cannot read yet, where its results can be wrong, and what we would do next. Every point is based on the code as it is today; the file that backs it is named in brackets.

## What the system does not do
- **It does not diagnose.** It never names a condition as fact, gives a dose or treatment, or tells someone to start or stop a medicine. Every sentence shown passes a wording check that blocks this (`pranapulse/explain.py`, `check_language`).
- **It does not give a risk score, probability or confidence number.** Each finding has a data-sufficiency flag instead: Sufficient, Limited or Insufficient (`pranapulse/detect.py`, `_flag`).
- **It does not compare people with each other.** The baseline is always the same person's earlier data (`pranapulse/detect.py`).
- **It does not use medical history to decide what to report.** Medical History and Medication History only add context to the wording; detection runs on readings, labs and cycles (`docs/results/validation_summary.md`).
- **It covers three areas only:** Cardiovascular / hypertension, Metabolic health, and Women's health (PCOS) (`pranapulse/reference.py`, `AREAS`).
- **It is not a medical device** and has not been tested on real patients. All 900 workbooks are synthetic.

## Data it cannot read yet
- **Four workbook sheets are not used:** Habits Weekly, Symptoms Timeline, Encounters & Notes and Medication Adherence. The loader reads only Patient Profile, Vitals Daily, Wearable Daily, Lab Results, Medical History, Medication History and Women Health (`pranapulse/loader.py`).
- **Scanned PDFs and photos need Tesseract OCR installed.** Without it, those files are refused with a message asking for a text PDF, CSV or XLSX. Values read by OCR are marked so the person can check them (`pranapulse/intake.py`).
- **Only the first 12 pages of a scanned PDF are read** (`pranapulse/intake.py`, `_ocr_pdf`).
- **Uploaded lab reports are matched against a fixed list of 15 standard tests** (HbA1c, fasting glucose, lipids, liver and kidney markers, blood count, vitamins). A test outside that list is reported as not read, not guessed (`pranapulse/reports.py`, `CANON`).
- **Readings outside plausible limits are rejected,** for example systolic BP outside 50–260 mmHg (`pranapulse/readings.py`, `MEASURES`).
- **The PCOS pattern needs a cycle log.** Without one the app says the women's health pattern cannot be checked. Cycle data is never inferred from sex (`pranapulse/record.py`, `docs/data-schema.md`).

## Where results can be wrong
- **Thresholds are placeholders.** A recent change is reported when the latest 14 days sit more than 0.8 times the person's own daily variation from the 90 days before. This was 1.5 until 15 Nov. On 900 workbooks the recent check flags 0 people at 1.5x and 26 at 0.8x, so the number decides how many people get a finding (`pranapulse/signals.py`, `docs/three-approaches.md`).
- **Usual ranges are general adult values** that have not been confirmed with the partner (`pranapulse/reference.py`, `docs/user-guide.md`).
- **Validation shows consistency, not accuracy.** The five demo patients score 1.00 precision and recall, but they were built to contain those patterns. On the 900 workbooks, cardiovascular findings appear about as often for people without related history (2%) as with it (3%), so that section does not separate people well yet (`docs/results/validation_summary.md`).
- **Missing days weaken results.** Some workbooks average about 48 missing wearable days. Low coverage gives a Limited flag or holds the finding back (`docs/data-schema.md`, `pranapulse/detect.py`).
- **The trend projection is a straight line** through recent weekly averages with a 95% range. It cannot predict a sudden change (`pranapulse/forecast.py`).
- **The cycle check uses every recorded cycle,** so older regular cycles can hide a recent change (`pranapulse/detect.py`, `docs/three-approaches.md`).
- **The local model can still word things badly.** In the 30 Oct test, 11 of 42 safety questions that reached the model got a reassuring or condition-hinting answer, even though all passed the wording check. After the safety word list was widened, the 22 Nov re-run gave the fixed safe answer to all 150 safety questions. The model can still be wrong on normal questions: 3 of 100 stated a wrong unit or direction that the number check does not catch, and 1 reassured (`docs/safety-test-results.md`).
- **OCR can misread numbers.** That is why OCR values are flagged for the person to check (`pranapulse/intake.py`).

## Reasoning choices

**How we chose the approach.** Early on we listed four options: statistical and time-series checks, ML anomaly detection (for example isolation forest), an LLM reasoning over the timeline, and a hybrid of statistical detection with an LLM explanation layer (`docs/architecture.md`, section 4). We built the hybrid: statistics decide what is found, and the local LLM only rewords the result. The three choices below explain why.

**Why statistics on the person's own history instead of a trained model.**
- *No labels.* The dataset has no column saying which patient has which pattern, so there is nothing reliable to train on (`docs/data-schema.md`).
- *Fairness to the individual.* A person's "normal" differs from the population. Comparing them with their own baseline (the first and last 90 days, and the latest 14 days against the 90 before) detects change for that person.
- *Every number can be explained.* The rule is a difference larger than the person's daily variation plus a trend test (Kendall tau, p < 0.01). Each finding shows the dates compared, the averages and the days with data, so a provider can check it by hand (`pranapulse/signals.py`, `pranapulse/detect.py`).
- *Synthetic data.* A model trained on 900 synthetic people would learn how the data was generated, not how real patients behave.

**Why there is no confidence score.**
- The business partner advised against a numeric confidence score (`docs/architecture.md`, section 6).
- A percentage would look like a medical probability, which we cannot support with synthetic data.
- Instead each finding says how much data stands behind it: **Sufficient** (at least 85% of days with data and at least 72 days in each window), **Limited** (at least 60% and 45 days), or **Insufficient**, which is held back rather than shown (`pranapulse/detect.py`, `_flag`). The wording check also blocks the words confidence, probability and risk score (`pranapulse/explain.py`).

**Why the local LLM only rewords answers, behind checks.**
- *Detection stays statistical.* The model never decides what is found. It gets only the computed facts and is asked to reword a safe draft answer (`pranapulse/llm.py`).
- *Nothing leaves the machine.* The model runs locally through Ollama.
- *Safety questions skip the model.* Questions about diagnosis, disease, medicine, dose, cancer, danger and similar words get a fixed safe answer (`pranapulse/ask.py`, `SAFETY`).
- *Every reply is checked.* A reply is used only if it passes the wording check, every number in it appears in the patient's findings, and every finding or evidence ID it cites exists. If it fails, the model gets one retry, then the template answer is shown (`pranapulse/ask.py`, `reply_ok`). If Ollama is not running, the template answer is used.

## What we would do next
1. **Calibrate the thresholds and usual ranges** with the partner and, if possible, with real de-identified data.
2. **Start the baseline after a major history event,** such as surgery. The partner asked for this and it is not built yet (`docs/three-approaches.md`).
3. **Use only the most recent 6 cycles** for the PCOS check so old cycles do not hide a recent change.
4. **Read the unused sheets:** medication adherence, symptoms timeline, habits and encounter notes, as context.
5. **Tighten the assistant's reply check:** a reply must state the same direction and unit as its finding, and a question about a measure the person does not have (such as cycles) must say so (`docs/safety-test-results.md`).
6. **Improve the cardiovascular section,** which does not yet separate people with related history from those without.
7. **Make setup easier:** add `reportlab` to `requirements.txt` (two tests need it) and document installing Tesseract with English language data.
