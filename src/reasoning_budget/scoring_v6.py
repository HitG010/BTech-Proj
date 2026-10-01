"""Opt-in final-section numeric scoring; frozen numeric-v5 remains unchanged.

Only an explicit line-anchored final-answer header or numeric #### delimiter
can separate earlier unlabelled boxes from the final answer. Every final section
must contain only agreeing numeric claims and display formatting. Labelled
numeric answers before that section still count as claims, never as working.
"""

import argparse
import re
from pathlib import Path

from . import records as record_types
from . import scoring as v5
from .data import load_gold, load_questions
from .runner import load_run
from .storage import atomic_json, digest, read_json, run_lock

SCORING_VERSION = "numeric-v6"
POLICY = {
    "version": SCORING_VERSION,
    "scope": "line-anchored final-answer headers or numeric #### delimiters",
    "prefix": "ignore unlabelled balanced boxes; retain labelled numeric answer claims",
    "final": "every final section must contain only agreeing exact numeric claims and formatting",
    "fallback": "numeric-v5 when no explicit final section exists",
    "reject": "incomplete generation, unclosed boxes, malformed sections, alternatives and conflicts",
    "gold": "extraction never receives gold; final selection never depends on correctness",
}
_FINAL = re.compile(
    r"^[ \t]*(?:#{1,6}[ \t]+)?(?:✅[ \t]*)?(?:\*\*[ \t]*)?"
    r"final[ \t]+answer[ \t]*(?:\*\*)?[ \t]*"
    r"(?:(?::|=|is\b)[ \t]*(?:\*\*)?[ \t]*(?P<body>[^\n]*)|(?P<header>$))",
    re.I | re.M,
)
_FINAL_INTENT = re.compile(
    r"^[ \t]*(?:#{1,6}[ \t]+)?(?:✅[ \t]*)?(?:\*\*[ \t]*)?final[ \t]+answer\b",
    re.I | re.M,
)
_HASH = re.compile(
    r"^[ \t]*####(?!#)[ \t]*(?P<body>"
    r"(?=\\\$|[$+−\d.-]|\\(?:boxed|frac|dfrac|tfrac|textbf|textit|textrm|text|"
    r"mathrm|mathbf|operatorname)\b)[^\n]*)",
    re.M,
)
_LABEL = re.compile(r"\b(?:final[ \t]+)?answer[ \t]*(?:is\b|:|=)[ \t]*([^\n]*)", re.I)
_DISPLAY = re.compile(r"(?<!\\)\$\$|\\\[|\\\]|\\\(|\\\)")
_NUMERIC_HEAD = re.compile(
    r"^(?:[$+−\d.-]|\\(?:\$|boxed|frac|dfrac|tfrac|textbf|textit|textrm|text|"
    r"mathrm|mathbf|operatorname)\b)"
)


def implementation_digest():
    """Include reused numeric helpers and score schema, not only this wrapper."""
    return digest({
        "scoring_v6.py": Path(__file__).read_text(),
        "scoring_v5.py": Path(v5.__file__).read_text(),
        "records.py": Path(record_types.__file__).read_text(),
    })


def _boxes(text):
    """Balanced outer box spans, retaining complete nested LaTeX contents."""
    spans, cursor = [], 0
    while match := re.search(r"\\boxed\s*\{", text[cursor:]):
        start, body = cursor + match.start(), cursor + match.end()
        end, depth = body, 1
        while end < len(text) and depth:
            depth += (text[end] == "{") - (text[end] == "}")
            end += 1
        if depth:
            return [], "incomplete"
        spans.append((start, end, text[body:end - 1]))
        cursor = end
    return spans, None


def _display(text):
    stack, pieces, cursor = [], [], 0
    for match in _DISPLAY.finditer(text):
        token = match.group()
        pieces.extend([text[cursor:match.start()], " "])
        cursor = match.end()
        if token == "$$":
            if stack == ["$$"]:
                stack.pop()
            elif not stack:
                stack.append(token)
            else:
                return None, "invalid_number"
        elif token in {r"\[", r"\("}:
            if stack:
                return None, "invalid_number"
            stack.append(token)
        elif not stack or stack.pop() != {r"\]": r"\[", r"\)": r"\("}[token]:
            return None, "invalid_number"
    if stack:
        return None, "incomplete"
    pieces.append(text[cursor:])
    return "".join(pieces), None


