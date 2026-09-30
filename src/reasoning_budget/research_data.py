"""Freeze gold-free, disjoint GSM8K roles for the Phase 1 data-efficiency study."""

import hashlib
from pathlib import Path

import yaml

from .data import check_questions, load_questions, normalized
from .records import Question
from .storage import atomic_json, digest, read_json, run_lock

DEFAULT_COUNTS = {
    "bridge": 25,
    "repeat": 50,
    "acquisition_reserved": 175,
    "acquisition_external": 1025,
    "validation": 200,
    "confirmation": 2000,
}
SCHEMA_VERSION = 1


def _file_sha256(path):
    hasher = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _protocol_payload(path):
    record = read_json(path)
    if "payload" in record and "checksum" in record:
        if digest(record["payload"]) != record["checksum"]:
            raise ValueError(f"Protocol checksum mismatch: {path}")
        return record["payload"]
    return record


def _question_rows_from_manifest(path):
    """Read question identities from dataset or run manifests, never scoring data."""
    raw = read_json(path)
    if "questions_sha256" in raw:
        return [question.to_dict() for question in load_questions(Path(path).parent)]
    payload = raw.get("payload")
    if payload is not None:
        if digest(payload) != raw.get("checksum"):
            raise ValueError(f"Run manifest checksum mismatch: {path}")
        identity = payload.get("identity", {})
        questions = identity.get("questions", [])
        if questions:
            return questions
    return []


def _inventory(artifacts, root, base_manifest):
    questions_by_id, prompt_owner, source_digests = {}, {}, {}
    base_path = Path(base_manifest).resolve()
    excluded_root = Path(root).resolve()
    for manifest_path in sorted(Path(artifacts).rglob("manifest.json")):
        resolved = manifest_path.resolve()
        if resolved.is_relative_to(excluded_root):
            continue
        rows = _question_rows_from_manifest(manifest_path)
        source_digests[str(resolved)] = _file_sha256(resolved)
        if resolved == base_path:
            # The base dataset declares the reserved candidate pool. It is not prior use.
            continue
        for row in rows:
            identifier = row.get("id")
            prompt = row.get("prompt")
            if not identifier or not isinstance(prompt, str) or not prompt.strip():
                raise ValueError(f"Invalid question identity in {manifest_path}")
            text = normalized(prompt)
            previous = questions_by_id.get(identifier)
            if previous is not None and previous != text:
                raise ValueError(f"Conflicting prior prompt for question ID {identifier}")
            if text in prompt_owner and prompt_owner[text] != identifier:
                # Keep both identities in the inventory; matching is checked by prompt too.
                pass
            questions_by_id[identifier] = text
            prompt_owner[text] = identifier
    return questions_by_id, source_digests


def _load_prior_used(learnability, probe, strict=True):
    learn_path = Path(learnability) / "protocol.json"
    probe_path = Path(probe) / "protocol.json"
    learn = _protocol_payload(learn_path)
    continuation = _protocol_payload(probe_path)
    train = learn.get("groups", {}).get("train", [])
    diagnostic = continuation.get("diagnostic", [])
    if strict and (len(train) != 50 or len(diagnostic) != 100):
        raise ValueError("Expected 50 prior training and 100 prior diagnostic questions")
    rows = train + diagnostic
    ids = {row["id"] for row in rows}
    texts = {normalized(row["prompt"]) for row in rows}
    if len(ids) != len(rows) or len(texts) != len(rows):
        raise ValueError("Prior training/diagnostic roles are not 150 unique questions")
    if strict and len(rows) != 150:
        raise ValueError("Expected 150 prior training/diagnostic questions")
    return (
        ids,
        texts,
        {
            str(learn_path.resolve()): _file_sha256(learn_path),
            str(probe_path.resolve()): _file_sha256(probe_path),
        },
    )


def _source_question(prompt, revision, split):
    from .data import normalized as normalize_prompt

    key = normalize_prompt(prompt)
    identifier = f"gsm8k-train-{digest(key)[:20]}"
    return Question(identifier, f"openai/gsm8k:main@{revision}", split, prompt)


def _hash_order(rows, seed):
    return sorted(
        rows,
        key=lambda row: digest(
            {"seed": seed, "question": {"id": row[1].id, "prompt": normalized(row[1].prompt)}}
        ),
    )


