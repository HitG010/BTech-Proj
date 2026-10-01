"""Final-section numeric scoring with consistency checks on explanatory prose.

The rejected v6 candidate required numeric-only final sections. V7 retains its
structural/endpoint guards, allows prose around an explicit numeric claim, and
uses extra numerals only to veto conflicts, never to supply an answer.
"""

import argparse
import re
from pathlib import Path

from . import scoring as v5
from . import scoring_v6 as v6
from .data import load_gold, load_questions
from .records import ScoredResult
from .runner import load_run
from .storage import atomic_json, digest, read_json, run_lock

SCORING_VERSION = "numeric-v7"
_FINAL_NAME = r"final[ \t]+answer"
_DECLARATION = (
    rf"(?:\*\*{_FINAL_NAME}\*\*|{_FINAL_NAME})[ \t]*(?::|=|is\b)|"
    rf"\*\*{_FINAL_NAME}[ \t]*(?::|=|is\b)\*\*"
)
_FINAL = re.compile(
    r"^[ \t]*(?:#{1,6}[ \t]+)?(?:✅[ \t]*)?"
    rf"(?:(?:{_DECLARATION})[ \t]*(?P<body>[^\n]*)|"
    rf"(?:\*\*)?{_FINAL_NAME}(?:\*\*)?[ \t]*(?P<header>$))", re.I | re.M,
)
POLICY = v6.POLICY | {
    "version": SCORING_VERSION,
    "final": "agreeing explicit numeric claims; prose is allowed if it adds no conflicting numeral, alternative or negation",
    "prose_numbers": "consistency veto only; never supply an extracted answer",
    "development": "v6 rejected after gold-free prose compatibility check; v5 primary bridge preserved",
}
_DANGER = re.compile(
    r"\b(?:or|nor|either|not|no|never|wrong|incorrect|instead|alternative|alternatively|"
    r"versus|vs|maybe|uncertain|mistake|error|false|perhaps|possibly|likely|could|might|"
    r"doubl(?:e|ed|es|ing)|halv(?:e|ed|es|ing)|half|twice|tripl(?:e|ed|es|ing)|"
    r"subtract(?:ed|s|ing)?|increas(?:e|ed|es|ing)|decreas(?:e|ed|es|ing)|"
    r"multipl(?:y|ies|ied|ying)|divid(?:e|ed|es|ing)|add(?:ed|s|ing)?|plus|minus|times|"
    r"squared|cubed|power|mod|modulo|remainder|reduc(?:e|ed|es|ing))\b|"
    r"\b(?:percent\s+of|out\s+of|raised\s+to|(?:less|greater|more)\s+than|rather\s+than)\b|"
    r"%\s+of\b|"
    r"\b(?:isn|aren|wasn|weren|don|doesn|didn|can|couldn|shouldn|wouldn)['’]t\b", re.I,
)
_WRITTEN = re.compile(
    r"\b(?:zero|one|two|three|four|five|six|seven|"
    r"eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|"
    r"nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|"
    r"million|billion)\b", re.I,
)


def implementation_digest():
    return digest({"scoring_v7.py": Path(__file__).read_text(),
                   "v6_and_numeric_helpers_sha256": v6.implementation_digest()})


def _plain_numbers(text):
    text = v5.clean_claim(text)
    text = re.sub(r"[+-]?\d*\.\d*\\overline\{\d+\}",
                  lambda m: str(v5.numeric(m.group())), text)
    text = re.sub(r"\\(?:dfrac|tfrac|frac)\s*\{([^{}]+)\}\s*\{([^{}]+)\}",
                  r"\1/\2", text)
    # No word-boundary filter: an extra value such as '5miles' cannot hide a
    # contradiction. Numbers mentioned in prose are never candidate answers.
    return [v5.numeric(number) for number in re.findall(v5.NUMBER, text)]


def _unsafe_prose_math(prose, text, boxes):
    if re.search(r"%\s*(?=[+−\-\d.\\])", prose):
        return True
    for start, end, _ in boxes:
        if re.search(r"[+−\-×÷*/=<>^][ \t*$]*$", text[:start].rstrip()) or re.match(
            r"^[ \t*$]*[+−\-×÷*/=<>^%][ \t]*(?=[+−\-\d.\\])", text[end:]
        ):
            return True
    clean = v5.clean_claim(prose)
    clean = re.sub(r"[+-]?\d*\.\d*\\overline\{\d+\}",
                   lambda m: str(v5.numeric(m.group())), clean)
    clean = re.sub(r"\\(?:dfrac|tfrac|frac)\s*\{([^{}]+)\}\s*\{([^{}]+)\}", r"\1/\2", clean)
    clean = re.sub(v5.NUMBER, " ", clean)
    clean = re.sub(r"\*\*", " ", clean)  # Balanced emphasis is formatting.
    clean = re.sub(r"([A-Za-z]+)/([A-Za-z]+)",
                   lambda m: " ".join(m.groups()) if all(w.lower() in v5.UNIT_WORDS for w in m.groups())
                   else m.group(), clean)
    clean = re.sub(r"^\s*[-*_]{3,}\s*$", " ", clean, flags=re.M)
    return bool(re.search(r"[+−×÷*/=<>^\\]", clean))


