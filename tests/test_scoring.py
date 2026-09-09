import pytest

from reasoning_budget.scoring import numeric, parse_answer, score_record


@pytest.mark.parametrize(
    "text, expected",
    [
        ("42", "42"),
        ("Final answer: -4", "-4"),
        ("#### 1,234", "1234"),
        ("The answer is 4.25.", "17/4"),
        (r"\boxed{\frac{3}{4}}", "3/4"),
        (r"\boxed{-2.50}", "-5/2"),
        ("Final answer: -3/2", "-3/2"),
        ("Compute 3 + 4 = 7.\n7 apples remain.", "7"),
        (".75", "3/4"),
        (r"\boxed{0.75} Final answer: 3/4", "3/4"),
        ("1e3", "1000"),
    ],
)
def test_numeric_answers(text, expected):
    assert parse_answer(text) == (expected, "ok")


@pytest.mark.parametrize(
    "text,status",
    [
        (r"\boxed{3} and \boxed{4}", "conflicting"),
        ("Final answer: 3\nFinal answer: 4", "conflicting"),
        ("Final answer: 3 or 4", "ambiguous"),
        ("I cannot solve this.", "missing"),
        (r"\boxed{3", "incomplete"),
        ("", "missing"),
        ("<think>42</think>", "reasoning_in_answer"),
        (r"\boxed{1/0}", "invalid_number"),
    ],
)
def test_failures(text, status):
    assert parse_answer(text) == (None, status)


def test_truncated_answer_never_accepted():
    assert parse_answer("Final answer: 42", incomplete=True) == (None, "incomplete")


def test_gold_cannot_select_conflicting_answer():
    record = {
        "job": {"id": "j", "question_id": "q", "mode": "thinking"},
        "status": "completed",
        "result": {
            "reasoning": "42",
            "final_answer": r"\boxed{3} \boxed{4}",
            "answer_truncated": False,
            "termination": "eos",
        },
    }
    for gold in ["3", "4", "42"]:
        assert score_record(record, gold)["parser_status"] == "conflicting"
        assert not score_record(record, gold)["correct"]
    record["result"]["final_answer"] = ""
    assert not score_record(record, "42")["correct"]


def test_exact_decimal_fraction():
    assert numeric("0.1") == numeric("1/10")


def test_invalid_unboxed_fraction_is_a_parse_failure():
    assert parse_answer("1/0") == (None, "invalid_number")


def test_conflicting_inline_box_and_final_claim():
    assert parse_answer(r"Final answer: 3, or \boxed{4}") == (None, "conflicting")


def test_multiline_display_box_after_final_answer_label():
    assert parse_answer("### Final Answer:\n$$\n\\boxed{54}\n$$") == ("54", "ok")
    assert parse_answer("Final answer:\n\\[\n\\boxed{12}\n\\]") == ("12", "ok")


@pytest.mark.parametrize(
    "text, expected",
    [
        (r"\boxed{\$18}", "18"),
        (r"\boxed{18\%}", "18"),
        (r"\boxed{18 \text{ hours}}", "18"),
        (r"\boxed{\text{18}}", "18"),
        (r"\boxed{\$1,800}", "1800"),
        (r"\boxed{~18}", "18"),
        (r"\boxed{18 \, \text{dollars}}", "18"),
        (r"\boxed{18\text{ cm}}", "18"),
        (r"\boxed{18.}", "18"),
        (r"\boxed{18 km/h}", "18"),
        (r"\boxed{\dfrac{3}{4}}", "3/4"),
        (r"\boxed{\textbf{-4}}", "-4"),
        (r"\boxed{18} and \boxed{18 \text{ hours}}", "18"),
    ],
)
def test_latex_decoration_is_ignored_numeric_v3(text, expected):
    assert parse_answer(text) == (expected, "ok")


@pytest.mark.parametrize(
    "text",
    [
        r"\boxed{2:30}",
        r"\boxed{18 \div 2 = 9}",
        r"\boxed{x = 18}",
        r"\boxed{137.\overline{3}}",
        r"\boxed{18 \text{ or } 19}",
    ],
)
def test_decorated_claims_stay_conservative(text):
    assert parse_answer(text) == (None, "invalid_number")
