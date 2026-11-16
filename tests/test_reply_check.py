"""The assistant uses a model reply only if every number and every finding/evidence ID in it comes from the patient's own findings."""
from pranapulse import ask

ALLOWED = '{"findings":[{"id":"F1","evidence":["E1","E2"]}],"readings":[{"last_90_days_avg":112.4}]} Your average is 112.4.'


def test_reply_with_an_invented_number_is_rejected():
    assert not ask.reply_ok("Your average is 131.9 in the last 90 days.", ALLOWED)


def test_reply_with_an_unknown_evidence_id_is_rejected():
    assert not ask.reply_ok("See F1 and E7 for the reading of 112.4.", ALLOWED)
    assert not ask.reply_ok("See F4 for the reading of 112.4.", ALLOWED)


def test_valid_reply_is_accepted():
    assert ask.reply_ok("Your average is 112.4 (see F1, E2). It may be worth discussing with a healthcare provider.", ALLOWED)


GOOD = "Your average is 112.4, which may be worth discussing with a healthcare provider."


def _patch_model(monkeypatch, replies):
    calls = iter(replies)
    monkeypatch.setattr(ask.llm, "_generate", lambda *a, **k: next(calls))


def test_bad_first_reply_is_retried_once_and_good_second_reply_is_used(monkeypatch):
    _patch_model(monkeypatch, ["Your average is 999.", GOOD])
    assert ask._ai("what is my average", "Your average is 112.4.", [], {}, [], None) == GOOD


def test_two_bad_replies_fall_back_to_the_template_answer(monkeypatch):
    _patch_model(monkeypatch, ["Your average is 999.", "See E9."])
    assert ask._ai("what is my average", "Your average is 112.4.", [], {}, [], None) is None
    monkeypatch.setattr(ask.llm, "available", lambda: True)
    _patch_model(monkeypatch, ["Your average is 999.", "See E9."])
    text, source, *_ = ask.answer("what is my average", [], None, use_model=True)
    assert source == "template"
