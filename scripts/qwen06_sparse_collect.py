"""Bounded two-stage local runtime for the frozen Qwen3-0.6B sparse guard.

Only runtime-v1 receives writes. Operator commands are prepare, launch, resume,
and status; collector, supervisor, and finalizer are private authenticated modes.
"""

import argparse
import os
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path

from reasoning_budget import scoring_v7
from reasoning_budget.confirmation import file_hash
from reasoning_budget.records import GenerationJob, GenerationResult, Question
from reasoning_budget.storage import atomic_json, digest, envelope, run_lock, verified
from scripts import opportunity_panel_collect as orig
from scripts import opportunity_panel_recovery as recovery
from scripts import qwen06_sparse_validation as sparse

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = sparse.OUTPUT / "runtime-v1"
SOURCE_FILES = ("scripts/qwen06_sparse_collect.py", "tests/test_qwen06_sparse_collect.py",
                "docs/qwen06-sparse-runtime-protocol.md")
VERSION = "qwen06-sparse-runtime-v1"
SPEC = {"version": VERSION, "questions": 228, "max_eligible": 32,
        "global_tokens": 250000, "global_seconds": 21600,
        "setup_seconds": 900, "job_seconds": 600,
        "maximum_setups": 2, "maximum_invocations": 2, "maximum_launches": 2,
        "maximum_polled_rss_bytes": 9 * 1024**3, "poll_seconds": 2,
        "watchdog_grace_seconds": 5, "automatic_resume": False,
        "cloud_spend_usd": 0, "first_failure_stop": True}


def fail(message):
    raise orig.IntegrityError(message)


def source_hashes():
    return {name: file_hash(ROOT / name) for name in SOURCE_FILES}


def prepared_paths():
    return ([sparse.OUTPUT / name for name in ("policy-plan.json", "fit-started.json",
             "policy.json", "policy-review.json", "question-protocol.json")]
            + [sparse.CHILD / name for name in ("child-manifest.json", "preparation-plan.json",
                "dataset/questions.json", "dataset/manifest.json")])


def safe_path():
    if (RUNTIME.is_symlink() or sparse.OUTPUT.is_symlink()
            or RUNTIME.resolve() != sparse.OUTPUT.resolve() / "runtime-v1"
            or RUNTIME.exists() and any(p.is_symlink() for p in RUNTIME.rglob("*"))):
        fail("Sparse runtime path contains symlink or escaped output")


def _write(path, value):
    orig.write_once(path, value)


def _current_inputs():
    protocol = sparse.checked_questions()
    policy = verified(sparse.OUTPUT / "policy.json")
    child = verified(sparse.CHILD / "child-manifest.json")
    if (protocol["arm"]["scoring_version"] != "numeric-v7"
            or protocol["arm"]["scoring_implementation_sha256"] != scoring_v7.implementation_digest()
            or len(protocol["arm"]["jobs"]) != 456
            or len(child["selected"]) != 228
            or policy["fit"]["threshold"] == "always"):
        fail("Prepared sparse study identity or contrast changed")
    return protocol, policy, child


def prepare():
    """One-time runtime snapshot; never constructs the model or opens references."""
    safe_path()
    if RUNTIME.exists():
        fail("Sparse runtime already prepared or attempted")
    with run_lock(RUNTIME):
        if any(p.name != ".lock" for p in RUNTIME.iterdir()):
            fail("Sparse runtime already prepared")
        protocol, policy, child = _current_inputs()
        pins = {str(p): file_hash(p) for p in prepared_paths()}
        jobs = protocol["arm"]["jobs"]
        direct = [j for j in jobs if j["mode"] == "direct"]
        thinking = [j for j in jobs if j["mode"] == "thinking"]
        if (len(direct) != 228 or len(thinking) != 228
                or {j["question_id"] for j in direct} != {r["child_question"]["id"] for r in child["selected"]}
                or {j["question_id"] for j in thinking} != {j["question_id"] for j in direct}
                or any(j["sample"] != 0 for j in jobs)
                or len({j["id"] for j in jobs}) != 456
                or len({j["seed"] for j in jobs}) != 456
                or sum(j["max_tokens"] for j in direct) != 228 * 512
                or any(j["max_tokens"] != 2562 for j in thinking)):
            fail("Frozen sparse jobs or limits changed")
        for path, sha in protocol["arm"]["asset_file_sha256"].items():
            if file_hash(path) != sha:
                fail("Pinned local solver asset changed")
        plan = {"version": VERSION, "spec": SPEC, "source_file_sha256": source_hashes(),
            "environment": orig.stable_environment(), "prepared_file_sha256": pins,
            "question_protocol_sha256": digest(protocol), "policy_sha256": digest(policy),
            "child_sha256": digest(child), "old_study_inventory_sha256":
                verified(sparse.OUTPUT / "policy-plan.json")["old_study_inventory_sha256"],
            "scoring_implementation_sha256": scoring_v7.implementation_digest(),
            "generation_implementation_sha256": protocol["arm"]["generation_implementation_sha256"],
            "direct_jobs": direct, "thinking_jobs": thinking,
            "question_ids": [r["child_question"]["id"] for r in child["selected"]],
            "threshold": policy["fit"]["threshold"], "prepared_at": time.time(),
            "generation_started": False, "reference_access": False,
            "purpose": "fresh sparse guard diagnostic, not confirmation"}
        _write(RUNTIME / "prepare-started.json", {"plan_sha256": digest(plan),
            "started_at": time.time(), "one_time": True})
        _write(RUNTIME / "plan.json", plan)
        atomic_json(RUNTIME / "status.json", envelope({"state": "prepared",
            "plan_sha256": digest(plan), "updated_at": time.time(),
            "direct_completed": 0, "thinking_completed": 0,
            "generation_started": False, "references_opened": False}))
        return {"plan_sha256": digest(plan), "direct_jobs": 228,
                "potential_thinking_jobs": 228, "collection": "locked_until_independent_prelaunch_audit"}


def read_plan(*, check_assets=False, verify_inputs=True):
    safe_path()
    plan = verified(RUNTIME / "plan.json")
    marker = verified(RUNTIME / "prepare-started.json")
    if (plan["version"] != VERSION or plan["spec"] != SPEC
            or marker["plan_sha256"] != digest(plan) or marker["one_time"] is not True
            or plan["source_file_sha256"] != source_hashes()
            or plan["environment"] != orig.stable_environment()
            or plan["scoring_implementation_sha256"] != scoring_v7.implementation_digest()):
        fail("Sparse runtime source, scorer, or environment changed")
    for path, sha in plan["prepared_file_sha256"].items():
        if file_hash(path) != sha:
            fail("Frozen prepared input changed")
    if set(plan["prepared_file_sha256"]) != {str(p) for p in prepared_paths()}:
        fail("Frozen prepared input inventory changed")
    if verify_inputs:
        protocol, policy, child = _current_inputs()
    else:
        # Collector authentication is deliberately cheap. The setup reservation
        # precedes the full source/asset walk and model construction below.
        protocol = verified(sparse.OUTPUT / "question-protocol.json")
        policy = verified(sparse.OUTPUT / "policy.json")
        child = verified(sparse.CHILD / "child-manifest.json")
    if (digest(protocol) != plan["question_protocol_sha256"]
            or digest(policy) != plan["policy_sha256"]
            or digest(child) != plan["child_sha256"]
            or verified(sparse.OUTPUT / "policy-plan.json")["old_study_inventory_sha256"]
               != plan["old_study_inventory_sha256"]
            or protocol["arm"]["generation_implementation_sha256"]
               != plan["generation_implementation_sha256"]
            or plan["direct_jobs"] != [j for j in protocol["arm"]["jobs"] if j["mode"] == "direct"]
            or plan["thinking_jobs"] != [j for j in protocol["arm"]["jobs"] if j["mode"] == "thinking"]
            or plan["question_ids"] != [r["child_question"]["id"] for r in child["selected"]]
            or plan["threshold"] != policy["fit"]["threshold"]):
        fail("Sparse runtime input or job identity changed")
    if list((RUNTIME / "launches").glob("*.json")):
        review = verified(RUNTIME / "prelaunch-review.json")
        if review != {"plan_sha256": digest(plan),
                       "prepared_file_sha256": digest(plan["prepared_file_sha256"]),
                       "decision": "independently_audited_allow_launch"}:
            fail("Sparse prelaunch review changed after launch")
    if check_assets:
        for path, sha in protocol["arm"]["asset_file_sha256"].items():
            if file_hash(path) != sha:
                fail("Pinned local solver asset changed")
    return plan, protocol, child


