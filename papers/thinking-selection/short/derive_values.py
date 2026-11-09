"""Derive the short paper's values that are not printed in a tracked report.

Reads only the published paper cache (verified by its checksum through the
reproduction script's loader); it fits nothing, generates nothing, and opens no
reference answer. Prints:

- how many main-panel questions contain a rescue, a harm, or either;
- the escalation rate of each follow-up rule in Table 1, from its recorded
  decisions (both four-draw directions, 400 states).

    PYTHONPATH=.:src .venv/bin/python papers/thinking-selection/short/derive_values.py [CACHE]
"""

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts.reproduce_paper import DEFAULT_CACHE, K4, arrays, load_cache  # noqa: E402


def main():
    cache = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CACHE
    repeat, _, families = arrays(load_cache(cache))
    direct, thinking = repeat[3][..., 0], repeat[4][..., 0]
    rescue = (direct == 0) & (thinking == 1)
    harm = (direct == 1) & (thinking == 0)
    result = {
        "cache_sha256_checked_by_loader": True,
        "rescues": int(rescue.sum()), "harms": int(harm.sum()),
        "questions_with_rescue": int(rescue.any(axis=1).sum()),
        "questions_with_harm": int(harm.any(axis=1).sum()),
        "questions_with_rescue_or_harm": int((rescue | harm).any(axis=1).sum()),
        "follow_up_escalation_rate": {
            name: {"escalations": int(sum(conds[c].sum() for c in K4)),
                   "states": int(sum(conds[c].size for c in K4)),
                   "rate": float(np.mean([conds[c].mean() for c in K4]))}
            for name, conds in families.items()},
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
