import copy
from fractions import Fraction
from unittest import mock

import numpy as np
import pytest

from reasoning_budget import repeat_stats as historical
from scripts import audit_deferral_curves as audit
from scripts import opportunity_panel_plan as plan

SMALL = copy.deepcopy(audit.SPEC)
SMALL["lambda_grid"] = [0.05, 0.1]
SMALL["refit"].update(bootstrap_draws=4, repartitions=3)


def repeat_panel(seed=0, informative_answers=True):
    rng = np.random.default_rng(seed)
    n = 50
    ids = [f"q{i:02d}" for i in range(n)]
    fold_of = np.arange(n) % 5
    q = rng.normal(size=(n, 24))
    hardness = rng.random(n)
    d, t = np.zeros((n, 8, 3)), np.zeros((n, 8, 3))
    d[..., 0] = rng.random((n, 8)) > 0.4 * hardness[:, None]
    t[..., 0] = rng.random((n, 8)) > 0.1 * hardness[:, None]
    d[..., 1] = rng.integers(80, 300, size=(n, 8))
    t[..., 1] = rng.integers(300, 1500, size=(n, 8))
    d[..., 2], t[..., 2] = 1.0, 5.0
    z = np.zeros((n, 8, 4))
    z[..., 0] = rng.normal(-0.2, 0.05, size=(n, 8)) - 0.1 * (d[..., 0] == 0)
    z[..., 1] = rng.normal(4, 0.3, size=(n, 8))
    statuses = np.where(rng.random((n, 8)) < 0.05, "invalid_number", "ok").astype(object)
    d[..., 0] *= statuses == "ok"
    z[..., 2] = statuses == "ok"
    answers = np.empty((n, 8), dtype=object)
    for i in range(n):
        for s in range(8):
            if statuses[i, s] != "ok":
                answers[i, s] = None
            elif d[i, s, 0]:
                answers[i, s] = "42"
            else:
                wrong = rng.integers(0, 1000) if informative_answers else 7
                answers[i, s] = str(43 + wrong)
    return ids, q, z, d, t, fold_of, answers, statuses


def two_solver_panel(seed=1):
    rng = np.random.default_rng(seed)
    ids = [f"t{i:03d}" for i in range(64)]
    fold_of = np.arange(64) % 5
    panels = {}
    for solver, direct_rate in zip(audit.SOLVERS, (0.6, 0.85)):
        dc = (rng.random((64, 2)) < direct_rate).astype(float)
        statuses = np.full((64, 2), "ok", dtype=object)
        answers = np.where(dc == 1, "12", "13").astype(object)
        answers[rng.random((64, 2)) < 0.3] = "99"
        dc[answers == "99"] = 0.0
        panels[solver] = {"direct_correct": dc,
                          "thinking_correct": (rng.random((64, 2)) < 0.85).astype(float),
                          "direct_tokens": rng.integers(100, 300, (64, 2)).astype(float),
                          "thinking_tokens": rng.integers(400, 2000, (64, 2)).astype(float),
                          "confidence": rng.normal(-0.3, 0.1, (64, 2)) - 0.2 * (dc == 0),
                          "answers": answers, "statuses": statuses}
    return ids, fold_of, panels


@pytest.fixture(scope="module")
def repeat():
    return repeat_panel()


@pytest.fixture(scope="module")
def two():
    return two_solver_panel()


def payload(repeat, two):
    ids, q, z, d, t, fold_of, _, _ = repeat
    two_ids, two_folds, panels = two
    return {"repeat": (q, z, d, t, fold_of),
            "two_solver": ({s: {k: v for k, v in p.items() if k not in ("answers", "statuses")}
                            for s, p in panels.items()}, list(two_ids), two_folds)}


