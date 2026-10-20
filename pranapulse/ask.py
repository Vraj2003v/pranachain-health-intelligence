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


MEASURES = {
    "weight": r"weight|kilos?|\bkg\b",
    "sbp": r"systolic|blood pressure|\bbp\b|pressure",
    "dbp": r"diastolic",
    "rhr": r"heart rate|resting hr|pulse|\brhr\b",
    "steps": r"steps?|walking|activity",
    "sleep": r"sleep",
    "hrv": r"\bhrv\b|variability",
}
AREA_OF = {"weight": "Metabolic health", "steps": "Metabolic health", "sleep": "Metabolic health",
           "sbp": "Cardiovascular / hypertension", "dbp": "Cardiovascular / hypertension",
           "rhr": "Cardiovascular / hypertension", "hrv": "Cardiovascular / hypertension"}

FOLLOW = {
    "measure": ["Compare it with another measure", "How much data is behind this?", "What does the projection show?"],
    "compare": ["What changed the most?", "What does the baseline mean?"],
    "most": ["Why was this flagged?", "What does the projection show?"],
    "default": SUGGESTED[:3],
}


def _mentioned(q):
    return [k for k, pat in MEASURES.items() if re.search(pat, q)]


def _move(r):
    pct = (r.diff / r.mean_first * 100) if r.mean_first else 0
    way = "up" if r.diff > 0 else "down"
    return way, abs(r.diff), pct


def _line(r):
    way, amt, pct = _move(r)
    d = r.decimals
    return (f"{r.label} averaged {r.mean_first:,.{d}f} {r.unit} in your first {WINDOW_DAYS} days and {r.mean_last:,.{d}f} {r.unit} "
            f"in your last {WINDOW_DAYS} days ({way} {amt:,.{d}f}, about {abs(pct):.1f}%)")


def answer_data(question, insights, results, history=()):
    """Answers tied to the actual readings. Returns (text, action, followups) or None if it is not a data question."""
    q = question.lower()
    keys = [k for k in _mentioned(q) if k in results]
    last = next((h.get("key") for h in reversed(list(history)) if h.get("key")), None)
    if not keys and last and last in results and re.search(r"\b(it|that|this|more|same)\b", q):
        keys = [last]
    if re.search(r"most|biggest|largest|top|main", q) and re.search(r"chang|move|differ|shift", q):
        ranked = sorted((r for r in results.values() if r.flag != "Insufficient"), key=lambda r: abs(r.effect), reverse=True)[:3]
        if not ranked:
            return ("There was not enough data to rank changes." + CLOSE, None, FOLLOW["default"], None)
        lines = "; ".join(f"{r.label} ({_move(r)[0]} {abs(_move(r)[2]):.1f}%, {abs(r.effect):.1f} times your usual day-to-day variation)" for r in ranked)
        return (f"Measured against your own day-to-day variation, the largest shifts were: {lines}. A larger number means the change "
                "stood out more from your normal ups and downs." + CLOSE,
                {"tab": "timeline", "key": ranked[0].key, "label": f"Open {ranked[0].label} trend"}, FOLLOW["most"], ranked[0].key)
    if len(keys) >= 2 and re.search(r"compar|vs|versus|against|and|with", q):
        a, b = keys[:2]
        return (f"{_line(results[a])}. {_line(results[b])}. Percentages put them on one scale so you can compare them." + CLOSE,
                {"tab": "explore", "keys": [a, b], "label": f"Compare {results[a].label} and {results[b].label}"}, FOLLOW["compare"], a)
    if keys:
        k = keys[0]
        r = results[k]
        flagged = any(k in i.signals for i in insights)
        extra = (" This measure is part of a flagged finding." if flagged else " It stayed within your usual range, so nothing was flagged for it.")
        return (_line(r) + "." + extra + CLOSE,
                {"tab": "timeline", "key": k, "label": f"Open {r.label} trend"}, FOLLOW["measure"], k)
    if re.search(r"how many days|how long|how much data|readings", q) and re.search(r"how many days|how long", q):
        return None
    return None


def answer(question: str, insights, area: str | None = None, use_model: bool = True, results=None, history=()):
    """Returns (text, source, action, followups, key)."""
    if results:
        hit = answer_data(question, insights, results, history)
        if hit:
            text, action, follow, key = hit
            assert not check_language(text), check_language(text)
            return text, "template", action, follow, key
    text, source = _answer_text(question, insights, area, use_model, history)
    return text, source, None, FOLLOW["default"], None


def _answer_text(question: str, insights, area: str | None = None, use_model: bool = True, history=()):
    base = answer_template(question, insights, area)
    assert not check_language(base), check_language(base)
    if not use_model or not llm.available():
        return base, "template"
    facts = [llm.facts(i) for i in _area(insights, area)[:3]]
    talk = "\n".join(f"{h.get('who')}: {h.get('text')}" for h in list(history)[-6:])
    prompt = f"Conversation so far:\n{talk}\nQuestion from the patient: {question}\nFacts:\n{json.dumps(facts, indent=2)}\nDraft answer:\n{base}"
    try:
        text = llm._generate(prompt, llm.DEFAULT_MODEL, llm.OLLAMA_URL, 90)
    except Exception:
        return base, "template"
    if not text or check_language(text):
        return base, "template"
    return text, "local model"