def _line_values(line):
    # Generic labels inside the final section still introduce numeric claims.
    line = re.sub(r"^(?:the[ \t]+)?answer[ \t]*(?:is\b|:|=)[ \t]*", "", line, flags=re.I)
    spans, error = _boxes(line)
    if error:
        return [], error
    values, pieces, cursor = [], [], 0
    for start, end, content in spans:
        try:
            values.append(v5.claim_value(content))
        except ValueError:
            return [], "invalid_number"
        pieces.extend([line[cursor:start], " "])
        cursor = end
    pieces.append(line[cursor:])
    remainder = "".join(pieces)
    if v5.clean_claim(remainder).strip("*:").strip():
        if len(v5.claim_tokens(remainder)) > 1:
            return [], "ambiguous"
        try:
            values.append(v5.claim_value(remainder))
        except ValueError:
            return [], "invalid_number"
    if not values:
        return [], "missing"
    return values, None


def _section_values(section):
    text, error = _display(section)
    if error:
        return [], error
    values, pending, depth = [], [], 0
    for line in text.splitlines():
        line = line.strip()
        if not line or re.fullmatch(r"[-*_]{3,}", line):
            continue
        pending.append(line)
        depth += line.count("{") - line.count("}")
        if depth < 0:
            return [], "invalid_number"
        if depth:
            continue
        claims, error = _line_values(" ".join(pending))
        if error:
            return [], error
        values.extend(claims)
        pending = []
    if pending:
        return [], "incomplete"
    return (values, None) if values else ([], "missing")


def _prefix_values(prefix):
    values = []
    for match in _LABEL.finditer(prefix):
        body = match.group(1).strip()
        # Ordinary prose such as "ensure the answer is correct" is not a claim.
        before = prefix[prefix.rfind("\n", 0, match.start()) + 1:match.start()]
        anchored = not before.strip(" #*✅\t")
        head = body.lstrip(" *$~:")
        if not anchored and not _NUMERIC_HEAD.match(head):
            continue
        if not body:
            # A multiline earlier labelled answer is still a claim. Inspect its
            # first content line; never substitute a later final marker.
            candidates = [line.strip() for line in prefix[match.end():].splitlines()
                          if line.strip() and line.strip() not in {"$$", r"\[", r"\("}]
            if not candidates:
                return [], "missing"
            body = candidates[0]
        body = re.sub(r"\\[\[\]() ]", " ", body)
        body = body.replace("$$", " ")
        claims, error = _line_values(body)
        if error:
            return [], error
        values.extend(claims)
    return values, None


def parse_answer(final_answer, *, incomplete=False):
    """Return (exact rational, status) without accepting or accessing gold."""
    if incomplete or not final_answer.strip() or "<think>" in final_answer or "</think>" in final_answer:
        return v5.parse_answer(final_answer, incomplete=incomplete)
    text = final_answer.strip()
    _, error = _boxes(text)
    if error:
        return None, error
    final_markers = list(_FINAL.finditer(text))
    if any(m.start() not in {f.start() for f in final_markers}
           for m in _FINAL_INTENT.finditer(text)):
        return None, "invalid_number"
    markers = sorted([*final_markers, *_HASH.finditer(text)], key=lambda m: m.start())
    if not markers:
        return v5.parse_answer(text)
    values, error = _prefix_values(text[:markers[0].start()])
    if error:
        return None, error
    for i, marker in enumerate(markers):
        end = markers[i + 1].start() if i + 1 < len(markers) else len(text)
        section = (marker.group("body") or "") + "\n" + text[marker.end():end]
        claims, error = _section_values(section)
        if error:
            return None, error
        values.extend(claims)
    if len(set(values)) != 1:
        return None, "conflicting"
    return str(values[0]), "ok"


