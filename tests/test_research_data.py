import json
from pathlib import Path

import pyarrow as pa
import pyarrow.ipc as ipc
import pytest

from reasoning_budget import research_data
from reasoning_budget.data import normalized, save_dataset
from reasoning_budget.records import Question
from reasoning_budget.storage import atomic_json, digest, read_json

FIXTURE_COUNTS = {
    "bridge": 2,
    "repeat": 1,
    "acquisition_reserved": 3,
    "acquisition_external": 2,
    "validation": 1,
    "confirmation": 2,
}


def _question(prompt, split="train", source="openai/gsm8k:main"):
    identifier = f"gsm8k-train-{digest(normalized(prompt))[:20]}"
    return Question(identifier, source, split, prompt)


def _write_arrow(path, prompts):
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.table(
        {
            "question": prompts,
            "answer": ["SECRET_GOLD_SENTINEL" for _ in prompts],
        }
    )
    with pa.OSFile(str(path), "wb") as sink, ipc.new_stream(sink, table.schema) as writer:
        writer.write_table(table)


def _make_fixture(root, prompts=None):
    artifacts = root / "artifacts"
    data_dir = artifacts / "data" / "gsm8k"
    cache_dir = root / "cache"
    learn = artifacts / "learnability" / "baselines-v1"
    probe = artifacts / "probe" / "continuation-v1"
    revision = "fixture-revision"
    reserved_prompts = [f"Reserved question {i}" for i in range(8)]
    external_prompts = [f"External question {i}" for i in range(8)]
    prompts = prompts or reserved_prompts + external_prompts
    reserved = [_question(p) for p in reserved_prompts]
    save_dataset(
        data_dir,
        reserved,
        {q.id: "7" for q in reserved},
        {
            "source": "openai/gsm8k",
            "subset": "main",
            "revision": revision,
            "seed": 1,
            "sizes": {"pilot": 0, "train": 8, "validation": 0, "test": 0},
        },
    )
    learn.mkdir(parents=True)
    probe.mkdir(parents=True)
    atomic_json(
        learn / "protocol.json",
        {
            "groups": {"train": [reserved[0].to_dict()]},
        },
    )
    atomic_json(probe / "protocol.json", {"diagnostic": [reserved[1].to_dict()]})
    prior_external = _question(external_prompts[0], split="old-confirmation")
    save_dataset(
        artifacts / "confirmation" / "old" / "data",
        [prior_external],
        {prior_external.id: "7"},
        {"source": "fixture-old"},
    )
    arrow = cache_dir / "openai___gsm8k" / "main" / "0.0.0" / revision / "gsm8k-train.arrow"
    _write_arrow(arrow, prompts)
    args = {
        "root": root / "research" / "data-efficiency-v1",
        "data_dir": data_dir,
        "artifacts": artifacts,
        "cache_dir": cache_dir,
        "learnability": learn,
        "probe": probe,
        "seed": 7,
        "counts": FIXTURE_COUNTS,
    }
    return args, arrow, reserved, external_prompts


def test_prepare_freezes_disjoint_gold_free_roles_and_load_verifies(tmp_path):
    args, arrow, reserved, external = _make_fixture(tmp_path)
    path = research_data.prepare(**args)
    payload = research_data.load_allocation(path)
    assert payload["source"]["cached_rows"] == 16
    assert payload["source"]["arrow_sha256"] == research_data._file_sha256(arrow)
    assert payload["role_counts"] == {
        "bridge": 2,
        "repeat": 1,
        "acquisition": 5,
        "validation": 1,
        "confirmation": 2,
        "reserve": 2,
    }
    records = [row for rows in payload["roles"].values() for row in rows]
    questions = [row["question"] for row in records]
    assert len({q["id"] for q in questions}) == len(questions)
    assert len({normalized(q["prompt"]) for q in questions}) == len(questions)
    assert "SECRET_GOLD_SENTINEL" not in json.dumps(payload)
    assert not any("answer" in row for row in records)
    acquisition_reserved = {
        q["question"]["prompt"] for q in payload["roles"]["acquisition"] if q["pool"] == "reserved"
    }
    assert acquisition_reserved <= {q.prompt for q in reserved[2:]}
    all_external = {
        record["question"]["prompt"]
        for role, rows in payload["roles"].items()
        if role in {"validation", "confirmation", "reserve"}
        for record in rows
    }
    all_external.update(
        record["question"]["prompt"]
        for record in payload["roles"]["acquisition"]
        if record["pool"] == "external"
    )
    assert external[0] not in all_external
    frozen = (path / "manifest.json").read_bytes()
    assert research_data.prepare(**args) == path
    assert (path / "manifest.json").read_bytes() == frozen


def test_hash_order_is_stable_when_source_rows_are_reordered():
    prompts = [f"order question {i}" for i in range(20)]
    rows = [(i, _question(prompt)) for i, prompt in enumerate(prompts)]
    forward = [q.id for _, q in research_data._hash_order(rows, seed=99)]
    reverse = [q.id for _, q in research_data._hash_order(list(reversed(rows)), seed=99)]
    assert forward == reverse


