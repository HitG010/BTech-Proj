"""Independent tiny-fixture G1 checks; never run the study simulation grid."""

import math
from copy import deepcopy
from dataclasses import replace
from itertools import combinations

import numpy as np
import pytest

from scripts import review_threshold_acquisition_synthetic as independent
from scripts import threshold_acquisition_synthetic as subject


def pool(confidence=(0.2, 0.5, 0.8), direct=(1, 0, 1)):
    return subject.PublicPool(np.array(confidence), np.array(direct),
                              np.full(len(confidence), 128))


def finite_values(public, actions, truth):
    """Direct sum written independently of production cache/gain helpers."""
    beta = 0.05 / 1000
    baseline = sum(d - beta * c for d, c in
                   zip(public.direct_correct, public.direct_tokens, strict=True)) / public.n
    return np.array([
        baseline + sum(int(row[i]) * (y - public.direct_correct[i] - beta * c)
                       for (i, _), (y, c) in truth.items()) / (public.n * 2)
        for row in actions
    ])


@pytest.mark.parametrize("prefix", [(), ((0, 0),), ((0, 0), (0, 1), (1, 0))])
def test_exhaustive_audit_mean_and_design_covariance_after_unequal_repeats(prefix):
    public = pool()
    actions = subject.policy_grid(public.confidence).actions
    truth = {(0, 0): (1, 100), (0, 1): (0, 2200), (1, 0): (1, 1800),
             (1, 1): (0, 300), (2, 0): (1, 1700), (2, 1): (0, 2562)}
    observed = {cell: truth[cell] for cell in prefix}
    remaining = [cell for cell in truth if cell not in observed]
    predictions = np.array([-0.21, 0.14, -0.45])
    sample_size = min(2, len(remaining))
    estimates, covariance_estimates = [], []
    for sample in combinations(remaining, sample_size):
        estimate, covariance = subject.audit_estimate(
            public, actions, observed, remaining, predictions,
            {cell: truth[cell] for cell in sample})
        estimates.append(estimate)
        covariance_estimates.append(covariance)
    estimates = np.array(estimates)
    np.testing.assert_allclose(estimates.mean(axis=0), finite_values(public, actions, truth),
                               atol=2e-15, rtol=0)
    centered = estimates - estimates.mean(axis=0)
    design_covariance = centered.T @ centered / len(estimates)
    np.testing.assert_allclose(np.mean(covariance_estimates, axis=0), design_covariance,
                               atol=2e-15, rtol=0)


def test_audit_exact_after_observed_cost_dependent_stop_and_when_all_remaining_bought():
    public = pool()
    actions = subject.policy_grid(public.confidence).actions
    for first_cost in (100, 2500):
        truth = {(0, 0): (0, first_cost), (0, 1): (1, 150), (1, 0): (1, 2562),
                 (1, 1): (0, 200), (2, 0): (0, 1600), (2, 1): (1, 2000)}
        observed = {(0, 0): truth[(0, 0)]}
        # A legitimate adaptive history: only the already revealed first cost
        # decides whether the next cell is bought before the audit begins.
        if observed[(0, 0)][1] < 200:
            observed[(0, 1)] = truth[(0, 1)]
        remaining = [cell for cell in truth if cell not in observed]
        predictions = np.array([-0.9, 0.3, -0.05])
        estimates = []
        for sample in combinations(remaining, 2):
            estimate, _ = subject.audit_estimate(public, actions, observed, remaining,
                                                predictions, {c: truth[c] for c in sample})
            estimates.append(estimate)
        np.testing.assert_allclose(np.mean(estimates, axis=0), finite_values(public, actions, truth),
                                   atol=2e-15, rtol=0)
        exact, covariance = subject.audit_estimate(public, actions, observed, remaining,
                                                 predictions, {c: truth[c] for c in remaining})
        np.testing.assert_allclose(exact, finite_values(public, actions, truth), atol=2e-15, rtol=0)
        assert not covariance.any()


