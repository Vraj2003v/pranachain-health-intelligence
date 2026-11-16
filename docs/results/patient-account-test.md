# Patient account test (issue #64)

Tester: Krish. Date: 15 Nov 2026. Branch: `krish-readme-guide` (main at the merge of PR #70).
Set-up: Windows laptop, Python 3.13, fresh clone, `pip install -r requirements.txt` (about 4 minutes), `python -m uvicorn api.main:app --port 8000`, Chrome.
Account: a new **Patient** account (`patient@test.com`) with **Try demo patients**. The first account on this laptop was the administrator, so a second account was made for this test.
Desktop: Chrome, dark mode. Phone: Chrome device view (DevTools, 400 × 464), not a physical phone.
The local model was not running, so the assistant showed "AI off · standard answers".

## Checks

| Check | Result |
|---|---|
| Sign up as Patient, sign out, sign in again | OK |
| My summary: three areas (Cardiovascular, Metabolic, Women's health) | OK, names match the user guide |
| Open an area (Metabolic, See what changed): chart, zoom bar, projection | OK |
| Trends: measure buttons, 3 months / 6 months / Full year | OK |
| Compare: two measures, % change / Real units, Whole year | OK |
| Assistant: "Why was this flagged?" | OK, answered from the readings |
| Assistant: "Do I have diabetes?" | OK, safety reply ("does not name or decide any condition") |
| Assistant closes with Esc | OK |
| My files | OK |
| Phone view: no sideways scrolling, all 4 tabs in the bottom bar, assistant fits | OK |

## What is wrong or confusing for a patient

| # | Screen | Problem |
|---|---|---|
| 1 | My summary, Cardiovascular card | Shows **No clear change** and **Worth watching** at the same time; a patient cannot tell which one applies. |
| 2 | Sidebar (patient account) | A patient sees **Search patient ID**, **Only patients with an insight** and other people (DEMO-C, DEMO-D, DEMO-E). Also noted in the 30 Oct review; not changed. |
| 3 | Summary card, assistant | Wording mixes "you" and "this patient": the Metabolic card says "over this patient's year", and the assistant answer says "this patient's usual day-to-day variation". |
| 4 | Area detail chart (Weight) | The **Your usual: 88.6** label sits on top of the data dots at the left and is hard to read. The y-axis labels are unevenly spaced (94.1, 90.7, 88.7, 86.7). |
| 5 | Several screens | The round chat button covers the bottom-right of content: the "Ask about metabolic" box, the Compare chart and the summary cards on the phone view. |
| 6 | Trends legend (dark mode) | **Weekly average** is dark blue on a dark background and is hard to read. |
| 7 | Trends and Compare | The same range option is called **Full year** on Trends and **Whole year** on Compare. |
| 8 | Assistant popup | Cramped: the answer and the suggested questions each have their own small scroll area, so even one answer needs scrolling and the last line is cut off. |
| 9 | Phone view, top bar | The patient picker text is cut off ("DEMO-A · Changes fo…"). |
