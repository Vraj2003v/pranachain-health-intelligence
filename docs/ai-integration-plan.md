# AI integration plan (PranaPulse)

Principle: **statistics decide, the language model only explains.** Detection, baselines, flags and projections stay deterministic and testable. The model never sees raw rows, never decides what is flagged, and every reply must pass `check_language` or it is replaced by the template wording.

## Where AI is used today
| Piece | Status |
|---|---|
| Insight wording (Explain with local model) | Built and tried with real local models through Ollama: llama3.1:8b and llama3.2:3b were compared on 12 answers (`docs/model-comparison.md`); llama3.2:3b is used for the live demo (`PRANAPULSE_MODEL`). Template fallback when the model is off or a reply fails the checks. |
| Assistant chat (floating, all pages) | Built. Answers from the computed readings (rules); the local model only rewords a checked draft. Every model reply must pass three checks (wording, every number from the findings, every finding ID exists), with one retry before the template is shown (`pranapulse/ask.py`, `reply_ok`). Safety questions get a fixed answer and never reach the model. A **How this answer was made** panel shows the route, what the model was given, each reply and its checks. Re-tested with 250 answers on 22 Nov (`docs/safety-test-results.md`). |
| Compare measures | Built (no AI; statistics only). |

## Phases

Status key: **Done** is in the code today. **Plan, not built** means it is a proposal only; nothing in the repository does it yet.

1. **Done. Make the existing model path real.** Run Llama 3.1 8B and Qwen 2.5 7B (Bhavya) on 10 insights each; score on faithfulness (no invented numbers), tone, and `check_language` pass rate. Pick one default. Log failures. *Result:* llama3.1:8b and llama3.2:3b were run; Qwen 2.5 7B was not run. llama3.2:3b is the demo default (`docs/model-comparison.md`).
2. **Plan, not built. Grounded chat with tool calls.** Replace rule intents with *tool calls*: the model picks a function (`get_measure`, `compare`, `top_changes`, `explain_finding`, `data_quality`) with arguments, our code runs it on the patient's data, and the model only words the returned facts. Wording check runs on the final text. Same fallback as today. *Status:* the assistant still uses rule-based routing, not tool calls. Only the number check from this phase is built (`_numbers_ok` in `pranapulse/ask.py`).
3. **Plan, not built. Retrieval over history.** Index each patient's history, medications and lab notes as short snippets; retrieve only snippets tied to the flagged measures ("Metformin since Mar 2025") so explanations connect to history without sending whole files. *Status:* there is no retrieval index. History, medications, clinical notes and medication adherence are added to findings as plain context.
4. **Plan, not built. Pattern assist (research track).** Use a simple learned model (e.g. isolation forest or change-point detection) only to *suggest* extra windows to check, such as the mid-year episodes that first-vs-last 90 days can miss. Anything it suggests still has to pass the same statistical test before it is shown. *Status:* no learned model is in the code; detection is statistics only.
5. **Partly done. Evaluation set.** 50 hand-reviewed workbooks (Harsh), 30 red-team questions (diagnosis, dosing, "am I dying"), regression tests that run in CI. *Status:* the red-team questions are built into `scripts/assistant_test.py` (30 safety and 20 normal questions per patient, 250 answers, re-run 22 Nov). Tests run with `pytest` on each machine; there is no CI yet.

## Guardrails (unchanged)
- No diagnosis, no risk score, no treatment advice, no numeric "confidence". Cautious words plus pointing to a healthcare provider are required.
- Facts only: the prompt contains computed values; answers with numbers not in the facts are rejected (number-match check built, `pranapulse/ask.py`).
- Local by default: Ollama on the user's machine; nothing leaves the device. Hosted models are optional and off unless the team and PranaChain agree.
- Not fine-tuned. Fine-tuning is out of scope; prompt, tools and checks do the work.
- Audit: each question is logged (who, when, which file), never the health data itself.

## Substitutes by environment
| Setting | Model option |
|---|---|
| Laptop 16 GB | Llama 3.1 8B or Qwen 2.5 7B via Ollama |
| Laptop 8 GB / Codespace | Llama 3.2 3B via Ollama |
| No model available | Template wording (default, always works) |
| Online demo | Hosted API behind the same wording check, only with synthetic data |

## Questions to settle with Abhishek
1. Is a local model enough for the final pitch, or should a hosted model be shown?
2. May the assistant answer free-text questions, or only guided ones?
3. How should "risk" language be phrased given our no-risk-score rule (proposal: Changes found / No clear change / Not enough data)?
