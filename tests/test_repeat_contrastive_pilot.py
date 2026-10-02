"""Synthetic checks only: no cached real labels, model load, or text encoding."""
import inspect
from copy import deepcopy

import numpy as np
import pytest
import torch

from reasoning_budget.storage import verified
from scripts import repeat_contrastive_pilot as pilot


def fixture_panel(n=15):
    rng = np.random.default_rng(7)
    q = np.concatenate([pilot.normalize(rng.normal(size=(n, 384))), np.zeros((n, 3))], axis=1)
    draft = pilot.normalize(rng.normal(size=(n, 8, 384)))
    z = rng.normal(size=(n, 8, 4))
    d = np.zeros((n, 8, 3))
    t = np.zeros_like(d)
    d[:, :, 0] = rng.integers(0, 2, (n, 8))
    t[:, :, 0] = rng.integers(0, 2, (n, 8))
    d[:, :, 1:] = [100, 1]
    t[:, :, 1:] = [500, 2]
    return q, draft, z, d, t


def test_frozen_grid_has_exactly_600_fits_and_matched_objectives():
    assert len(pilot.FAMILIES) == 8
    assert len(pilot.SPEC["conditions"]) * 5 * (4 + 1) * len(pilot.FAMILIES) == 600
    assert pilot.SPEC["max_fits"] == 600
    assert set(pilot.OBJECTIVES) == {"gain_mse", "regret_ce", "bidirectional", "binary_ce"}


def test_representation_preserves_cached_question_vectors_and_ignores_lexical():
    q, draft, *_ = fixture_panel()
    before = q.copy()
    features = pilot.representations(q, draft)
    np.testing.assert_array_equal(features["q_only"][:, 0], q[:, :384])
    np.testing.assert_array_equal(q, before)
    np.testing.assert_allclose(np.linalg.norm(features["q_plus_draft"], axis=2), 1)
    q[:, 384:] = 100000
    changed = pilot.representations(q, draft)
    for key in features:
        np.testing.assert_array_equal(changed[key], features[key])


def test_representation_feature_api_excludes_thinking_correctness_and_cost():
    assert list(inspect.signature(pilot.representations).parameters) == ["question_features", "draft_embeddings"]
    assert list(inspect.signature(pilot.encode_direct_drafts).parameters) == ["direct_text", "pinned_inventory"]
    assert list(inspect.signature(pilot.fit_head).parameters) == ["train_features", "train_gain", "objective"]
    with pytest.raises(ValueError, match="strings"):
        pilot.encode_direct_drafts([[{"thinking": "future"}] * 8], {})


def test_tail_truncation_keeps_answer_end_and_records_original_length():
    ids, metadata = pilot.tail_tokens(list(range(400)), 2)
    assert ids == list(range(146, 400))
    assert metadata == {"raw_tokens": 400, "kept_tokens": 254, "truncated": True}
    assert pilot.tail_tokens([1, 2, 3], 2)[0] == [1, 2, 3]
    assert pilot.tail_tokens([], 2)[1]["truncated"] is False
    with pytest.raises(ValueError, match="capacity"):
        pilot.tail_tokens([1], 256)


def test_direct_text_selector_never_reads_thinking_text_or_references():
    rows = [{"job": {"mode": "thinking"}, "result": {"future": "unused"}}]
    rows += [{"job": {"mode": "direct", "question_id": "q", "sample": draw},
              "status": "completed", "result": {"final_answer": str(draw)}}
             for draw in range(8)]
    assert pilot.direct_texts({"ids": ["q"], "rows": rows}) == [[str(i) for i in range(8)]]
    with pytest.raises(ValueError, match="coverage"):
        pilot.direct_texts({"ids": ["q"], "rows": rows[:-1]})
    with pytest.raises(ValueError, match="Duplicate"):
        pilot.direct_texts({"ids": ["q"], "rows": rows + rows[1:2]})


def test_reject_bad_embeddings():
    q, draft, *_ = fixture_panel()
    with pytest.raises(ValueError, match="normalized"):
        pilot.representations(q * 2, draft)
    with pytest.raises(ValueError, match="Zero"):
        pilot.representations(q, draft * 0)
    with pytest.raises(ValueError, match="Nonfinite"):
        pilot.normalize(np.array([np.nan]))


