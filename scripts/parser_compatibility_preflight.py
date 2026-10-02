"""Bounded, gold-free Phase 2a extraction compatibility; never score an answer.

Only this separately frozen wrapper is a candidate. The production/frozen v7
parser and every existing score remain unchanged. Contextual numeric quantities,
written counts and unit conversion are deliberately outside the candidate.
"""

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from reasoning_budget import scoring_v7 as v7
from reasoning_budget.storage import digest, envelope, verified

ROOT = Path(__file__).resolve().parents[1]
STUDY = Path("artifacts/research/data-efficiency-v1")
OUTPUT = STUDY / "parser-compatibility-v1"
BASELINE_DIGEST = "c63d69c3c9cb89a0ee72915172bba569b3ec8329d5ef0be30291297fe7bb8964"
RUNS = [
    ("historical", "artifacts/runs/d00485799f1c8932bafa", 400),
    ("historical", "artifacts/runs/931c0e7a434abe265049", 300),
    ("historical", "artifacts/runs/c79bba43ba316a88f2c6", 200),
    ("bridge", str(STUDY / "bridge-v1/runs/legacy/7d1c88b192e8e60d7e7e"), 100),
    ("bridge", str(STUDY / "bridge-v1/runs/v3/e8bcb668582ef482339f"), 100),
    ("repeat", str(STUDY / "repeat-panel-v1/runs/2a0d296557c397e64553"), 800),
]
# Exactly one balanced, whole-line bold wrapper; no nested emphasis, no
# unmarked prose, no multiline claim reclassification and no numeric rewrite.
_BOLD_FINAL = re.compile(
    r"^(?P<prefix>[ \t]*(?:#{1,6}[ \t]+)?(?:✅[ \t]*)?)"
    r"\*\*(?P<claim>final[ \t]+answer[ \t]*(?::|=|is\b)[^*\n]*)\*\*[ \t]*$",
    re.I | re.M,
)
POLICY = {
    "candidate": "final-declaration-balanced-bold-v1",
    "normalization": "Remove only a balanced whole-line ** wrapper enclosing an anchored explicit Final answer :/= /is declaration; delegate all extraction to unchanged v7.",
    "units": "Retain v7 numeric/unit syntax. Do not convert units or erase differing numeric literals.",
    "context": "Retain v7 digit-consistency veto and written-numeral rejection; no context erasure.",
    "guards": "Retain incomplete/leakage/unclosed-box, malformed-final, conflicting-label, multi-answer, negation and alternative rejection.",
    "scope": "One candidate, no post-comparison adaptation. Extraction only; no correctness, labels, fitting, references or generation.",
    "gate": "All prespecified synthetic cases pass, no accepted-to-rejected or accepted-value changes, and every newly accepted cached text has a single explicit scalar claim under the frozen grammar.",
    "decision": "Compatible candidate is eligible only for a future separately authorized scoring sidecar. Keep v7 and all primary labels regardless; reject candidate if any gate fails.",
}


def normalize(text):
    return _BOLD_FINAL.sub(lambda match: match["prefix"] + match["claim"], text)


def parse_answer(text, *, incomplete=False):
    return v7.parse_answer(normalize(text), incomplete=incomplete)


def extract_record(record):
    result = record.get("result")
    if record["status"] != "completed" or result is None:
        return None, "generation_failure"
    return parse_answer(
        result["final_answer"],
        incomplete=result["answer_truncated"]
        or result["termination"] in {"timeout", "early_eos", "reasoning_in_answer"},
    )


