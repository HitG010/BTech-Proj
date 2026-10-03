"""Question-only reserve child and pure two-draw opportunity diagnostics.

This module has no collection, model loading, reference, or scoring entry point.
"""

import argparse
import hashlib
import math
import platform
from pathlib import Path

from reasoning_budget.data import normalized
from reasoning_budget.records import Question
from reasoning_budget.research_data import load_allocation
from reasoning_budget.storage import atomic_json, digest, envelope, read_json, run_lock, verified

ROOT = Path("artifacts/research/data-efficiency-v1")
CHILD = "opportunity64-v1"
SPLIT = "opportunity64"
SEED = 20261007
LAM = 0.05
FILES = ("scripts/opportunity_panel_plan.py", "tests/test_opportunity_panel_plan.py",
         "docs/opportunity-panel-preparation.md", "src/reasoning_budget/research_data.py",
         "src/reasoning_budget/data.py", "src/reasoning_budget/records.py",
         "src/reasoning_budget/storage.py")


def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _safe_child(root, child):
    root = Path(root).absolute()
    child = Path(child).absolute()
    if child != root / "reserve-children" / CHILD:
        raise ValueError("Child must use the dedicated reserve-children path")
    for path in (root, root / "reserve-children", child):
        if path.is_symlink():
            raise ValueError("Symlink in child path")
    if child.parent.resolve() != (root / "reserve-children").resolve():
        raise ValueError("Child escaped the study root")
    return root, child


def _no_symlinks(paths):
    if any(Path(path).is_symlink() for path in paths):
        raise ValueError("Symlink in child artifacts")


def _siblings(parent, selected_ids, selected_prompts, child):
    for path in parent.iterdir():
        if path == child or path.name == ".lock":
            continue
        if path.is_symlink() or not path.is_dir():
            raise ValueError(f"Invalid reserve child entry: {path}")
        manifest = path / "child-manifest.json"
        if not manifest.is_file() or manifest.is_symlink():
            raise ValueError(f"Unauditable reserve child: {path}")
        payload = verified(manifest)
        rows = payload["selected"]
        ids = {r["parent_question"]["id"] for r in rows}
        prompts = {normalized(r["parent_question"]["prompt"]) for r in rows}
        if len(ids) != len(rows) or len(prompts) != len(rows):
            raise ValueError("Sibling has duplicate question identities")
        if ids & selected_ids or prompts & selected_prompts:
            raise ValueError("Reserve child overlaps another child")


def choose_child(allocation):
    """Select without labels and leave every parent record byte-for-byte intact."""
    reserve = allocation["roles"]["reserve"]
    if len(reserve) < 64:
        raise ValueError("Reserve contains fewer than 64 questions")
    ordered = sorted(reserve, key=lambda r: digest({
        "seed": SEED, "id": r["question"]["id"],
        "prompt": normalized(r["question"]["prompt"]),
    }))
    chosen = ordered[:64]
    reserve_ids = [r["question"]["id"] for r in reserve]
    reserve_prompts = [normalized(r["question"]["prompt"]) for r in reserve]
    if len(set(reserve_ids)) != len(reserve) or len(set(reserve_prompts)) != len(reserve):
        raise ValueError("Duplicate reserve identity")
    ids = [r["question"]["id"] for r in chosen]
    prompts = [normalized(r["question"]["prompt"]) for r in chosen]
    others = [r for role, rows in allocation["roles"].items() if role != "reserve" for r in rows]
    if set(ids) & {r["question"]["id"] for r in others} or set(prompts) & {
        normalized(r["question"]["prompt"]) for r in others
    }:
        raise ValueError("Reserve overlaps another parent role")
    selected = []
    for r in chosen:
        if r["pool"] != "external" or r["group_id"] != r["question"]["id"]:
            raise ValueError("Reserve source provenance changed")
        if r["normalized_prompt_sha256"] != digest(normalized(r["question"]["prompt"])):
            raise ValueError("Reserve prompt provenance changed")
        child_q = dict(r["question"], split=SPLIT)
        Question(**child_q)
        selected.append({"parent_question": r["question"], "child_question": child_q,
                         "upstream_index": r["upstream_index"], "pool": r["pool"],
                         "normalized_prompt_sha256": r["normalized_prompt_sha256"],
                         "group_id": r["group_id"]})
    folds = {r["group_id"]: i % 5 for i, r in enumerate(selected)}
    return selected, folds