def test_audit_estimator_is_not_clipped_to_feasible_utility_range():
    public = pool((0.1, 0.2, 0.3, 0.4, 0.5), (0, 0, 0, 0, 0))
    actions = np.ones((1, 5), dtype=bool)
    remaining = [(i, r) for i in range(5) for r in range(2)]
    estimate, _ = subject.audit_estimate(public, actions, {}, remaining,
                                        np.array([-0.12, 0.99, 0.99, 0.99, 0.99]),
                                        {(0, 0): (1, 1)})
    assert estimate[0] > 1


def test_strict_threshold_ties_and_minimum_escalation_choice():
    confidence = np.array([0.8, 0.2, 0.2, 0.5, 0.5, 0.5, 0.8, 0.9])
    grid = subject.policy_grid(confidence)
    assert grid.thresholds[0] == -np.inf and grid.thresholds[-1] == np.inf
    np.testing.assert_array_equal(grid.actions, confidence[None, :] < grid.thresholds[:, None])
    assert len({tuple(row) for row in grid.actions}) == len(grid.actions)
    # The maximum training value .9 is not among the seven quantile boundaries.
    np.testing.assert_array_equal(np.sum(grid.actions, axis=1), [0, 2, 5, 8])
    assert subject.choose_policy(np.zeros(len(grid.actions)), grid.actions) == 0
    close = np.zeros(len(grid.actions))
    close[2] = 5e-13
    assert subject.choose_policy(close, grid.actions) == 0
    close[2] = 2e-12
    assert subject.choose_policy(close, grid.actions) == 2
    tied = subject.policy_grid(np.repeat(0.5, 8))
    assert len(tied.actions) == 2
    assert not tied.actions[0].any() and tied.actions[1].all()


@pytest.mark.parametrize("field", ["state_ids", "direct_job_ids"])
def test_identity_arrays_have_exact_length_and_unique_state_mapping(field):
    with pytest.raises(ValueError, match="identit|length"):
        subject.PublicPool(np.array([0.2, 0.8]), np.array([0, 1]), np.array([128, 128]),
                           **{field: ("same", "same", "extra")})


def test_joint_covariance_removal_keeps_fixed_history_mean_cost_and_plausibility():
    public = pool((0.4, 0.4, 0.4, 0.4), (0, 1, 0, 1))
    observed = {(0, 0): (1, 2304), (0, 1): (0, 384),
                (1, 0): (1, 2304), (1, 1): (0, 384), (2, 0): (1, 2304)}
    posterior = subject.build_posterior(public, observed)
    actions = np.array([[0, 0, 0, 0], [0, 0, 1, 0], [1, 1, 1, 1]], dtype=bool)
    plausible = np.arange(3)
    before = {name: getattr(posterior, name).copy()
              for name in ("mean", "cost", "variance", "sums", "counts")}
    joint = subject.candidate_score(public, actions, posterior, plausible)
    removed = subject.candidate_score(public, actions, posterior, plausible, no_cross=True)
    assert not np.array_equal(posterior.within, posterior.within_no_cross)
    assert not np.allclose(joint, removed, rtol=1e-8, atol=0)
    for name, values in before.items():
        np.testing.assert_array_equal(getattr(posterior, name), values)
    altered_uncertainty = replace(posterior, within_no_cross=posterior.within_no_cross * 3,
                                 between_no_cross=posterior.between_no_cross * 2,
                                 variance_no_cross=posterior.variance_no_cross * 2)
    np.testing.assert_array_equal(subject.model_values(public, actions, altered_uncertainty),
                                  subject.model_values(public, actions, posterior))
    np.testing.assert_array_equal(subject.plausible_policies(public, actions, altered_uncertainty),
                                  subject.plausible_policies(public, actions, posterior))


