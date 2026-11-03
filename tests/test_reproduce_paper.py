import copy
import json
import sys
from pathlib import Path

import numpy as np
import pytest

from reasoning_budget.storage import envelope
from scripts import audit_deferral_curves as audit
from scripts import reproduce_paper as rp

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_audit_deferral_curves import repeat_panel, two_solver_panel  # noqa: E402


def confidence_decisions(repeat):
    ids, q, z, d, t, fold_of, _, _ = repeat
    base = audit.historical_spec()
    return {name: audit.run_condition(q, z, d, t, fold_of, *audit.K4[name], base)[0]["confidence"]
            for name in rp.K4}


def synthetic_families(repeat, seed=3):
    rng = np.random.default_rng(seed)
    confidence = confidence_decisions(repeat)
    families = {}
    for i, name in enumerate(rp.FAMILIES):
        if i == 0:
            families[name] = {c: confidence[c].tolist() for c in rp.K4}
        else:
            families[name] = {c: (rng.random((50, 4)) < 0.3).tolist() for c in rp.K4}
    return families


@pytest.fixture(scope="module")
def cache_path(tmp_path_factory):
    repeat, two = repeat_panel(), two_solver_panel()
    payload = rp.build_payload(repeat, two, synthetic_families(repeat),
                               {"note": "synthetic"})
    path = tmp_path_factory.mktemp("cache") / "paper-cache.json"
    path.write_text(json.dumps(envelope(payload), allow_nan=False))
    return path


@pytest.fixture(scope="module")
def results(cache_path):
    repeat, two, families = rp.arrays(rp.load_cache(cache_path))
    return rp.recompute(repeat, two, families, processes=1, skip_refit=True)


def expected_from(results):
    table1 = {name: {k: v for k, v in row.items() if k != "escalations"}
              for name, row in results["table1"].items()}
    table2 = {name: {k: v for k, v in row.items() if v is not None}
              for name, row in results["table2"].items()}
    return table1, table2, dict(results["text"])


def test_cache_round_trip_preserves_every_array(cache_path):
    repeat, two = repeat_panel(), two_solver_panel()
    got_repeat, got_two, families = rp.arrays(rp.load_cache(cache_path))
    for a, b in zip(got_repeat[1:6], repeat[1:6]):
        np.testing.assert_array_equal(a, np.asarray(b))
    assert got_repeat[0] == repeat[0]
    assert got_repeat[6].tolist() == repeat[6].tolist() and None in got_repeat[6].ravel()
    assert got_repeat[7].tolist() == repeat[7].tolist()
    for solver in rp.SOLVERS:
        for key, value in two[2][solver].items():
            assert got_two[2][solver][key].tolist() == np.asarray(value).tolist()
    assert set(families) == set(rp.FAMILIES)
    assert all(v.shape == (50, 4) and v.dtype == bool for f in families.values()
               for v in f.values())


def test_load_cache_rejects_wrong_format_and_missing_family(tmp_path, cache_path):
    payload = rp.load_cache(cache_path)
    bad = copy.deepcopy(payload)
    bad["format"] = "other"
    (tmp_path / "a.json").write_text(json.dumps(envelope(bad)))
    with pytest.raises(ValueError):
        rp.load_cache(tmp_path / "a.json")
    bad = copy.deepcopy(payload)
    bad["family_decisions"].pop("cpu_selected")
    (tmp_path / "b.json").write_text(json.dumps(envelope(bad)))
    with pytest.raises(ValueError):
        rp.load_cache(tmp_path / "b.json")
    tampered = json.loads(cache_path.read_text())
    tampered["payload"]["repeat"]["folds"][0] = 4 - tampered["payload"]["repeat"]["folds"][0]
    (tmp_path / "c.json").write_text(json.dumps(tampered))
    with pytest.raises(ValueError):
        rp.load_cache(tmp_path / "c.json")