def test_normalized_prior_prompt_and_every_prior_id_are_excluded(tmp_path):
    args, _, reserved, external = _make_fixture(tmp_path)
    # A historical manifest with a distinct ID but a normalized duplicate prompt blocks it too.
    duplicate = Question("legacy-alias", "fixture", "old", f"  {external[2].upper()}  ")
    save_dataset(
        Path(args["artifacts"]) / "legacy" / "data",
        [duplicate],
        {duplicate.id: "9"},
        {"source": "fixture-legacy"},
    )
    payload = research_data.load_allocation(research_data.prepare(**args))
    assigned = {
        normalized(record["question"]["prompt"])
        for records in payload["roles"].values()
        for record in records
    }
    assert normalized(external[2]) not in assigned
    assert reserved[0].id not in {
        record["question"]["id"] for records in payload["roles"].values() for record in records
    }


def test_existing_allocation_rejects_changed_seed_or_source(tmp_path):
    args, arrow, _, _ = _make_fixture(tmp_path)
    path = research_data.prepare(**args)
    with pytest.raises(ValueError, match="frozen with different inputs"):
        research_data.prepare(**{**args, "seed": 8})
    _write_arrow(
        arrow,
        [f"Reserved question {i}" for i in range(8)]
        + [f"External question {i}" for i in range(8)]
        + ["Added source row"],
    )
    with pytest.raises(ValueError, match="Pinned upstream GSM8K training source changed"):
        research_data.prepare(**args)
    assert read_json(path / "manifest.json")["checksum"]


def test_load_allocation_detects_manifest_tampering(tmp_path):
    args, _, _, _ = _make_fixture(tmp_path)
    path = research_data.prepare(**args)
    manifest = read_json(path / "manifest.json")
    manifest["payload"]["roles"]["bridge"][0]["question"]["prompt"] = "tampered"
    atomic_json(path / "manifest.json", manifest)
    with pytest.raises(ValueError, match="checksum mismatch"):
        research_data.load_allocation(path)


def test_load_rejects_reenveloped_source_index_and_role_boundary_tampering(tmp_path):
    args, _, _, _ = _make_fixture(tmp_path)
    path = research_data.prepare(**args)
    manifest_path = path / "manifest.json"
    original = read_json(manifest_path)

    bad_index = json.loads(json.dumps(original))
    first = bad_index["payload"]["roles"]["bridge"][0]
    first["upstream_index"] = (first["upstream_index"] + 1) % 16
    bad_index["checksum"] = digest(bad_index["payload"])
    atomic_json(manifest_path, bad_index)
    with pytest.raises(ValueError, match="does not match pinned source row"):
        research_data.load_allocation(path)

    bad_role = json.loads(json.dumps(original))
    first = bad_role["payload"]["roles"]["bridge"][0]
    first["question"]["split"] = "reserve"
    bad_role["payload"]["role_question_sha256"]["bridge"] = digest(
        [row["question"] for row in bad_role["payload"]["roles"]["bridge"]]
    )
    bad_role["checksum"] = digest(bad_role["payload"])
    atomic_json(manifest_path, bad_role)
    with pytest.raises(ValueError, match="invalid role or source"):
        research_data.load_allocation(path)


def test_load_rejects_reenveloped_pool_swap_between_reserved_and_external(tmp_path):
    args, _, _, _ = _make_fixture(tmp_path)
    path = research_data.prepare(**args)
    manifest_path = path / "manifest.json"
    manifest = read_json(manifest_path)
    bridge = manifest["payload"]["roles"]["bridge"][0]
    acquisition = next(
        row for row in manifest["payload"]["roles"]["acquisition"] if row["pool"] == "external"
    )
    bridge_question, acquisition_question = bridge["question"], acquisition["question"]
    bridge["question"] = {**acquisition_question, "split": "bridge"}
    bridge["pool"] = "reserved"
    acquisition["question"] = {**bridge_question, "split": "acquisition"}
    acquisition["pool"] = "external"
    for record in (bridge, acquisition):
        record["group_id"] = record["question"]["id"]
        record["normalized_prompt_sha256"] = digest(normalized(record["question"]["prompt"]))
    payload = manifest["payload"]
    payload["role_question_sha256"]["bridge"] = digest(
        [row["question"] for row in payload["roles"]["bridge"]]
    )
    payload["role_question_sha256"]["acquisition"] = digest(
        [row["question"] for row in payload["roles"]["acquisition"]]
    )
    manifest["checksum"] = digest(payload)
    atomic_json(manifest_path, manifest)
    with pytest.raises(
        ValueError, match="Reserved role question is outside original reserved train"
    ):
        research_data.load_allocation(path)


def test_load_rejects_new_historical_manifest_and_invalid_seeds(tmp_path):
    args, _, _, _ = _make_fixture(tmp_path)
    path = research_data.prepare(**args)
    with pytest.raises(ValueError, match="Historical dataset/run manifest inventory changed"):
        save_dataset(
            Path(args["artifacts"]) / "later" / "data",
            [Question("new-id", "fixture", "old", "new historical prompt")],
            {"new-id": "3"},
            {"source": "later"},
        )
        research_data.load_allocation(path)
    for seed in (-1, True, 1.5):
        with pytest.raises(ValueError, match="nonnegative integer"):
            research_data.prepare(**{**args, "seed": seed})