def test_information_equation_uses_exact_purchased_gains_and_remaining_cell_weights():
    public = pool((0.2, 0.8), (0, 0))
    observed = {(0, 0): (1, 100), (0, 1): (0, 2304), (1, 0): (0, 384)}
    posterior = subject.build_posterior(public, observed)
    actions = subject.policy_grid(public.confidence).actions
    particles = np.stack([np.array([(-1)**k * 2.0, (k - 15.5) / 8]) for k in range(32)])
    scores, diagnostics = subject.information_score(public, actions, posterior, particles)
    beta = 0.05 / 1000
    state_means = np.clip(posterior.mean + np.sqrt(posterior.variance) * particles,
                         -public.direct_correct - beta * 2562, 1 - public.direct_correct)
    expected_choices = []
    for particle in state_means:
        values = []
        for row in actions:
            total = 0.0
            for i in range(public.n):
                total += row[i] * sum(y - public.direct_correct[i] - beta * c
                                     for (state, _), (y, c) in observed.items() if state == i)
                total += row[i] * (2 - sum(state == i for state, _ in observed)) * particle[i]
            values.append(public.baseline + total / 4)
        maximum = max(values)
        expected_choices.append(min(k for k, value in enumerate(values) if value >= maximum - 1e-12))
    assert diagnostics["particle_thresholds"] == expected_choices
    for i in range(public.n):
        expected_joint = np.zeros((len(actions), 4))
        for k, particle in zip(expected_choices, state_means, strict=True):
            py = min(0.999, max(0.001, particle[i] + public.direct_correct[i] + beta * posterior.cost[i]))
            ph0, ph1 = posterior.high_given_correctness[i]
            for o, probability in enumerate(((1 - py) * (1 - ph0), (1 - py) * ph0,
                                             py * (1 - ph1), py * ph1)):
                expected_joint[k, o] += probability / 32
        np.testing.assert_allclose(diagnostics["joint_tables"][i], expected_joint, atol=2e-15, rtol=0)
        rows, columns = expected_joint.sum(axis=1), expected_joint.sum(axis=0)
        mi = sum(expected_joint[k, o] * math.log(expected_joint[k, o] / (rows[k] * columns[o]))
                 for k in range(len(actions)) for o in range(4) if expected_joint[k, o] > 0)
        assert scores[i] == pytest.approx(mi / posterior.cost[i], abs=1e-15)
    # A direct exact calculation, independent of the particle construction.
    table = np.array([[0.45, 0.05], [0.05, 0.45]])
    expected = math.log(2) + 0.9 * math.log(0.9) + 0.1 * math.log(0.1)
    assert subject.mutual_information(table) == pytest.approx(expected, abs=1e-15)
    assert subject.mutual_information(np.array([[1.0, 0], [0, 0]])) == 0


