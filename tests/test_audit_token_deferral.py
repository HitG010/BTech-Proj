import numpy as np
import pytest

from reasoning_budget import repeat_stats as historical
from scripts import audit_token_deferral as audit

SMALL = {**audit.SPEC, "bootstrap_draws": 200}


def reference_warp(logits, token, temperature, top_k, top_p):
    """Independent full-vocabulary temperature, top-k, top-p in transformers order."""
    scores = np.asarray(logits, dtype=float) / temperature
    scores = np.where(scores < np.sort(scores)[-top_k], -np.inf, scores)
    order = np.argsort(scores)
    probabilities = np.exp(scores[order] - scores.max())
    probabilities /= probabilities.sum()
    remove = np.cumsum(probabilities) <= 1 - top_p
    remove[-1] = False
    scores[order[remove]] = -np.inf
    if not np.isfinite(scores[token]):
        return -np.inf
    kept = scores[np.isfinite(scores)]
    return scores[token] - kept.max() - np.log(np.exp(kept - kept.max()).sum())


def test_warped_logprobs_match_full_vocabulary_reference():
    rng = np.random.default_rng(0)
    logits = rng.normal(0, 3, size=(40, 300))
    tokens = rng.integers(0, 300, size=40)
    tokens[:15] = logits[:15].argmax(1)
    order = np.argsort(-logits, axis=1)[:, :20]
    top_values = np.take_along_axis(logits, order, axis=1)
    got = audit.warped_logprobs(top_values, order, tokens, 0.7, 0.8)
    expected = [reference_warp(row, token, 0.7, 20, 0.8) for row, token in zip(logits, tokens)]
    np.testing.assert_allclose(got, expected)
    assert np.isfinite(got[:15]).all() and np.isinf(got[15:]).any()


def test_warped_logprobs_reject_unsorted_or_misaligned_inputs():
    with pytest.raises(ValueError):
        audit.warped_logprobs([[1.0, 2.0]], [[0, 1]], [0], 0.7, 0.8)
    with pytest.raises(ValueError):
        audit.warped_logprobs([[2.0, 1.0]], [[0, 1]], [0, 1], 0.7, 0.8)


def test_quantile_features_order_and_values():
    raw = [-3.0, -1.0, -0.5, -0.1, 0.0]
    features = audit.quantile_features(raw)
    assert len(features) == len(audit.FEATURES) == 11
    assert features[0] == -3.0 and features[4] == -0.5 and features[8] == 0.0
    assert features[9] == pytest.approx(np.mean(raw))
    assert features[10] == pytest.approx(np.log1p(5))
    for bad in ([], [np.nan], [[1.0]]):
        with pytest.raises(ValueError):
            audit.quantile_features(bad)


def fidelity_row(i, difference=0.0, **changes):
    row = {"job_id": f"j{i}", "question_id": f"q{i // 8}", "sample": i % 8,
           "prompt_tokens": 100, "recorded_prompt_tokens": 100, "answer_tokens": 20,
           "recorded_answer_tokens": 20, "decoded_matches": True,
           "raw_mean": -0.3 + difference, "recorded_raw_mean": -0.3,
           "warped_mean": -0.1, "recorded_warped_mean": -0.1, "warped_support_misses": 0}
    return row | changes


def test_fidelity_gate_boundaries():
    assert audit.fidelity([fidelity_row(i, 0.001) for i in range(400)])["passed"]
    rows = [fidelity_row(i, 0.05 if i < 4 else 0.0) for i in range(400)]
    assert audit.fidelity(rows)["passed"]
    rows = [fidelity_row(i, 0.05 if i < 5 else 0.0) for i in range(400)]
    assert not audit.fidelity(rows)["checks"]["raw_mean_share_within_tolerance"]
    rows = [fidelity_row(i) for i in range(400)]
    rows[0]["raw_mean"] = -0.15
    report = audit.fidelity(rows)
    assert not report["passed"] and not report["checks"]["raw_mean_maximum_difference"]


@pytest.mark.parametrize("key,value", [("prompt_tokens", 99), ("answer_tokens", 19),
                                       ("decoded_matches", False), ("recorded_raw_mean", None),
                                       ("sample", 0)])