def _selection_record(row, role, pool):
    index, question = row
    question = Question(
        question.id,
        question.source,
        role,
        question.prompt,
        question.answer_type,
    )
    return {
        "question": question.to_dict(),
        "upstream_index": index,
        "normalized_prompt_sha256": digest(normalized(question.prompt)),
        "group_id": question.id,
        "pool": pool,
    }


def _validate_payload(payload):
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Unsupported research allocation schema")
    if type(payload.get("seed")) is not int or payload["seed"] < 0:
        raise ValueError("Allocation seed must be a nonnegative integer")
    roles = payload.get("roles")
    checksums = payload.get("role_question_sha256")
    if (
        not isinstance(roles, dict)
        or not isinstance(checksums, dict)
        or set(roles) != set(checksums)
    ):
        raise ValueError("Allocation role structure is invalid")
    all_ids, all_texts = set(), set()
    for role, records in roles.items():
        if digest([record["question"] for record in records]) != checksums[role]:
            raise ValueError(f"Question checksum mismatch for role {role}")
        questions = []
        for record in records:
            if set(record) != {
                "question",
                "upstream_index",
                "normalized_prompt_sha256",
                "group_id",
                "pool",
            }:
                raise ValueError("Unexpected allocation record fields")
            question = Question(**record["question"])
            text = normalized(question.prompt)
            if (
                question.split != role
                or question.source != f"openai/gsm8k:main@{payload['source']['revision']}"
            ):
                raise ValueError(f"Question has invalid role or source: {question.id}")
            allowed_pools = {
                "bridge": {"reserved"},
                "repeat": {"reserved"},
                "acquisition": {"reserved", "external"},
                "validation": {"external"},
                "confirmation": {"external"},
                "reserve": {"external"},
            }
            if role not in allowed_pools or record["pool"] not in allowed_pools[role]:
                raise ValueError(f"Question is in the wrong source pool: {question.id}")
            if type(record["upstream_index"]) is not int or not (
                0 <= record["upstream_index"] < payload["source"]["cached_rows"]
            ):
                raise ValueError(f"Question has invalid upstream row index: {question.id}")
            if record["group_id"] != question.id or record["normalized_prompt_sha256"] != digest(
                text
            ):
                raise ValueError(f"Question identity checksum mismatch: {question.id}")
            expected_id = f"gsm8k-train-{digest(text)[:20]}"
            if question.id != expected_id:
                raise ValueError(f"Question ID does not match normalized prompt: {question.id}")
            if question.id in all_ids or text in all_texts:
                raise ValueError("Allocation roles overlap by ID or normalized prompt")
            all_ids.add(question.id)
            all_texts.add(text)
            questions.append(question)
        check_questions(questions)
    expected_counts = payload.get("role_counts", {})
    if {role: len(rows) for role, rows in roles.items()} != expected_counts:
        raise ValueError("Allocation role counts do not match records")
    request = payload.get("counts_requested", {})
    expected_role_counts = {
        "bridge": request.get("bridge"),
        "repeat": request.get("repeat"),
        "acquisition": request.get("acquisition_reserved", 0)
        + request.get("acquisition_external", 0),
        "validation": request.get("validation"),
        "confirmation": request.get("confirmation"),
        "reserve": payload["eligible_pool_counts"]["external"]
        - request.get("acquisition_external", 0)
        - request.get("validation", 0)
        - request.get("confirmation", 0),
    }
    if expected_role_counts != expected_counts:
        raise ValueError("Role counts do not match the frozen allocation plan")
    acquisition_pools = {
        pool: sum(record["pool"] == pool for record in roles["acquisition"])
        for pool in ("reserved", "external")
    }
    if acquisition_pools != {
        "reserved": request.get("acquisition_reserved"),
        "external": request.get("acquisition_external"),
    }:
        raise ValueError("Acquisition pool strata do not match the frozen plan")


