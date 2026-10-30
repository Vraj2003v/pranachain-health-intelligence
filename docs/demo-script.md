# PranaPulse demo script (about 4 minutes)

Before presenting:
- Start the app, sign in, and have the demo patients loaded (**My files** tab, **Add demo patients**, or **Try demo patients** on the welcome screen).
- Ask the assistant one warm-up question (for example "How is my weight?"). The first answer is slower while the local model loads; later answers are faster. Check that the assistant header does not say "AI off"; if it does, the model is not running and answers will be the standard wording.
- Use DEMO-A (metabolic) for the patient part; it is selected by default.
- Have a second browser window signed in with a doctor account for the doctor part. To show **Activity log**, use the administrator account (the first account created on this installation).

## Patient part (3 minutes)

| Time | Do this | Say this |
|---|---|---|
| 0:00 | Open **My summary** (hide the Getting started box with ✕ first) | "PranaPulse compares each person with their own earlier self, never with a population average." |
| 0:25 | Click the **Weight, sugar and activity** card | "This area shows a change worth a closer look: several related measures moved the same way over the year." |
| 0:50 | Open **Trends**, pick a measure, hover over the projection | "The chart shows daily values, the weekly average and an 8-week straight-line projection with a 95% range. It is a continuation of the trend, not a prediction." |
| 1:20 | Open **Compare** (Weight and Systolic BP are already picked), switch between **% change** and **Real units** | "Related measures can be viewed side by side to see whether they moved together." |
| 1:45 | Press the round 💬 chat button and ask "Why was this flagged?" | "Answers come from the person's own readings. A local model only rewords them, and every reply is checked for safe wording and for numbers that are not in the data." |
| 2:15 | Ask "Do I have diabetes?" | "Safety questions never reach the model. The tool does not diagnose, rate risk or advise on treatment." |
| 2:35 | Open **My files**, show where readings are added and deleted | "Everything runs on this computer; the person can delete their data at any time." |
| 2:50 | Press the theme button (🌓 / ☀️ / 🌙) | "The interface follows the device setting or the person's own choice of light or dark." |

## Doctor part (about 1 minute)

| Time | Do this | Say this |
|---|---|---|
| 3:00 | Switch to the doctor window: **All patients** | "A doctor starts with the whole group: how many patients have an insight, and how many are quiet. Quiet is intended." |
| 3:15 | Click a scenario card, then a patient row | "Each card filters to one area: cardiovascular, metabolic or women's health." |
| 3:25 | Open **Full findings** | "Every finding has an evidence table with the readings behind it, grouped by area." |
| 3:40 | Open **Data quality** | "For every signal we show how much data there was. Limited data is badged; insufficient data is never reported." |
| 3:50 | (Administrator account) Open **Activity log** | "Every sign-in, upload, question and deletion is logged, so it is clear who did what." |

Points to land: per-person baseline, explainable evidence, honest data-sufficiency flags, no diagnosis, runs locally.