def _all(folder):
    return {p.stem: verified(p) for p in (RUNTIME / folder).glob("*.json")}


def _jobs(plan):
    return {j["id"]: j for j in plan["direct_jobs"] + plan["thinking_jobs"]}


def _launch_rows(plan):
    rows = _all("launches")
    plan_sha = digest(plan)
    if len(rows) > SPEC["maximum_launches"]:
        fail("Sparse launch ceiling exceeded")
    for key, row in rows.items():
        if (row["launch_id"] != key or row["plan_sha256"] != plan_sha
                or type(row["explicit_resume"]) is not bool
                or not orig.finite_number(row["reserved_at"])):
            fail("Sparse launch identity changed")
    ordered = sorted(rows.values(), key=lambda r: r["reserved_at"])
    if any(r["explicit_resume"] != (i == 1) for i, r in enumerate(ordered)):
        fail("Sparse initial/resume launch order changed")
    return ordered


def usage(plan, *, now=None, validated_mask=None):
    """Reverse-snapshot ledger; unresolved operations retain full reservation."""
    plan_sha = digest(plan)
    receipts = _all("ledger/settlements")
    attempts = _all("attempt-records")
    reservations = _all("ledger/reservations")
    if not set(receipts) <= set(reservations) or not set(attempts) <= set(reservations):
        fail("Orphan sparse ledger entry")
    jobs = _jobs(plan)
    mask = (validated_mask if validated_mask is not None else
            read_mask(plan) if (RUNTIME / "eligibility.json").exists() else None)
    invocations = _all("invocations")
    if len(invocations) > SPEC["maximum_invocations"]:
        fail("Sparse invocation ceiling exceeded")
    for invocation_id, invocation in invocations.items():
        launch = verified(RUNTIME / "launches" / f"{invocation['launch_id']}.json")
        supervisor = verified(RUNTIME / "supervisor-starts" / f"{invocation['launch_id']}.json")
        if (invocation["invocation_id"] != invocation_id
                or invocation["plan_sha256"] != plan_sha
                or launch["plan_sha256"] != plan_sha
                or supervisor["launch_id"] != invocation["launch_id"]
                or supervisor["pid"] != invocation["supervisor_pid"]):
            fail("Sparse invocation/launch/supervisor binding changed")
    tokens = 0
    seconds = 0.0
    setups = 0
    setup_by_invocation = set()
    seen_attempts = {}
    for key, row in reservations.items():
        invocation = invocations.get(row["invocation_id"])
        invocation_start_path = (RUNTIME / "invocation-starts" /
                                 f"{row['invocation_id']}.json")
        invocation_start = verified(invocation_start_path) if invocation_start_path.exists() else None
        if (row["id"] != key or invocation is None
                or invocation_start is None
                or invocation_start["invocation_id"] != row["invocation_id"]
                or not orig.finite_number(invocation_start["started_at"])
                or row["started_at"] < invocation_start["started_at"]
                or row["plan_sha256"] != plan_sha
                or invocation["plan_sha256"] != plan_sha
                or row["kind"] not in ("setup", "job")
                or not orig.finite_number(row["started_at"])
                or row["started_at"] < plan["prepared_at"]
                or type(row["reserved_tokens"]) is not int or row["reserved_tokens"] < 0
                or not orig.finite_number(row["reserved_seconds"]) or row["reserved_seconds"] <= 0):
            fail("Sparse reservation identity changed")
        if row["kind"] == "setup":
            setups += 1
            if (row["invocation_id"] in setup_by_invocation
                    or row["reserved_tokens"] != 0
                    or row["reserved_seconds"] > SPEC["setup_seconds"]):
                fail("Sparse setup reservation invalid")
            setup_by_invocation.add(row["invocation_id"])
        else:
            job = jobs.get(row["job_id"])
            setup = reservations.get(row["session_id"])
            setup_path = RUNTIME / "ledger/settlements" / f"{row['session_id']}.json"
            setup_receipt = verified(setup_path) if setup_path.exists() else None
            if (job is None or row["reserved_tokens"] != job["max_tokens"]
                    or row["reserved_seconds"] > SPEC["job_seconds"]
                    or setup is None or setup["kind"] != "setup"
                    or setup["invocation_id"] != row["invocation_id"]
                    or setup_receipt is None or setup_receipt["status"] != "loaded"
                    or setup_receipt["id"] != row["session_id"]
                    or setup_receipt["reservation_sha256"] != digest(setup)
                    or row["started_at"] < setup_receipt["finished_at"]):
                fail("Sparse job reservation or loaded setup changed")
            if job["mode"] == "thinking":
                if (mask is None or job["question_id"] not in mask["eligible_question_ids"]
                        or row["started_at"] < mask["frozen_at"]):
                    fail("Unselected thinking job was reserved")
            elif mask is not None and row["started_at"] >= mask["frozen_at"]:
                fail("Direct reservation after frozen eligibility")
            seen_attempts.setdefault(job["id"], []).append(row)
        receipt = receipts.get(key)
        spent, duration = row["reserved_tokens"], row["reserved_seconds"]
        if receipt is not None:
            anchor = verified(RUNTIME / "anchors" / f"{key}.json")
            if (anchor["id"] != key or anchor["reservation_sha256"] != digest(row)
                    or anchor["invocation_id"] != row["invocation_id"]
                    or anchor["pid"] != invocation_start["pid"]
                    or not orig.finite_number(anchor["monotonic_before_reserve"])):
                fail("Settled sparse operation lost its monotonic anchor")
            if (receipt["id"] != key or receipt["reservation_sha256"] != digest(row)
                    or receipt["status"] not in (("loaded", "failed") if row["kind"] == "setup" else ("completed", "failed"))
                    or type(receipt["charged_tokens"]) is not int
                    or not 0 <= receipt["charged_tokens"] <= row["reserved_tokens"]
                    or not orig.finite_number(receipt["elapsed_seconds"])
                    or receipt["elapsed_seconds"] < 0
                    or not orig.finite_number(receipt["finished_at"])
                    or receipt["finished_at"] < row["started_at"]):
                fail("Sparse settlement identity or cost changed")
            spent, duration = receipt["charged_tokens"], receipt["elapsed_seconds"]
            if receipt["status"] in ("loaded", "completed") and duration > row["reserved_seconds"]:
                fail("Successful sparse operation exceeded reservation")
            if row["kind"] == "job":
                record = attempts.get(key)
                if record is None or receipt["record_sha256"] != digest(record):
                    fail("Sparse attempt/receipt link changed")
                if (record["job"] != jobs[row["job_id"]]
                        or record["attempt_id"] != key
                        or record["session_id"] != row["session_id"]
                        or record["status"] != receipt["status"]
                        or record["plan_sha256"] != plan_sha
                        or record["implementation_sha256"] != plan["generation_implementation_sha256"]):
                    fail("Sparse attempt identity changed")
                actual = row["reserved_tokens"]
                if record["result"] is not None:
                    try:
                        actual = orig.validate_result(GenerationResult(**record["result"]),
                                                      GenerationJob(**record["job"]))
                    except (ValueError, TypeError, KeyError):
                        if receipt["status"] == "completed":
                            fail("Completed sparse result invalid")
                if receipt["charged_tokens"] != actual:
                    fail("Sparse token charge differs from result")
                if receipt["status"] == "completed":
                    if (record["result"] is None or record["result"]["termination"] == "timeout"
                            or verified(RUNTIME / "results" / f"{row['job_id']}.json") != record):
                        fail("Sparse completed result differs from settled attempt")
        tokens += spent
        seconds += duration
    if (setups > SPEC["maximum_setups"]
            or any(len(v) > 2 or len({r["invocation_id"] for r in v}) != len(v)
                   for v in seen_attempts.values())):
        fail("Sparse setup or attempt ceiling exceeded")
    start_path, end_path = RUNTIME / "collection-start.json", RUNTIME / "collection-end.json"
    opening = verified(start_path) if start_path.exists() else None
    ending = verified(end_path) if end_path.exists() else None
    launches = _launch_rows(plan)
    if opening is not None and (opening["plan_sha256"] != plan_sha
            or not orig.finite_number(opening["started_at"])
            or opening["started_at"] < plan["prepared_at"]
            or not launches or opening["launch_id"] != launches[0]["launch_id"]
            or opening["started_at"] < launches[0]["reserved_at"]):
        fail("Sparse collection start changed")
    if launches and opening is None:
        fail("Sparse launch lacks global wall-clock origin")
    if reservations and opening is None:
        fail("Sparse operation preceded collection start")
    if opening and any(r["started_at"] < opening["started_at"] for r in reservations.values()):
        fail("Sparse reservation preceded collection start timestamp")
    if ending is not None and (opening is None or ending["plan_sha256"] != plan_sha
            or not orig.finite_number(ending["finished_at"])
            or ending["finished_at"] < opening["started_at"]
            or any(r["started_at"] > ending["finished_at"] for r in reservations.values())
            or any(r["finished_at"] > ending["finished_at"] for r in receipts.values())):
        fail("Sparse collection end changed")
    wall = max(0.0, (ending["finished_at"] if ending is not None
                     else time.time() if now is None else now) - opening["started_at"]) if opening else 0.0
    return {"charged_tokens": tokens, "charged_seconds": seconds, "wall_seconds": wall,
            "budget_seconds": max(wall, seconds), "setup_reservations": setups,
            "attempts": sum(r["kind"] == "job" for r in reservations.values()),
            "unresolved": len(set(reservations) - set(receipts))}


