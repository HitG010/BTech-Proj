
import numpy as np
import pytest
from threadpoolctl import threadpool_limits

from reasoning_budget.storage import digest
from scripts import repeat_clm_probe as probe


@pytest.fixture(autouse=True)
def one_thread():
    with threadpool_limits(limits=1):
        yield


def request_panel():
    return {"ids": ["fixture"], "protocol": {"selected": [{"question": {"id": "fixture", "prompt": "Question text"}}]},
        "rows": [{"job": {"mode": "direct", "question_id": "fixture", "sample": i},
                  "status": "completed", "result": {"final_answer": f"Draft {i}"}} for i in range(8)]}


def test_request_reads_only_current_direct_drafts():
    class Forbidden:
        def __getitem__(self, key):
            raise AssertionError("Thinking result was inspected")
    panel = request_panel()
    panel["rows"].append({"job": {"mode": "thinking"}, "result": Forbidden()})
    request = probe.requests_for(panel)
    assert len(request["states"]) == 8
    assert request["states"][3]["sample"] == 3
    assert "Question text" in request["states"][3]["text"]
    assert "Draft 3" in request["states"][3]["text"]
    assert set(request["states"][3]) == {"question_id", "sample", "text"}
    assert set(request) == {"schema_version", "states", "actions"}


@pytest.mark.parametrize("change", ["duplicate", "missing", "nonstring"])
def test_request_requires_exact_direct_coverage(change):
    panel = request_panel()
    if change == "duplicate":
        panel["rows"].append(panel["rows"][0])
    elif change == "missing":
        panel["rows"].pop()
    else:
        panel["rows"][0]["result"]["final_answer"] = None
    with pytest.raises(ValueError):
        probe.requests_for(panel)


def test_tail_recipe_preserves_final_tokens_and_adds_no_specials():
    class Tokenizer:
        def encode(self, text, add_special_tokens):
            assert add_special_tokens is False
            return list(range(2050))
    ids, meta = probe.tail_ids(Tokenizer(), "fixture")
    assert ids == list(range(3, 2050))
    assert meta == {"raw_tokens": 2050, "kept_tokens": 2047, "truncated": True}


def data(n=20, width=32):
    rng = np.random.default_rng(106)
    semantic = rng.normal(size=(n, 8, width))
    margin = rng.normal(size=(n, 8))
    z = rng.normal(size=(n, 8, 4))
    d, t = np.zeros((n, 8, 3)), np.zeros((n, 8, 3))
    d[..., 0] = rng.integers(0, 2, (n, 8))
    t[..., 0] = rng.integers(0, 2, (n, 8))
    d[..., 1:] = [100, 2]
    t[..., 1:] = [500, 8]
    return semantic, margin, d, t, z


def test_transforms_fit_only_training_questions_and_draws():
    semantic, margin, _, _, _ = data()
    questions, draws = list(range(12)), [0, 1, 2, 3]
    raw = probe.Representation("raw_encoder_ridge", semantic, margin, questions, draws)
    scalar = probe.Representation("clm_calibrated", semantic, margin, questions, draws)
    np.testing.assert_allclose(raw.pca.mean_, semantic[np.ix_(questions, draws)].reshape(-1, 32).mean(0))
    assert scalar.scaler.mean_[0] == pytest.approx(margin[np.ix_(questions, draws)].mean())
    changed, changed_margin = semantic.copy(), margin.copy()
    changed[12:] = changed[:, 4:] = 1000
    changed_margin[12:] = changed_margin[:, 4:] = 1000
    later = probe.Representation("raw_encoder_ridge", changed, changed_margin, questions, draws)
    np.testing.assert_array_equal(raw.pca.components_, later.pca.components_)