def test_cap_before_reveal_nested_checkpoints_and_fixed_repeat_ids():
    public = pool(tuple(np.linspace(0.1, 0.9, 8)), (0,) * 8)
    trace = []
    interface = None
    revealed = []

    def reveal(cell):
        identifier = f"{cell[0]}:{cell[1]}"
        assert interface.ledger.reservations[identifier] == 2562
        assert trace[-1]["kind"] == "reserve" or trace[-1]["kind"] == "settle"
        revealed.append(cell)
        return (cell[0] % 2, 200 + 100 * cell[1])

    interface = subject.PurchaseInterface(public, reveal, trace)
    outcome = subject.run_strategy(public, interface, "uniform_coverage", np.random.default_rng(171),
                                   [(0, 0), (1, 0)], np.zeros((32, 8)),
                                   budgets=(17000, 20000, 30000))
    purchased = {}
    reservations = {}
    charged = int(public.direct_tokens.sum())
    audited_at_previous = set()
    latest_snapshot = None
    after_snapshot = False
    for event in outcome["trace"]:
        if event["kind"] == "adaptive_decision":
            assert not after_snapshot
            assert set(map(tuple, event["observed_cells"])) == set(purchased)
            assert audited_at_previous.issubset(set(purchased))
            probabilities = np.array(event["state_probabilities"])
            assert probabilities.sum() == pytest.approx(1)
            state, repeat = event["chosen_cell"]
            remaining_count = sum((state, r) not in purchased for r in range(2))
            assert event["chosen_cell_probability"] == pytest.approx(probabilities[state] / remaining_count)
            assert len(event["remaining_cells"]) == 16 - len(purchased)
        elif event["kind"] == "audit_snapshot":
            latest_snapshot = event
            after_snapshot = True
            assert set(map(tuple, event["observed_cells"])) == set(purchased)
            assert event["batch_reservation"] == len(event["sample"]) * 2562
            assert len(event["sample"]) == min(4, 16 - len(purchased))
        elif event["kind"] == "reserve":
            assert event["tokens"] == 2562
            assert charged + sum(reservations.values()) + 2562 <= event["budget"]
            reservations[event["id"]] = 2562
        elif event["kind"] == "reveal":
            cell = tuple(event["cell"])
            assert event["id"] in reservations and cell not in purchased
            assert event["state_id"] == public.state_ids[cell[0]]
            assert event["direct_job_id"] == public.direct_job_ids[cell[0]]
            if event["phase"] == "audit":
                assert cell in set(map(tuple, latest_snapshot["sample"]))
                if not any(c in purchased for c in map(tuple, latest_snapshot["sample"])):
                    assert len(reservations) == len(latest_snapshot["sample"])
            purchased[cell] = (event["correct"], event["tokens"])
        elif event["kind"] == "settle":
            cap = reservations.pop(event["id"])
            assert event["actual"] + event["refund"] == cap
            charged += event["actual"]
            assert charged == event["charged"]
            assert sum(reservations.values()) == event["reserved"]
        elif event["kind"] == "checkpoint":
            assert not reservations and event["charged_tokens"] == charged <= event["budget"]
            assert event["purchased_cells"] == len(purchased)
            audited_at_previous.update(map(tuple, latest_snapshot["sample"]))
            after_snapshot = False
    assert not reservations
    assert len(revealed) == len(set(revealed)) == outcome["access_count"]
    assert interface.observed == purchased
    with pytest.raises(ValueError, match="already bought"):
        interface.purchase(revealed[0], 30000, "adaptive")


@pytest.mark.parametrize("invalid", [(0.9, 100), (1, 2562.9), (1, 0), (2, 128)])
def test_purchase_interface_rejects_malformed_hidden_outcomes(invalid):
    public = pool()
    interface = subject.PurchaseInterface(public, lambda cell: invalid, [])
    with pytest.raises(ValueError, match="synthetic"):
        interface.purchase((0, 0), 64000, "seed")


@pytest.mark.parametrize("field,invalid", [("direct_correct", [0.5, 1]),
                                         ("direct_tokens", [128.5, 128])])
def test_public_pool_rejects_fractional_direct_inputs_before_integer_cast(field, invalid):
    arguments = {"confidence": np.array([0.2, 0.8]), "direct_correct": np.array([0, 1]),
                 "direct_tokens": np.array([128, 128]), field: np.array(invalid)}
    with pytest.raises(ValueError):
        subject.PublicPool(**arguments)


def test_first_scored_selection_is_blind_to_unpurchased_labels_and_costs():
    public = pool(tuple(np.linspace(0.1, 0.9, 8)), (0, 1, 0, 1, 0, 1, 0, 1))
    common = {(0, 0): (0, 300), (1, 0): (1, 500)}
    decisions = []
    for hidden_outcome in ((0, 1), (1, 2562)):
        trace = []
        interface = subject.PurchaseInterface(public, lambda cell: common.get(cell, hidden_outcome), trace)
        subject.run_strategy(public, interface, "closest_cost_aware", np.random.default_rng(915),
                             list(common), np.tile(np.linspace(-2, 2, 32)[:, None], (1, 8)),
                             budgets=(17000,))
        adaptive = [event for event in trace if event["kind"] == "adaptive_decision"]
        assert adaptive, "fixture must exercise a scored acquisition before its audit"
        decisions.append(adaptive[0])
    assert decisions[0] == decisions[1]


