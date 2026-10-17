"""Optional local-LLM rewrite of an insight summary (Ollama). Wording only; detection stays statistical.

Safe by design: only computed facts are sent, nothing leaves the machine, every reply must pass
check_language, and any failure falls back to the template text.
"""
import json
import urllib.request

from .explain import check_language

OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "llama3.1:8b"

SYSTEM = (
    "You rewrite a health-pattern summary for a patient in plain, calm language. Use ONLY the facts given. "
    "Do not diagnose, name a condition, give treatment or medication advice, or add numbers that are not given. "
    "Use cautious words such as 'may' or 'could'. End by saying it may be worth discussing with a healthcare provider. "
    "Maximum 3 sentences."
)


def facts(insight) -> dict:
    return {"title": insight.title, "summary": insight.summary, "points": insight.bullets,
            "linked_history": [c.split(" — ")[0] for c in insight.context[:3]],
            "data_flag": insight.flag}


def available(model: str = DEFAULT_MODEL, url: str = OLLAMA_URL) -> bool:
    """True if the Ollama server is running and the model has been pulled."""
    try:
        with urllib.request.urlopen(f"{url}/api/tags", timeout=2) as r:
            names = [m["name"] for m in json.load(r).get("models", [])]
        return any(n == model or n.startswith(model.split(":")[0] + ":") and model in n for n in names)
    except Exception:
        return False


def _generate(prompt: str, model: str, url: str, timeout: int) -> str:
    body = json.dumps({"model": model, "system": SYSTEM, "prompt": prompt, "stream": False,
                       "options": {"temperature": 0.2}}).encode()
    req = urllib.request.Request(f"{url}/api/generate", body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)["response"].strip()


def explain(insight, model: str = DEFAULT_MODEL, url: str = OLLAMA_URL, timeout: int = 90, generate=_generate):
    """Return (text, source). source is 'local model' or 'template' (fallback)."""
    fallback = insight.summary or insight.narrative
    try:
        text = generate("Facts:\n" + json.dumps(facts(insight), indent=2), model, url, timeout)
    except Exception:
        return fallback, "template"
    if not text or check_language(text):
        return fallback, "template"
    return text, "local model"