def completed_rows(plan, mode):
    jobs = {j["id"]: j for j in (plan["direct_jobs"] if mode == "direct" else plan["thinking_jobs"])}
    plan_sha = digest(plan)
    paths = list((RUNTIME / "results").glob("*.json"))
    if len(paths) > 260 or any(p.stem not in _jobs(plan) for p in paths):
        fail("Unknown sparse result")
    result = []
    for frozen in jobs.values():
        path = RUNTIME / "results" / f"{frozen['id']}.json"
        if not path.exists():
            continue
        row = verified(path)
        if (row["job"] != frozen or row["status"] != "completed"
                or row["plan_sha256"] != plan_sha
                or row["question_protocol_sha256"] != plan["question_protocol_sha256"]
                or row["implementation_sha256"] != plan["generation_implementation_sha256"]):
            fail("Sparse result identity changed")
        value = GenerationResult(**row["result"])
        orig.validate_result(value, GenerationJob(**frozen))
        if value.termination == "timeout":
            fail("Timeout cannot be completed")
        receipt_path = RUNTIME / "ledger/settlements" / f"{row['attempt_id']}.json"
        if not receipt_path.exists():
            # Live publication is in flight. After an observed failed process,
            # retain the valid output and charge its entire unknown reservation.
            attempt = verified(RUNTIME / "ledger/reservations" / f"{row['attempt_id']}.json")
            invocation = verified(RUNTIME / "invocations" / f"{attempt['invocation_id']}.json")
            launch_id = invocation["launch_id"]
            process_path = RUNTIME / "invocation-processes" / f"{launch_id}.json"
            finish_path = RUNTIME / "supervisor-finishes" / f"{launch_id}.json"
            if not process_path.exists() or not finish_path.exists():
                continue
            process, finish = verified(process_path), verified(finish_path)
            stored = verified(RUNTIME / "attempt-records" / f"{row['attempt_id']}.json")
            setup = verified(RUNTIME / "ledger/settlements" / f"{row['session_id']}.json")
            if (process["launch_id"] != launch_id
                    or process["invocation_id"] != attempt["invocation_id"]
                    or process["exit_code"] in (None, 0)
                    or not orig.finite_number(process["finished_at"])
                    or process["finished_at"] < attempt["started_at"]
                    or finish["state"] != "needs_attention"
                    or attempt["job_id"] != frozen["id"]
                    or attempt["session_id"] != row["session_id"]
                    or stored != row or setup["status"] != "loaded"):
                fail("Terminal unknown sparse result lacks failed-process evidence")
            result.append(row)
            continue
        attempt = verified(RUNTIME / "ledger/reservations" / f"{row['attempt_id']}.json")
        receipt = verified(receipt_path)
        setup = verified(RUNTIME / "ledger/settlements" / f"{row['session_id']}.json")
        if (attempt["job_id"] != frozen["id"] or attempt["session_id"] != row["session_id"]
                or receipt["status"] != "completed" or receipt["record_sha256"] != digest(row)
                or setup["status"] != "loaded"):
            fail("Sparse result/ledger link changed")
        result.append(row)
    return result


def _mask_payload(plan, rows):
    if len(rows) != 228:
        fail("All direct outputs must settle before eligibility")
    selected = sparse.eligibility(rows, plan["direct_jobs"], plan["threshold"])
    return {"plan_sha256": digest(plan), "direct_records_sha256": digest(rows),
            "threshold": plan["threshold"], "direct_question_count": 228,
            "eligible_question_ids": selected, "eligible_count": len(selected),
            "eligible_thinking_job_ids": [j["id"] for j in plan["thinking_jobs"]
                                          if j["question_id"] in selected],
            "gold_free": True, "no_reference_access": True}


def read_mask(plan):
    mask = verified(RUNTIME / "eligibility.json")
    rows = completed_rows(plan, "direct")
    frozen_at = mask.get("frozen_at")
    expected = _mask_payload(plan, rows)
    if (not orig.finite_number(frozen_at) or frozen_at < plan["prepared_at"]
            or {k: v for k, v in mask.items() if k != "frozen_at"} != expected):
        fail("Immutable sparse eligibility changed")
    for row in rows:
        receipt_path = RUNTIME / "ledger/settlements" / f"{row['attempt_id']}.json"
        if receipt_path.exists():
            evidence_at = verified(receipt_path)["finished_at"]
        else:
            reservation = verified(RUNTIME / "ledger/reservations" / f"{row['attempt_id']}.json")
            invocation = verified(RUNTIME / "invocations" / f"{reservation['invocation_id']}.json")
            process = verified(RUNTIME / "invocation-processes" / f"{invocation['launch_id']}.json")
            evidence_at = process["finished_at"]
        if not orig.finite_number(evidence_at) or evidence_at > frozen_at:
            fail("Eligibility was frozen before direct completion evidence")
    return mask


