# Interface review (fill in)

Reviewer: Krish. Date: 30 Oct 2026. Devices: desktop (Chromium, 1366×768) and phone (Pixel 7 screen size, 412×915, emulated in Chromium). Demo patients loaded; local model not running during the test, so the assistant gave standard answers ("AI off").

| # | Screen / tab | Light or dark | Device | What is confusing for a patient | Screenshot file |
|---|---|---|---|---|---|
| 1 | My summary, sidebar | Both | Desktop and phone | A patient account shows five people (DEMO-A to DEMO-E) with "Search patient ID", "Only patients with an insight" and a "Viewing" drop-down. The page says "Good afternoon, Pat" but then "Patient DEMO-A, 52, Female", so it is unclear whose readings these are. | ui-review-screens/03-patient-summary.png |
| 2 | Trends, Compare, Ask a question | Light | Desktop | The wording switches between "you" and "this patient": the header says "Patient DEMO-A … this patient's own baseline", the summary card says "over this patient's year", and one assistant answer says both "this patient's usual variation" and "your own usual pattern". | ui-review-screens/06-trends.png, ui-review-screens/09-assistant-answer.png |
| 3 | My summary | Light | Phone | There are two patient pickers on the same screen (the top "DEMO-A · Flagged" box and "Viewing DEMO-A"), and the word "Flagged" sounds alarming for a patient. The tab bar is cut off after "Trends", with no sign that it scrolls sideways, so "Compare" and "My files" are easy to miss. | ui-review-screens/13-phone-patient-My-summary.png |
| 4 | Sign-up | Light | Desktop | The first account created becomes Administrator even when "Patient" is chosen, so a first-time user lands on All patients and Activity log. The form does say this in small text, but it is easy to miss. | ui-review-screens/01-first-account-landing.png, ui-review-screens/02-first-account-home.png |
| 5 | Sidebar collapsed | Light | Desktop | When the sidebar is folded, the **?** guide button and the light/dark button disappear until it is opened again. | ui-review-screens/05-sidebar-collapsed.png |
| 6 | All patients (doctor) | Light | Desktop and phone | The round chat button sits on top of the bottom-right of the table and hides part of the last row and column. | ui-review-screens/04-doctor-all-patients.png, ui-review-screens/13-phone-doctor-All-patients.png |

Checks (mark OK or note a problem):
- [x] Sign-up with Patient role, then sign-in: OK. Note: on a new database the first account becomes Administrator whatever role is picked (row 4).
- [x] Doctor account shows All patients and the sidebar patient list: OK, 5 demo patients listed, scenario cards and Download CSV work.
- [x] Sidebar collapses and opens again, content stays centred: OK, tabs stay centred. Note: ? and theme buttons are hidden while folded (row 5).
- [x] Compare tab: two measures, chart readable: OK. Weight and Systolic BP are pre-selected; 3 months / 6 months / Whole year and % change / Real units work.
- [x] Assistant popup opens, answers, closes with the cross or Escape: OK. "Why was this flagged?" answered from the readings; "Do I have diabetes?" got the safety reply; Escape closes it. Not tested with the local model running.
- [x] Light and dark mode both readable: OK. The button cycles Auto → Light → Dark.
- [x] Phone: no sideways scrolling, tabs usable: OK, no page scrolls sideways on any tab (patient or doctor). Note: the tab bar itself scrolls sideways with no hint (row 3).
