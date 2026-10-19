"""Plain-language answers to a patient's questions about their own findings.

Answers are built from the computed findings only. Every answer must pass check_language; the optional
local model may rephrase it, but a reply that fails the check is dropped for the template answer.
"""
import json
import re

from . import llm
from .explain import check_language
from .signals import RECENT_DAYS, WINDOW_DAYS

CLOSE = " This may be worth discussing with a healthcare provider."

SUGGESTED = [
    "Why was this flagged?",
    "What does the baseline mean?",
    "How much data is behind this?",
    "What does the projection show?",
    "What should I do next?",
    "Does this mean I have a condition?",
]


def _area(insights, area):
    return [i for i in insights if not area or i.scenario == area]


def answer_template(question: str, insights, area: str | None = None) -> str:
    q = question.lower()
    items = _area(insights, area)
    where = f" in the {area} area" if area else ""
    if re.search(r"diagnos|disease|condition|do i have|serious|dangerous|risk", q):
        return ("This tool does not name or decide any condition, and it does not rate your health. It only shows where your own "
                "readings moved away from your usual pattern, with the evidence." + CLOSE)
    if re.search(r"baseline|90|usual|normal|compare", q):
        return (f"Your baseline is your own average over a {WINDOW_DAYS}-day stretch. We compare your first and last {WINDOW_DAYS} days, "
                f"and your latest {RECENT_DAYS} days against the {WINDOW_DAYS} days before them, so you are compared with yourself, "
                "not with other people." + CLOSE)
    if re.search(r"data|enough|missing|sure|reliab|trust", q):
        if not items:
            return "There was nothing to flag, so there is no finding to qualify." + CLOSE
        flags = ", ".join(sorted({i.flag for i in items}))
        return (f"The data flag for your findings{where} is: {flags}. It says how many days of readings were available, "
                "not how sure the tool is. Limited means some days were missing, so the finding could be less reliable." + CLOSE)
    if re.search(r"project|forecast|future|next (week|month)|weeks", q):
        k = next((i for i in items if i.forecast_key), None)
        if not k:
            return "There was not enough weekly data to draw a projection here." + CLOSE
        return ("The dashed line carries your recent trend forward 8 weeks in a straight line, with a shaded 95% range. "
                "It shows what could happen if nothing changes. It is not a prediction." + CLOSE)
    if re.search(r"should i|what (do|can) i|next step|advice|treat|medic", q):
        return ("This tool cannot advise on treatment. A sensible next step is to bring these findings and the evidence to "
                "a healthcare provider, who can look at them alongside your full history." + CLOSE)
    if re.search(r"why|flag|found|changed|what happened|show", q):
        if not items:
            return ("Nothing moved beyond your own usual range" + where + ", so nothing was flagged. "
                    "Small day-to-day changes are not reported." + CLOSE)
        i = items[0]
        pts = "; ".join(i.bullets[:3])
        return (f"{i.title}. {pts}. These readings moved further from your own usual pattern than normal day-to-day variation." + CLOSE)
    return ("I can explain why something was flagged, what the baseline is, how much data stands behind it, "
            "and what the projection shows. Try one of the suggested questions." + CLOSE)


def answer(question: str, insights, area: str | None = None, use_model: bool = True):
    base = answer_template(question, insights, area)
    assert not check_language(base), check_language(base)
    if not use_model or not llm.available():
        return base, "template"
    facts = [llm.facts(i) for i in _area(insights, area)[:3]]
    prompt = f"Question from the patient: {question}\nFacts:\n{json.dumps(facts, indent=2)}\nDraft answer:\n{base}"
    try:
        text = llm._generate(prompt, llm.DEFAULT_MODEL, llm.OLLAMA_URL, 90)
    except Exception:
        return base, "template"
    if not text or check_language(text):
        return base, "template"
    return text, "local model"