def _verify_live_inputs(payload):
    source = payload["source"]
    arrow_path = Path(source["arrow_path"])
    if _file_sha256(arrow_path) != source["arrow_sha256"]:
        raise ValueError("Pinned upstream GSM8K training source changed")
    base_manifest = Path(payload["base_dataset_manifest_path"])
    if _file_sha256(base_manifest) != payload["base_dataset_manifest_sha256"]:
        raise ValueError("Base GSM8K dataset manifest changed")
    current_manifest = read_json(base_manifest)
    if current_manifest["metadata"].get("revision") != source["revision"]:
        raise ValueError("Base GSM8K revision differs from the frozen allocation")
    base_questions = load_questions(base_manifest.parent)
    artifacts = Path(payload["artifact_root"])
    excluded_root = Path(payload["allocation_root"])
    inventory_questions, current_inventory = _inventory(artifacts, excluded_root, base_manifest)
    if digest(current_inventory) != payload["inventory_manifest_sha256"]:
        raise ValueError("Historical dataset/run manifest inventory changed")
    for path, checksum in payload["prior_protocols"].items():
        if _file_sha256(path) != checksum:
            raise ValueError(f"Prior allocation protocol changed: {path}")
    strict = payload["counts_requested"] == DEFAULT_COUNTS
    prior_ids, prior_texts, _ = _load_prior_used(
        Path(payload["prior_protocol_paths"]["learnability"]).parent,
        Path(payload["prior_protocol_paths"]["probe"]).parent,
        strict=strict,
    )
    generation = payload["generation_constraints"]
    config_path = Path(generation["config_path"])
    if _file_sha256(config_path) != generation["config_sha256"]:
        raise ValueError("Bridge generation configuration changed")
    base_by_id = {question.id: normalized(question.prompt) for question in base_questions}
    reserved_ids = {question.id for question in base_questions if question.split == "train"}
    base_texts = set(base_by_id.values())
    historical_texts = set(inventory_questions.values())
    historical_ids = set(inventory_questions)
    for role, records in payload["roles"].items():
        for record in records:
            question = record["question"]
            identifier, text, pool = question["id"], normalized(question["prompt"]), record["pool"]
            if identifier in prior_ids or text in prior_texts:
                raise ValueError(
                    f"Allocated question was used by prior training/diagnostic: {identifier}"
                )
            if identifier in historical_ids or text in historical_texts:
                raise ValueError(f"Allocated question overlaps historical allocation: {identifier}")
            if pool == "reserved":
                if identifier not in reserved_ids or base_by_id.get(identifier) != text:
                    raise ValueError(
                        f"Reserved role question is outside original reserved train: {identifier}"
                    )
            elif identifier in base_by_id or text in base_texts:
                raise ValueError(f"External role question overlaps base dataset: {identifier}")


def _verify_source_rows(payload):
    from datasets import Dataset

    source = payload["source"]
    dataset = Dataset.from_file(source["arrow_path"]).select_columns(["question"])
    prompts = dataset["question"]
    if len(prompts) != source["cached_rows"]:
        raise ValueError("Pinned upstream question row count changed")
    for role_rows in payload["roles"].values():
        for record in role_rows:
            index = record["upstream_index"]
            prompt = prompts[index]
            question = record["question"]
            if prompt != question["prompt"]:
                raise ValueError(f"Question prompt does not match pinned source row {index}")
            if question["id"] != f"gsm8k-train-{digest(normalized(prompt))[:20]}":
                raise ValueError(f"Question ID does not match pinned source row {index}")


def load_allocation(path):
    """Load and integrity-check the frozen allocation manifest without reading gold."""
    record = read_json(Path(path) / "manifest.json" if Path(path).is_dir() else path)
    payload = record.get("payload")
    if payload is None or digest(payload) != record.get("checksum"):
        raise ValueError("Allocation manifest checksum mismatch")
    _validate_payload(payload)
    _verify_live_inputs(payload)
    _verify_source_rows(payload)
    return payload