def test_training_only_pca_and_standardization_ignore_evaluation_states():
    q, draft, z, *_ = fixture_panel()
    semantic = pilot.representations(q, draft)["q_plus_draft"]
    questions, draws = list(range(10)), list(range(4))
    a = pilot.TrainingTransform.fit(semantic, z, questions, draws)
    changed_semantic, changed_z = semantic.copy(), z.copy()
    changed_semantic[10:] = 100
    changed_semantic[:, 4:] = -100
    changed_z[10:] = 10000
    changed_z[:, 4:] = -10000
    b = pilot.TrainingTransform.fit(changed_semantic, changed_z, questions, draws)
    np.testing.assert_array_equal(a.pca.components_, b.pca.components_)
    np.testing.assert_array_equal(a.draft_scaler.mean_, b.draft_scaler.mean_)
    x = a.transform(semantic, z, questions, draws)
    assert x.shape == (40, 12)
    np.testing.assert_allclose(x.mean(0), 0, atol=1e-12)
    np.testing.assert_allclose(x.std(0)[:8], 1 / np.sqrt(8))
    np.testing.assert_allclose(x.std(0)[8:], 1 / np.sqrt(4))
    assert a.questions == tuple(questions) and a.draws == tuple(draws)


def test_all_heads_match_120_parameters_fixed_initialization_and_temperature():
    a, b = pilot.action_head(), pilot.action_head()
    assert sum(p.numel() for p in a.parameters()) == 120
    for left, right in zip(a.parameters(), b.parameters()):
        torch.testing.assert_close(left, right)
    x = torch.ones((3, 12))
    with torch.no_grad():
        states = torch.nn.functional.normalize(a.projection(x), dim=1)
        prototypes = torch.nn.functional.normalize(a.prototypes, dim=1)
        torch.testing.assert_close(a(x), states @ prototypes.T / .1)


@pytest.mark.parametrize("objective", pilot.OBJECTIVES)
def test_all_objectives_have_finite_gradients_with_duplicate_positives(objective):
    head = pilot.action_head()
    x = torch.tensor(np.random.default_rng(4).normal(size=(8, 12)), dtype=torch.float32)
    gains = torch.tensor([.9, .9, .5, .5, -.1, -.1, -1.1, -1.1])
    loss = pilot.objective_loss(head(x), gains, objective)
    loss.backward()
    assert torch.isfinite(loss)
    assert all(p.grad is not None and torch.isfinite(p.grad).all() for p in head.parameters())


def test_reverse_targets_include_all_same_action_positives_and_normalize_regret():
    gains = torch.tensor([1., 2., -3., -1., 0.])
    target, present = pilot.reverse_targets(gains)
    assert present == [0, 1]
    torch.testing.assert_close(target[1], torch.tensor([1 / 3, 2 / 3, 0., 0., 0.]))
    torch.testing.assert_close(target[0], torch.tensor([0., 0., .75, .25, 0.]))
    torch.testing.assert_close(target.sum(1), torch.ones(2))


def test_bidirectional_loss_matches_multi_positive_formula():
    logits = torch.tensor([[.2, .8], [.4, .6], [.9, .1]])
    gain = torch.tensor([1., 2., -1.])
    ce = torch.nn.functional.cross_entropy(logits, (gain > 0).long(), reduction="none")
    forward = (ce * gain.abs()).sum() / gain.abs().sum()
    reverse_logp = torch.log_softmax(logits.T, dim=1)
    reverse = (-reverse_logp[0, 2] - (reverse_logp[1, 0] / 3 + reverse_logp[1, 1] * 2 / 3)) / 2
    torch.testing.assert_close(pilot.objective_loss(logits, gain, "bidirectional"), (forward + reverse) / 2)


@pytest.mark.parametrize("gain", [torch.zeros(3), torch.ones(3), -torch.ones(3)])
def test_absent_action_and_zero_regret_losses_remain_finite(gain):
    logits = torch.randn(3, 2, requires_grad=True)
    loss = pilot.objective_loss(logits, gain, "bidirectional")
    loss.backward()
    assert torch.isfinite(loss) and torch.isfinite(logits.grad).all()
    _, present = pilot.reverse_targets(gain)
    assert len(present) == (0 if not gain.any() else 1)


def test_gain_margin_mse_and_weighted_ce_use_frozen_target_semantics():
    logits = torch.tensor([[0., .5], [0., -.2]])
    gain = torch.tensor([.9, -.1])
    torch.testing.assert_close(pilot.objective_loss(logits, gain, "gain_mse"), torch.tensor((.4**2 + .1**2) / 2))
    ce = torch.nn.functional.cross_entropy(logits, torch.tensor([1, 0]), reduction="none")
    torch.testing.assert_close(pilot.objective_loss(logits, gain, "regret_ce"), ce[0] * .9 + ce[1] * .1)
    torch.testing.assert_close(pilot.objective_loss(logits, gain, "binary_ce"), ce.mean())


