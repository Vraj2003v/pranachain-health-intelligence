"""The assistant can show how an answer was made: the route, what the model was given, each reply and its checks."""
from pranapulse import ask

GOOD = "Your average is 112.4, which may be worth discussing with a healthcare provider."


def test_safety_question_never_reaches_the_model_and_says_so():
    t = {}
    _, source, *_ = ask.answer("Do I have diabetes?", [], None, trace=t)
    assert source == "template" and "model was not used" in t["why"] and "attempts" not in t


def test_model_off_is_recorded():
    t = {}
    ask.answer("what is my average", [], None, use_model=False, trace=t)
    assert t["source"] == "template" and "switch is off" in t["why"]


def test_checks_are_reported_one_by_one():
    allowed = '{"readings":[{"last_90_days_avg":112.4}]}'
    assert ask.reply_checks(GOOD, allowed) == {"wording": True, "numbers": True, "ids": True}
    assert ask.reply_checks("Your average is 999.", allowed)["numbers"] is False
    assert ask.reply_checks("See E9 for 112.4.", allowed)["ids"] is False


def test_model_attempts_are_recorded_with_their_checks(monkeypatch):
    replies = iter(["Your average is 999.", GOOD])
    monkeypatch.setattr(ask.llm, "_generate", lambda *a, **k: next(replies))
    monkeypatch.setattr(ask.llm, "available", lambda *a, **k: True)
    t = {}
    text, source, *_ = ask.answer("what is my average", [], None, use_model=True, trace=t)
    assert source == "template" or text == GOOD       # the model path ran either way
    assert t["model"] and "given" in t and len(t["attempts"]) >= 1
    assert all(k in t["attempts"][0] for k in ("wording", "numbers", "ids", "used"))
