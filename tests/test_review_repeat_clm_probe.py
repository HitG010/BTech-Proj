import importlib.util

import numpy as np
import pytest
import torch

from scripts import clm_local_preflight as local
from scripts.review_repeat_clm_probe import conditional_interval, functional_projection
from scripts.review_router_feasibility import interval


@pytest.mark.parametrize("depth,layernorm,residual,activation", [
    (2, False, False, "gelu"), (3, True, False, "relu"), (4, True, True, "silu")])
def test_functional_reviewer_matches_official_head_on_synthetic_values(depth, layernorm, residual, activation):
    spec = importlib.util.spec_from_file_location("synthetic_official_clm_heads", local.ENV / "assets/official-heads.py")
    if not (local.ENV / "assets/official-heads.py").exists():
        pytest.skip("Optional public CLM source is absent")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    torch.manual_seed(221)
    cfg = {"hidden_size": 16, "width": 12, "projection_dim": 8, "depth": depth,
           "layernorm": layernorm, "residual": residual, "activation": activation}
    head = module.make_head(width=12, hidden=16, proj=8, depth=depth,
        layernorm=layernorm, residual=residual, activation=activation).eval()
    values = torch.randn(5, 16)
    with torch.inference_mode():
        expected = torch.nn.functional.normalize(head(values), dim=-1)
        actual = functional_projection(values, head.state_dict(), cfg)
    np.testing.assert_allclose(actual.numpy(), expected.numpy(), atol=1e-7, rtol=0)


def test_seed_discrepancy_is_preserved_and_corrected_additively():
    values = np.random.default_rng(63).normal(size=50)
    original = interval(values, 20261002)
    correction = conditional_interval(original, values, 20261002, 20261006)
    assert correction["original_ci90"] == original
    expected = np.quantile(values[np.random.default_rng(20261006).integers(0, 50, (2000, 50))].mean(1), [.05, .95])
    np.testing.assert_array_equal(correction["protocol_ci90"], expected)
    assert correction["protocol_ci90"] != original
    with pytest.raises(AssertionError):
        conditional_interval([0, 0], values, 20261002, 20261006)
