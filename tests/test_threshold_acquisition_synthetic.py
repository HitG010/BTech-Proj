"""Synthetic engineering fixtures; no study-grid performance comparisons."""

import copy
import json
from pathlib import Path

import numpy as np
import pytest

from scripts import threshold_acquisition_synthetic as g1


def pool(n=8):
    return g1.PublicPool(np.linspace(0.1, 0.9, n), np.arange(n) % 2, np.full(n, 128))


def test_spec_is_exactly_bounded_and_prospectively_named():
    assert len(g1.SETTINGS) == 8
    assert len(g1.METHODS) == 9
    assert len(g1.SPEC["synthetic_seeds"]) == 30
    assert g1.SPEC["budgets"] == [64000, 128000, 256000]
    assert g1.SPEC["primary_settings"] == ["high_noise_repeat", "threshold_cost_negative"]
    assert g1.SPEC["primary_comparators"] == ["uniform_coverage", "closest_cost_aware"]
    assert g1.SPEC["primary_mean_difference_min"] == 0.005
    assert g1.SPEC["primary_positive_pairs_min"] == 20
    assert g1.SPEC["singleton_stop_methods"] == list(g1.METHODS[3:])
    assert g1.SPEC["runtime_seconds"] == 1200 and g1.SPEC["retries"] == 0
    assert g1.SPEC["settings"]["heterogeneous_nonmonotonic"]["fixed_confidence_cuts"] == [0.25, 0.5, 0.75]


@pytest.mark.parametrize("setting", g1.SETTINGS)
def test_synthetic_generation_is_seeded_capped_and_independent_evaluation(setting):
    seed = g1.SPEC["synthetic_seeds"][0]
    public, correct, tokens = g1.generate_cache(setting, seed)
    again, other_correct, other_tokens = g1.generate_cache(setting, seed)
    evaluation, eval_correct, eval_tokens = g1.generate_cache(setting, seed, evaluation=True)
    assert public.n == 64 and evaluation.n == 512
    assert public.as_dict() == again.as_dict()
    np.testing.assert_array_equal(correct, other_correct)
    np.testing.assert_array_equal(tokens, other_tokens)
    assert correct.shape == tokens.shape == (64, 2)
    assert eval_correct.shape == eval_tokens.shape == (512, 2)
    assert set(np.unique(correct)) <= {0, 1}
    assert 1 <= tokens.min() <= tokens.max() <= 2562
    assert not correct.flags.writeable and not tokens.flags.writeable
    assert not public.confidence.flags.writeable
    assert set(public.state_ids).isdisjoint(evaluation.state_ids)
    assert not np.array_equal(public.confidence, evaluation.confidence[:64])
    if setting == "null_no_benefit":
        assert not correct.any()
        assert np.all(correct - public.direct_correct[:, None] - 0.00005 * tokens <= 0)


def test_three_association_cases_have_matched_expected_marginals():
    zero = g1.SPEC["settings"]["threshold_cost_zero"]
    positive = g1.SPEC["settings"]["threshold_cost_positive"]
    negative = g1.SPEC["settings"]["threshold_cost_negative"]
    for name in ("pD", "pT_below_above_half", "length"):
        assert zero[name] == positive[name] == negative[name]
    # Analytic uniform intersections, not empirically tuned finite simulations.
    for p in zero["pT_below_above_half"]:
        joint_positive = min(p, 0.5)
        joint_negative = max(p - 0.5, 0)
        assert joint_positive - p * 0.5 > 0
        assert joint_negative - p * 0.5 < 0
        length_mean = sum(zero["length"]) / 2
        for parameters in (positive, negative):
            assert length_mean == sum(parameters["length"]) / 2


def test_purchase_reservation_failure_never_opens_hidden_cell():
    public = pool()
    calls = []
    interface = g1.PurchaseInterface(public, lambda cell: calls.append(cell) or (1, 100), [])
    with pytest.raises(ValueError, match="reservation exceeds"):
        interface.purchase((0, 0), int(public.direct_tokens.sum()) + 2561, "adaptive")
    assert not calls and not interface.observed and interface.reveal_count == 0
    assert interface.ledger.charged == int(public.direct_tokens.sum())


