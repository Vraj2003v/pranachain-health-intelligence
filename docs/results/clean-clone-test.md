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

## Other clones
- Harsh and Bhavya confirmed they deleted their old clones and cloned again.

## Still to do by hand (needs a person)
- Repeat the same steps in a new GitHub Codespace and note anything different.