def test_family_decisions_follow_report_layout_and_check_confidence():
    ids = ["q1", "q2"]
    confidence = {c: {"q1": [True, False, False, False], "q2": [False] * 4} for c in rp.K4}
    report = {"statistics": {"conditions": {
        theirs: {"per_question": {qid: {"policies": {
            "confidence": {"decisions": confidence[ours][qid]},
            "nested_selected": {"decisions": [True, True, False, False]}}} for qid in ids}}
        for ours, theirs in zip(rp.K4, ("A4_to_B4", "B4_to_A4"))}}}
    got = rp.family_decisions(report, ("statistics", "conditions"), ("A4_to_B4", "B4_to_A4"),
                              "nested_selected", ids, confidence)
    assert got["k4_A_to_B"] == [[True, True, False, False]] * 2
    broken = copy.deepcopy(report)
    broken["statistics"]["conditions"]["A4_to_B4"]["per_question"]["q2"]["policies"][
        "confidence"]["decisions"] = [True] * 4
    with pytest.raises(ValueError):
        rp.family_decisions(broken, ("statistics", "conditions"), ("A4_to_B4", "B4_to_A4"),
                            "nested_selected", ids, confidence)
    broken = copy.deepcopy(report)
    broken["statistics"]["conditions"]["B4_to_A4"]["per_question"]["q1"]["policies"][
        "nested_selected"]["decisions"] = [True, False]
    with pytest.raises(ValueError):
        rp.family_decisions(broken, ("statistics", "conditions"), ("A4_to_B4", "B4_to_A4"),
                            "nested_selected", ids, confidence)


def test_public_identity_keeps_hashes_and_drops_local_details():
    identity = {"study": "/Users/someone/project/artifacts/x/opportunity-panel-v1",
                "report_sha256": "abc", "runtime_environment": {"platform": "macOS"}}
    assert rp.public_identity(identity) == {"report_sha256": "abc",
                                            "study": "opportunity-panel-v1"}


def test_family_matching_confidence_has_zero_difference(results):
    first = next(iter(rp.FAMILIES))
    row = results["table1"][first]
    conf = results["table1"]["confidence"]
    assert row["delta"] == pytest.approx(0, abs=1e-12) and row["ci90"] == [0.0, 0.0]
    assert row["accuracy"] == pytest.approx(conf["accuracy"])
    assert row["tokens"] == pytest.approx(conf["tokens"])
    assert row["lift"] == pytest.approx(conf["lift"])


def test_family_row_without_escalation_equals_always_direct(results):
    repeat = repeat_panel()
    _, _, z, d, t, _, _, _ = repeat
    decisions = {c: np.zeros((50, 4), dtype=bool) for c in rp.K4}
    confidence = {c: np.zeros(50) for c in rp.K4}
    refs = audit.references(audit.repeat_states(d, t, z, audit.K4), 0.05)
    row = rp.family_row(decisions, d, t, confidence, refs, 20261002)
    direct = results["table1"]["always_direct"]
    assert row["accuracy"] == pytest.approx(direct["accuracy"])
    assert row["tokens"] == pytest.approx(direct["tokens"])
    assert row["lift"] == pytest.approx(0, abs=1e-12) and row["escalations"] == 0


def test_recomputed_values_are_internally_consistent(results):
    t1, text = results["table1"], results["text"]
    assert t1["confidence"]["delta"] == 0
    assert t1["always_direct"]["delta"] == pytest.approx(
        -results["table2"]["repeat_confidence_minus_accept"]["point"], abs=1e-12)
    assert t1["combined"]["delta"] == results["table2"]["repeat_combined_minus_confidence"]["point"]
    assert sum(text[k] for k in ("repeat_rescues", "repeat_harms", "repeat_both_correct",
                                 "repeat_both_wrong")) == 400
    assert all(results["table2"][k]["refit"] is None for k in results["table2"])
    assert [r["lambda"] for r in results["sweeps"]["repeat_qwen3_1.7b"]] == \
        audit.SPEC["lambda_grid"]
    assert set(t1) == set(rp.TABLE1) and set(results["table2"]) == set(rp.TABLE2)
    assert set(results["text"]) == set(rp.TEXT)


