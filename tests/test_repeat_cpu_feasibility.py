"""Synthetic-only leakage, accounting and immutable-plan checks."""

from copy import deepcopy

import numpy as np
import pytest
from threadpoolctl import threadpool_limits

from reasoning_budget.storage import atomic_json, digest, envelope, run_lock
from scripts import repeat_cpu_feasibility as cpu


@pytest.fixture(autouse=True)
def one_cpu_thread():
    with threadpool_limits(limits=1):
        yield


@pytest.fixture
def mock_preflight(monkeypatch):
    monkeypatch.setattr(cpu, "parser_preflight", lambda _: {"payload_sha256": "fixture-preflight"})


def panel(n=20):
    rng = np.random.default_rng(44)
    ids = [f"fixture-{i}" for i in range(n)]
    q = rng.normal(size=(n, 387))
    z = rng.normal(size=(n, 8, 4))
    z[:, :, 2:] = rng.integers(0, 2, (n, 8, 2))
    d = np.zeros((n, 8, 3))
    t = np.zeros_like(d)
    d[:, :, 0] = rng.integers(0, 2, (n, 8))
    t[:, :, 0] = rng.integers(0, 2, (n, 8))
    d[:, :, 1:] = [100, 2]
    t[:, :, 1:] = [500, 8]
    return ids, q, d, t, z, {qid: i % 5 for i, qid in enumerate(ids)}


def fold(data):
    ids, q, d, t, z, folds = data
    train = np.array([i for i, qid in enumerate(ids) if folds[qid] != 0])
    test = np.array([i for i, qid in enumerate(ids) if folds[qid] == 0])
    gain = t[:, :, 0] - d[:, :, 0] - 0.05 * t[:, :, 1] / 1000
    return cpu.new_fold(q, z, d, t, gain, train, test, [0, 1, 2, 3], [4, 5, 6, 7], 20261002)


def test_new_fold_ignores_opposite_half_and_all_heldout_labels():
    data = panel()
    original_actions, original_detail = fold(data)
    ids, q, d, t, z, folds = data
    changed_d, changed_t = d.copy(), t.copy()
    changed_d[:, 4:, 0] = 1 - changed_d[:, 4:, 0]
    changed_t[:, 4:, 0] = 1 - changed_t[:, 4:, 0]
    changed_t[:, 4:, 1:] *= 10
    heldout = [i for i, qid in enumerate(ids) if folds[qid] == 0]
    changed_d[heldout, :, 0] = 1 - changed_d[heldout, :, 0]
    changed_t[heldout, :, 0] = 1 - changed_t[heldout, :, 0]
    changed_actions, changed_detail = fold((ids, q, changed_d, changed_t, z, folds))
    assert original_detail == changed_detail
    for key in original_actions:
        np.testing.assert_array_equal(original_actions[key], changed_actions[key])
    for split in original_detail["inner_splits"]:
        assert set(split["training_indices"]).isdisjoint(split["validation_indices"])
        assert set(split["training_indices"]).isdisjoint(heldout)
        assert split["training_pairs"] == 4 * len(split["training_indices"])


def test_pca_and_scalers_fit_unique_training_questions_and_training_draws():
    _, q, _, _, z, _ = panel()
    train, draws = np.arange(12), [0, 1, 2, 3]
    fitted = cpu.Representation("compressed", q, z, train, draws)
    np.testing.assert_allclose(fitted.pca.mean_, q[train, :384].mean(0))
    np.testing.assert_allclose(fitted.lex_scaler.mean_, q[train, 384:].mean(0))
    np.testing.assert_allclose(fitted.z_scaler.mean_, z[np.ix_(train, draws)].reshape(-1, 4).mean(0))
    assert fitted.pca.n_samples_ == 12
    changed_q, changed_z = q.copy(), z.copy()
    changed_q[12:] = 1000
    changed_z[12:] = 1000
    changed_z[:, 4:] = 1000
    changed = cpu.Representation("compressed", changed_q, changed_z, train, draws)
    np.testing.assert_array_equal(fitted.pca.components_, changed.pca.components_)
    np.testing.assert_array_equal(fitted.z_scaler.mean_, changed.z_scaler.mean_)
    x = fitted.transform(q, z, train, draws).reshape(12, 4, 15)
    np.testing.assert_allclose(x[:, 0, :11], x[:, 3, :11])
    # Every standardized block has total second moment one.
    assert np.mean(x[:, :, :8] ** 2) == pytest.approx(1 / 8)
    assert np.mean(x[:, :, 8:11] ** 2) == pytest.approx(1 / 3)
    assert np.mean(x[:, :, 11:] ** 2) == pytest.approx(1 / 4)