def test_fidelity_gate_fails_on_each_identity_check(key, value):
    rows = [fidelity_row(i) for i in range(400)]
    rows[3][key] = value
    assert not audit.fidelity(rows)["passed"]


def test_fidelity_requires_every_draft():
    assert not audit.fidelity([fidelity_row(i) for i in range(399)])["passed"]


def synthetic_panel(signal, seed=0):
    rng = np.random.default_rng(seed)
    n = 50
    ids = [f"q{i:02d}" for i in range(n)]
    folds = {qid: i % 5 for i, qid in enumerate(ids)}
    q = rng.normal(size=(n, 387))
    hard = rng.random((n, 8)) < 0.15
    d, t = np.zeros((n, 8, 3)), np.zeros((n, 8, 3))
    d[..., 0], t[..., 0] = (~hard).astype(float), 1.0
    d[..., 1], t[..., 1], d[..., 2], t[..., 2] = 200.0, 1000.0, 1.0, 5.0
    z = rng.normal(size=(n, 8, 4))
    z[..., 0] = rng.normal(-0.3, 0.05, size=(n, 8))
    rows, job_ids = [], {}
    for i, qid in enumerate(ids):
        for s in range(8):
            raw = rng.normal(-0.2, 0.05, size=int(rng.integers(20, 60)))
            if (hard[i, s] if signal else rng.random() < 0.15):
                raw[int(rng.integers(len(raw)))] = -6.0
            job = f"{qid}-direct-{s}"
            job_ids[qid, s] = job
            rows.append({"job_id": job, "question_id": qid, "sample": s,
                         "raw_logprobs": raw.tolist(), "recorded_warped_mean": float(z[i, s, 0])})
    features, recorded = audit.feature_tensor(ids, rows, job_ids)
    assert np.array_equal(recorded, z[..., 0])
    return (ids, q, d, t, z, folds), features


@pytest.fixture(scope="module")
def informative():
    data, features = synthetic_panel(signal=True)
    return data, features, audit.analyze(data, features, spec=SMALL)


def test_informative_token_feature_passes_the_primary_screen(informative):
    _, _, result = informative
    primary = result["average_vs_confidence"]["learned_error_score"]
    assert result["primary_reading"] == "pass" and primary["screen"]["passes"]
    assert primary["accuracy"] == 1.0 and primary["mean"] > 0.01 and primary["ci90"][0] > 0
    assert result["average_vs_confidence"]["min_token_threshold"]["mean"] > 0.01
    assert not result["historical_actions_verified"]


def test_confidence_is_the_zero_reference_and_conditions_are_complete(informative):
    _, _, result = informative
    assert set(result["conditions"]) == {"k4_A_to_B", "k4_B_to_A", "k8_full"}
    for condition in result["conditions"].values():
        summary = condition["summary"]
        assert set(audit.CANDIDATES) | {"accept", "escalate", "confidence"} == set(summary)
        assert summary["confidence"]["delta_vs_confidence"]["mean"] == 0
        assert len(condition["folds"]) == 5


def test_uninformative_token_feature_does_not_pass():
    data, features = synthetic_panel(signal=False, seed=1)
    result = audit.analyze(data, features, spec=SMALL)
    assert result["primary_reading"] == "fail"


def test_analysis_is_deterministic(informative):
    data, features, result = informative
    assert audit.analyze(data, features, spec=SMALL) == result


def test_score_threshold_matches_historical_confidence_search():
    data, _ = synthetic_panel(signal=True)
    ids, q, d, t, z, folds = data
    train = np.arange(40)
    assert audit.score_threshold(z[..., 0], d, t, train, [0, 1, 2, 3], 0.05) == \
        historical._confidence_threshold(z, d, t, train, [0, 1, 2, 3], 0.05)


def test_feature_tensor_rejects_mismatched_duplicate_or_missing_rows():
    ids = ["a", "b"]
    job_ids = {(qid, s): f"{qid}{s}" for qid in ids for s in range(2)}
    rows = [{"job_id": f"{qid}{s}", "question_id": qid, "sample": s, "raw_logprobs": [-0.1, -0.2],
             "recorded_warped_mean": -0.1} for qid in ids for s in range(2)]
    features, _ = audit.feature_tensor(ids, rows, job_ids, draws=2)
    assert features.shape == (2, 2, 11)
    for broken in (rows[:-1], rows + [rows[0]],
                   [rows[0] | {"job_id": "other"}] + rows[1:]):
        with pytest.raises(ValueError):
            audit.feature_tensor(ids, broken, job_ids, draws=2)


