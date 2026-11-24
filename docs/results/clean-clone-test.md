# Clean clone test after the history rewrite

The repository history was rewritten, so every clone made before it has to be deleted and made again. This is a test of the README steps from a new clone, run on a clean Linux machine with Python 3.11 and no earlier files.

| Step | Result |
|---|---|
| `git clone` | Works. Latest commit is the merge of PR #60. |
| `python -m venv`, `pip install -r requirements.txt` | Works. The install is large (streamlit, plotly, scikit-learn), so allow a few minutes. |
| Quick tests (20 tests in 4 files) | 20 passed in about 6 seconds. |
| `python -m uvicorn api.main:app --port 8000` | Starts. The page at `/` loads from the committed `web/dist`, so Node is not needed. |
| Full test suite | 199 passed in 36 seconds on this machine (the 10 Nov run took 17 minutes), so the time depends on the machine; the README now says so. |

## What was unclear or missing, and what was fixed in the README
1. Two sections were called "run" (Streamlit and React) and the README did not say which one to use. Now: use the React app; Streamlit is the older one.
2. No single place listed the steps from a fresh clone. Added **Start here: set up from a fresh clone**.
3. The README did not say how long the full test suite takes. Added, with a few-second set of quick tests.
4. The 1,000 workbooks are not in the repository, but the scripts expect `data/raw`. Added where to put them.
5. The "Repository Structure" section still described an empty project. Updated to the real folders.
6. Old clones: added a line to delete and clone again after the rewrite.

## Second run: Windows laptop (Krish, 15 Nov)
| Step | Result |
|---|---|
| Delete the old clone, `git clone` | Works. |
| `python -m venv .venv`, `.venv\Scripts\activate`, `pip install -r requirements.txt` | Works with Python 3.13 (the first run used 3.11). About 4 minutes. |
| `python -m uvicorn api.main:app --port 8000` | Starts; the page at `http://localhost:8000` loads. |
| First account | Became the administrator, as the README says. A second account was made for the patient test (see `patient-account-test.md`). |
| `python docs/progress_log/build_log.py` | Works (needs openpyxl, which `requirements.txt` installs). The `.xlsx` is ignored by git (`*.xlsx` in `.gitignore`), so it is not committed. |

## Third run: GitHub Codespace (Krish, 15 Nov)
The Codespace was created from `main` and set itself up with the `.devcontainer` settings, so none of the README steps had to be typed.

| Step | Result |
|---|---|
| Create codespace on main | Works. Python 3.11.18. |
| Automatic set-up (`postCreateCommand`): `pip install`, `npm ci && npm run build` in `web/`, full `pytest` | Works, about 3 minutes in total. |
| Full test suite (run by the set-up) | **199 passed, 213 warnings in 59.39 s.** The warnings include a `Pandas4Warning` from `pranapulse/loader.py` line 53 (the `join` in the daily loader); no test failed. |
| App (`postAttachCommand`) | Starts by itself on port 8000 and opens in the browser at the forwarded address; the sign-in page loads. |

Different from the laptop: in a Codespace there is no venv step and nothing to type, and the full suite runs during set-up. The test output is only in the creation log (**Ctrl+Shift+P → View Creation Log**), which is easy to miss. The README could say this in one line.

## Other clones
- Harsh and Bhavya confirmed they deleted their old clones and cloned again.

## Fourth run: Windows laptop, final main (Krish, 23 Nov, issue #105)
Fresh clone of `main` at commit `e0ead73` (after the history clean-up), Windows, Python 3.13, new virtual environment. The local model (Ollama) was **not** running, so the assistant showed "AI off - standard answers" and every answer was the standard wording; nothing was reworded by a model. The usual-range answer was not on `main` when this was run (not found in `git log`), so the app steps need repeating after that merge.

| Step | Result |
|---|---|
| Rename the old folder, `git clone`, `python -m venv .venv`, activate, `pip install -r requirements.txt` | Works. |
| Quick tests from the README (4 files) | 24 passed in 36 s. |
| `python -m pytest -q tests/test_json_safe.py tests/test_ask_trace.py` | 6 passed. |
| `python -m uvicorn api.main:app --port 8000`, open `http://localhost:8000` | Starts; the page loads. A first sign-in and one first registration attempt were rejected (401, 400) before an account was created; the second registration worked. |
| **Try demo patients** | Works: DEMO-A to DEMO-E load; DEMO-B opens as Quiet. |
| Upload the cardio demo files (`demo-files/cardio`) | The first upload was incomplete: patient PC8101 showed data from 2026-04-02 only and no LDL pattern. Uploading all six files again gave 58 years, Male, data 2026-01-01 to 2026-06-30 (181 days), and one Cardiovascular pattern with six measures. |
| Pattern finding on PC8101 | "Labs out of range: 3 of 3" (LDL cholesterol 118, 134 and 152 mg/dL, all above 0-100) and a Limits line ("Based on ..."). |
| Assistant, normal question ("Why was this flagged?") | Explains the pattern from the findings. |
| Assistant, safety question ("Do I have diabetes?") | Fixed answer: the tool does not name or decide any condition; no yes or no. |
| Assistant, "What is my average?" | Standard reply that it can only answer from this patient's findings. |

## What was unclear
- When only some of the six cardio files are selected, the app still creates the patient and flags it, with a shorter window and no pattern, and does not say that files are missing. Select all six (Ctrl+A in the file picker).
- The README does not say that the assistant shows "AI off" unless Ollama is installed and running.
