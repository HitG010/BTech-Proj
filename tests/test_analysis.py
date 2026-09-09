from reasoning_budget.analysis import _near_miss, reasoning_claim


def test_reasoning_claim_takes_the_latest_box_or_labelled_number():
    assert reasoning_claim("so 12 apples. **Final Answer** \\boxed{42}") == "42"
    assert reasoning_claim("So the answer should be 54. Wait, no, the answer is 55") == "55"
    assert reasoning_claim("the answer is 3 dollars. Actually \\boxed{4} then answer is 5") == "5"
    assert reasoning_claim("the answer is 5, but \\boxed{4.25}") == "17/4"
    assert reasoning_claim("Therefore, the answer is 360,000 dollars.") == "360000"
    assert reasoning_claim("the answer is approximately right") is None
    assert reasoning_claim("no answer stated here") is None


def test_near_miss_flags_rounding_and_small_relative_error_only():
    assert _near_miss("13733/100", "138")
    assert _near_miss("1990", "2000")
    assert not _near_miss("30000", "360000")
    assert not _near_miss("138", "138")
    assert not _near_miss(None, "138")