def test_paired_fit_is_deterministic_and_cpu_only():
    x = np.random.default_rng(3).normal(size=(12, 12))
    g = np.array([.9, -.1] * 6)
    a, b = pilot.fit_head(x, g, "regret_ce"), pilot.fit_head(x, g, "regret_ce")
    for left, right in zip(a.parameters(), b.parameters()):
        torch.testing.assert_close(left, right, rtol=0, atol=0)
        assert left.device.type == "cpu"
    assert torch.get_num_threads() <= 2


def test_outer_question_and_opposite_half_labels_cannot_select_or_fit(monkeypatch):
    q, draft, z, d, t = fixture_panel()
    semantic = pilot.representations(q, draft)
    ids = [f"q{i}" for i in range(len(q))]
    train, test = list(range(12)), list(range(12, 15))
    acquired = []
    def fake_fit(x, gain, objective):
        acquired.append((x.copy(), gain.copy(), objective))
        return None
    monkeypatch.setattr(pilot, "fit_head", fake_fit)
    monkeypatch.setattr(pilot, "margins", lambda model, x, shape: x[:, 0].reshape(shape))
    actions_a, details_a = pilot.fit_fold(ids, semantic, z, d, t, train, test, list(range(4)), list(range(4, 8)), 0)
    fits_a = deepcopy(acquired)
    assert len(fits_a) == 40
    acquired.clear()
    d2, t2 = d.copy(), t.copy()
    d2[:, 4:, 0] = 1 - d2[:, 4:, 0]
    t2[:, 4:, :2] = [1, 99999]
    d2[test, :, 0] = 1 - d2[test, :, 0]
    t2[test, :, :2] = [0, 99999]
    actions_b, details_b = pilot.fit_fold(ids, semantic, z, d2, t2, train, test, list(range(4)), list(range(4, 8)), 0)
    assert details_a == details_b
    for policy in actions_a:
        np.testing.assert_array_equal(actions_a[policy], actions_b[policy])
    for (x1, g1, loss1), (x2, g2, loss2) in zip(fits_a, acquired):
        np.testing.assert_array_equal(x1, x2)
        np.testing.assert_array_equal(g1, g2)
        assert loss1 == loss2
    assert all(not (set(item["train_ids"]) & set(ids[i] for i in test)) for item in details_a["inner_splits"])


def test_overlap_guards_before_fitting():
    q, draft, z, d, t = fixture_panel()
    semantic = pilot.representations(q, draft)
    with pytest.raises(ValueError, match="questions overlap"):
        pilot.fit_fold(list(map(str, range(15))), semantic, z, d, t, [0, 1], [1, 2], [0], [4], 0)
    with pytest.raises(ValueError, match="halves overlap"):
        pilot.fit_fold(list(map(str, range(15))), semantic, z, d, t, [0, 1], [2], [0, 1], [1, 2], 0)


def test_sunk_direct_cost_and_rescue_harm_counts_are_conserved():
    d = np.array([[[0., 100., 1.], [1., 100., 1.]]])
    t = np.array([[[1., 500., 2.], [0., 500., 2.]]])
    rows = pilot.evaluate_actions(d, t, [0], [0, 1], np.array([[True, True]]))
    assert rows["tokens"][0] == 600
    assert rows["accuracy"][0] == .5
    assert rows["utility"][0] == pytest.approx(.47)
    assert rows["rescued"][0] == rows["harmed"][0] == 1
    assert rows["positive_gain_escalations"][0] == rows["nonpositive_gain_escalations"][0] == 1


def test_exploratory_screen_requires_both_directions_and_all_loo_positive():
    passing = pilot.screen(np.full(10, .02), np.full(10, .02))
    assert passing["passes"] and passing["scale_acquisition"] is False
    assert not pilot.screen(np.full(10, .04), np.full(10, -.001))["passes"]
    isolated = np.zeros(10)
    isolated[0] = .2
    assert not pilot.screen(isolated, isolated)["passes"]


def test_exclusive_artifact_write_never_overwrites_even_identical_payload(tmp_path):
    path = tmp_path / "plan.json"
    pilot.write_new(path, {"version": 1})
    before = path.read_bytes()
    assert verified(path) == {"version": 1}
    with pytest.raises(ValueError, match="already exists"):
        pilot.write_new(path, {"version": 1})
    assert path.read_bytes() == before
    linked = tmp_path / "symlink.json"
    linked.symlink_to(path)
    with pytest.raises(ValueError, match="symlink"):
        pilot.write_new(linked, {})
