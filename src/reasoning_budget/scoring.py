"""Conservative exact numeric scoring, independent of the gold answer."""

import re
from fractions import Fraction

from .records import ScoredResult

SCORING_VERSION = "numeric-v4"
NUMBER = r"[+−-]?(?:(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?(?:\s*/\s*[+-]?\d+(?:\.\d+)?)?"
TOKEN = re.compile(r"(?<![\w.])" + NUMBER + r"(?![\w.])")


def numeric(text):
    text = text.strip().replace("−", "-").replace(",", "")
    text = re.sub(r"\\(?:dfrac|tfrac|frac)\s*\{([^{}]+)\}\s*\{([^{}]+)\}", r"\1/\2", text)
    text = text.strip(" $\t\n")
    repeating = re.fullmatch(r"([+-]?)(\d*)\.(\d*)\\overline\{(\d+)\}", text)
    if repeating:
        sign, whole, prefix, cycle = repeating.groups()
        scale = 10 ** len(prefix)
        value = (
            Fraction(int(whole or "0"))
            + Fraction(int(prefix or "0"), scale)
            + Fraction(int(cycle), scale * (10 ** len(cycle) - 1))
        )
        return -value if sign == "-" else value
    if not re.fullmatch(NUMBER, text):
        raise ValueError(f"Not a numeric answer: {text!r}")
    try:
        if "/" in text:
            numerator, denominator = text.split("/")
            return Fraction(numerator.strip()) / Fraction(denominator.strip())
        return Fraction(text)
    except (ValueError, ZeroDivisionError, OverflowError) as exc:
        raise ValueError(f"Invalid numeric answer: {text!r}") from exc


def _boxes(text):
    values = []
    for match in re.finditer(r"\\boxed\s*\{", text):
        start, depth, end = match.end(), 1, match.end()
        while end < len(text) and depth:
            depth += (text[end] == "{") - (text[end] == "}")
            end += 1
        if depth:
            return [], True
        values.append(text[start : end - 1])
    return values, False


def parse_answer(final_answer, *, incomplete=False):
    """Return (canonical rational, status); never receives a gold label.

    Explicit boxed / final-answer / #### claims must agree. Otherwise accept a
    standalone number or the sole numeric literal on the last nonempty line.
    Truncated output is conservatively unscorable, even if a number is present.
    """
    if incomplete:
        return None, "incomplete"
    text = final_answer.strip()
    if "<think>" in text:
        # A malformed or unseparated reasoning span must never supply an answer.
        return None, "reasoning_in_answer"
    if "</think>" in text:
        return None, "reasoning_in_answer"
    if not text:
        return None, "missing"
    boxed, unclosed = _boxes(text)
    if unclosed:
        return None, "incomplete"
    claims = list(boxed)
    # GSM8K's #### delimiter must introduce a numerical claim. Markdown
    # headings such as "#### Billy:" are not missing/conflicting answers.
    # Keep the lexical answer matcher independent so "#### Final answer: 3"
    # is still checked against every box, rather than swallowed as a heading.
    hash_marker = r"(?<!#)####(?!#)(?=[ \t]*(?:[+$−\d.-]|\\(?:boxed|frac|dfrac|tfrac)\b))"
    pattern = rf"(?:{hash_marker}|(?:final\s+)?answer\s*(?:is|:|=))\s*([^\n]+)"
    for match in re.finditer(pattern, text, re.I):
        segment = match.group(1)
        segment_boxes, _ = _boxes(segment)
        if segment_boxes:
            # Remove balanced boxes before looking for a second explicit claim.
            # "Final answer: 3, or \\boxed{4}" must not silently choose 4.
            for content in segment_boxes:
                segment = re.sub(r"\\boxed\s*\{" + re.escape(content) + r"\}", "", segment)
        try:
            tokens = [str(numeric(segment.rstrip(".")))]
        except ValueError:
            tokens = TOKEN.findall(segment.rstrip("."))
        if not tokens and segment_boxes:
            continue
        if not tokens and boxed and not re.search(r"[A-Za-z0-9]", segment):
            # A multiline display delimiter after "Final answer:" is not a
            # second empty claim; the balanced box below supplies the answer.
            continue
        if len(tokens) != 1:
            return None, "ambiguous" if tokens else "missing"
        claims.append(tokens[0])
    if claims:
        try:
            values = {numeric(claim) for claim in claims}
        except ValueError:
            return None, "invalid_number"
        if len(values) != 1:
            return None, "conflicting"
        return str(values.pop()), "ok"
    last_line = text.splitlines()[-1].strip().rstrip(".")
    if re.match(r"^#{1,6}(?:[ \t]|$)", last_line):
        return None, "missing"
    try:
        return str(numeric(last_line)), "ok"
    except ValueError:
        tokens = TOKEN.findall(last_line)
        if len(tokens) == 1:
            try:
                return str(numeric(tokens[0])), "ok"
            except ValueError:
                return None, "invalid_number"
        return None, "ambiguous" if tokens else "missing"


def score_record(record, gold):
    job, result = record["job"], record.get("result")
    if record["status"] != "completed" or result is None:
        answer, status = None, "generation_failure"
    else:
        answer, status = parse_answer(
            result["final_answer"],
            incomplete=result["answer_truncated"]
            or result["termination"] in {"timeout", "early_eos", "reasoning_in_answer"},
        )
    return ScoredResult(
        job["id"],
        job["question_id"],
        job["mode"],
        answer,
        status == "ok" and numeric(answer) == numeric(gold),
        status,
        SCORING_VERSION,
    ).to_dict()