def _section_values(section, inline):
    text, error = v6._display(section)
    if error:
        return [], error
    text = re.sub(r"\*\*([^*\n]+)\*\*", r"\1", text)
    if _DANGER.search(text):
        return [], "invalid_number"
    boxes, error = v6._boxes(text)
    if error:
        return [], error
    values, parts, cursor = [], [], 0
    for start, end, content in boxes:
        try:
            values.append(v5.claim_value(content))
        except ValueError:
            return [], "invalid_number"
        parts.extend([text[cursor:start], " "])
        cursor = end
    parts.append(text[cursor:])
    prose = "".join(parts)
    # Written numerals in prose are not parsed; never let a second answer hide
    # behind spelling while digit literals are held to a consistency check.
    if _WRITTEN.search(prose):
        return [], "invalid_number"
    try:
        if _unsafe_prose_math(prose, text, boxes):
            return [], "invalid_number"
    except ValueError:
        return [], "invalid_number"
    # A nonempty same-line declaration cannot defer to a later box. A box
    # already on that line is explicit; its surrounding prose is checked below.
    if inline.strip() and not v6._boxes(inline)[0]:
        claims, error = v6._section_values(inline)
        if error:
            return [], error
        values.extend(claims)
    labelled, error = v6._prefix_values(text)
    if error:
        return [], error
    values.extend(labelled)
    for line in prose.splitlines():
        # Standalone strict numeric/unit claims remain binding after a box.
        try:
            values.append(v5.claim_value(line.strip()))
        except ValueError:
            pass
    if not values:
        return [], "missing"
    try:
        extra = _plain_numbers(prose)
    except ValueError:
        return [], "invalid_number"
    if len(set(values + extra)) != 1:
        return [], "conflicting"
    return values, None


def parse_answer(final_answer, *, incomplete=False):
    if incomplete or not final_answer.strip() or "<think>" in final_answer or "</think>" in final_answer:
        return v5.parse_answer(final_answer, incomplete=incomplete)
    text = final_answer.strip()
    _, error = v6._boxes(text)
    if error:
        return None, error
    final_markers = list(_FINAL.finditer(text))
    if any(m.start() not in {f.start() for f in final_markers}
           for m in v6._FINAL_INTENT.finditer(text)):
        return None, "invalid_number"
    markers = sorted([*final_markers, *v6._HASH.finditer(text)], key=lambda m: m.start())
    if not markers:
        return v5.parse_answer(text)
    values, error = v6._prefix_values(text[:markers[0].start()])
    if error:
        return None, error
    for i, marker in enumerate(markers):
        end = markers[i + 1].start() if i + 1 < len(markers) else len(text)
        inline = marker.group("body") or ""
        claims, error = _section_values(inline + "\n" + text[marker.end():end], inline)
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
    return ScoredResult(job["id"], job["question_id"], job["mode"], answer,
                        status == "ok" and v5.numeric(answer) == v5.numeric(gold),
                        status, SCORING_VERSION).to_dict()


def score_run(run_dir):
    """Opt-in scoring of the complete frozen bridge or synthetic fixture only."""
    run_dir = Path(run_dir)
    with run_lock(run_dir):
        manifest, rows = load_run(run_dir)
        if not rows or any(row["status"] != "completed" for row in rows):
            raise ValueError("V7 scoring requires the complete run endpoint")
        dataset = Path(manifest["identity"]["config"]["data_dir"])
        meta = read_json(dataset / "manifest.json").get("metadata", {})
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
            from .research_bridge import checked_arm, read_protocol

            study = dataset.parent.parent / "bridge-v1"
            protocol = read_protocol(study)
            if str(run_dir.resolve()) not in {a["snapshot"]["run_dir"] for a in protocol["arms"].values()} or any(
                len(arm_rows) != len(protocol["arms"][arm]["snapshot"]["jobs"])
                or any(row["status"] != "completed" for row in arm_rows)
                for arm in protocol["arms"]
                for _, arm_rows in [checked_arm(study, protocol, arm)]
            ):
                raise ValueError("Paired bridge endpoint is incomplete or run is not a frozen arm")
        gold = load_gold(dataset)
        if digest(gold) != manifest["scoring_gold_sha256"] or set(gold) != {q.id for q in questions}:
            raise ValueError("Frozen gold identity differs")
        artifact = {
            "scoring_version": SCORING_VERSION, "scoring_implementation_sha256": implementation_digest(),
            "policy": POLICY, "run_id": manifest["run_id"], "records_sha256": digest(rows),
            "gold_sha256": digest(gold), "scores": [score_record(row, gold[row["job"]["question_id"]]) for row in rows],
        }
        path = run_dir / f"scores.{SCORING_VERSION}.json"
        if path.exists() and read_json(path) != artifact:
            raise ValueError("V7 score cache identity changed; use a new scorer version")
        if not path.exists():
            atomic_json(path, artifact)
        return artifact


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", help="Complete frozen bridge or synthetic fixture; writes versioned v7 scores")
    args = parser.parse_args()
    artifact = score_run(args.run_dir)
    print(f"{len(artifact['scores'])} scores: {Path(args.run_dir) / ('scores.' + SCORING_VERSION + '.json')}")


if __name__ == "__main__":
    main()