def freeze_mask(plan):
    if (RUNTIME / "eligibility.json").exists():
        return read_mask(plan)
    if (RUNTIME / "collection-end.json").exists():
        fail("Collection closed before sparse eligibility")
    try:
        mask = _mask_payload(plan, completed_rows(plan, "direct"))
    except ValueError as error:
        if "more than 32 eligible" in str(error):
            raise ResourceStop(str(error)) from error
        raise
    mask["frozen_at"] = time.time()
    _write(RUNTIME / "eligibility.json", mask)
    return mask


def progress(plan):
    mask = read_mask(plan) if (RUNTIME / "eligibility.json").exists() else None
    tally = usage(plan, validated_mask=mask)
    direct_count = 228 if mask else len(completed_rows(plan, "direct"))
    thinking_rows = completed_rows(plan, "thinking")
    thinking_count = len(thinking_rows)
    if mask is None and thinking_count:
        fail("Thinking result preceded eligibility")
    if mask is not None and any(row["job"]["question_id"] not in mask["eligible_question_ids"]
                                for row in thinking_rows):
        fail("Unselected thinking result")
    return tally | {"direct_completed": direct_count, "direct_expected": 228,
                    "thinking_completed": thinking_count,
                    "thinking_expected": mask["eligible_count"] if mask else None,
                    "eligible": mask["eligible_count"] if mask else None,
                    "stage": "thinking" if mask else "direct"}


def status(state, plan, **extra):
    try:
        counts = progress(plan)
    except BaseException as error:
        if state != "needs_attention":
            raise
        counts = {"integrity_error": f"{type(error).__name__}: {error}"}
    atomic_json(RUNTIME / "status.json", envelope({"state": state,
        "plan_sha256": digest(plan), "progress": counts, "updated_at": time.time(),
        "automatic_resume": False, "cloud_spend_usd": 0, **extra}))


def reserve(plan, kind, invocation_id, *, job=None, session_id=None, before_active=None):
    if (RUNTIME / "collection-end.json").exists():
        fail("Sparse collection already closed")
    tally = usage(plan)
    remaining = SPEC["global_seconds"] - tally["budget_seconds"]
    amount = 0 if job is None else job.max_tokens
    if (remaining <= 0 or tally["charged_tokens"] + amount > SPEC["global_tokens"]
            or kind == "setup" and tally["setup_reservations"] >= SPEC["maximum_setups"]):
        raise orig.BudgetExhausted("Sparse global budget cannot admit operation")
    if job is not None:
        frozen = _jobs(plan).get(job.id)
        if frozen != job.to_dict() or (RUNTIME / "results" / f"{job.id}.json").exists():
            fail("Sparse job unknown or already complete")
        attempts = [r for r in _all("ledger/reservations").values()
                    if r["kind"] == "job" and r["job_id"] == job.id]
        if len(attempts) >= 2 or any(r["invocation_id"] == invocation_id for r in attempts):
            fail("Sparse job cannot retry within invocation or beyond explicit resume")
        if job.mode == "thinking":
            if job.question_id not in read_mask(plan)["eligible_question_ids"]:
                fail("Unselected thinking job")
        elif (RUNTIME / "eligibility.json").exists():
            fail("Direct job after frozen eligibility")
    row = {"id": uuid.uuid4().hex, "plan_sha256": digest(plan),
        "invocation_id": invocation_id, "kind": kind, "started_at": time.time(),
        "reserved_tokens": amount, "reserved_seconds": min(remaining,
            SPEC["setup_seconds"] if kind == "setup" else SPEC["job_seconds"])}
    if job is not None:
        row.update(job_id=job.id, session_id=session_id)
    _write(RUNTIME / "ledger/reservations" / f"{row['id']}.json", row)
    if before_active is not None:
        before_active(row)
    atomic_json(RUNTIME / "active.json", envelope(row))
    return row


def anchored_reserve(plan, kind, invocation_id, *, job=None, session_id=None):
    before = time.monotonic()
    def anchor(row):
        _write(RUNTIME / "anchors" / f"{row['id']}.json", {"id": row["id"],
            "reservation_sha256": digest(row), "monotonic_before_reserve": before,
            "pid": os.getpid(), "invocation_id": invocation_id})
    return reserve(plan, kind, invocation_id, job=job, session_id=session_id,
                   before_active=anchor)


def settle(reservation, state, began, *, tokens=None, record=None):
    charged = reservation["reserved_tokens"] if tokens is None else tokens
    receipt = {"id": reservation["id"], "reservation_sha256": digest(reservation),
        "status": state, "charged_tokens": charged,
        "elapsed_seconds": time.monotonic() - began, "finished_at": time.time()}
    if record is not None:
        receipt["record_sha256"] = digest(record)
    _write(RUNTIME / "ledger/settlements" / f"{reservation['id']}.json", receipt)
    atomic_json(RUNTIME / "active.json", envelope({"kind": "idle"}))
    return receipt


def authenticate_collector(invocation_id):
    plan, protocol, child = read_plan(verify_inputs=False)
    binding = verified(RUNTIME / "invocations" / f"{invocation_id}.json")
    launch = verified(RUNTIME / "launches" / f"{binding['launch_id']}.json")
    parent = verified(RUNTIME / "supervisor-starts" / f"{binding['launch_id']}.json")
    if (binding != {"invocation_id": invocation_id, "launch_id": launch["launch_id"],
            "plan_sha256": digest(plan), "supervisor_pid": os.getppid()}
            or parent["pid"] != os.getppid() or parent["launch_id"] != launch["launch_id"]
            or launch["plan_sha256"] != digest(plan)
            or (RUNTIME / "supervisor-finishes" / f"{launch['launch_id']}.json").exists()):
        fail("Private sparse collector is not bound to live supervisor")
    return plan, protocol, child, launch


def collect(invocation_id):
    plan, protocol, child, _ = authenticate_collector(invocation_id)
    with run_lock(RUNTIME / "collection"):
        _write(RUNTIME / "invocation-starts" / f"{invocation_id}.json", {
            "invocation_id": invocation_id, "pid": os.getpid(), "started_at": time.time()})
        setup_began = time.monotonic()
        session = anchored_reserve(plan, "setup", invocation_id)
        _write(RUNTIME / "invocation-ready" / f"{invocation_id}.json", {
            "invocation_id": invocation_id, "session_id": session["id"], "ready_at": time.time()})
        try:
            checked_plan, protocol, child = read_plan()
            if digest(checked_plan) != digest(plan):
                fail("Sparse plan changed after setup reservation")
            arm = protocol["arm"]
            config = orig.from_dict(arm["config"])
            for path, sha in arm["asset_file_sha256"].items():
                if file_hash(path) != sha:
                    fail("Pinned 0.6B model asset changed")
            engine = orig.TransformersBackend(config)
            if engine.metadata != arm["backend_metadata"]:
                fail("Pinned 0.6B backend metadata changed")
            engine.load()
            if hasattr(engine, "_sync"):
                engine._sync()
            if time.monotonic() - setup_began > session["reserved_seconds"]:
                raise orig.BudgetExhausted("Sparse model setup exceeded reservation")
        except BaseException:
            settle(session, "failed", setup_began, tokens=0)
            raise
        receipt = settle(session, "loaded", setup_began, tokens=0)
        if receipt["elapsed_seconds"] > session["reserved_seconds"]:
            raise orig.BudgetExhausted("Sparse model setup exceeded reservation")
        questions = {r["child_question"]["id"]: Question(**r["child_question"])
                     for r in child["selected"]}
        def run_job(frozen):
            job = GenerationJob(**frozen)
            began = time.monotonic()
            attempt = anchored_reserve(plan, "job", invocation_id, job=job, session_id=session["id"])
            row = {"plan_sha256": digest(plan),
                "question_protocol_sha256": plan["question_protocol_sha256"],
                "implementation_sha256": plan["generation_implementation_sha256"],
                "job": frozen, "status": "failed", "result": None,
                "attempt_id": attempt["id"], "session_id": session["id"]}
            tokens, error = None, None
            try:
                result = engine.generate(questions[job.question_id], job,
                                         began + attempt["reserved_seconds"])
                row["result"] = result.to_dict()
                tokens = orig.validate_result(result, job)
                if result.termination == "timeout":
                    raise RuntimeError("Sparse generation deadline reached")
                if time.monotonic() - began > attempt["reserved_seconds"]:
                    raise orig.BudgetExhausted("Sparse generation exceeded reservation")
                row["status"] = "completed"
            except BaseException as exc:
                error = exc
                row["error"] = f"{type(exc).__name__}: {exc}"
            _write(RUNTIME / "attempt-records" / f"{attempt['id']}.json", row)
            if row["status"] == "completed":
                _write(RUNTIME / "results" / f"{job.id}.json", row)
            settle(attempt, row["status"], began, tokens=tokens, record=row)
            status("collecting", plan, invocation_id=invocation_id)
            print(f"sparse {job.mode} {job.question_id} {row['status']}", flush=True)
            if error is not None:
                raise error
        for frozen in plan["direct_jobs"]:
            if not (RUNTIME / "results" / f"{frozen['id']}.json").exists():
                run_job(frozen)
        mask = freeze_mask(plan)
        for frozen in plan["thinking_jobs"]:
            if (frozen["question_id"] in mask["eligible_question_ids"]
                    and not (RUNTIME / "results" / f"{frozen['id']}.json").exists()):
                run_job(frozen)
        return progress(plan)