def extract_record(record):
    result = record.get("result")
    if record["status"] != "completed" or result is None:
        return None, "generation_failure"
    return parse_answer(result["final_answer"], incomplete=result["answer_truncated"]
                        or result["termination"] in {"timeout", "early_eos", "reasoning_in_answer"})


def score_record(record, gold):
    answer, status = extract_record(record)
    job = record["job"]
    return record_types.ScoredResult(
        job["id"], job["question_id"], job["mode"], answer,
        status == "ok" and v5.numeric(answer) == v5.numeric(gold), status, SCORING_VERSION,
    ).to_dict()


def score_run(run_dir):
    """Opt-in bridge sensitivity scoring or isolated fake-fixture verification.

    Phase 2 must freeze its own endpoint/gold permission before using the pure
    score_record API. This CLI does not grant permission to score real repeats.
    """
    run_dir = Path(run_dir)
    with run_lock(run_dir):
        manifest, rows = load_run(run_dir)
        if not rows or any(row["status"] != "completed" for row in rows):
            raise ValueError("V6 scoring requires the complete run endpoint")
        dataset = Path(manifest["identity"]["config"]["data_dir"])
        data_manifest = read_json(dataset / "manifest.json")
        meta = data_manifest.get("metadata", {})
        if meta.get("upstream") != "train" or meta.get("role") not in {"bridge", "repeat"}:
            raise ValueError("Only isolated bridge/repeat training gold is permitted")
        questions = load_questions(dataset)
        expected = manifest["identity"]["questions"]
        if {q.id: q.to_dict() for q in questions} != {q["id"]: q for q in expected} or any(
            q.split != meta["role"] for q in questions
        ):
            raise ValueError("Dataset includes questions outside this isolated run")
        if manifest["identity"]["config"]["backend"] == "fake":
            if any(not q.source.startswith(("fixture", "arithmetic-v1")) for q in questions):
                raise ValueError("Fake scoring is limited to explicit synthetic fixtures")
        else:
            if meta["role"] != "bridge":
                raise ValueError("Real repeat scoring requires its own frozen Phase 2 study protocol")
            # A completed arm alone must not bypass the paired bridge endpoint.
            from .research_bridge import checked_arm, read_protocol

            study = dataset.parent.parent / "bridge-v1"
            protocol = read_protocol(study)
            if str(run_dir.resolve()) not in {
                a["snapshot"]["run_dir"] for a in protocol["arms"].values()
            } or any(
                len(arm_rows) != len(protocol["arms"][arm]["snapshot"]["jobs"])
                or any(row["status"] != "completed" for row in arm_rows)
                for arm in protocol["arms"]
                for _, arm_rows in [checked_arm(study, protocol, arm)]
            ):
                raise ValueError("Paired bridge endpoint is incomplete or run is not a frozen arm")
        gold = load_gold(dataset)  # No base dataset / official test gold is opened.
        if digest(gold) != manifest["scoring_gold_sha256"] or set(gold) != {q.id for q in questions}:
            raise ValueError("Frozen gold identity differs")
        artifact = {
            "scoring_version": SCORING_VERSION,
            "scoring_implementation_sha256": implementation_digest(), "policy": POLICY,
            "run_id": manifest["run_id"], "records_sha256": digest(rows),
            "gold_sha256": digest(gold), "scores": [score_record(row, gold[row["job"]["question_id"]])
                                                    for row in rows],
        }
        path = run_dir / f"scores.{SCORING_VERSION}.json"
        if path.exists() and read_json(path) != artifact:
            raise ValueError("V6 score cache identity changed; use a new scorer version")
        if not path.exists():
            atomic_json(path, artifact)
        return artifact


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", help="Complete frozen bridge or synthetic fixture; writes versioned v6 scores")
    args = parser.parse_args()
    artifact = score_run(args.run_dir)
    print(f"{len(artifact['scores'])} scores: {Path(args.run_dir) / ('scores.' + SCORING_VERSION + '.json')}")


if __name__ == "__main__":
    main()