def test_batch_cannot_reveal_a_cell_without_its_prior_cap():
    public = pool()
    calls = []
    interface = g1.PurchaseInterface(public, lambda cell: calls.append(cell) or (1, 100), [])
    with pytest.raises(ValueError, match="batch must reserve"):
        interface.purchase((0, 0), 64000, "audit", pre_reserved=True)
    assert not calls and not interface.observed


def test_candidate_matches_analytical_repeat_versus_new_state_example():
    public = g1.PublicPool([0.3, 0.6], [0, 0], [128, 128])
    between, within, counts = np.array([0.1, 0.04]), np.array([0.4, 0.01]), np.array([1, 0])
    variance = 1 / (1 / between + counts / within)
    posterior = g1.Posterior(np.zeros(2), variance, np.array([200.0, 100.0]), within,
                             between, within.copy(), between.copy(), variance.copy(),
                             np.full((2, 2), 0.5), counts, np.zeros(2))
    actions = np.array([[0, 0], [1, 1]], dtype=bool)
    scores = g1.candidate_score(public, actions, posterior, np.array([0, 1]))
    assert scores[0] * 16 == pytest.approx(0.48 / 200)
    assert scores[1] * 16 == pytest.approx(0.162 / 100)
    assert scores[0] > scores[1]


def test_uniform_controls_and_repeat_removal_have_expected_support():
    public = pool()
    observed = {(0, 0): (1, 300), (1, 0): (0, 500), (2, 0): (1, 300), (2, 1): (0, 500)}
    model = g1.build_posterior(public, observed)
    actions = g1.policy_grid(public.confidence).actions
    plausible = np.arange(len(actions))
    coverage, _, _ = g1.state_probabilities(public, "uniform_coverage", model, actions, plausible, np.zeros((32, 8)))
    repeat, _, _ = g1.state_probabilities(public, "uniform_repeat", model, actions, plausible, np.zeros((32, 8)))
    removed, _, _ = g1.state_probabilities(public, "candidate_no_repeat", model, actions, plausible, np.zeros((32, 8)))
    assert coverage[:3].sum() == 0 and coverage[3:].sum() == pytest.approx(1)
    assert repeat[0] == repeat[1] == 0.5 and repeat[2:].sum() == 0
    assert removed[:3].sum() == 0 and removed[3:].sum() == pytest.approx(1)


def test_mutual_information_rejects_invalid_probabilities():
    for table in (np.array([1, 0]), np.array([[0.8, 0.3]]), np.array([[1.1, -0.1]])):
        with pytest.raises(ValueError, match="joint table"):
            g1.mutual_information(table)


def test_exact_cache_when_all_cells_observed_is_prediction_independent():
    public = pool(2)
    actions = g1.policy_grid(public.confidence).actions
    observed = {(0, 0): (1, 100), (0, 1): (0, 200), (1, 0): (0, 300), (1, 1): (1, 400)}
    result, covariance = g1.audit_estimate(public, actions, observed, [], np.array([200.0, -100.0]), {})
    correct, tokens = np.array([[1, 0], [0, 1]]), np.array([[100, 200], [300, 400]])
    np.testing.assert_allclose(result, g1.cache_values(public, correct, tokens, actions), atol=1e-15)
    assert not covariance.any()


def test_audit_rejects_noncomplement_and_unreserved_pool_members():
    public = pool(2)
    actions = g1.policy_grid(public.confidence).actions
    with pytest.raises(ValueError, match="complement"):
        g1.audit_estimate(public, actions, {}, [(0, 0)], np.zeros(2), {(0, 0): (1, 100)})
    with pytest.raises(ValueError, match="frozen remaining"):
        g1.audit_estimate(public, actions, {(0, 0): (1, 100)}, [(0, 1), (1, 0), (1, 1)],
                          np.zeros(2), {(0, 0): (1, 100)})


