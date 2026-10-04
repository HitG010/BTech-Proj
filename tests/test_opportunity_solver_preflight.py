import copy
import hashlib
from types import SimpleNamespace

import pytest

from reasoning_budget.records import GenerationResult
from scripts import opportunity_solver_preflight as preflight


def metadata():
    return SimpleNamespace(sha=preflight.REVISION, siblings=[
        SimpleNamespace(rfilename=name, size=10, lfs=None, blob_id="a" * 40)
        for name in preflight.FILES])


def test_inventory_pins_revision_allowlist_sizes_and_remote_objects():
    info = metadata()
    info.siblings.append(SimpleNamespace(rfilename="unwanted.bin", size=10**12))
    selected, total = preflight.inventory(info)
    assert set(selected) == set(preflight.FILES)
    assert total == 10 * len(preflight.FILES)
    info.sha = "main"
    with pytest.raises(ValueError, match="revision"):
        preflight.inventory(info)


def test_inventory_rejects_missing_unknown_and_over_budget_metadata():
    info = metadata()
    info.siblings[0].size = None
    with pytest.raises(ValueError, match="sizes"):
        preflight.inventory(info)
    info = metadata()
    info.siblings[0].size = preflight.SPEC["maximum_public_asset_bytes"] + 1
    with pytest.raises(ValueError, match="ceiling"):
        preflight.inventory(info)
    info = metadata()
    info.siblings[0].blob_id = "not-an-object"
    with pytest.raises(ValueError, match="hashes"):
        preflight.inventory(info)
    info = metadata()
    info.siblings.pop()
    with pytest.raises(ValueError, match="incomplete"):
        preflight.inventory(info)


def test_lfs_and_git_hashes_verify_actual_bytes(tmp_path):
    data = b"fixture model bytes\n"
    path = tmp_path / "model"
    path.write_bytes(data)
    sha = hashlib.sha256(data).hexdigest()
    git = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
    for algorithm, oid in (("sha256-lfs", sha), ("git-blob-sha1", git)):
        assert preflight.validate_file(path, {"bytes": len(data), "remote_object": oid,
            "algorithm": algorithm}) == sha
    with pytest.raises(ValueError, match="remote object"):
        preflight.validate_file(path, {"bytes": len(data), "remote_object": "a" * 40,
            "algorithm": "git-blob-sha1"})


def test_public_lfs_size_and_hash_are_required():
    info = metadata()
    info.siblings[-1].lfs = SimpleNamespace(size=10, sha256="b" * 64)
    selected, _ = preflight.inventory(info)
    assert selected[preflight.FILES[-1]]["algorithm"] == "sha256-lfs"
    info.siblings[-1].lfs.size = 11
    with pytest.raises(ValueError, match="LFS size"):
        preflight.inventory(info)


def test_real_record_schema_confidence_and_first_failure_boundary():
    # Use the production dataclass so stale reporting field names cannot pass.
    values = GenerationResult("7", "", "7", 20, 0, 2, 0, .2, 0, .2, 0,
        False, False, "eos", -.1, {}, -.3).to_dict()
    row = {"mode": "direct", "result": values}
    preflight.check_job(row)
    values["mean_generated_logprob_raw"] = None
    with pytest.raises(ValueError, match="confidence"):
        preflight.check_job(row)
    values["mean_generated_logprob_raw"] = -.3
    values["termination"] = "timeout"
    with pytest.raises(ValueError, match="endpoint"):
        preflight.check_job(row)


def test_synthetic_endpoint_requires_both_modes_and_caps():
    result = GenerationResult("7", "", "7", 20, 0, 2, 0, .2, 0, .2, 0,
        False, False, "eos", -.1, {}, -.3).to_dict()
    rows = [{"mode": "direct", "result": result}, {"mode": "thinking", "result": copy.deepcopy(result)}]
    rows[1]["result"].update(reasoning_tokens=32, inserted_tokens=2, forced_closure=True)
    assert preflight.check_jobs(rows) == 38
    with pytest.raises(ValueError, match="two synthetic"):
        preflight.check_jobs(rows[:1])
    rows[1]["result"]["reasoning_tokens"] = 33
    with pytest.raises(ValueError, match="endpoint"):
        preflight.check_jobs(rows)


def test_tokenizer_guard_checks_actual_eos_closure_and_budget():
    meta = {"model_revision": preflight.REVISION, "tokenizer_revision": preflight.REVISION,
        "closure_ids": [151668, 271], "closure_tokens": 2, "eos_token_ids": [151643, 151645]}
    assert preflight.check_tokenizer(meta) == 786944
    meta["closure_ids"] = [151668]
    with pytest.raises(ValueError, match="tokenizer"):
        preflight.check_tokenizer(meta)


def test_exclusive_output_and_isolated_caches_before_worker_imports(tmp_path, monkeypatch):
    path = tmp_path / "immutable.json"
    preflight.write_new(path, {"fixture": True})
    with pytest.raises(FileExistsError):
        preflight.write_new(path, {"changed": True})
    monkeypatch.setattr(preflight, "OUTPUT", tmp_path / "own")
    monkeypatch.setattr(preflight, "CACHE", tmp_path / "own/hub")
    env = preflight.child_environment()
    for name in ("HF_HOME", "HF_HUB_CACHE", "HF_XET_CACHE", "HF_ASSETS_CACHE"):
        assert env[name].startswith(str(tmp_path / "own"))
    assert env["HF_HUB_DISABLE_XET"] == "1"


