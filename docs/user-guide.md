# PranaPulse: user guide

PranaPulse looks at a person's own health readings and shows where something has moved away from their usual pattern. It highlights patterns that may be worth discussing with a healthcare provider. It does not diagnose or give medical advice.

## Getting started

### Create an account or sign in
Choose **Create account**, enter your name, email and password, and pick who you are:
- **Patient**: see your own readings and ask questions.
- **Doctor / healthcare provider**: review patients and the evidence behind each finding.

Your role decides which tabs you see. The very first account created on a new installation becomes the administrator, whichever role is picked. Next time, choose **Sign in**.

### Add readings
On the welcome screen, choose **Upload workbooks** (.xlsx), or **Try demo patients** to explore with example data. You can add or delete files later from the **My files** tab (**Files** for doctors). Your files are only visible to your own account.

### Find your way around
- **Tabs** across the top switch between pages.
- **Sidebar** on the left lists the loaded workbooks. Search by patient ID, or tick **Only patients with an insight**. The **‹** button folds the sidebar away and **›** opens it again.
- **Chat button**: the round 💬 button at the bottom right opens the assistant on any page. Press ✕ or Escape to close it.
- **Guide button**: the **?** button at the top opens a plain-language guide to terms such as *baseline*, *weekly average*, *projection* and *95% range*.
- **Light / dark mode**: the button next to **?** cycles through 🌓 Auto (follows your device), ☀️ Light and 🌙 Dark.
- The **?** and light/dark buttons are hidden while the sidebar is folded; press **›** to see them again.
- At the bottom of the sidebar, you can sign out or permanently delete your account and all your files.

On a phone, the sidebar becomes a drop-down for picking a workbook, with the **?**, theme and **Sign out** buttons at the top. The tabs sit in a bar at the bottom of the screen, within thumb reach; swipe it sideways to reach the last tabs. Measure buttons and the **3 months / 6 months / Full year** buttons also swipe and tap easily.

## For patients

Your tabs are **My summary**, **Trends**, **Compare** and **My files**. The assistant is the round 💬 button in the corner on every screen.

### 1. My summary
Shows three disease areas, named plainly: **Cardiovascular**, **Metabolic** and **Women's health**. Each card lists the measures it looks at (a disease area only uses its own measures) and says **No clear change**, or how many changes were found (for example **1 change found**), with a plain sentence about what moved. Click a card to read more, or choose **Open all trends**. A **Getting started** checklist appears the first time; hide it with ✕.

### 2. The assistant (💬 button)
Press the 💬 button. Ask things like "Why was this flagged?" "How is my weight?" or "What is the usual range?". Answers come from your own readings and only from the measures of the disease area you are asking about, and the assistant can open the matching chart for you. Questions about diagnosis, medicines or treatment are not answered; ask a healthcare provider instead.

### 3. Trends
Pick a measure to see daily values, the weekly average and, where there is enough data, a straight-line **projection** 8 weeks ahead with a shaded **95% range**. Events from your history are marked on the chart. Lab results (such as HbA1c, fasting glucose and LDL cholesterol) and cycle length have their own charts. Hover over (or tap) the chart to see exact values. Choose **3 months**, **6 months** or **Full year** above the chart. For measures with a usual adult range (blood pressure, resting heart rate, sleep) a green band shows it, and a line under the chart says whether the recent average is within it; tick or untick **Show usual range**. Weight, steps and HRV have no single usual range, so they are compared with your own baseline only. The projection shows what happens if the recent trend continues; it is not a prediction.

### 4. Compare
Pick up to four measures to see on one chart whether they moved together. Each line shows the weekly average as a % change from your own first 90 days, so different units fit on one scale. Choose **3 months**, **6 months** or **Whole year**, and switch between **% change** and **Real units** (real units work with two measures or fewer).

### 5. My files
Upload more workbooks, add demo patients, open a file, or delete one file or all of them.

## For doctors and healthcare providers

Doctors start on **All patients** and also have **Patient summary**, **Trends**, **Compare**, **Full findings**, **Data quality** and **Files**. The administrator also has **Activity log**.

### All patients
- The top row shows how many patients are loaded, how many have an insight, how many are quiet, and how many insights rest on limited data.
- The three scenario cards (**Metabolic health**, **Cardiovascular / hypertension**, **Women's health (PCOS)**) filter the table to one area. Click the card again to clear it.
- Filter by status or data flag, search by patient ID, and sort by clicking a column heading.
- **Download CSV** saves the patient list.
- Click a row to open that patient.

"Quiet" is intended: ordinary day-to-day variation is not reported.

### Patient summary
The same three-area view a patient sees, for the selected patient. **See the full evidence** jumps to **Full findings**.

### Full findings
Findings grouped under **Cardiovascular**, **Metabolic** and **Women's health**, each with its key figures and an **evidence table** showing the readings behind it. **See trend line and projection** opens the chart, and **Explain with local model** rewrites the finding in plainer words.

### Data quality
For each signal: the source sheet, the share of days with data, how many readings fall in the earlier and recent windows, the change and the data flag.
- **Sufficient**: enough data to report.
- **Limited**: reported with a badge; treat it with more caution.
- **Insufficient**: not reported as an insight.

The flag describes how much data was available, not how certain the result is.

### Full findings
Findings are grouped by disease area, with jump buttons (Cardiovascular, Metabolic, Women's health) and a count for each. Every finding shows a tag for where the recent readings sit against the usual range: **Outside the usual range**, **Within the usual range, worth watching**, or **Personal baseline only** (no single usual range exists). The evidence table has the usual range and where the recent value sits against it.

### Activity log (administrator only)
A list of who did what in the app (sign-ins, failed sign-ins, uploads, patients opened, questions asked, deletions), newest first, showing the last 200 events. Only the administrator sees this tab. The administrator is the first account created on a new installation; nobody can choose this role when signing up.

### Trends, Compare and the assistant
These work as described for patients, for whichever patient is selected in the sidebar.

## Tips
- If a result worries you, talk to a healthcare provider.
- This is a prototype for academic use on synthetic or anonymised data.


### Attention level
Each disease area shows a short level: **No clear change**, **Worth watching** or **Worth discussing with a healthcare provider**. It is a simple rule on the findings shown (how far the readings sit from the usual range, and how much data is behind them). It does not name a condition and is not a measure of likelihood.

### The summary follows the measure you pick
In an area's detail, the summary above the graph changes with the measure tab (for example Systolic BP, then Diastolic BP). A measure with a finding shows that finding. A measure without one shows its latest value, the change against your first 90 days, and where it sits against the usual range. Other findings in the same area are listed under it.
