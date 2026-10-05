"""Synthetic question-role and prospective power/budget safeguards."""

import copy

import pytest
from scipy.stats import norm

from reasoning_budget.storage import digest
from scripts.qwen06_next_design import audit_roles, calculate


def fixture():
    rows = [{"question": {"id": f"q{i}", "prompt": f"question {i}"},
             "normalized_prompt_sha256": f"prompt{i}", "upstream_index": i}
            for i in range(3)]
    parent = {"roles": {"reserve": rows}}
    child = {"parent_payload_sha256": digest(parent), "selected": [
        {"parent_question": rows[0]["question"],
         "normalized_prompt_sha256": "prompt0", "upstream_index": 0}]}
    return parent, child


def test_role_audit_is_read_only_and_rejects_duplicate_children():
    parent, child = fixture()
    before = copy.deepcopy(parent)
    assert audit_roles(parent, [child])["unclaimed"] == 2
    assert parent == before
    with pytest.raises(ValueError, match="duplicate"):
        audit_roles(parent, [child, child])
    bad = copy.deepcopy(child)
    bad["selected"][0]["upstream_index"] = 1
    with pytest.raises(ValueError, match="source"):
        audit_roles(parent, [bad])


def test_power_and_budget_are_sensitivity_not_a_claim_for_one_percent():
    result = calculate({"unclaimed": 484}, 512, 2562)
    design = result["conditional_design"]
    assert (design["responses"], design["response_only_token_bound"],
            design["remaining_reserve_if_allocated"]) == (456, 700872, 256)
    cell = next(x for x in result["power_grid"] if x["effect"] == .01 and x["sd"] == .16)
    assert cell["required_n_80pct"] == 2010
    expected = norm.cdf(.01 * 228**.5 / .16 - norm.ppf(.975)) + norm.cdf(
        -.01 * 228**.5 / .16 - norm.ppf(.975))
    assert cell["power_by_n"]["228"] == pytest.approx(expected)
    assert expected < .2
    with pytest.raises(ValueError, match="capacity"):
        calculate({"unclaimed": 227}, 512, 2562)