def test_descriptive_auroc_and_length_correlation(informative):
    data, features, _ = informative
    _, _, d, t, z, _ = data
    stats = audit.descriptive(features, z, d, t)
    assert stats["pooled_auroc"]["negative_min_token"]["incorrect_direct"] > 0.95
    assert 0.3 < stats["pooled_auroc"]["negative_recorded_confidence"]["incorrect_direct"] < 0.7
    assert set(stats["spearman_with_log_length"]) == {"recorded_confidence", "min_token"}


def test_markdown_renders_complete_report(informative):
    data, features, result = informative
    _, _, d, t, z, _ = data
    result = result | {"descriptive": audit.descriptive(features, z, d, t)}
    fid = audit.fidelity([fidelity_row(i) for i in range(400)])
    text = audit.markdown({"statistics": result, "extraction_fidelity": fid})
    assert "Primary reading (learned error score): **pass**" in text
    assert all(name in text for name in audit.CANDIDATES)


def test_spec_and_sources_are_frozen_as_declared():
    assert audit.SPEC["primary_candidate"] == "learned_error_score"
    assert audit.SPEC["candidates"] == list(audit.CANDIDATES)
    assert audit.SPEC["bootstrap_draws"] == 2000 and audit.SPEC["interval"] == [0.05, 0.95]
    assert audit.SPEC["primary_conditions"] == ["k4_A_to_B", "k4_B_to_A"]
    assert all((audit.ROOT / name).is_file() for name in audit.SOURCE_FILES)
    assert audit.OUTPUT.parent == audit.BASE == audit.REPEAT.parent


def test_teacher_forcing_reproduces_backend_stage_confidence():
    """Real backend._stage on a tiny random Qwen3 versus one teacher-forced pass."""
    from types import SimpleNamespace

    torch = pytest.importorskip("torch")
    transformers = pytest.importorskip("transformers")
    from reasoning_budget.backend import TransformersBackend

    torch.manual_seed(0)
    config = transformers.Qwen3Config(
        vocab_size=64, hidden_size=32, intermediate_size=64, num_hidden_layers=2,
        num_attention_heads=4, num_key_value_heads=2, head_dim=8,
        max_position_embeddings=128, tie_word_embeddings=False)
    model = transformers.Qwen3ForCausalLM(config).eval()
    with torch.no_grad():
        model.lm_head.weight.mul_(8)
    engine = object.__new__(TransformersBackend)
    engine.torch, engine.model, engine.close_id, engine.eos_ids = torch, model, 63, [62]
    engine.config = SimpleNamespace(model=SimpleNamespace(device="cpu"))
    engine.generation_configs = {"direct": transformers.GenerationConfig(
        do_sample=True, temperature=0.7, top_k=20, top_p=0.8, min_p=0.0,
        repetition_penalty=1.0, num_beams=1, use_cache=True, eos_token_id=[62],
        pad_token_id=62, bos_token_id=1)}
    prefix = [1, 5, 9, 12, 7, 30]
    torch.manual_seed(3)
    tokens, _, _, logprob, logprob_raw = engine._stage(
        prefix, 24, "direct", float("inf"), confidence=True)
    raw, top_values, top_indices = audit.teacher_force(engine, prefix, tokens, 20)
    warped = audit.warped_logprobs(top_values, top_indices, tokens, 0.7, 0.8)
    assert len(raw) == len(tokens) > 5
    assert float(raw.mean()) == pytest.approx(logprob_raw, abs=1e-5)
    assert np.isfinite(warped).all()
    assert float(warped.mean()) == pytest.approx(logprob, abs=1e-5)
    shifted, _, _ = audit.teacher_force(engine, prefix[:-1], [prefix[-1], *tokens[:-1]], 20)
    assert abs(float(shifted.mean()) - logprob_raw) > 1e-3