def test_grouped_splits_equal_original_without_copies():
    questions = np.array([3, 8, 11, 14, 20, 21, 30, 33, 40, 47])
    split = audit.grouped_splits(np.arange(50))
    for seed in (20261002, 20261003):
        expected = historical._inner_splits(questions, seed, 4)
        got = split(questions, seed, 4)
        assert len(got) == len(expected)
        for (a, b), (c, e) in zip(got, expected):
            assert a.tolist() == c.tolist() and b.tolist() == e.tolist()


def test_grouped_splits_keep_copies_together():
    groups = np.array([5, 5, 9, 2, 2, 2, 7, 1, 1, 4, 6, 3])
    questions = np.arange(len(groups))
    split = audit.grouped_splits(groups)(questions, 7, 4)
    covered = []
    for inside, heldout in split:
        assert not set(groups[inside]) & set(groups[heldout])
        assert sorted(np.concatenate([inside, heldout]).tolist()) == questions.tolist()
        covered.extend(heldout.tolist())
    assert sorted(covered) == questions.tolist()


def test_run_condition_reproduces_historical_routine(repeat):
    ids, q, z, d, t, fold_of, _, _ = repeat
    folds = {qid: int(f) for qid, f in zip(ids, fold_of)}
    gain = audit.gains(d, t, 0.05)
    for name, (a, b) in audit.K4.items():
        result, deltas = historical._run_condition(ids, q, z, d, t, gain, folds, name, a, b,
                                                   historical.ANALYSIS)
        decisions, metrics, _ = audit.run_condition(q, z, d, t, fold_of, a, b,
                                                    audit.historical_spec())
        for policy in audit.REPEAT_POLICIES:
            for i, qid in enumerate(ids):
                assert (decisions[policy][i].tolist()
                        == result["per_question"][qid]["policies"][policy]["decisions"])
        mine = metrics["combined"]["utility"] - metrics["selected_baseline"]["utility"]
        np.testing.assert_allclose(mine, deltas, rtol=0, atol=1e-12)
        reduced, _, _ = audit.run_condition(q, z, d, t, fold_of, a, b,
                                            audit.historical_spec(learners=["combined"]))
        for policy in audit.REDUCED_POLICIES:
            assert np.array_equal(reduced[policy], decisions[policy])


def test_identity_bootstrap_replicates_equal_point_estimates(repeat, two):
    ids, q, z, d, t, fold_of, _, _ = repeat
    two_ids, two_folds, panels = two
    audit._init(payload(repeat, two))
    point = audit.repeat_endpoints(q, z, d, t, fold_of, audit.historical_spec())
    boot = audit._repeat_bootstrap(np.arange(len(ids)))
    for name in audit.REPEAT_ENDPOINTS:
        assert boot[name] == pytest.approx(point[name].mean(), abs=1e-12)
    two_boot = audit._two_solver_bootstrap(np.arange(64))
    for solver in audit.SOLVERS:
        expected = audit.two_solver_delta(panels[solver], two_folds, two_ids).mean()
        assert two_boot[solver] == pytest.approx(expected, abs=1e-12)


def test_two_solver_actions_match_frozen_crossfit_and_lambda_patch(two):
    ids, fold_of, panels = two
    panel = panels["qwen3-0.6b"]
    rows = [{"question_id": qid, "solver": "x", "draw": draw,
             "confidence": float(panel["confidence"][i, draw]),
             "direct_correct": int(panel["direct_correct"][i, draw]),
             "thinking_correct": int(panel["thinking_correct"][i, draw]),
             "thinking_tokens": int(panel["thinking_tokens"][i, draw])}
            for i, qid in enumerate(ids) for draw in (0, 1)]
    frozen = plan.confidence_crossfit(rows, dict(zip(ids, map(int, fold_of))), "x")
    actions, thresholds = audit.two_solver_actions(panel, fold_of, ids)
    for i, qid in enumerate(ids):
        for draw in (0, 1):
            assert actions[i, draw] == frozen[qid, 1 - draw, draw]["escalate"]
            assert thresholds[i, draw] == frozen[qid, 1 - draw, draw]["threshold"]
    assert actions.any()
    never, _ = audit.two_solver_actions(panel, fold_of, ids, lam=10.0)
    assert not never.any() and plan.LAM == 0.05
    copied_rows, folds = audit.two_solver_rows(panel, fold_of, ids)
    for lam in (0.0, 0.05, 0.2):
        with mock.patch.object(plan, "LAM", lam):
            frozen = plan.confidence_crossfit(copied_rows, folds, "s")
        assert audit.confidence_crossfit(copied_rows, folds, lam) == frozen
    audit.check_frozen_crossfit(panel, fold_of, ids)