def test_small_exact_engineering_enumeration_has_no_bias():
    checks = g1.engineering_checks()
    assert checks["pass"] and checks["exact_audit_histories"] == 16
    assert checks["maximum_enumerated_bias"] < 1e-12


def test_acquisition_overhead_uses_preserved_times_with_separate_scope():
    records = [{"setting": "tiny", "trajectories": [{"method": "candidate", "acquisition_elapsed_seconds": duration}]}
               for duration in (1.25, 2.75)]
    report = g1.summarize_acquisition_timing(records)
    assert len(report) == 1
    assert report[0]["mean_acquisition_elapsed_seconds"] == 2.0
    assert report[0]["minimum_acquisition_elapsed_seconds"] == 1.25
    assert report[0]["maximum_acquisition_elapsed_seconds"] == 2.75
    assert report[0]["trajectories"] == 2
    assert "excludes_evaluation_verification_compression" in report[0]["interpretation"]
    records[0]["trajectories"][0]["acquisition_elapsed_seconds"] = -1
    with pytest.raises(ValueError, match="elapsed time"):
        g1.summarize_acquisition_timing(records)


def fixture_trajectory():
    public = pool()
    seed, setting = 2026100900, "threshold_cost_zero"
    ordinal = g1.SETTINGS.index(setting)
    trace = []
    interface = g1.PurchaseInterface(public, lambda cell: (cell[0] % 2, 200 + 100 * cell[1]), trace)
    particles = g1.make_rng(seed, ordinal, 4).standard_normal((32, public.n))
    trajectory = g1.run_strategy(public, interface, "uniform_coverage", g1.make_rng(seed, ordinal, 3),
                                  g1.common_seed_cells(public, seed, ordinal), particles)
    return trajectory, setting, seed, particles


def test_complete_tiny_trace_replays_exactly_and_detects_probability_change():
    trajectory, setting, seed, particles = fixture_trajectory()
    checks = g1.validate_trajectory(trajectory, setting, seed, particles)
    assert checks["checkpoints"] == 3 and checks["purchases"] == 16
    altered = copy.deepcopy(trajectory)
    snapshot = next(event for event in altered["trace"] if event["kind"] == "audit_snapshot")
    snapshot["inclusion_probability"] *= 0.5
    with pytest.raises(ValueError, match="audit inclusion"):
        g1.validate_trajectory(altered, setting, seed, particles)


def test_public_policy_grid_does_not_use_outcomes_or_costs():
    p = pool()
    altered = g1.PublicPool(p.confidence, 1 - p.direct_correct, np.full(p.n, 512))
    assert g1.policy_grid(p.confidence).as_dict() == g1.policy_grid(altered.confidence).as_dict()
    assert g1.common_seed_cells(p, 123, 0) == g1.common_seed_cells(altered, 123, 0)


def test_evaluation_reports_group_weighted_utility_and_common_direct_cost():
    public = g1.PublicPool([0.2, 0.8], [0, 1], [128, 512])
    correctness = np.array([[1, 0], [0, 1]])
    tokens = np.array([[100, 300], [200, 400]])
    result = g1.evaluate_policy(public, correctness, tokens, 0.5)
    assert result["accuracy"] == 0.75
    assert result["deployment_tokens"] == 420
    assert result["utility"] == pytest.approx(0.75 - 0.00005 * 420)
    assert result["groups"] == 2 and result["draws_per_group"] == 2


def test_compressed_record_is_immutable_deterministic_and_bounded(tmp_path):
    first, second = tmp_path / "a.gz", tmp_path / "b.gz"
    record = {"arithmetic": [0.1, 0.2], "nested": {"first": True}}
    g1.compressed_json(first, record, 1000)
    g1.compressed_json(second, record, 1000)
    assert first.read_bytes() == second.read_bytes()
    with pytest.raises(FileExistsError):
        g1.compressed_json(first, {"different": True}, 1000)
    with pytest.raises(ValueError, match="byte limit"):
        g1.compressed_json(tmp_path / "too-small.gz", record, 1)
    assert not (tmp_path / "too-small.gz").exists()


