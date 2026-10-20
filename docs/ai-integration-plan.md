# AI integration plan (PranaPulse)

Principle: **statistics decide, the language model only explains.** Detection, baselines, flags and projections stay deterministic and testable. The model never sees raw rows, never decides what is flagged, and every reply must pass `check_language` or it is replaced by the template wording.

## Where AI is used today
| Piece | Status |
|---|---|
| Insight wording (Explain with local model) | Built, Ollama + Llama 3.1 8B, template fallback. Not yet tried with a real model. |
| Assistant chat (floating, all pages) | Built. Answers from the computed readings (rules); optional local-model rewrite of general answers; multi-turn memory; buttons that open the right chart. |
| Compare measures | Built (no AI; statistics only). |

## Phases
1. **Now to 2 Nov: make the existing model path real.** Run Llama 3.1 8B and Qwen 2.5 7B (Bhavya) on 10 insights each; score on faithfulness (no invented numbers), tone, and `check_language` pass rate. Pick one default. Log failures.
2. **Grounded chat (2 to 16 Nov).** Replace rule intents with *tool calls*: the model picks a function (`get_measure`, `compare`, `top_changes`, `explain_finding`, `data_quality`) with arguments, our code runs it on the patient's data, and the model only words the returned facts. Wording check runs on the final text. Same fallback as today.
3. **Retrieval over history.** Index each patient's history, medications and lab notes as short snippets; retrieve only snippets tied to the flagged measures ("Metformin since Mar 2025") so explanations connect to history without sending whole files.
4. **Pattern assist (research track).** Use a simple learned model (e.g. isolation forest or change-point detection) only to *suggest* extra windows to check, such as the mid-year episodes that first-vs-last 90 days can miss. Anything it suggests still has to pass the same statistical test before it is shown.
5. **Evaluation set.** 50 hand-reviewed workbooks (Harsh), 30 red-team questions (diagnosis, dosing, "am I dying"), regression tests that run in CI.

## Guardrails (unchanged)
- No diagnosis, no risk score, no treatment advice, no numeric "confidence". Cautious words plus pointing to a healthcare provider are required.
- Facts only: the prompt contains computed values; answers with numbers not in the facts are rejected (add a number-match check in phase 2).
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