def test_correction_keeps_confidence_below_absolute_margin():
    confidence = np.array([[True, False, True, False]])
    predicted = np.array([[0.01, 0.04, -0.05, 0.08]])
    assert cpu.correction(confidence, predicted, 0.02, 0.05).tolist() == [[True, False, False, True]]


def test_historical_actions_must_match_each_cached_question_and_policy():
    ids = ["fixture-a", "fixture-b"]
    actions = {name: np.array([[False, True], [True, False]]) for name in
               ("accept", "escalate", "confidence", "solver_only", "combined")}
    primary = {"statistics": {"conditions": {"k4_A_to_B": {"per_question": {
        qid: {"policies": {name: {"decisions": actions[name][i].tolist()} for name in actions}}
        for i, qid in enumerate(ids)}}}}}
    cpu.verify_historical(primary, "k4_A_to_B", ids, [0, 1], actions)
    primary["statistics"]["conditions"]["k4_A_to_B"]["per_question"][ids[1]]["policies"]["combined"]["decisions"][0] = False
    with pytest.raises(ValueError, match="Historical action reproduction"):
        cpu.verify_historical(primary, "k4_A_to_B", ids, [0, 1], actions)


def test_action_accounting_charges_direct_and_only_selected_thinking():
    ids = ["fixture-a", "fixture-b"]
    d, t = np.zeros((2, 8, 3)), np.zeros((2, 8, 3))
    d[:, :, 1:] = [100, 2]
    t[:, :, 1:] = [500, 8]
    d[0, :, 0] = t[1, :, 0] = 1
    actions = {"confidence": np.zeros((2, 2), dtype=bool),
               "candidate": np.array([[True, False], [True, False]])}
    rows = {qid: {"policies": {}} for qid in ids}
    for name, decision in actions.items():
        measured = cpu.historical._rows(d, t, np.arange(2), [0, 1], decision, 0.05)
        for i, qid in enumerate(ids):
            rows[qid]["policies"][name] = {metric: float(value[i]) for metric, value in measured.items()} | {"decisions": decision[i].tolist()}
    result = cpu.summarize(ids, rows, d, t, [0, 1])["candidate"]
    assert result["mean_tokens"] == 350
    assert result["mean_seconds"] == 6
    assert result["mean_accuracy"] == 0.5
    assert result["mean_utility"] == pytest.approx(0.4825)
    assert result["positive_gain_escalations"] == 1
    assert result["nonpositive_gain_escalations"] == 1
    assert result["harmful_escalations"] == 1
    assert result["missed_positive_gain_opportunities"] == 1
    assert result["pairs"] == 4
    assert result["delta_vs_confidence"]["mean"] == pytest.approx(-0.0125)


def test_plan_bound_matches_all_fixed_fits_and_prepare_never_fits(monkeypatch, tmp_path, mock_preflight):
    identity = {"records_sha256": "fixture-records"}
    monkeypatch.setattr(cpu, "load_inputs", lambda _: (None, None, identity))
    monkeypatch.setattr(cpu, "analyze", lambda *_: pytest.fail("Prepare fitted a model"))
    plan = cpu.prepare(tmp_path / "study", tmp_path / "output")
    bound = plan["fit_bound"]
    assert bound["outer_fits"] * sum(bound[name] for name in
        ("historical_ridge_per_outer", "new_inner_ridge_per_outer", "new_outer_ridge_per_outer")) == cpu.SPEC["maximum_ridge_fits"]
    assert bound["outer_fits"] * bound["pca_per_outer"] == cpu.SPEC["maximum_pca_fits"]
    assert cpu.prepare(tmp_path / "study", tmp_path / "output") == plan
    identity["records_sha256"] = "changed"
    with pytest.raises(ValueError, match="identity changed"):
        cpu.prepare(tmp_path / "study", tmp_path / "output")


def test_run_requires_frozen_plan_and_exact_input_identity_before_fit(monkeypatch, tmp_path, mock_preflight):
    output = tmp_path / "out"
    monkeypatch.setattr(cpu, "analyze", lambda *_: pytest.fail("Guard failed before fit"))
    with pytest.raises(ValueError, match="Prepare and freeze"):
        cpu.run(tmp_path / "study", output)
    monkeypatch.setattr(cpu, "load_inputs", lambda _: (None, None, {"records": "A"}))
    cpu.prepare(tmp_path / "study", output)
    monkeypatch.setattr(cpu, "load_inputs", lambda _: (None, None, {"records": "B"}))
    with pytest.raises(ValueError, match="identity changed"):
        cpu.run(tmp_path / "study", output)