def test_copied_crossfit_skips_an_empty_fold(two):
    ids, fold_of, panels = two
    keep = fold_of != 4
    sub_ids = [qid for qid, k in zip(ids, keep) if k]
    panel = {key: value[keep] for key, value in panels["qwen3-0.6b"].items()}
    rows, folds = audit.two_solver_rows(panel, fold_of[keep], sub_ids)
    with pytest.raises(ValueError):
        plan.confidence_crossfit(rows, folds, "s")
    results = audit.confidence_crossfit(rows, folds, 0.05)
    assert len(results) == 2 * len(sub_ids)
    assert {r["fold"] for r in results.values()} == {0, 1, 2, 3}
    train = [r for r in rows if r["draw"] == 0 and folds[r["question_id"]] != 0]

    def gain(threshold):
        return sum((r["confidence"] < threshold) * (r["thinking_correct"] - r["direct_correct"]
                   - 0.05 * r["thinking_tokens"] / 1000) for r in train) / len(train)

    candidates = [-np.inf, *sorted({r["confidence"] for r in train}), np.inf]
    best = max(gain(c) for c in candidates)
    chosen = results[next(q for q in sub_ids if folds[q] == 0), 0, 1]["threshold"]
    assert gain(chosen) == best


def test_copy_ids_preserve_sort_order():
    ids = ["a1", "a12", "b"]
    names = audit.copy_ids(ids, np.array([1, 0, 1, 2, 0]))
    assert len(set(names)) == 5
    assert sorted(names) == ["a1#0000", "a1#0001", "a12#0000", "a12#0001", "b#0000"]


def test_parallel_results_match_serial(repeat, two):
    work = payload(repeat, two)
    samples = np.random.default_rng(0).integers(0, 50, size=(3, 50))
    two_samples = np.random.default_rng(1).integers(0, 64, size=(3, 64))
    serial = audit.run_jobs(audit._repeat_bootstrap, samples, work, 1)
    assert audit.run_jobs(audit._repeat_bootstrap, samples, work, 2) == serial
    serial_two = audit.run_jobs(audit._two_solver_bootstrap, two_samples, work, 1)
    assert audit.run_jobs(audit._two_solver_bootstrap, two_samples, work, 2) == serial_two
    assert len({tuple(sorted(r.items())) for r in serial}) > 1


def test_repartitions_are_balanced_and_deterministic():
    parts = audit.repartitions(5, 64, 3)
    assert all(sorted(np.bincount(p).tolist()) == [12, 13, 13, 13, 13] for p in parts)
    assert all(np.array_equal(a, b) for a, b in zip(parts, audit.repartitions(5, 64, 3)))
    assert len({tuple(p) for p in parts}) == 5


def test_fixed_means_match_historical_interval():
    values = np.random.default_rng(4).normal(size=50)
    ci, sd = audit.fixed_means(values, 20261002, 2000, [0.05, 0.95])
    assert ci == historical._ci(values, historical.ANALYSIS) and sd > 0