def _payload(root, allocation, repository):
    selected, folds = choose_child(allocation)
    parent = root / "allocations" / "manifest.json"
    return {"schema_version": 1, "status": "prepared_question_only_collection_locked",
            "parent_file_sha256": file_sha(parent), "parent_payload_sha256": digest(allocation),
            "source": allocation["source"], "seed": SEED, "selected": selected,
            "folds": folds, "exclusions": [
                {"role": role, "id": r["question"]["id"],
                 "normalized_prompt_sha256": r["normalized_prompt_sha256"]}
                for role, rows in allocation["roles"].items() if role != "reserve" for r in rows],
            "prospective": {"questions": 64, "solvers": ["Qwen/Qwen3-1.7B", "Qwen/Qwen3-0.6B"],
                            "draws_per_mode": 2, "modes": ["direct", "thinking"],
                            "responses": 512, "answer_cap": 512, "reasoning_cap": 2048,
                            "assumed_closure_tokens": 2, "response_only_bound": 786944,
                            "lambda": LAM, "fits": 0},
            "readiness": {"qwen3_0_6b_candidate_revision": "c1899de289a04d12100db370d81485cdf75e47ca",
                          "revision_source": "https://huggingface.co/api/models/Qwen/Qwen3-0.6B",
                          "qwen3_0_6b_assets": "unresolved",
                          "qwen3_0_6b_closure": "unverified", "endpoint": "unfrozen",
                          "global_setup_retry_limits": "unfrozen", "scorer_protocol": "unfrozen",
                          "collection": "locked"},
            "frozen_files_sha256": {name: file_sha(repository / name) for name in FILES},
            "environment": {"python": platform.python_version(), "platform": platform.platform()}}


def prepare(root=ROOT, repository=None):
    root = Path(root).absolute()
    repository = Path(repository or Path(__file__).resolve().parent.parent).resolve()
    root, child = _safe_child(root, root / "reserve-children" / CHILD)
    allocation = load_allocation(root / "allocations")
    payload = _payload(root, allocation, repository)
    ids = {r["group_id"] for r in payload["selected"]}
    prompts = {normalized(r["parent_question"]["prompt"]) for r in payload["selected"]}
    parent = child.parent
    with run_lock(parent):
        _siblings(parent, ids, prompts, child)
        if child.exists() or child.is_symlink():
            raise ValueError("Child already exists; use verify for read-only inspection")
        child.mkdir()
        rows = [r["child_question"] for r in payload["selected"]]
        dataset = child / "dataset"
        dataset.mkdir()
        atomic_json(dataset / "questions.json", rows)
        atomic_json(dataset / "manifest.json", {
            "schema_version": 1, "metadata": {"role": SPLIT, "gold_deferred": True,
                "parent_payload_sha256": payload["parent_payload_sha256"]},
            "questions_sha256": digest(rows), "gold_sha256": None,
            "splits": {SPLIT: [r["id"] for r in rows]},
        })
        atomic_json(child / "child-manifest.json", envelope(payload))
        atomic_json(child / "preparation-plan.json", envelope({
            "child_manifest_sha256": digest(payload), "dataset_questions_sha256": file_sha(dataset / "questions.json"),
            "dataset_manifest_sha256": file_sha(dataset / "manifest.json"),
            "status": "prepared_question_only_collection_locked",
        }))
    return child


def verify(root=ROOT, repository=None):
    root = Path(root).absolute()
    repository = Path(repository or Path(__file__).resolve().parent.parent).resolve()
    root, child = _safe_child(root, root / "reserve-children" / CHILD)
    dataset = child / "dataset"
    _no_symlinks((child / "child-manifest.json", child / "preparation-plan.json",
                  dataset, dataset / "questions.json", dataset / "manifest.json"))
    allocation = load_allocation(root / "allocations")
    payload = verified(child / "child-manifest.json")
    if payload != _payload(root, allocation, repository):
        raise ValueError("Child identity, source, or frozen file changed")
    ids = {r["group_id"] for r in payload["selected"]}
    prompts = {normalized(r["parent_question"]["prompt"]) for r in payload["selected"]}
    _siblings(child.parent, ids, prompts, child)
    plan = verified(child / "preparation-plan.json")
    if (dataset / "gold.json").exists() or (dataset / "gold.json").is_symlink():
        raise ValueError("Child gold file is forbidden")
    if plan != {"child_manifest_sha256": digest(payload),
                "dataset_questions_sha256": file_sha(dataset / "questions.json"),
                "dataset_manifest_sha256": file_sha(dataset / "manifest.json"),
                "status": "prepared_question_only_collection_locked"}:
        raise ValueError("Child preparation plan changed")
    rows = read_json(dataset / "questions.json")
    manifest = read_json(dataset / "manifest.json")
    if rows != [r["child_question"] for r in payload["selected"]] or manifest != {
        "schema_version": 1, "metadata": {"role": SPLIT, "gold_deferred": True,
            "parent_payload_sha256": payload["parent_payload_sha256"]},
        "questions_sha256": digest(rows), "gold_sha256": None,
        "splits": {SPLIT: [r["id"] for r in rows]},
    }:
        raise ValueError("Child question dataset changed")
    return payload


