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
    "text,expected",
    [
        (r"\boxed{137.\overline{3}}", "412/3"),
        (r"Final answer: 0.1\overline{6}", "1/6"),
        (r"-1.2\overline{34}", "-611/495"),
        (r"\boxed{0.\overline{9}}", "1"),
    ],
)
def test_repeating_decimals(text, expected):
    assert parse_answer(text) == (expected, "ok")


def test_repeating_decimal_does_not_round_to_gold():
    assert parse_answer(r"\boxed{137.\overline{3}} \boxed{138}") == (None, "conflicting")


@pytest.mark.parametrize(
    "heading", ["#### Billy:", "#### **Tiffany's total**:", "#### Saturday (day 7)"]
)
def test_markdown_headings_do_not_override_a_box(heading):
    assert parse_answer(heading + "\nCalculation.\nFinal answer:\n$$\n\\boxed{1}\n$$") == (
        "1",
        "ok",
    )
    assert parse_answer(heading) == (None, "missing")


def test_hash_answer_claims_still_conflict_without_using_gold():
    assert parse_answer("#### 3\n\\boxed{4}") == (None, "conflicting")
    assert parse_answer("#### Final answer: 3\n\\boxed{4}") == (None, "conflicting")
    assert parse_answer("#### -3/2\n\\boxed{-1.5}") == ("-3/2", "ok")
    assert parse_answer("#### 3 or 4") == (None, "ambiguous")
    assert parse_answer("#### Billy:\n\\boxed{1}", incomplete=True) == (None, "incomplete")


@pytest.mark.parametrize(
    "text, expected",
    [
        (r"\boxed{\$18}", "18"),
        (r"\boxed{18\%}", "18"),
        (r"\boxed{18 \text{ hours}}", "18"),
        (r"\boxed{\text{18}}", "18"),
        (r"\boxed{\text{18 dollars}}", "18"),
        (r"Final answer: \text{18 dollars}", "18"),
        (r"\boxed{\text{18 cm}}", "18"),
        (r"\boxed{18 miles per hour}", "18"),
        (r"\boxed{\$1,800}", "1800"),
        (r"\boxed{~18}", "18"),
        (r"\boxed{18 \, \text{dollars}}", "18"),
        (r"\boxed{18\text{ cm}}", "18"),
        (r"\boxed{18.}", "18"),
        (r"\boxed{18 km/h}", "18"),
        (r"\boxed{\dfrac{3}{4}}", "3/4"),
        (r"\boxed{\textbf{-4}}", "-4"),
        (r"\boxed{18} and \boxed{18 \text{ hours}}", "18"),
        (r"\boxed{\$0.1\overline{6} \text{ dollars}}", "1/6"),
        (r"Final answer: \$0.1\overline{6} dollars", "1/6"),
        (r"#### 137.\overline{3} \text{ cm}", "412/3"),
    ],
)
def test_decorated_numeric_claims(text, expected):
    assert parse_answer(text) == (expected, "ok")


@pytest.mark.parametrize(
    "text",
    [
        r"\boxed{2:30}",
        r"\boxed{18 \div 2 = 9}",
        r"\boxed{x = 18}",
        r"\boxed{18 \text{ or } 19}",
        r"\boxed{7 \text{or 8}}",
        r"\boxed{7 \text{x = 8}}",
        r"\boxed{not 7}",
        r"\boxed{7 is wrong}",
        r"\boxed{7 or eight}",
        r"\boxed{7 \text{hours} or \text{eight hours}}",
        r"\boxed{7 \text{not hours}}",
        r"\boxed{7 \text{or} \text{eight}}",
        r"\boxed{\text{not 7}}",
        r"\boxed{7 plus eight}",
        r"\boxed{7 was incorrect}",
    ],
)
def test_decorated_claims_stay_conservative(text):
    assert parse_answer(text) == (None, "invalid_number")


@pytest.mark.parametrize(
    "text", ["Final answer: 7 or eight", "Final answer: 7 is wrong", "7 or eight"]
)
def test_written_alternatives_and_negation_cannot_score_correct(text):
    assert parse_answer(text) == (None, "invalid_number")
    record = {
        "job": {"id": "j", "question_id": "q", "mode": "direct"},
        "status": "completed",
        "result": {"final_answer": text, "answer_truncated": False, "termination": "eos"},
    }
    assert not score_record(record, "7")["correct"]


@pytest.mark.parametrize(
    "text, expected",
    [
        (
            "To ensure the answer is correct, add it back: 54 + 37 = 91.\n\n\\boxed{54}",
            "54",
        ),
        ("The answer is approximately 18.\n\n$$\\boxed{18}$$", "18"),
        ("The answer is: **18**", "18"),
        (r"Final answer: $\boxed{7}$", "7"),
        ("Answer: the calculation is correct.\n\\boxed{54}", "54"),
    ],
)
def test_prose_after_answer_label_is_not_a_claim(text, expected):
    assert parse_answer(text) == (expected, "ok")


def test_decorated_and_plain_claims_must_agree():
    assert parse_answer("Final answer: \\$18 dollars\n\\boxed{\\textbf{18.0}}") == (
        "18",
        "ok",
    )
    assert parse_answer("Final answer: \\$18 dollars\n\\boxed{\\textbf{19}}") == (
        None,
        "conflicting",
    )


def test_multiple_explicit_numbers_remain_ambiguous_with_decorations():
    assert parse_answer(r"Final answer: 18 cm or 19 cm") == (None, "ambiguous")
    assert parse_answer(r"#### 18 \text{ cm} or 19 \text{ cm}") == (None, "ambiguous")
    assert parse_answer(r"Final answer: 7 \text{or 8}") == (None, "ambiguous")


def test_latex_fraction_claim_survives_heading_and_prose_matching():
    assert parse_answer(r"#### Final answer: \dfrac{3}{4}") == ("3/4", "ok")
    assert parse_answer("#### Final answer: \\dfrac{3}{4}\n\\boxed{2/3}") == (
        None,
        "conflicting",
    )
    assert parse_answer("Answer: the answer is correct.\n\\boxed{3/4}") == (
        "3/4",
        "ok",
    )