def private_collector(invocation_id):
    authenticate_collector(invocation_id)  # Wrong PID cannot write a finish record.
    with run_lock(RUNTIME / "collector-entry"):
        if ((RUNTIME / "invocation-starts" / f"{invocation_id}.json").exists()
                or (RUNTIME / "invocation-finishes" / f"{invocation_id}.json").exists()):
            fail("Sparse private collector invocation already used")
        try:
            from scripts.macos_runtime_guard import user_activity
            with user_activity():
                result = collect(invocation_id)
            _write(RUNTIME / "invocation-finishes" / f"{invocation_id}.json", {
                "state": "complete", "progress": result})
            return 0
        except BaseException as error:
            kind = ("budget" if isinstance(error, orig.BudgetExhausted) else
                    "resource" if "more than 32 eligible" in str(error) else
                    "integrity" if isinstance(error, (ValueError, orig.IntegrityError)) else "runtime")
            _write(RUNTIME / "invocation-finishes" / f"{invocation_id}.json", {
                "state": "stopped", "failure_kind": kind,
                "reason": f"{type(error).__name__}: {error}"})
            print(f"Sparse collector stopped: {type(error).__name__}: {error}", flush=True)
            return 1


def _stop(process):
    if process is not None and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def monitor(process, plan, invocation_id, began, telemetry):
    missing_id, missing_since, last_status = None, None, began - 10
    while process.poll() is None:
        now = time.monotonic()
        ready = RUNTIME / "invocation-ready" / f"{invocation_id}.json"
        if not ready.exists() and now - began > SPEC["setup_seconds"]:
            raise RuntimeError("Sparse collector startup watchdog reached")
        tally = usage(plan)
        if (tally["budget_seconds"] > SPEC["global_seconds"]
                or tally["charged_tokens"] > SPEC["global_tokens"]):
            raise orig.BudgetExhausted("Sparse global wall/token budget reached")
        active_path = RUNTIME / "active.json"
        if active_path.exists():
            active = verified(active_path)
            if active.get("kind") != "idle":
                if active["invocation_id"] != invocation_id:
                    try:
                        prior = verified(RUNTIME / "invocations" / f"{active['invocation_id']}.json")
                        prior_launch = prior["launch_id"]
                        previous_process = verified(RUNTIME / "invocation-processes" / f"{prior_launch}.json")
                        previous_finish = verified(RUNTIME / "supervisor-finishes" / f"{prior_launch}.json")
                    except (FileNotFoundError, KeyError, ValueError) as error:
                        fail(f"Sparse active operation has unknown prior owner: {error}")
                    if (prior["invocation_id"] != active["invocation_id"]
                            or prior["plan_sha256"] != digest(plan)
                            or previous_process["invocation_id"] != active["invocation_id"]
                            or previous_process["launch_id"] != prior_launch
                            or previous_process["exit_code"] in (None, 0)
                            or previous_finish["state"] != "needs_attention"):
                        fail("Sparse active operation belongs to unknown live collector")
                    active = {"kind": "idle"}  # Prior charge remains in the ledger.
            if active.get("kind") != "idle":
                anchor_path = RUNTIME / "anchors" / f"{active['id']}.json"
                if anchor_path.exists():
                    anchor = verified(anchor_path)
                    if (anchor["reservation_sha256"] != digest(active)
                            or anchor["pid"] != process.pid or anchor["id"] != active["id"]
                            or anchor["invocation_id"] != invocation_id):
                        fail("Sparse active monotonic anchor changed")
                    if now - anchor["monotonic_before_reserve"] > (
                            active["reserved_seconds"] + SPEC["watchdog_grace_seconds"]):
                        raise RuntimeError("Sparse monotonic operation watchdog reached")
                    missing_id, missing_since = None, None
                elif missing_id != active["id"]:
                    missing_id, missing_since = active["id"], now
                elif now - missing_since > SPEC["watchdog_grace_seconds"]:
                    fail("Sparse active reservation lacks monotonic anchor")
        reading = subprocess.run(["/bin/ps", "-o", "rss=", "-p", str(process.pid)],
            capture_output=True, text=True, timeout=5)
        if reading.returncode == 0 and reading.stdout.strip():
            telemetry["maximum_polled_rss_bytes"] = max(telemetry["maximum_polled_rss_bytes"],
                int(reading.stdout.strip()) * 1024)
            telemetry["rss_samples"] += 1
        elif process.poll() is None:
            raise RuntimeError("Sparse child RSS telemetry unavailable")
        if telemetry["maximum_polled_rss_bytes"] > SPEC["maximum_polled_rss_bytes"]:
            raise RuntimeError("Sparse sampled RSS ceiling reached")
        if now - last_status >= 10:
            status("collecting", plan, child_pid=process.pid,
                   maximum_polled_rss_bytes=telemetry["maximum_polled_rss_bytes"])
            last_status = now
        time.sleep(SPEC["poll_seconds"])


def live_wall_seconds():
    start = verified(RUNTIME / "collection-start.json")
    return time.time() - start["started_at"]


def terminal_unknowns(plan):
    """Prior killed operations keep full reservations but can close on explicit resume."""
    reservations = _all("ledger/reservations")
    settlements = _all("ledger/settlements")
    unknown = [r for key, r in reservations.items() if key not in settlements]
    launches = _launch_rows(plan)
    if not launches:
        return 0
    current = launches[-1]["launch_id"]
    invocations = _all("invocations")
    for row in unknown:
        invocation = invocations[row["invocation_id"]]
        launch_id = invocation["launch_id"]
        process = verified(RUNTIME / "invocation-processes" / f"{launch_id}.json")
        finish = verified(RUNTIME / "supervisor-finishes" / f"{launch_id}.json")
        if (launch_id == current or process["exit_code"] in (None, 0)
                or process["launch_id"] != launch_id
                or process["invocation_id"] != row["invocation_id"]
                or finish["state"] != "needs_attention"):
            fail("Current or unobserved unresolved operation cannot close endpoint")
    return len(unknown)


