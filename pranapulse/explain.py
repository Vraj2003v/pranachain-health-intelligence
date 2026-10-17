"""Plain-language wording plus the guardrail checker every sentence must pass before it is shown."""
import re

BANNED = [
    (r"\bdiagnos", "names or implies a diagnosis"),
    (r"\byou (have|are experiencing|are suffering)\b", "states a condition as fact"),
    (r"\bthis means\b", "unqualified certainty"),
    (r"\b(stop|start|increase|reduce) (taking|your)\b", "gives a medical instruction"),
    (r"\bemergency\b|\bgo to the (er|hospital)\b|\burgent(ly)?\b", "alarming or emergency wording"),
    (r"\bdangerous\b|\bserious(ly)?\b|\bcritical\b", "alarming wording"),
    (r"\bconfidence\b|\bprobability\b|\brisk score\b", "numeric confidence or risk score"),
]
REQUIRED = [(r"\bmay\b|\bcould\b", "must use cautious wording"),
            (r"\bprovider\b", "must point to a healthcare provider")]


def check_language(text: str):
    """Return a list of problems; an empty list means the text may be shown."""
    low = text.lower()
    problems = [why for pat, why in BANNED if re.search(pat, low)]
    problems += [why for pat, why in REQUIRED if not re.search(pat, low)]
    return problems