def test_aulc_is_exact_normalized_trapezoid_and_immutable_write_preserves_first_bytes(tmp_path):
    x = (64000, 128000, 256000)
    y = (0.1, -0.25, 0.8)
    expected = sum((x[k + 1] - x[k]) * (y[k + 1] + y[k]) / 2 for k in range(2)) / (x[-1] - x[0])
    assert subject.aulc(list(y)) == pytest.approx(expected, abs=1e-15)
    path = tmp_path / "record.json"
    subject.immutable_json(path, {"first": [1, 2]})
    original = path.read_bytes()
    with pytest.raises(FileExistsError):
        subject.immutable_json(path, {"replacement": True})
    assert path.read_bytes() == original


@pytest.mark.parametrize("tamper", ["ledger", "prediction", "repeat_identity", "estimate", "aulc"])
def test_independent_artifact_reviewer_detects_trace_and_arithmetic_tampering(tamper):
    public = pool(tuple(np.linspace(0.1, 0.9, 8)), (0,) * 8)
    interface = subject.PurchaseInterface(public, lambda cell: (cell[0] % 2, 200 + 100 * cell[1]), [])
    trajectory = subject.run_strategy(public, interface, "uniform_coverage", np.random.default_rng(271),
                                      [(0, 0), (1, 0)], np.zeros((32, 8)),
                                      budgets=(17000, 20000, 30000))
    for cp, utility in zip(trajectory["checkpoints"], (0.1, 0.2, 0.3), strict=True):
        cp["evaluation"] = {"utility": utility}
    trajectory["normalized_aulc"] = 0.1 / 6 + 0.2 / 2 + 0.3 / 3
    checked = independent.review_trajectory(trajectory)
    assert checked["checkpoints"] == 3 and checked["purchases"] == trajectory["access_count"]
    changed = deepcopy(trajectory)
    if tamper == "ledger":
        next(event for event in changed["trace"] if event["kind"] == "settle")["charged"] += 1
    elif tamper == "prediction":
        next(event for event in changed["trace"] if event["kind"] == "audit_snapshot")["predictions"][0] += 0.1
    elif tamper == "repeat_identity":
        next(event for event in changed["trace"] if event["kind"] == "reveal")["direct_job_id"] = "different-state"
    elif tamper == "estimate":
        next(event for event in changed["trace"] if event["kind"] == "checkpoint")["utility_estimates"][0] += 0.1
    else:
        changed["normalized_aulc"] += 0.1
    with pytest.raises(ValueError, match="independent review failed"):
        independent.review_trajectory(changed)


@pytest.mark.parametrize("setting", subject.SETTINGS)
@pytest.mark.parametrize("evaluation", [False, True])
def test_independent_seeded_array_restoration_matches_each_frozen_distribution(setting, evaluation):
    # This restores synthetic arrays only; no acquisition, fitting, screen or
    # simulation curve is executed, and no study outcome is inspected.
    public, correct, tokens = subject.generate_cache(setting, 2026100900, evaluation)
    restored_public, restored_correct, restored_tokens = independent.regenerate_synthetic(
        subject.SPEC, setting, 2026100900, evaluation)
    assert restored_public == public.as_dict()
    np.testing.assert_array_equal(restored_correct, correct)
    np.testing.assert_array_equal(restored_tokens, tokens)


def test_recorded_timing_summary_is_independent_descriptive_arithmetic():
    timings = {("fixture", "candidate"): [0.01, 0.02, 0.03]}
    row = {"setting": "fixture", "method": "candidate", "mean_acquisition_elapsed_seconds": 0.02,
           "minimum_acquisition_elapsed_seconds": 0.01, "maximum_acquisition_elapsed_seconds": 0.03,
           "trajectories": 3, "interpretation": "descriptive_scope"}
    independent.verify_timing([row], timings, "descriptive_scope")
    changed = {**row, "mean_acquisition_elapsed_seconds": 0.04}
    with pytest.raises(ValueError, match="timing mean"):
        independent.verify_timing([changed], timings, "descriptive_scope")