def all_collectors_exited(plan, current_launch_id):
    invocations = _all("invocations")
    reservations = _all("ledger/reservations")
    if not invocations or len(invocations) > SPEC["maximum_invocations"]:
        fail("Sparse collector invocation coverage changed")
    latest = None
    for invocation_id, row in invocations.items():
        launch_id = row["launch_id"]
        process = verified(RUNTIME / "invocation-processes" / f"{launch_id}.json")
        finish_path = RUNTIME / "invocation-finishes" / f"{invocation_id}.json"
        finished = verified(finish_path) if finish_path.exists() else None
        no_child_launched = process["pid"] is None and process["exit_code"] is None
        if (row["plan_sha256"] != digest(plan)
                or process["launch_id"] != launch_id
                or process["invocation_id"] != invocation_id):
            fail("Sparse collector exit observation changed")
        if launch_id == current_launch_id:
            latest = process
            if process["exit_code"] != 0 or finished is None or finished["state"] != "complete":
                fail("Latest sparse collector did not exit successfully")
        else:
            supervisor_finish = verified(RUNTIME / "supervisor-finishes" / f"{launch_id}.json")
            if (not no_child_launched and process["exit_code"] in (None, 0)
                    or no_child_launched and any(r["invocation_id"] == invocation_id
                                                 for r in reservations.values())
                    or supervisor_finish["state"] != "needs_attention"
                    or finished is not None and finished["state"] != "stopped"):
                fail("Prior sparse collector terminal state changed")
    if latest is None:
        fail("Sparse finalizer lacks latest collector")
    return len(invocations)


def endpoint(plan):
    mask = read_mask(plan)
    direct = completed_rows(plan, "direct")
    thinking = completed_rows(plan, "thinking")
    if (len(direct) != 228 or len(thinking) != mask["eligible_count"]
            or {r["job"]["question_id"] for r in thinking} != set(mask["eligible_question_ids"])):
        fail("Sparse endpoint is incomplete")
    tally = usage(plan, validated_mask=mask)
    if (tally["unresolved"] != terminal_unknowns(plan)
            or tally["charged_tokens"] > SPEC["global_tokens"]
            or tally["budget_seconds"] > SPEC["global_seconds"]
            or live_wall_seconds() > SPEC["global_seconds"]):
        raise orig.BudgetExhausted("Sparse endpoint budget or settlement failed")
    return mask, direct, thinking, tally


def _score_header(plan, mask, thinking):
    return {"plan_sha256": digest(plan), "eligibility_sha256": digest(mask),
            "thinking_records_sha256": digest(thinking), "selected_sha256":
                digest(mask["eligible_question_ids"]),
            "scoring_version": "numeric-v7",
            "scoring_implementation_sha256": plan["scoring_implementation_sha256"]}


def _check_scores(scores, plan, mask, thinking):
    if any(scores.get(k) != v for k, v in _score_header(plan, mask, thinking).items()):
        fail("Sparse score sidecar identity changed")
    indexed = {row["job_id"]: row for row in scores["scores"]}
    expected = {row["job"]["id"]: row for row in thinking}
    if len(indexed) != len(scores["scores"]) or set(indexed) != set(expected):
        fail("Sparse score coverage changed")
    if (mask["eligible_count"] == 0) != (scores["gold_sha256"] is None):
        fail("Sparse selected-gold identity changed")
    for job_id, score in indexed.items():
        row = expected[job_id]
        extracted, parser_status = scoring_v7.extract_record(row)
        if (score["job_id"] != job_id or score["question_id"] != row["job"]["question_id"]
                or score["mode"] != "thinking" or score["scoring_version"] != "numeric-v7"
                or score["parser_status"] != parser_status
                or score["extracted_answer"] != extracted
                or type(score["correct"]) is not bool
                or parser_status != "ok" and score["correct"]):
            fail("Sparse cached score semantics changed")
    return indexed


def _statistics(plan, mask, thinking, scores):
    score_by_id = _check_scores(scores, plan, mask, thinking)
    outcomes = {row["job"]["question_id"]: {
        "thinking_correct": int(score_by_id[row["job"]["id"]]["correct"]),
        "thinking_tokens": sum(row["result"][k] for k in
                               ("reasoning_tokens", "answer_tokens", "inserted_tokens"))}
        for row in thinking}
    return sparse.sparse_delta(mask["eligible_question_ids"], outcomes,
                               plan["question_ids"], seed=sparse.SEED, draws=2000)


def selected_gold(plan, child, mask):
    """Called once after full endpoint; opens only M chosen upstream train answers."""
    from scripts.verify_phase2_repeat import verify
    live_plan, _, live_child = authenticate_finalizer()
    marker = verified(RUNTIME / "score-started.json")
    live_mask, _, _, _ = endpoint(live_plan)
    if (digest(live_plan) != digest(plan) or live_child != child or live_mask != mask
            or marker["plan_sha256"] != digest(plan)
            or marker["eligibility_sha256"] != digest(mask)
            or marker["selected_sha256"] != digest(mask["eligible_question_ids"])):
        fail("Sparse selected-reference callback was not authorized by full endpoint")
    verify(orig.BASE / "repeat-panel-v1")
    endpoint(live_plan)
    from datasets import Dataset
    selected = [r for r in child["selected"] if r["child_question"]["id"]
                in mask["eligible_question_ids"]]
    if len(selected) != mask["eligible_count"]:
        fail("Selected reference rows changed")
    if not selected:
        return {}
    source = child["source"]
    answers = Dataset.from_file(source["arrow_path"]).select_columns(["answer"]).select(
        [r["upstream_index"] for r in selected])["answer"]
    gold = {}
    for row, answer in zip(selected, answers):
        if "####" not in answer:
            fail("Selected training reference lacks delimiter")
        value = answer.rsplit("####", 1)[1].strip()
        scoring_v7.v5.numeric(value)
        gold[row["child_question"]["id"]] = value
    if set(gold) != set(mask["eligible_question_ids"]):
        fail("Selected-only training reference coverage changed")
    return gold


def score_endpoint(plan, child, mask, thinking):
    path = RUNTIME / "scores.numeric-v7.json"
    marker_path = RUNTIME / "score-started.json"
    if path.exists():
        cached = verified(path)
        _check_scores(cached, plan, mask, thinking)
        if mask["eligible_count"]:
            if not marker_path.exists():
                fail("Selected score cache lacks one-time reference marker")
            marker = verified(marker_path)
            if (marker["plan_sha256"] != digest(plan)
                    or marker["eligibility_sha256"] != digest(mask)
                    or marker["selected_sha256"] != digest(mask["eligible_question_ids"])):
                fail("Selected score marker changed")
        elif marker_path.exists():
            fail("Zero-eligible endpoint must not have reference marker")
        return cached
    if marker_path.exists():
        fail("Score marker exists without valid cache; references may not reopen")
    gold = {}
    if mask["eligible_count"]:
        # Do expensive preservation work before the live budget check. The
        # marker is written immediately before selected-answer access.
        read_plan()
        request = verified(RUNTIME / "finalize-request.json")
        all_collectors_exited(plan, request["launch_id"])
        endpoint(plan)
        _write(marker_path, {"plan_sha256": digest(plan),
            "eligibility_sha256": digest(mask), "selected_sha256":
                digest(mask["eligible_question_ids"]), "started_at": time.time()})
        gold = selected_gold(plan, child, mask)
    scores = [scoring_v7.score_record(row, gold[row["job"]["question_id"]])
              for row in thinking]
    artifact = _score_header(plan, mask, thinking) | {"gold_sha256": digest(gold) if gold else None,
                                                   "scores": scores}
    _check_scores(artifact, plan, mask, thinking)
    _write(path, artifact)
    return artifact


