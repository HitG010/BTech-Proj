"""Conservative exact numeric scoring, independent of the gold answer."""

import re
from fractions import Fraction

from .records import ScoredResult

SCORING_VERSION = "numeric-v5"
NUMBER = r"[+−-]?(?:(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?(?:\s*/\s*[+-]?\d+(?:\.\d+)?)?"
TOKEN = re.compile(r"(?<![\w.])" + NUMBER + r"(?![\w.])")
WRAPPER = re.compile(r"\\(?:textbf|textit|textrm|text|mathrm|mathbf|operatorname)\s*\{([^{}]*)\}")
SPACING = re.compile(r"\\(?:qquad|quad|[,;!: ])|~")
UNIT_REMAINDER = re.compile(r"[A-Za-z\s.,/()'°-]*")
# Deliberately finite: arbitrary prose around a numeral can negate it or offer
# an alternative in words. Unsupported unit phrases remain parse failures.
UNIT_WORDS = frozenset(
    "dollar dollars cent cents euro euros pound pounds rupee rupees yen "
    "mm cm m km inch inches foot feet yard yards mile miles "
    "millimeter millimeters centimeter centimeters meter meters "
    "kilometer kilometers g kg gram grams kilogram kilograms ounce ounces "
    "ton tons lb lbs ml l liter liters litre litres gallon gallons "
    "second seconds minute minutes hour hours day days week weeks month months "
    "year years s h degree degrees celsius fahrenheit percent percentage "
    "apple apples item items unit units person persons people student students "
    "book books dollar dollars coin coins ticket tickets box boxes bag bags "
    "ball balls marble marbles piece pieces cookie cookies egg eggs chicken chickens "
    "square cubic per remain remaining left total each".split()
)


def unit_suffix(text):
    """Accept a small numeric-unit vocabulary, never arbitrary answer prose."""
    if not UNIT_REMAINDER.fullmatch(text):
        return False
    words = re.findall(r"[A-Za-z]+", text.lower())
    connectors = {"square", "cubic", "per", "remain", "remaining", "left", "total", "each"}
    return bool(words) and all(w in UNIT_WORDS for w in words) and any(
        w not in connectors for w in words
    )


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


def clean_claim(text):
    """Unwrap formatting without erasing words, numbers, or alternatives."""
    for marker in (r"\$", "$", r"\%", "%"):
        text = text.replace(marker, " ")
    text = SPACING.sub(" ", text)

    return (
        WRAPPER.sub(lambda match: " " + match.group(1).strip() + " ", text)
        .strip()
        .rstrip(".")
        .strip()
        .strip("*")
        .strip()
    )


def claim_value(claim):
    """Parse one explicit numeric claim, optionally followed by a plain unit."""
    cleaned = clean_claim(claim.strip().strip("*:").strip())
    try:
        return numeric(cleaned)
    except ValueError:
        pass
    cleaned = re.sub(
        r"\\(?:dfrac|tfrac|frac)\s*\{([^{}]+)\}\s*\{([^{}]+)\}", r"\1/\2", cleaned
    )
    match = re.fullmatch(
        rf"([+-]?\d*\.\d*\\overline\{{\d+\}}|{NUMBER})(.+)", cleaned
    )
    if match and unit_suffix(match.group(2)):
        return numeric(match.group(1))
    raise ValueError(f"Not a numeric claim: {claim!r}")


def claim_tokens(claim):
    """Count numeric claims without counting fraction/repeating syntax twice."""
    cleaned = clean_claim(claim)
    cleaned = re.sub(
        r"(?<![\w.])([+-]?\d*)\.(\d*)\\overline\{(\d+)\}",
        lambda match: match.group(1) + "." + match.group(2) + match.group(3),
        cleaned,
    )
    cleaned = re.sub(
        r"\\(?:dfrac|tfrac|frac)\s*\{([^{}]+)\}\s*\{([^{}]+)\}",
        r"\1/\2",
        cleaned,
    )
    cleaned = re.sub(r"\\overline\{\d+\}", "", cleaned)
    return TOKEN.findall(cleaned)


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
    claims = []
    # GSM8K's #### delimiter must introduce a numerical claim. Markdown
    # headings such as "#### Billy:" are not missing/conflicting answers.
    # Keep the lexical answer matcher independent so "#### Final answer: 3"
    # is still checked against every box, rather than swallowed as a heading.
    hash_marker = (
        r"(?<!#)####(?!#)(?=[ \t]*(?:\\\$|[$+−\d.-]|"
        r"\\(?:boxed|frac|dfrac|tfrac|textbf|textit|textrm|text|mathrm|mathbf|operatorname)\b))"
    )
    pattern = rf"(?:{hash_marker}|(?:final\s+)?answer\s*(?:is|:|=))\s*([^\n]+)"
    for match in re.finditer(pattern, text, re.I):
        segment = match.group(1)
        head = re.sub(r"^(?:\s|\$|\\\$|\*|~|:|\\\(|\\\[|[(\[{])+", "", segment)
        if not (
            head.startswith(r"\boxed")
            or re.match(NUMBER, head)
            or re.match(r"\\[dt]?frac", head)
            or re.match(r"\\(?:textbf|textit|textrm|text|mathrm|mathbf|operatorname)\b", head)
        ):
            # Labels followed by ordinary prose are not explicit numeric claims.
            continue
        segment_boxes, _ = _boxes(segment)
        if segment_boxes:
            # Remove balanced boxes before looking for a second explicit claim.
            # "Final answer: 3, or \\boxed{4}" must not silently choose 4.
            for content in segment_boxes:
                segment = re.sub(r"\\boxed\s*\{" + re.escape(content) + r"\}", "", segment)
            # Keep each numeric alternative as a claim: the boxes are parsed
            # separately below and must agree with this unboxed numeral.
            segment = re.sub(r"[,;\s]*(?:or|and)\s*$", "", segment, flags=re.I)
        tokens = claim_tokens(segment.rstrip("."))
        if not tokens and segment_boxes:
            continue
        if not tokens and boxed and not re.search(r"[A-Za-z0-9]", segment):
            # A multiline display delimiter after "Final answer:" is not a
            # second empty claim; the balanced box below supplies the answer.
            continue
        if len(tokens) > 1:
            return None, "ambiguous" if tokens else "missing"
        if not tokens:
            return None, "missing"
        try:
            claims.append(claim_value(segment.rstrip(".")))
        except ValueError:
            return None, "invalid_number"
    for claim in boxed:
        try:
            claims.append(claim_value(claim))
        except ValueError:
            return None, "invalid_number"
    if claims:
        if len(set(claims)) != 1:
            return None, "conflicting"
        return str(claims[0]), "ok"
    last_line = text.splitlines()[-1].strip().rstrip(".")
    if re.match(r"^#{1,6}(?:[ \t]|$)", last_line):
        return None, "missing"
    tokens = claim_tokens(last_line)
    if len(tokens) > 1:
        return None, "ambiguous"
    if not tokens:
        return None, "missing"
    try:
        return str(claim_value(last_line)), "ok"
    except ValueError:
        return None, "invalid_number"


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