def test_compare_passes_self_and_flags_a_perturbation(results):
    table1, table2, text = expected_from(results)
    checks = rp.compare(results, table1, table2, text)
    assert checks and all(c["passed"] for c in checks)
    assert all(c.get("skipped") for c in checks if c["field"] in ("refit", "repartition"))
    table1["combined"]["delta"] += 1e-5
    text["repeat_rescues"] += 1
    failed = [c for c in rp.compare(results, table1, table2, text) if not c["passed"]]
    assert {(c["item"], c["field"]) for c in failed} == {("combined", "delta"),
                                                         ("repeat_rescues", "value")}


def test_compare_figure_against_manifest_layout(results):
    figure = {key: {"sweep": copy.deepcopy(rows)} for key, rows in results["sweeps"].items()}
    assert all(c["passed"] for c in rp.compare(results, {}, {}, {}, figure=figure))
    figure["two_solver_qwen3_0.6b"]["sweep"][4]["confidence"]["tokens"] += 1.0
    failed = [c for c in rp.compare(results, {}, {}, {}, figure=figure) if not c["passed"]]
    assert len(failed) == 1 and "λ=0.05" in failed[0]["item"]


def test_published_figure_manifest_is_readable():
    values = rp.figure_values()
    assert set(values) == {"repeat_qwen3_1.7b", "two_solver_qwen3_0.6b", "two_solver_qwen3_1.7b"}
    assert all(len(v["sweep"]) == 10 for v in values.values())
    assert "combined" in values["repeat_qwen3_1.7b"]["sweep"][0]
    assert rp.figure_values("/nonexistent/manifest.json") is None


def test_check_writes_reports_and_refuses_to_overwrite(tmp_path, cache_path, results):
    expected = expected_from(results)
    report = rp.check(cache_path, tmp_path / "out", skip_refit=True, figure=None,
                      expected=expected)
    assert report["passed"] and report["results"]["refit_skipped"]
    text = (tmp_path / "out" / "reproduction.md").read_text()
    assert "All published values reproduced." in text and "Two-draft agreement" in text
    json.loads((tmp_path / "out" / "reproduction.json").read_text())
    with pytest.raises(FileExistsError):
        rp.check(cache_path, tmp_path / "out", skip_refit=True, figure=None, expected=expected)
    bad = (expected[0], expected[1], dict(expected[2], repeat_harms=-1))
    report = rp.check(cache_path, tmp_path / "out2", skip_refit=True, figure=None, expected=bad)
    assert not report["passed"]
    assert "MISMATCHES FOUND" in (tmp_path / "out2" / "reproduction.md").read_text()


def test_export_refuses_to_overwrite(tmp_path):
    existing = tmp_path / "paper-cache.json"
    existing.write_text("{}")
    with pytest.raises(FileExistsError):
        rp.export(existing)


def test_published_constants_cover_the_paper_tables():
    assert set(rp.TABLE1) == {"always_direct", "always_think", "oracle", "confidence",
                              "combined", "agreement", *rp.FAMILIES}
    assert set(rp.LABELS) == set(rp.TABLE1)
    assert len(rp.TABLE2) == 5 and all(set(v) == {"point", "fixed", "refit", "repartition"}
                                       for v in rp.TABLE2.values())
    seeds = {name: spec[4] for name, spec in rp.FAMILIES.items()}
    assert seeds["cpu_selected"] == 20261002 and seeds["neural_selected"] == 20261004
    assert {seeds[k] for k in ("clm_zero_shot", "clm_calibrated", "pca8_ridge",
                               "clm_raw_selected")} == {20261006}
    assert {seeds[k] for k in ("token_learned_error", "token_min_threshold",
                               "token_gain_ridge")} == {20261030}
    assert all(v["ci90"][0] <= v["delta"] <= v["ci90"][1]
               for v in rp.TABLE1.values() if "ci90" in v)
