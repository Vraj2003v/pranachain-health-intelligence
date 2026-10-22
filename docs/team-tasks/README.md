# Week 4 tasks: what to run, what to submit

Due before the meeting on **Mon 2 Nov**. Results go on your GitHub issue as a comment, and the result files are committed to `docs/results/`.

First time only: `git clone https://github.com/Vraj2003v/pranachain-health-intelligence`, then in the folder:

```
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Harsh (Issue #35): assistant safety test
1. Start Ollama (optional, for AI answers): `ollama pull llama3.1:8b`
2. Run: `python scripts/assistant_test.py --folder <folder with PC workbooks> --patients 10`
3. Open `assistant_test_results.csv` in Excel. Read each answer and fill **Verdict** (OK / Unsafe / Unclear / Wrong) and **Note**.
4. Ask Sheetal to confirm the Final Pitch date.
5. Submit: copy the file to `docs/results/assistant_test_results.csv`, commit, and comment on #35: how many OK / Unsafe / Unclear / Wrong, the worst three answers, and the Final Pitch date.

## Bhavya (Issue #36): model comparison and threshold
1. `ollama pull llama3.1:8b`, `ollama pull llama3.2:3b`, `ollama pull qwen2.5:7b`
2. Run: `python scripts/compare_models.py --models llama3.1:8b llama3.2:3b qwen2.5:7b --folder <workbooks> --patients 10`
3. Open `model_comparison.csv`. Score **Faithful (1-5)** and **Tone (1-5)** by hand for each answer.
4. Threshold: in `pranapulse/detect.py` find `RECENT_MIN_EFFECT = 1.5`. Run `python scripts/scan_dataset.py` with 1.5, 1.0 and 0.8 and note how many patients each flags.
5. Submit: copy the CSV to `docs/results/model_comparison.csv`, commit, and comment on #36: the summary table printed by the script, your average scores, your recommended default model, and your recommended threshold with the counts.

## Krish (Issue #37): interface review and demo script
1. Start the app: `python -m uvicorn api.main:app --port 8000` and open http://localhost:8000. For phone, run `python run_network.py` and open the LAN link on your phone.
2. Create a Patient account and a Doctor account. Check light and dark mode, the Compare tab, the assistant popup, collapsing the sidebar, and the guide (?).
3. Fill `docs/ui-review.md` (copy the table rows): each confusing thing, the screen it is on, and a screenshot name.
4. Read `docs/demo-script.md` (a draft is there), practise it once, and fix any step that does not match what you see.
5. Submit: commit `docs/ui-review.md` and `docs/demo-script.md`, and comment on #37 with the top three issues.

## How to commit (pick one)
**Website, no git:** open the repo on GitHub, Add file, Upload files, drop your file(s) into the right folder, write a short message, and choose a new branch with a pull request.

**Git:**
```
git checkout -b my-task
git add docs/results docs/ui-review.md docs/demo-script.md
git commit -m "Add week 4 results"
git push -u origin my-task
```
Then open a pull request on GitHub and tell Vraj.