def opportunity_stats(rows, question_ids, solver, draw):
    """Descriptive rates from synthetic/already-authorized outcomes supplied by caller."""
    subset = [r for r in rows if r["solver"] == solver and r["draw"] == draw]
    if (not question_ids or len(set(question_ids)) != len(question_ids)
            or {r["question_id"] for r in subset} != set(question_ids)
            or len(subset) != len(question_ids)):
        raise ValueError("One paired row per question is required")
    rescue = harm = positive = 0
    for r in subset:
        if r["direct_correct"] not in (0, 1) or r["thinking_correct"] not in (0, 1):
            raise ValueError("Binary correctness required")
        if not math.isfinite(r["thinking_tokens"]) or r["thinking_tokens"] < 0:
            raise ValueError("Invalid thinking cost")
        rescue += int(r["thinking_correct"] == 1 and r["direct_correct"] == 0)
        harm += int(r["thinking_correct"] == 0 and r["direct_correct"] == 1)
        positive += int(r["thinking_correct"] - r["direct_correct"]
                        - LAM * r["thinking_tokens"] / 1000 > 0)
    n = len(subset)
    return {"questions": n, "rescue": rescue, "harm": harm, "positive_gain": positive,
            "rescue_rate": rescue / n, "harm_rate": harm / n,
            "positive_gain_rate": positive / n}


def confidence_crossfit(rows, folds, solver):
    """Return actions only; held-out and opposite-half labels cannot tune them."""
    ids = set(folds)
    selected_rows = [r for r in rows if r["solver"] == solver]
    keyed = {(r["question_id"], r["draw"]): r for r in selected_rows}
    if (set(keyed) != {(q, d) for q in ids for d in (0, 1)}
            or len(keyed) != len(selected_rows) or len(keyed) != 2 * len(ids)):
        raise ValueError("Exactly two rows per solver/question required")
    if set(folds.values()) != set(range(5)):
        raise ValueError("Five question folds required")
    results = {}
    for train_draw, eval_draw in ((0, 1), (1, 0)):
        for fold in range(5):
            train = [keyed[q, train_draw] for q in sorted(ids) if folds[q] != fold]
            test = [keyed[q, eval_draw] for q in sorted(ids) if folds[q] == fold]
            confidence = [r["confidence"] for r in train + test]
            if any(not math.isfinite(v) for v in confidence):
                raise ValueError("Finite confidence required")
            for r in train:
                if (r["direct_correct"] not in (0, 1) or r["thinking_correct"] not in (0, 1)
                        or not math.isfinite(r["thinking_tokens"]) or r["thinking_tokens"] < 0):
                    raise ValueError("Training correctness/cost is invalid")
            candidates = [-math.inf, *sorted(set(r["confidence"] for r in train)), math.inf]
            def objective(threshold):
                action = [r["confidence"] < threshold for r in train]
                gain = sum(a * (r["thinking_correct"] - r["direct_correct"]
                                - LAM * r["thinking_tokens"] / 1000)
                           for a, r in zip(action, train)) / len(train)
                return (gain, -sum(action), -threshold)
            threshold = max(candidates, key=objective)
            for r in test:
                results[(r["question_id"], train_draw, eval_draw)] = {
                    "fold": fold, "threshold": threshold,
                    "escalate": bool(r["confidence"] < threshold),
                }
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "verify"))
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    result = prepare(args.root) if args.command == "prepare" else verify(args.root)
    print(result if args.command == "prepare" else result["status"])


if __name__ == "__main__":
    main()