def fixtures():
    """Answer literals are synthetic syntax expectations, never dataset gold."""
    cases = []
    for number, expected in [("7", "7"), ("-3/2", "-3/2"), ("0.125", "1/8")]:
        for prefix in ["", "### ", "### ✅ "]:
            for separator in [":", "=", " is"]:
                cases.append({"text": prefix + "**Final answer" + separator
                              + " $\\boxed{" + number + "}$**",
                              "incomplete": False, "expected": [expected, "ok"]})
    for text, expected in [
        ("**Final answer: 7 dollars**", ["7", "ok"]),
        ("**Final answer: \\boxed{7}**\nThe total is 7 dollars.", ["7", "ok"]),
        ("Intermediate \\boxed{2}\n**Final answer: \\boxed{7}**", ["7", "ok"]),
        ("**Final answer: \\boxed{7} or 9**", [None, "invalid_number"]),
        ("**Final answer: \\boxed{7} is not correct**", [None, "invalid_number"]),
        ("**Final answer: \\boxed{7} isn't correct**", [None, "invalid_number"]),
        ("**Final answer: \\boxed{7} perhaps**", [None, "invalid_number"]),
        ("**Final answer: \\boxed{7} rather than nine**", [None, "invalid_number"]),
        ("**Final answer: \\boxed{7} and \\boxed{9}**", [None, "conflicting"]),
        ("**Final answer: \\boxed{7}**\nFinal answer: 9", [None, "conflicting"]),
        ("Answer: 9\n**Final answer: \\boxed{7}**", [None, "conflicting"]),
        ("**Final answer: \\boxed{7**", [None, "incomplete"]),
        ("**Final answer: see below**\n\\boxed{7}", [None, "invalid_number"]),
        ("**Final answer: **", [None, "missing"]),
        ("**Final answer: \\boxed{7} + 7**", [None, "invalid_number"]),
        ("**Final answer: \\boxed{7} times itself**", [None, "invalid_number"]),
        ("**Final answer: \\boxed{7} percent of 7**", [None, "invalid_number"]),
        ("**Final answer: \\boxed{7}**\nThe total is 9miles.", [None, "conflicting"]),
        ("Final answer:\n0.07 dollars, which is 7 cents.\n\\boxed{7}",
         [None, "conflicting"]),
        ("Final answer:\nIncluding the extra 3 inches, the length is:\n\\boxed{7}",
         [None, "conflicting"]),
        ("Final answer:\nThe remaining two workers need:\n\\boxed{7}",
         [None, "invalid_number"]),
        ("Final answer:\nThe price of one pear is:\n\\boxed{7}",
         [None, "invalid_number"]),
        ("**Final answer: \\boxed{7} dollars**", ["7", "ok"]),
        ("**Final answer: \\boxed{7} cents**", ["7", "ok"]),
        ("**Final answer: \\boxed{7} miles/hour**", ["7", "ok"]),
        ("**Final answer: \\boxed{7} % 7**", [None, "invalid_number"]),
        ("**Final answer: \\boxed{7}**\nThe other answer is nine.",
         [None, "invalid_number"]),
        ("<think>secret</think>\n**Final answer: \\boxed{7}**",
         [None, "reasoning_in_answer"]),
    ]:
        cases.append({"text": text, "incomplete": False, "expected": expected})
    cases.append({"text": "**Final answer: \\boxed{7}**", "incomplete": True,
                  "expected": [None, "incomplete"]})
    return cases


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_once(path, payload):
    """Exclusive creation: never overwrite a frozen plan or result."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        json.dump(envelope(payload), stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")


def input_inventory(root):
    inventory = []
    for group, run, expected in RUNS:
        paths = sorted((root / run / "results").glob("*.json"))
        if len(paths) != expected:
            raise ValueError(f"Endpoint mismatch for {run}: {len(paths)} != {expected}")
        inventory.append({"group": group, "run": run, "count": expected,
                          "files": {str(p.relative_to(root)): file_hash(p) for p in paths}})
    return inventory


def protected_inventory(root):
    # Raw hashes establish preservation without parsing scores/correctness.
    # No reference/gold files, source dataset or model weights are opened.
    paths = list((root / "src/reasoning_budget").glob("*.py"))
    paths += list((root / "configs").rglob("*.yaml"))
    for directory in ["parser-v6-preflight-v1", "parser-v7-preflight-v1",
                      "repeat-parser-audit-v1", "repeat-panel-v1", "bridge-v1"]:
        base = root / STUDY / directory
        paths += list(base.glob("*.json")) + list(base.glob("*.md"))
    return {str(p.relative_to(root)): file_hash(p) for p in sorted(set(paths))}


def source_inventory(root):
    return {path: file_hash(root / path) for path in [
        "scripts/parser_compatibility_preflight.py", "tests/test_parser_compatibility_preflight.py",
    ]}


def freeze(root=ROOT):
    if v7.implementation_digest() != BASELINE_DIGEST:
        raise ValueError("Frozen v7 implementation changed")
    plan = {"version": "parser-compatibility-v1", "created_at_utc":
            datetime.now(timezone.utc).isoformat(), "policy": POLICY,
            "v7_implementation_sha256": BASELINE_DIGEST,
            "source_files": source_inventory(root), "synthetic_fixtures": fixtures(),
            "inputs": input_inventory(root), "protected_files": protected_inventory(root),
            "reference_access": False, "gold_access": False, "generation": False,
            "primary_labels_unchanged": True, "cloud_spend_usd": 0,
            "prior_audit_informed_scope": True,
            "limitations": "Gold-free syntax coverage on reused development outputs; not correctness validation, unseen-data generalization or a primary-gate rescue."}
    write_once(root / OUTPUT / "plan.json", plan)
    return digest(plan)


def execute(root=ROOT):
    plan_path = root / OUTPUT / "plan.json"
    plan = verified(plan_path)
    if (plan["policy"] != POLICY or plan["source_files"] != source_inventory(root)
            or plan["v7_implementation_sha256"] != v7.implementation_digest()
            or plan["inputs"] != input_inventory(root)
            or plan["protected_files"] != protected_inventory(root)):
        raise ValueError("Frozen preflight identity changed")
    synthetic = []
    for case in plan["synthetic_fixtures"]:
        observed = list(parse_answer(case["text"], incomplete=case["incomplete"]))
        synthetic.append({**case, "observed": observed, "passed": observed == case["expected"]})
    counts, changes, regressions, extractions = Counter(), [], [], []
    for run in plan["inputs"]:
        for path in run["files"]:
            row = verified(root / path)
            old, new = v7.extract_record(row), extract_record(row)
            counts[run["group"]] += 1
            result = row.get("result") or {}
            item = {"path": path, "group": run["group"], "job_id": row["job"]["id"],
                    "mode": row["job"]["mode"], "v7": list(old), "candidate": list(new),
                    "text_sha256": digest(result.get("final_answer", ""))}
            extractions.append(item)
            if old != new:
                text = result["final_answer"]
                item = dict(item, text=text, normalized_text=normalize(text),
                            review="Balanced bold final declaration normalized; every v7 scalar/conflict/lexical and incomplete guard reapplied.")
                changes.append(item)
                if old[1] == "ok" or new[1] != "ok":
                    regressions.append(item)
    unchanged = (plan["inputs"] == input_inventory(root)
                 and plan["protected_files"] == protected_inventory(root))
    synthetic_pass = all(case["passed"] for case in synthetic)
    review_pass = all(_BOLD_FINAL.search(c["text"]) and c["candidate"][1] == "ok"
                      for c in changes)
    compatible = synthetic_pass and not regressions and review_pass and unchanged
    report = {"version": "parser-compatibility-v1", "plan_sha256": digest(plan),
              "synthetic_cases": len(synthetic), "synthetic_pass": synthetic_pass,
              "records_compared": sum(counts.values()), "groups": dict(counts),
              "changed": len(changes), "changes": changes, "regressions": regressions,
              "transition_counts": dict(Counter(f'{c["v7"][1]} -> {c["candidate"][1]}'
                                               for c in changes)),
              "compatibility_gate_pass": compatible,
              "decision": "compatible_narrow_candidate_retain_v7_primary" if compatible
              else "reject_candidate_retain_v7",
              "synthetic_results": synthetic, "extractions": extractions,
              "input_records_preserved": unchanged,
              "protected_original_file_count": len(plan["protected_files"]),
              "no_correctness_assessed": True, "no_score_cache_written": True,
              "no_references_or_gold_opened": True, "no_generation": True,
              "primary_labels": "unchanged frozen v7", "cloud_spend_usd": 0,
              "limitations": plan["limitations"]}
    write_once(root / OUTPUT / "report.json", report)
    return {key: report[key] for key in ["decision", "synthetic_cases", "synthetic_pass",
                                       "records_compared", "groups", "changed",
                                       "compatibility_gate_pass", "input_records_preserved"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["freeze", "execute"])
    args = parser.parse_args()
    print(json.dumps(freeze() if args.action == "freeze" else execute(), indent=2))


if __name__ == "__main__":
    main()
