from types import SimpleNamespace

import numpy as np
import pytest

from scripts.clm_local_preflight import SPEC, check_geometry, selected_download_size, synthetic_ids


class Tokenizer:
    def encode(self, text, add_special_tokens):
        assert add_special_tokens is False
        return [11, 23, 42]


def test_synthetic_sequence_has_exact_bounded_length_without_special_tokens():
    assert synthetic_ids(Tokenizer(), "fixture", 5) == [11, 23, 42, 11, 23]
    assert len(synthetic_ids(Tokenizer(), "fixture", 2047)) == 2047
    with pytest.raises(ValueError):
        synthetic_ids(Tokenizer(), "fixture", 2048)


def test_download_size_requires_complete_metadata_and_excludes_other_files():
    info = SimpleNamespace(siblings=[SimpleNamespace(rfilename="a", size=5),
        SimpleNamespace(rfilename="b", size=10)])
    assert selected_download_size(info, ["a"]) == 5
    with pytest.raises(ValueError):
        selected_download_size(info, ["c"])
    info.siblings[0].size = None
    with pytest.raises(ValueError):
        selected_download_size(info, ["a"])


def endpoint():
    rows = [{"id": f"synthetic-{length}-{repeat}", "input_tokens": length, "seconds": 0.5}
        for length in SPEC["sequence_lengths"] for repeat in range(2)]
    rows += [{"id": f"action-{i}", "input_tokens": 16, "seconds": 0.2} for i in range(2)]
    vectors = np.zeros((10, 4096), dtype=np.float32)
    vectors[:, 0] = 1
    return rows, vectors


def test_geometry_rejects_nonfinite_or_zero_norm_outputs():
    rows, vectors = endpoint()
    assert check_geometry(rows, vectors)["maximum_identical_input_difference"] == 0
    vectors[0] = 0
    with pytest.raises(ValueError):
        check_geometry(rows, vectors)
    vectors[0, 0] = np.nan
    with pytest.raises(ValueError):
        check_geometry(rows, vectors)


def test_geometry_rejects_nonrepeating_or_incomplete_endpoint():
    rows, vectors = endpoint()
    vectors[1] = 0
    vectors[1, 1] = 1
    with pytest.raises(ValueError):
        check_geometry(rows, vectors)
    with pytest.raises(ValueError):
        check_geometry(rows[:-1], vectors[:-1])


def test_geometry_rejects_unprescribed_length_and_excessive_latency():
    rows, vectors = endpoint()
    rows[0]["input_tokens"] += 1
    with pytest.raises(ValueError):
        check_geometry(rows, vectors)
    rows, vectors = endpoint()
    rows[-1]["seconds"] = 61
    with pytest.raises(ValueError):
        check_geometry(rows, vectors)