@pytest.mark.parametrize("fixed,refit,reading", [
    ([-0.03, -0.001], [-0.04, -0.002], "sign_robust"),
    ([-0.03, -0.001], [-0.05, 0.01], "no_longer_excludes_zero"),
    ([-0.03, 0.01], [-0.05, 0.02], "both_include_zero"),
    ([-0.03, 0.01], [0.001, 0.02], "refit_excludes_zero"),
    ([0.01, 0.03], [-0.03, -0.01], "sign_reversed")])
def test_refit_reading(fixed, refit, reading):
    assert audit.refit_reading(fixed, refit) == reading


def test_references_random_line_and_envelopes():
    rng = np.random.default_rng(5)
    dc = (rng.random(200) < 0.8).astype(float)
    tc = (rng.random(200) < 0.9).astype(float)
    state = audit.states(dc, tc, rng.integers(100, 300, 200), rng.integers(500, 1500, 200),
                         rng.normal(size=200))
    refs = audit.references(state, 0.05)
    for name in ("always_direct", "always_escalate"):
        placed = audit.placed(refs[name], refs, 0.05)
        assert placed["lift_over_random"] == pytest.approx(0, abs=1e-12)
    assert audit.placed(refs["always_direct"], refs, 0.05)["oracle_share"] == 0
    assert audit.placed(refs["oracle"], refs, 0.05)["oracle_share"] == pytest.approx(1)
    envelope = audit.confidence_envelope(state, audit.SPEC["curve_fractions"], 0.05)
    assert envelope[0]["accuracy"] == refs["always_direct"]["accuracy"]
    assert envelope[-1]["tokens"] == pytest.approx(refs["always_escalate"]["tokens"])
    frontier = audit.oracle_frontier(state, audit.SPEC["curve_fractions"], 0.05)
    rescues = ((dc == 0) & (tc == 1)).sum()
    assert frontier[-1]["accuracy"] == pytest.approx(dc.mean() + rescues / 200)
    assert all(a["tokens"] <= b["tokens"] for a, b in zip(frontier, frontier[1:]))
    assert audit.position(0.5, 10.0, refs, 0.05)["lift_over_random"] is None


def test_agreement_values_and_consistency():
    values = audit.answer_values([["18", "18.0", "36/2", None]],
                                 [["ok", "ok", "ok", "invalid_number"]])
    assert values[0, 0] == values[0, 1] == values[0, 2] == Fraction(18)
    agree = audit.agreement_matrix(values, np.array([[1, 1, 1, 0]]))
    assert agree[0, 0, 1] and agree[0, 1, 2] and not agree[0, 0, 3] and not agree[0, 3, 3]
    with pytest.raises(ValueError):
        audit.agreement_matrix(values, np.array([[1, 0, 1, 0]]))


def test_agreement_rows_charge_both_drafts_and_thinking():
    d = np.array([[[1, 100], [0, 200]]], dtype=float)
    t = np.array([[[1, 1000], [1, 900]]], dtype=float)
    agree = np.zeros((1, 2, 2), dtype=bool)
    rows, composition = audit.agreement_rows(d, t, agree, [(0, 1), (1, 0)], 0.05)
    # Disagree: both states escalate; tokens = own draft + partner draft + thinking.
    assert rows["tokens"][0] == pytest.approx(((100 + 200 + 1000) + (200 + 100 + 900)) / 2)
    assert rows["accuracy"][0] == 1.0 and composition["escalated_rescues"] == 1.0
    agree[:] = True
    rows, composition = audit.agreement_rows(d, t, agree, [(0, 1)], 0.05)
    assert rows["tokens"][0] == 300 and rows["accuracy"][0] == 1.0
    assert composition["escalations"] == 0 and composition["missed_rescues"] == 0
    assert rows["second_draft_utility_cost"][0] == pytest.approx(0.05 * 200 / 1000)