def test_fold_selection_ignores_opposite_half_and_outer_test_labels():
    semantic, margin, d, t, z = data()
    train, test = list(range(4, 20)), list(range(4))
    actions, detail, _ = probe.fit_fold(semantic, margin, d, t, z, train, test, [0, 1, 2, 3], [4, 5, 6, 7], 0)
    changed_d, changed_t = d.copy(), t.copy()
    changed_d[:, 4:, 0] = 1 - changed_d[:, 4:, 0]
    changed_t[:, 4:, 0] = 1 - changed_t[:, 4:, 0]
    changed_t[:, 4:, 1:] *= 20
    changed_d[test, :, 0] = 1 - changed_d[test, :, 0]
    changed_t[test, :, 0] = 1 - changed_t[test, :, 0]
    later_actions, later_detail, _ = probe.fit_fold(semantic, margin, changed_d, changed_t, z,
        train, test, [0, 1, 2, 3], [4, 5, 6, 7], 0)
    assert detail == later_detail
    for policy in actions:
        np.testing.assert_array_equal(actions[policy], later_actions[policy])
    for split in detail["inner_splits"]:
        assert set(split["train_indices"]).isdisjoint(split["validation_indices"])
        assert set(split["train_indices"]).isdisjoint(test)
        assert split["draws"] == [0, 1, 2, 3]


def endpoint():
    states, actions = np.zeros((50, 8, 4096), np.float32), np.zeros((2, 4096), np.float32)
    states[..., 0] = 1
    actions[:, 0] = 1
    request = {"states": [{"text": f"fixture {i}"} for i in range(400)], "actions": ["accept", "think"]}
    texts = [item["text"] for item in request["states"]] + request["actions"]
    report = {"mlx_peak_bytes": 10, "truncated_states": 0, "rows": [
        {"index": i, "text_sha256": digest(text), "kind": "state" if i < 400 else "action",
         "raw_tokens": 5, "kept_tokens": 5, "truncated": False, "total_seconds": .2,
         "mlx_peak_bytes": 10} for i, text in enumerate(texts)]}
    return report, request, states, actions


@pytest.mark.parametrize("failure", ["shape", "nan", "norm", "row_order", "text", "length", "latency", "peak"])
def test_encoder_endpoint_rejects_partial_or_misbound_features(failure):
    report, request, states, actions = endpoint()
    probe.validate_endpoint(report, request, states, actions)
    if failure == "shape":
        states = states[:-1]
    elif failure == "nan":
        states[0, 0, 0] = np.nan
    elif failure == "norm":
        actions[0] = 0
    elif failure == "row_order":
        report["rows"].reverse()
    elif failure == "text":
        report["rows"][0]["text_sha256"] = "other"
    elif failure == "length":
        report["rows"][0]["kept_tokens"] = 6
    elif failure == "latency":
        report["rows"][0]["total_seconds"] = 61
    else:
        report["mlx_peak_bytes"] = 8 * 1024**3
    with pytest.raises(ValueError):
        probe.validate_endpoint(report, request, states, actions)


def test_complete_synthetic_grid_fit_bounds_and_accounting():
    semantic, margin, d, t, z = data()
    ids = [f"fixture-{i}" for i in range(20)]
    panel = {"ids": ids, "d": d, "t": t, "z": z, "folds": {qid: i % 5 for i, qid in enumerate(ids)}}
    result = probe.analyze(panel, semantic, margin, np.full((20, 8), .25), np.full((20, 8), .001))
    assert result["fit_count"] == 450 and result["pca_fit_count"] == 75
    for name, condition in result["conditions"].items():
        draws = probe.SPEC["conditions"][name][1]
        for qid, record in condition["per_question"].items():
            i = ids.index(qid)
            for policy, row in record["policies"].items():
                decision = np.asarray(row["decisions"])
                tokens = (d[i, draws, 1] + decision * t[i, draws, 1]).mean()
                accuracy = np.where(decision, t[i, draws, 0], d[i, draws, 0]).mean()
                assert row["tokens"] == pytest.approx(tokens)
                assert row["utility"] == pytest.approx(accuracy - .05 * tokens / 1000)
            zero = record["policies"]["clm_zero_shot"]
            assert zero["cached_solver_plus_observed_router_seconds"] == pytest.approx(zero["seconds"] + .251)
            assert record["policies"]["nested_selected"]["decisions"] == record["policies"][condition["folds"][record["fold"]]["selected_family"]]["decisions"]


def test_invalid_partitions_are_rejected():
    semantic, margin, d, t, z = data()
    with pytest.raises(ValueError):
        probe.fit_fold(semantic, margin, d, t, z, [0, 1], [1, 2], [0, 1], [4, 5], 0)
    with pytest.raises(ValueError):
        probe.fit_fold(semantic, margin, d, t, z, list(range(4, 20)), list(range(4)), [0, 1, 2, 3], [3, 4, 5, 6], 0)