def authenticate_finalizer():
    plan, protocol, child = read_plan()
    request = verified(RUNTIME / "finalize-request.json")
    parent = verified(RUNTIME / "supervisor-starts" / f"{request['launch_id']}.json")
    if (request["plan_sha256"] != digest(plan) or parent["pid"] != os.getppid()
            or parent["launch_id"] != request["launch_id"]
            or (RUNTIME / "supervisor-finishes" / f"{request['launch_id']}.json").exists()):
        fail("Private sparse finalizer is not bound to live supervisor")
    return plan, protocol, child


def finalize():
    with run_lock(RUNTIME / "analysis"), run_lock(RUNTIME / "collection"):
        plan, _, child = authenticate_finalizer()
        mask, direct, thinking, tally = endpoint(plan)
        request = verified(RUNTIME / "finalize-request.json")
        all_collectors_exited(plan, request["launch_id"])
        if (request["eligibility_sha256"] != digest(mask)
                or request["direct_records_sha256"] != digest(direct)
                or request["thinking_records_sha256"] != digest(thinking)
                or request["charged_tokens"] != tally["charged_tokens"]
                or not (RUNTIME / "collection-end.json").exists()
                or verified(RUNTIME / "invocation-processes" / f"{request['launch_id']}.json")["exit_code"] != 0):
            fail("Sparse finalizer request or exited collector changed")
        from scripts.verify_phase2_repeat import verify
        before = verify(orig.BASE / "repeat-panel-v1")
        read_plan()
        endpoint(plan)
        report_path = RUNTIME / "report.json"
        if report_path.exists():
            report = verified(report_path)
            cached = score_endpoint(plan, child, mask, thinking)
            analysis = verified(RUNTIME / "analysis-started.json")
            if (report["plan_sha256"] != digest(plan)
                    or report["eligibility_sha256"] != digest(mask)
                    or report["scores_sha256"] != digest(cached)
                    or report["statistics"] != _statistics(plan, mask, thinking, cached)
                    or report["ledger"] != tally
                    or analysis["plan_sha256"] != digest(plan)
                    or analysis["scores_sha256"] != digest(cached)):
                fail("Sparse cached report binding changed")
            return report
        scores = score_endpoint(plan, child, mask, thinking)
        _write(RUNTIME / "analysis-started.json", {"plan_sha256": digest(plan),
            "scores_sha256": digest(scores), "started_at": time.time()})
        statistics = _statistics(plan, mask, thinking, scores)
        after = verify(orig.BASE / "repeat-panel-v1")
        read_plan()
        endpoint(plan)
        report = {"version": VERSION, "plan_sha256": digest(plan),
            "question_protocol_sha256": plan["question_protocol_sha256"],
            "prelaunch_review_sha256": digest(verified(RUNTIME / "prelaunch-review.json")),
            "eligibility_sha256": digest(mask), "scores_sha256": digest(scores),
            "statistics": statistics, "ledger": tally,
            "protected_originals_verified_before": before["protected_originals_verified"],
            "protected_originals_verified_after": after["protected_originals_verified"],
            "full_parent_study_preserved": True,
            "references_opened_for": mask["eligible_count"],
            "zero_ineligible_references": True,
            "absolute_policy_accuracy_or_utility_reported": False,
            "further_study_only": True, "cloud_spend_usd": 0}
        _write(report_path, report)
        return report


class ResourceStop(RuntimeError):
    """Frozen eligibility exceeded the explicit 32-question resource ceiling."""


def _failure_kind(error):
    if isinstance(error, orig.BudgetExhausted):
        return "budget"
    if isinstance(error, ResourceStop):
        return "resource"
    if isinstance(error, (ValueError, orig.IntegrityError)):
        return "integrity"
    return "runtime"


def supervisor(launch_id):
    os.chdir(ROOT)
    signal.signal(signal.SIGHUP, signal.SIG_IGN)
    ready_path = RUNTIME / "launch-ready" / f"{launch_id}.json"
    deadline = time.monotonic() + 30
    while not ready_path.exists():
        if time.monotonic() > deadline:
            reason = "Sparse launch handshake expired"
            atomic_json(RUNTIME / "status.json", envelope({"state": "needs_attention",
                "failure_kind": "runtime", "reason": reason, "launch_id": launch_id,
                "updated_at": time.time(), "automatic_resume": False}))
            _write(RUNTIME / "supervisor-finishes" / f"{launch_id}.json",
                   {"launch_id": launch_id, "state": "needs_attention",
                    "failure_kind": "runtime", "reason": reason})
            return 1
        time.sleep(.1)
    with run_lock(RUNTIME / "supervisor"):
        if (RUNTIME / "supervisor-starts" / f"{launch_id}.json").exists():
            fail("Sparse supervisor launch was already used")
        try:
            plan, _, _ = read_plan()
            launch = verified(RUNTIME / "launches" / f"{launch_id}.json")
            ready = verified(ready_path)
            launches = _launch_rows(plan)
            if (launch["launch_id"] != launch_id or launches[-1] != launch
                    or launch["plan_sha256"] != digest(plan) or ready["launch_id"] != launch_id
                    or ready["plan_sha256"] != digest(plan)):
                fail("Sparse supervisor launch handshake changed")
            if len(launches) == 2:
                previous = verified(RUNTIME / "supervisor-finishes" /
                                    f"{launches[0]['launch_id']}.json")
                if (previous["state"] != "needs_attention"
                        or previous["failure_kind"] != "runtime"):
                    fail("Sparse resume lacks failed prior supervisor")
        except BaseException as error:
            reason = f"{type(error).__name__}: {error}"
            atomic_json(RUNTIME / "status.json", envelope({"state": "needs_attention",
                "failure_kind": "integrity", "reason": reason, "launch_id": launch_id,
                "updated_at": time.time(), "automatic_resume": False}))
            _write(RUNTIME / "supervisor-finishes" / f"{launch_id}.json",
                   {"launch_id": launch_id, "state": "needs_attention",
                    "failure_kind": "integrity", "reason": reason})
            return 1
        _write(RUNTIME / "supervisor-starts" / f"{launch_id}.json", {
            "launch_id": launch_id, "pid": os.getpid(), "started_at": time.time()})
        try:
            with run_lock(RUNTIME / "collection"):
                if (RUNTIME / "collection-end.json").exists():
                    fail("Sparse collection already closed")
                opening = verified(RUNTIME / "collection-start.json")
                if (opening["plan_sha256"] != digest(plan)
                        or opening["started_at"] < plan["prepared_at"]):
                    fail("Sparse global wall-clock origin changed")
                if len(_all("invocations")) >= SPEC["maximum_invocations"]:
                    fail("Sparse invocation ceiling reached")
                invocation_id = uuid.uuid4().hex
                _write(RUNTIME / "invocations" / f"{invocation_id}.json", {
                    "invocation_id": invocation_id, "launch_id": launch_id,
                    "plan_sha256": digest(plan), "supervisor_pid": os.getpid()})
            status("collecting", plan, launch_id=launch_id, invocation_id=invocation_id)
            telemetry = {"rss_samples": 0, "maximum_polled_rss_bytes": 0}
            process = None
            began = time.monotonic()
            try:
                with (RUNTIME / "logs" / f"collector-{invocation_id}.log").open("x") as log:
                    process = subprocess.Popen([sys.executable, "-m", "scripts.qwen06_sparse_collect",
                        "collector", "--invocation-id", invocation_id], cwd=ROOT,
                        stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                        env=orig.native_environment())
                    monitor(process, plan, invocation_id, began, telemetry)
            finally:
                _stop(process)
                _write(RUNTIME / "invocation-processes" / f"{launch_id}.json", {
                    "launch_id": launch_id, "invocation_id": invocation_id,
                    "pid": process.pid if process else None,
                    "exit_code": process.returncode if process else None,
                    "elapsed_monotonic_seconds": time.monotonic() - began,
                    "finished_at": time.time(), **telemetry})
            if process is None or process.returncode != 0:
                finish_path = RUNTIME / "invocation-finishes" / f"{invocation_id}.json"
                if finish_path.exists():
                    finished = verified(finish_path)
                    reason = finished.get("reason", "Sparse collector stopped")
                    if finished.get("failure_kind") == "budget":
                        raise orig.BudgetExhausted(reason)
                    if finished.get("failure_kind") == "resource":
                        raise ResourceStop(reason)
                    if finished.get("failure_kind") == "integrity":
                        fail(reason)
                    raise RuntimeError(reason)
                raise RuntimeError("Sparse collector exited without terminal event")
            if not telemetry["rss_samples"]:
                raise RuntimeError("No sparse collector RSS observations")
            mask, direct, thinking, tally = endpoint(plan)
            _write(RUNTIME / "collection-end.json", {
                "plan_sha256": digest(plan), "finished_at": time.time(),
                "eligibility_sha256": digest(mask)})
            status("analyzing", plan, launch_id=launch_id)
            _write(RUNTIME / "finalize-request.json", {"plan_sha256": digest(plan),
                "launch_id": launch_id, "eligibility_sha256": digest(mask),
                "direct_records_sha256": digest(direct),
                "thinking_records_sha256": digest(thinking),
                "charged_tokens": tally["charged_tokens"], "requested_at": time.time()})
            finalizer = None
            try:
                with (RUNTIME / "logs" / f"finalize-{launch_id}.log").open("x") as log:
                    finalizer = subprocess.Popen([sys.executable, "-m", "scripts.qwen06_sparse_collect",
                        "finalize"], cwd=ROOT, stdin=subprocess.DEVNULL,
                        stdout=log, stderr=subprocess.STDOUT, env=orig.native_environment())
                    while finalizer.poll() is None:
                        if live_wall_seconds() > SPEC["global_seconds"]:
                            raise orig.BudgetExhausted("Sparse finalization global wall ceiling reached")
                        time.sleep(SPEC["poll_seconds"])
            finally:
                _stop(finalizer)
                _write(RUNTIME / "finalize-process.json", {"pid": finalizer.pid if finalizer else None,
                    "exit_code": finalizer.returncode if finalizer else None,
                    "finished_at": time.time()})
            if finalizer is None or finalizer.returncode != 0:
                fail("Sparse finalization process failed")
            report = verified(RUNTIME / "report.json")
            status("complete", plan, launch_id=launch_id, report_sha256=digest(report))
            _write(RUNTIME / "supervisor-finishes" / f"{launch_id}.json", {
                "launch_id": launch_id, "state": "complete", "report_sha256": digest(report),
                "finished_at": time.time()})
            return 0
        except BaseException as error:
            kind = _failure_kind(error)
            reason = f"{type(error).__name__}: {error}"
            status("needs_attention", plan, launch_id=launch_id,
                   failure_kind=kind, reason=reason)
            _write(RUNTIME / "supervisor-finishes" / f"{launch_id}.json", {
                "launch_id": launch_id, "state": "needs_attention", "failure_kind": kind,
                "reason": reason, "finished_at": time.time()})
            print(reason, flush=True)
            return 1


