from pranapulse.ask import clean_reply

def test_clean_reply_strips_lead_ins():
    assert clean_reply("Here is the revised answer: Your average is 112.") == "Your average is 112."
    assert clean_reply("Patient question: What is my average?\nYour average is 112.") == "Your average is 112."
    assert clean_reply("Here is the revised answer:\nPatient question: x\nYour average is 112.") == "Your average is 112."