def test_agreement_screen_responds_to_answer_signal(repeat):
    ids, q, z, d, t, fold_of, answers, statuses = repeat
    spec = copy.deepcopy(audit.SPEC)
    spec["agreement"]["bootstrap_draws"] = 200
    metrics = {name: audit.run_condition(q, z, d, t, fold_of, a, b, audit.historical_spec())[1]
               for name, (a, b) in audit.CONDITIONS.items()}
    agree = audit.agreement_matrix(audit.answer_values(answers, statuses), d[:, :, 0])
    informative = audit.repeat_agreement(d, t, agree, metrics, spec)
    _, _, _, _, _, _, flat, flat_status = repeat_panel(informative_answers=False)
    collapsed = audit.agreement_matrix(audit.answer_values(flat, flat_status), d[:, :, 0])
    weak = audit.repeat_agreement(d, t, collapsed, metrics, spec)
    good, bad = (r["primary_k4"]["versus_confidence"]["mean"] for r in (informative, weak))
    assert good > bad
    assert informative["primary_k4"]["expected_composition"]["escalated_both_correct"] < \
        weak["primary_k4"]["expected_composition"]["escalated_both_correct"] + 1e-9
    assert set(informative["primary_k4"]["versus_confidence"]["directions"]) == set(audit.K4)


def test_analyze_end_to_end_small(repeat, two):
    result = audit.analyze(repeat, two, processes=1, spec=SMALL)
    assert set(result["curves"]) == {"repeat_qwen3_1.7b", "two_solver_qwen3_0.6b",
                                     "two_solver_qwen3_1.7b"}
    repeat_curve = result["curves"]["repeat_qwen3_1.7b"]
    assert repeat_curve["states"] == 400 and set(repeat_curve["policies"]) == \
        set(audit.REPEAT_POLICIES)
    assert [row["lambda"] for row in repeat_curve["lambda_sweep"]] == SMALL["lambda_grid"]
    sweep05 = repeat_curve["lambda_sweep"][0]["policies"]["confidence"]
    assert sweep05["accuracy"] == repeat_curve["policies"]["confidence"]["accuracy"]
    assert len(repeat_curve["reported_table3_points"]) == 9
    assert set(result["refit_uncertainty"]) == {
        "repeat_combined_minus_selected_baseline", "repeat_combined_minus_confidence",
        "repeat_confidence_minus_accept", "two_solver_qwen3_0.6b_confidence_minus_accept",
        "two_solver_qwen3_1.7b_confidence_minus_accept"}
    for item in result["refit_uncertainty"].values():
        assert item["repartition"]["count"] == 3 and item["reading"] in {
            "sign_robust", "no_longer_excludes_zero", "both_include_zero",
            "refit_excludes_zero", "sign_reversed"}
    assert result["agreement_primary_reading"] in {"pass", "fail"}
    assert not result["historical_actions_verified"]
    text = audit.markdown({"statistics": result, "runtime_environment_deviation": ["platform"]})
    assert "Refit-inclusive uncertainty" in text and "agreement" in text.lower()
    assert "Table 3, reported" in text


def test_spec_and_sources_are_frozen_as_declared():
    assert audit.SPEC["lambda"] == 0.05 and 0.05 in audit.SPEC["lambda_grid"]
    refit = audit.SPEC["refit"]
    assert refit["bootstrap_draws"] == 2000 and refit["repartitions"] == 200
    assert (refit["repeat_seed"], refit["two_solver_seed"], refit["repeat_repartition_seed"],
            refit["two_solver_repartition_seed"]) == (20261102, 20261103, 20261104, 20261105)
    assert audit.SPEC["agreement"]["bootstrap_seed"] == 20261101
    assert audit.SPEC["agreement"]["screen"]["minimum_mean"] == 0.01
    assert audit.SPEC["primary_conditions"] == ["k4_A_to_B", "k4_B_to_A"]
    assert all((audit.ROOT / name).is_file() for name in audit.SOURCE_FILES)
    assert audit.OUTPUT.parent == audit.BASE == audit.REPEAT.parent
    assert audit.ORIGINAL_INNER_SPLITS is historical._inner_splits