def launch(*, resume=False):
    os.chdir(ROOT)
    plan, _, _ = read_plan(check_assets=True)
    audit = verified(RUNTIME / "prelaunch-review.json")
    if audit != {"plan_sha256": digest(plan),
                  "prepared_file_sha256": digest(plan["prepared_file_sha256"]),
                  "decision": "independently_audited_allow_launch"}:
        fail("Independent sparse runtime prelaunch audit is required")
    clocks = recovery.launch_preflight()
    with run_lock(RUNTIME / "supervisor"):
        read_plan(check_assets=True)
        if verified(RUNTIME / "prelaunch-review.json") != audit:
            fail("Sparse prelaunch audit changed")
        rows = _launch_rows(plan)
        current = verified(RUNTIME / "status.json")
        if not resume:
            if rows or current["state"] != "prepared":
                fail("Initial sparse launch is one-time")
        else:
            if (len(rows) != 1 or current["state"] != "needs_attention"
                    or current.get("failure_kind") != "runtime"
                    or (RUNTIME / "collection-end.json").exists()
                    or (RUNTIME / "score-started.json").exists()):
                fail("Only one explicit runtime-failure resume is allowed")
            prior = verified(RUNTIME / "supervisor-finishes" / f"{rows[0]['launch_id']}.json")
            if prior["state"] != "needs_attention" or prior["failure_kind"] != "runtime":
                fail("Prior sparse launch is not resumable")
            tally = usage(plan)
            if (tally["charged_tokens"] >= SPEC["global_tokens"]
                    or tally["budget_seconds"] >= SPEC["global_seconds"]):
                raise orig.BudgetExhausted("Sparse global budget exhausted before resume")
        launch_id = uuid.uuid4().hex
        _write(RUNTIME / "launches" / f"{launch_id}.json", {
            "launch_id": launch_id, "plan_sha256": digest(plan),
            "reserved_at": time.time(), "explicit_resume": resume,
            "clock_preflight": clocks})
        if not resume:
            _write(RUNTIME / "collection-start.json", {"started_at": time.time(),
                "plan_sha256": digest(plan), "launch_id": launch_id})
        (RUNTIME / "logs").mkdir(exist_ok=True)
        try:
            with (RUNTIME / "logs" / f"supervisor-{launch_id}.log").open("x") as log:
                process = subprocess.Popen(["/usr/bin/caffeinate", "-s", "-i", sys.executable,
                    "-m", "scripts.qwen06_sparse_collect", "supervisor", "--launch-id", launch_id],
                    cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log,
                    stderr=subprocess.STDOUT, env=orig.native_environment(), start_new_session=True)
        except BaseException as error:
            reason = f"Launch failed: {type(error).__name__}: {error}"
            status("needs_attention", plan, launch_id=launch_id,
                   failure_kind="runtime", reason=reason)
            _write(RUNTIME / "supervisor-finishes" / f"{launch_id}.json", {
                "launch_id": launch_id, "state": "needs_attention", "failure_kind": "runtime",
                "reason": reason, "finished_at": time.time()})
            raise
        status("launched", plan, launch_id=launch_id, pid=process.pid)
    _write(RUNTIME / "launch-ready" / f"{launch_id}.json", {
        "launch_id": launch_id, "plan_sha256": digest(plan), "ready_at": time.time()})
    return {"launch_id": launch_id, "pid": process.pid,
            "log": str(RUNTIME / "logs" / f"supervisor-{launch_id}.log")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "status", "launch", "resume",
                                            "collector", "supervisor", "finalize"))
    parser.add_argument("--invocation-id")
    parser.add_argument("--launch-id")
    args = parser.parse_args()
    if args.command == "prepare":
        print(prepare())
    elif args.command == "status":
        print(verified(RUNTIME / "status.json"))
    elif args.command == "launch":
        print(launch())
    elif args.command == "resume":
        print(launch(resume=True))
    elif args.command == "collector":
        if not args.invocation_id:
            parser.error("Private invocation required")
        sys.exit(private_collector(args.invocation_id))
    elif args.command == "supervisor":
        if not args.launch_id:
            parser.error("Private launch required")
        sys.exit(supervisor(args.launch_id))
    else:
        print(finalize())


if __name__ == "__main__":
    main()