def synthetic_plan(tmp_path, monkeypatch):
    root = tmp_path / "repository"
    root.mkdir()
    for relative in g1.SPEC["source_files"]:
        file = root / relative
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text("frozen tiny fixture\n")
    monkeypatch.setattr(g1, "repository_root", lambda: root)
    monkeypatch.setattr(g1, "runtime_identity", lambda: {"python": "fixture", "numpy": "fixture"})

    class Result:
        def __init__(self, stdout):
            self.stdout = stdout

    def git_run(arguments, **kwargs):
        if arguments[1] == "rev-parse":
            return Result("a" * 40 + "\n")
        relative = arguments[2].split(":", 1)[1]
        return Result((root / relative).read_bytes())

    monkeypatch.setattr(g1.subprocess, "run", git_run)
    output = tmp_path / "new-study"
    prepared = g1.prepare(output, "a" * 40)
    return root, output, prepared


def test_prepare_pins_exact_source_runtime_spec_and_refuses_existing_output(tmp_path, monkeypatch):
    root, output, prepared = synthetic_plan(tmp_path, monkeypatch)
    plan = g1.validate_plan(output)
    assert plan["spec_sha256"] == g1.digest(g1.SPEC)
    assert plan["source_sha256"] == {relative: g1.file_digest(root / relative) for relative in g1.SPEC["source_files"]}
    assert prepared["plan_sha256"] == g1.file_digest(output / "plan.json")
    original = (output / "plan.json").read_bytes()
    with pytest.raises(FileExistsError):
        g1.prepare(output, "a" * 40)
    assert (output / "plan.json").read_bytes() == original
    assert g1.verify(output)["status"] == "prepared_verified"


def test_execute_requires_actual_plan_review_and_failed_invocation_cannot_retry(tmp_path, monkeypatch):
    _, output, prepared = synthetic_plan(tmp_path, monkeypatch)
    review = output / "prelaunch-review.json"
    g1.immutable_json(review, {"status": "pass", "plan_sha256": "wrong", "engineering_checks_passed": True,
                             "unresolved_blockers": []})
    with pytest.raises(ValueError, match="prelaunch review"):
        g1.execute(output, review)
    assert not (output / "invocation.json").exists()
    # Fixture replaces only its own review before any invocation exists.
    review.unlink()
    g1.immutable_json(review, {"status": "pass", "plan_sha256": prepared["plan_sha256"],
                             "engineering_checks_passed": True, "unresolved_blockers": []})

    def stop_before_any_grid(*args, **kwargs):
        raise RuntimeError("bounded synthetic fixture stop before acquisition")

    monkeypatch.setattr(g1, "run_seed", stop_before_any_grid)
    with pytest.raises(RuntimeError, match="fixture stop"):
        g1.execute(output, review)
    assert (output / "invocation.json").exists()
    finish = json.loads((output / "finish.json").read_text())
    assert finish["status"] == "failed" and finish["completed_seed_settings"] == 0
    invocation = (output / "invocation.json").read_bytes()
    with pytest.raises(FileExistsError):
        g1.execute(output, review)
    assert (output / "invocation.json").read_bytes() == invocation
    assert g1.verify(output)["status"] == "failed_run_preserved"


def test_cli_help_is_available_without_accessing_artifacts(capsys):
    with pytest.raises(SystemExit) as exited:
        g1.main(["--help"])
    assert exited.value.code == 0
    assert "prepare,run,verify" in capsys.readouterr().out


def test_source_has_no_project_or_historical_imports():
    import ast

    source = Path(g1.__file__).read_text()
    tree = ast.parse(source)
    imports = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
    imports += [alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names]
    assert all(not name.startswith(("reasoning_budget", "scripts.", "torch", "transformers", "datasets"))
               for name in imports if name is not None)