def prepare(
    root="artifacts/research/data-efficiency-v1",
    data_dir="artifacts/data/gsm8k",
    artifacts="artifacts",
    cache_dir=".cache/huggingface",
    learnability="artifacts/learnability/baselines-v1",
    probe="artifacts/probe/continuation-v1",
    seed=20261001,
    counts=None,
):
    """Freeze every Phase 1 GSM8K role using only upstream training questions."""
    from datasets import Dataset

    counts = dict(DEFAULT_COUNTS if counts is None else counts)
    strict_default = counts == DEFAULT_COUNTS
    if type(seed) is not int or seed < 0:
        raise ValueError("Selection seed must be a nonnegative integer")
    if set(counts) != set(DEFAULT_COUNTS) or any(
        type(n) is not int or n < 0 for n in counts.values()
    ):
        raise ValueError("Counts must specify every role as a nonnegative integer")
    root, data_dir = Path(root).resolve(), Path(data_dir).resolve()
    output = root / "allocations"
    dataset_manifest_path = data_dir / "manifest.json"
    dataset_manifest = read_json(dataset_manifest_path)
    metadata = dataset_manifest["metadata"]
    if metadata.get("source") != "openai/gsm8k" or metadata.get("subset") != "main":
        raise ValueError("Base dataset is not openai/gsm8k main")
    revision = metadata["revision"]
    arrow_path = (
        Path(cache_dir) / "openai___gsm8k" / "main" / "0.0.0" / revision / "gsm8k-train.arrow"
    ).resolve()
    if not arrow_path.is_file():
        raise FileNotFoundError(arrow_path)
    source_sha = _file_sha256(arrow_path)
    dataset = Dataset.from_file(str(arrow_path)).select_columns(["question"])
    if dataset.column_names != ["question"]:
        raise ValueError("Upstream dataset did not expose only the question column")
    prompts = dataset["question"]
    source_rows, seen_prompts, seen_ids = [], set(), set()
    for index, prompt in enumerate(prompts):
        text = normalized(prompt)
        if not text or text in seen_prompts:
            continue
        question = _source_question(prompt, revision, "train")
        if question.id in seen_ids:
            raise ValueError(f"Source question ID collision: {question.id}")
        seen_prompts.add(text)
        seen_ids.add(question.id)
        source_rows.append((index, question))
    if len(source_rows) != len(prompts):
        raise ValueError("Upstream training source contains duplicate/empty normalized prompts")

    base_questions = load_questions(data_dir)
    base_ids = {question.id for question in base_questions}
    base_texts = {normalized(question.prompt) for question in base_questions}
    reserved = [q for q in base_questions if q.split == "train"]
    if strict_default and len(reserved) != 400:
        raise ValueError("Expected the 400-question original reserved training split")
    by_source_id = {q.id: (i, q) for i, q in source_rows}
    reserved_source = []
    for q in reserved:
        if q.id not in by_source_id or normalized(q.prompt) != normalized(
            by_source_id[q.id][1].prompt
        ):
            raise ValueError(f"Reserved question does not match pinned upstream source: {q.id}")
        reserved_source.append(by_source_id[q.id])

    prior_ids, prior_texts, prior_protocol_digests = _load_prior_used(
        learnability, probe, strict=strict_default
    )
    inventory_ids, inventory_sources = _inventory(artifacts, root, dataset_manifest_path)
    # Explicitly preserve the old training and diagnostic samples even if a run manifest is missing.
    blocked_ids = set(inventory_ids) | prior_ids
    blocked_texts = set(inventory_ids.values()) | prior_texts
    reserved_candidates = [
        row
        for row in reserved_source
        if row[1].id not in prior_ids
        and row[1].id not in inventory_ids
        and normalized(row[1].prompt) not in prior_texts
        and normalized(row[1].prompt) not in set(inventory_ids.values())
    ]
    # The base data manifest is the reservation container. Other prior manifests block use.
    reserved_candidates = _hash_order(reserved_candidates, seed)
    external_candidates = [
        row
        for row in source_rows
        if row[1].id not in blocked_ids
        and normalized(row[1].prompt) not in blocked_texts
        and row[1].id not in base_ids
        and normalized(row[1].prompt) not in base_texts
    ]
    external_candidates = _hash_order(external_candidates, seed)
    expected_reserved = counts["acquisition_reserved"] + counts["bridge"] + counts["repeat"]
    if strict_default and len(reserved_candidates) != 250:
        raise ValueError(f"Expected 250 unused reserved IDs, found {len(reserved_candidates)}")
    if len(reserved_candidates) != expected_reserved:
        raise ValueError(
            f"Reserved role counts require {expected_reserved} IDs, found {len(reserved_candidates)}"
        )
    if strict_default and len(external_candidates) != 3773:
        raise ValueError(
            f"Expected 3773 unallocated external IDs, found {len(external_candidates)}"
        )
    if expected_reserved != len(reserved_candidates):
        raise ValueError("Reserved role counts must allocate the complete unused reserved pool")
    external_assigned = (
        counts["acquisition_external"] + counts["validation"] + counts["confirmation"]
    )
    if external_assigned > len(external_candidates):
        raise ValueError("External role counts exceed the available source pool")

    reserved_acquisition = reserved_candidates[counts["bridge"] + counts["repeat"] :]
    external_acquisition = external_candidates[: counts["acquisition_external"]]
    external_roles = {
        "validation": external_candidates[
            counts["acquisition_external"] : counts["acquisition_external"] + counts["validation"]
        ],
        "confirmation": external_candidates[
            counts["acquisition_external"] + counts["validation"] : external_assigned
        ],
        "reserve": external_candidates[external_assigned:],
    }
    role_counts = {
        "bridge": counts["bridge"],
        "repeat": counts["repeat"],
        "acquisition": counts["acquisition_reserved"] + counts["acquisition_external"],
        "validation": counts["validation"],
        "confirmation": counts["confirmation"],
        "reserve": len(external_candidates) - external_assigned,
    }
    role_rows = {
        "bridge": [
            _selection_record(row, "bridge", "reserved")
            for row in reserved_candidates[: counts["bridge"]]
        ],
        "repeat": [
            _selection_record(row, "repeat", "reserved")
            for row in reserved_candidates[counts["bridge"] : counts["bridge"] + counts["repeat"]]
        ],
        "acquisition": [
            *[_selection_record(row, "acquisition", "reserved") for row in reserved_acquisition],
            *[_selection_record(row, "acquisition", "external") for row in external_acquisition],
        ],
    }
    for role, rows in external_roles.items():
        role_rows[role] = [_selection_record(row, role, "external") for row in rows]
    source = {
        "dataset": "openai/gsm8k",
        "subset": "main",
        "split": "train",
        "revision": revision,
        "arrow_path": str(arrow_path),
        "arrow_sha256": source_sha,
        "cached_rows": len(prompts),
    }
    config_path = Path(__file__).resolve().parents[2] / "configs" / "research-gsm8k-v3.yaml"
    config = yaml.safe_load(config_path.read_text())
    generation_constraints = {
        "protocol": "qwen3-boxed-budget-v3",
        "config_path": str(config_path),
        "config_sha256": _file_sha256(config_path),
        "permitted_roles": ["bridge"],
        "permission_boundary": "Other roles require a later gate and frozen settings.",
        "config_snapshot": config,
    }
    payload = {
        "schema_version": SCHEMA_VERSION,
        "seed": seed,
        "selection": (
            "ascending storage.digest({seed, question:{id, normalized_prompt}}); "
            "independent of upstream row order"
        ),
        "source": source,
        "grouping": {
            "key": "question ID",
            "template_family": "unknown; the pinned source query reads only question",
        },
        "base_dataset_manifest_sha256": _file_sha256(dataset_manifest_path),
        "base_dataset_manifest_path": str(dataset_manifest_path),
        "artifact_root": str(Path(artifacts).resolve()),
        "allocation_root": str(root),
        "inventory_manifest_sha256": digest(inventory_sources),
        "inventory_manifests": inventory_sources,
        "prior_protocols": prior_protocol_digests,
        "prior_protocol_paths": {
            "learnability": str((Path(learnability) / "protocol.json").resolve()),
            "probe": str((Path(probe) / "protocol.json").resolve()),
        },
        "generation_constraints": generation_constraints,
        "excluded_ids_sha256": digest(sorted(blocked_ids)),
        "excluded_normalized_prompts_sha256": digest(sorted(blocked_texts)),
        "counts_requested": counts,
        "role_counts": role_counts,
        "eligible_pool_counts": {
            "reserved": len(reserved_candidates),
            "external": len(external_candidates),
        },
        "prompt_deduplication": {
            "normalization": "NFKC, casefold, collapse whitespace, strip",
            "source_rows": len(prompts),
            "unique_source_prompts": len(source_rows),
            "role_question_ids_unique": True,
            "role_normalized_prompts_unique": True,
        },
        "role_question_sha256": {
            role: digest([row["question"] for row in rows]) for role, rows in role_rows.items()
        },
        "roles": role_rows,
    }
    _validate_payload(payload)
    output.mkdir(parents=True, exist_ok=True)
    with run_lock(output):
        manifest_path = output / "manifest.json"
        if manifest_path.exists():
            existing = load_allocation(output)
            if existing != payload:
                raise ValueError("Allocation is frozen with different inputs; choose a new root")
            return output
        atomic_json(manifest_path, {"checksum": digest(payload), "payload": payload})
    return output
