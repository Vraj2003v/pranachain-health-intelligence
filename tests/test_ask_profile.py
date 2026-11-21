"""The assistant answers questions about the patient's own record (sex, age) from the record, never from a guess."""
from pranapulse.ask import answer, answer_profile


def test_sex_and_age_come_from_the_record():
    p = {"sex": "Female", "age": 42.0}
    assert answer_profile("Is this male or female", p) == "This record lists the patient as female."
    assert answer_profile("how old is the patient?", p) == "The record lists the patient's age as 42."
    both = answer_profile("what is their age and gender", p)
    assert "female" in both and "42" in both


def test_missing_values_say_so():
    assert answer_profile("is this patient male or female", {"sex": None, "age": None}) == "Sex is not recorded for this patient."
    assert answer_profile("age?", {"sex": "Male", "age": float("nan")}) == "Age is not recorded for this patient."


def test_other_questions_are_not_taken_over():
    assert answer_profile("Why was this flagged?", {"sex": "Female", "age": 42}) is None
    assert answer_profile("average weight", {"sex": "Female", "age": 42}) is None   # 'weight' must not match 'age'


def test_answer_uses_the_record_before_any_model():
    text, source, *_ = answer("Is this male or female", [], "Women's health (PCOS)", use_model=True, profile={"sex": "Female", "age": 42})
    assert source == "patient record" and "female" in text


def test_unknown_question_says_it_does_not_have_it():
    text, source, *_ = answer("what is the capital of France", [], None, use_model=False)
    assert "I don't have that information" in text and source == "template"