def test_cache_observation_does_not_double_count_snapshot_symlinks(tmp_path, monkeypatch):
    monkeypatch.setattr(preflight, "OUTPUT", tmp_path)
    monkeypatch.setattr(preflight, "CACHE", tmp_path / "hub")
    preflight.CACHE.mkdir()
    blob = preflight.CACHE / "blob"
    blob.write_bytes(b"12345")
    (preflight.CACHE / "snapshot").symlink_to(blob)
    assert preflight.cache_size() == 5


def test_synthetic_settings_reuse_decoder_prompt_and_never_load_real_dataset():
    config = preflight.synthetic_config()
    reference = preflight.load_config(preflight.ROOT / "configs/research-repeat-v1.yaml")
    assert config.prompt_suffix == reference.prompt_suffix
    assert config.closure_text == reference.closure_text
    assert config.direct == reference.direct and config.thinking == reference.thinking
    assert config.model.name == "Qwen/Qwen3-0.6B"
    assert config.model.revision == config.model.tokenizer_revision == preflight.REVISION
    assert config.model.local_files_only and config.model.device == "mps"
    assert config.data_dir == "unused-no-dataset-loader"
    assert config.answer_tokens == config.reasoning_tokens == 32


def controller_fixture(tmp_path, monkeypatch, alive=False):
    monkeypatch.setattr(preflight, "OUTPUT", tmp_path)
    monkeypatch.setattr(preflight, "paths_checked", lambda: None)
    child = SimpleNamespace(pid=123, returncode=None if alive else 0)
    child.poll = lambda: child.returncode

    def terminate():
        child.returncode = -15

    child.terminate = terminate
    child.kill = terminate
    child.wait = lambda timeout: child.returncode
    monkeypatch.setattr(preflight.subprocess, "Popen", lambda *args, **kwargs: child)
    return child


def test_watchdog_fails_closed_on_missing_rss(tmp_path, monkeypatch):
    controller_fixture(tmp_path, monkeypatch, alive=True)
    monkeypatch.setattr(preflight.subprocess, "run", lambda *a, **k:
        SimpleNamespace(returncode=1, stdout=""))
    with pytest.raises(RuntimeError, match="stopped"):
        preflight.run_child(["fixture"], 60, "worker", monitor_rss=True)
    result = preflight.verified(tmp_path / "worker-process.json")
    assert result["reason"] == "own worker RSS telemetry unavailable"
    assert result["exit_code"] == -15


def test_watchdog_checks_final_disk_growth_after_fast_exit(tmp_path, monkeypatch):
    controller_fixture(tmp_path, monkeypatch)
    amount = preflight.SPEC["maximum_observed_cache_bytes"] + 1
    monkeypatch.setattr(preflight, "cache_size", lambda: amount)
    with pytest.raises(RuntimeError, match="stopped"):
        preflight.run_child(["fixture"], 60, "download")
    result = preflight.verified(tmp_path / "download-process.json")
    assert result["final_cache_bytes"] == result["maximum_observed_cache_bytes"] == amount
    assert result["exit_code"] == 0 and result["reason"]


def test_launch_failure_preserves_reservation_and_process_record(tmp_path, monkeypatch):
    controller_fixture(tmp_path, monkeypatch)

    def fail(*args, **kwargs):
        raise OSError("fixture launch failure")

    monkeypatch.setattr(preflight.subprocess, "Popen", fail)
    with pytest.raises(RuntimeError, match="stopped"):
        preflight.run_child(["fixture"], 60, "worker")
    result = preflight.verified(tmp_path / "worker-process.json")
    assert result["pid"] is None and result["exit_code"] is None
    assert result["reason"] == "controller aborted: OSError"
    with pytest.raises(FileExistsError):
        preflight.run_child(["fixture"], 60, "worker")


def test_worker_claim_is_one_time_even_after_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(preflight, "OUTPUT", tmp_path)
    monkeypatch.setattr(preflight, "paths_checked", lambda: None)
    preflight.write_new(tmp_path / "worker-invocation.json", {})
    preflight.claim_worker("worker", "worker-report.json")
    with pytest.raises(FileExistsError):
        preflight.claim_worker("worker", "worker-report.json")


def test_final_disk_telemetry_errors_fail_closed(tmp_path, monkeypatch):
    controller_fixture(tmp_path, monkeypatch)

    def fail():
        raise PermissionError("fixture telemetry failure")

    monkeypatch.setattr(preflight, "cache_size", fail)
    with pytest.raises(RuntimeError, match="stopped"):
        preflight.run_child(["fixture"], 60, "download")
    assert "telemetry unavailable" in preflight.verified(tmp_path / "download-process.json")["reason"]


@pytest.mark.parametrize("answer,termination", [("", "eos"), ("  ", "eos"),
    (None, "eos"), ("7", "reasoning_in_answer")])
def test_nonempty_decoded_answer_required(answer, termination):
    result = GenerationResult("7", "", "7", 20, 0, 2, 0, .2, 0, .2, 0,
        False, False, "eos", -.1, {}, -.3).to_dict()
    result.update(final_answer=answer, termination=termination)
    with pytest.raises(ValueError, match="endpoint"):
        preflight.check_job({"mode": "direct", "result": result})
