# PranaPulse demo script (about 5 minutes)

Before presenting:
- Run `python scripts\make_cardio_demo.py`. It writes six synthetic files for patient PC8101 to `demo-files\cardio\` (two daily-reading CSVs, three lipid panels and a clinic summary).
- Run `python scripts\demo_check.py <dataset-folder> PC0466` and check that every row says pass (see `docs/results/demo-rehearsal.md`).
- Start the app, sign in, and load the demo patients (**My files**, **Add demo patients**, or **Try demo patients** on the welcome screen).
- Open the assistant and ask one warm-up question (for example "How is my weight?"). The first answer is slower while the local model loads. The assistant header should say **AI on** with the model name. If it says **AI off · standard answers**, Ollama is not running and every answer will be the standard wording.
- Use DEMO-A (metabolic) for the patient part; it is selected by default.
- Have a second browser window signed in with a doctor account for the doctor part. To show **Activity log**, use the administrator account (the first account created on this installation).

Throughout the demo, point once to the **five-step strip** at the top (Understand, Connect, Detect, Explain, Ask). It highlights the step the current screen belongs to: Files is Connect, findings are Detect, an open "Why was this flagged" is Explain, the assistant is Ask, everything else is Understand.

## Patient part (about 3 minutes 30 seconds)

| Time | Do this | Say this |
|---|---|---|
| 0:00 | Open **My summary** (hide the Getting started box with ✕ first). Point to the five-step strip | "PranaPulse compares each person with their own earlier self, never with a population average. The strip shows where we are in the five steps from the kickoff." |
| 0:20 | Click the **Metabolic** card and read the **Limits** line under the finding | "Several related measures moved the same way over the year. Each finding has a Limits line: how many readings stand behind it, the data flag, and that no condition is named." |
| 0:45 | Open **Trends**, pick **Weight**, tick **Show usual range** where the measure has one, and hover over the projection | "Daily values, the weekly average and an 8-week straight-line projection with a 95% range. The change is judged against the person's own baseline. The projection is not a prediction." |
| 1:10 | Open **Compare**, pick two measures and switch between **% change** and **Real units** | "Related measures side by side, to see whether they moved together." |
| 1:30 | Press the round chat button and ask **"What is my average?"**. Open **How this answer was made** under the answer | "This panel shows how every answer was made: which route was taken, and if the local model was used, exactly what it was given (computed facts only, no name, no raw rows, no dates), what it replied, and whether the reply passed the three checks: wording, every number from the findings, every finding ID real." |
| 2:00 | Ask **"Why was this flagged?"** | "The answer comes from the person's own readings. The model only rewords a checked draft." |
| 2:15 | Ask **"Do I have diabetes?"** and open **How this answer was made** again | "Safety questions never reach the model. The panel says so: a fixed answer is shown and the model was not used. In our 250-answer re-run, all 150 safety questions got this fixed answer." |
| 2:40 | Open **My files**, upload the six files from `demo-files\cardio\` together. Select PC8101 | "Files in different formats merge into one record. Six months of readings, three lipid panels and a clinic note now give a cardiovascular pattern. Each file can be removed again, and the record is rebuilt from what remains." |
| 3:10 | (If the dataset workbook is uploaded) select **PC0466** and open the **Women's health** card | "This is a patient from the provided dataset, not a file we made. Her cycle log gives an irregular-cycle finding, and the finding cites PCOS from her medical history as context." |

## Doctor part (about 1 minute 30 seconds)

| Time | Do this | Say this |
|---|---|---|
| 3:30 | Switch to the doctor window: **All patients** | "A doctor starts with the whole group: how many patients have a finding, and how many are quiet. Quiet is intended." |
| 3:45 | Click a scenario card, then a patient row | "Each card filters to one area: cardiovascular, metabolic or women's health." |
| 4:00 | Open **Full findings**, use the **Cardiovascular / Metabolic / Women's health** jump buttons, then open **Why was this flagged? Supporting evidence** on one finding | "Each disease area uses only its own measures. The evidence table shows the readings, the dates compared, the averages and the days with data, so the finding can be checked by hand." |
| 4:25 | Open **Data quality** | "For every signal we show how much data there was. Limited data is badged; insufficient data is never reported." |
| 4:40 | (Administrator account) Open **Activity log** | "Every sign-in, upload, question and deletion is logged, so it is clear who did what." |

Points to land: per-person baseline, explainable evidence with a Limits line on every finding, honest data-sufficiency flags, a visible record of how each assistant answer was made, no diagnosis, runs locally.