def test_cached_report_is_returned_without_refit_and_lock_blocks_writer(monkeypatch, tmp_path, mock_preflight):
    output = tmp_path / "out"
    monkeypatch.setattr(cpu, "load_inputs", lambda _: (None, None, {"records": "A"}))
    plan = cpu.prepare(tmp_path / "study", output)
    report = {"plan_sha256": digest(plan), "fixture": True}
    atomic_json(output / "report.json", envelope(report))
    monkeypatch.setattr(cpu, "analyze", lambda *_: pytest.fail("Existing output was refitted"))
    assert cpu.run(tmp_path / "study", output) == report
    with run_lock(output):
        with pytest.raises(ValueError, match="holds the run lock"):
            cpu.run(tmp_path / "study", output)
    corrupted = deepcopy(report) | {"plan_sha256": "another-plan"}
    atomic_json(output / "report.json", envelope(corrupted))
    with pytest.raises(ValueError, match="another plan"):
        cpu.run(tmp_path / "study", output)


def test_output_cannot_write_into_frozen_study(tmp_path):
    for target in (tmp_path, tmp_path / "new-child"):
        with pytest.raises(ValueError, match="outside the frozen study"):
            cpu.prepare(tmp_path, target)
        with pytest.raises(ValueError, match="outside the frozen study"):
            cpu.run(tmp_path, target)


def test_incomplete_endpoint_never_opens_cached_scores(monkeypatch, tmp_path):
    monkeypatch.setattr(cpu.diagnosis, "read_protocol", lambda _: {"snapshot": {"jobs": [{}] * 800}})
    monkeypatch.setattr(cpu.diagnosis, "checked_run", lambda *_: ({}, [{"status": "completed"}] * 799))
    monkeypatch.setattr(cpu, "verified", lambda *_: pytest.fail("Score opened before endpoint"))
    with pytest.raises(ValueError, match="all 800"):
        cpu.load_inputs(tmp_path)


def test_full_fixed_grid_instrumented_fit_counts_and_family_reporting(monkeypatch):
    counts = {"ridge": 0, "pca": 0}
    original_ridge, original_pca = cpu.Ridge.fit, cpu.PCA.fit

    def ridge(self, *args, **kwargs):
        counts["ridge"] += 1
        return original_ridge(self, *args, **kwargs)

    def pca(self, *args, **kwargs):
        counts["pca"] += 1
        return original_pca(self, *args, **kwargs)

    monkeypatch.setattr(cpu.Ridge, "fit", ridge)
    monkeypatch.setattr(cpu.PCA, "fit", pca)
    result = cpu.analyze(panel())
    assert counts == {"ridge": 1035, "pca": 75}
    assert result["fit_accounting"]["ridge_fits"] == counts["ridge"]
    assert set(result["family_average_vs_confidence"]) == {"draft4", "compressed", "correction", "selected_new"}
    for condition in result["conditions"].values():
        assert all(detail["training_pairs"] in (64, 128) for detail in condition["folds"])
        assert len(condition["summary"]) == 30
        for detail in condition["folds"]:
            assert len(detail["candidate_inner_utility"]) == 21
            settings = detail["settings"]
            assert detail["selected_family"] == max(cpu.SPEC["families"], key=lambda f: settings[f]["inner_utility"])
    assert result["promotion_screen"]["restores_primary_gate"] is False
    assert result["fit_accounting"]["router_latency_measured"] is False


def test_parser_preflight_requires_exact_completed_report(monkeypatch, tmp_path):
    payload = {"decision": "compatible_narrow_candidate_retain_v7_primary",
               "compatibility_gate_pass": True, "primary_labels": "unchanged frozen v7",
               "no_score_cache_written": True, "input_records_preserved": True}
    path = tmp_path / "parser-compatibility-v1" / "report.json"
    atomic_json(path, envelope(payload))
    monkeypatch.setattr(cpu, "PARSER_REPORT_SHA256", digest(payload))
    assert cpu.parser_preflight(tmp_path / "study")["payload_sha256"] == digest(payload)
    atomic_json(path, envelope(payload | {"input_records_preserved": False}))
    with pytest.raises(ValueError, match="Phase 2a"):
        cpu.parser_preflight(tmp_path / "study")
