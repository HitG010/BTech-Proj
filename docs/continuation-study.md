# Learning when another draft is worth buying

## Why this step

The completed 50-question diagnostic favored the two-draft DART adaptation over
question-only routers. That finding motivated this experiment; it does not prove
a new routing method. See [the completed study](stronger-router-study.md).

The candidate predicts the **recoverability of a first answer**, not just its
confidence: could another computation rescue it, damage it, or leave it wrong?
After paying for one direct response, choose one of:

1. Accept that response.
2. Buy another direct response; accept the first if valid numerical answers
   agree, otherwise generate a thinking response.
3. Skip the agreement probe and generate a thinking response immediately.

For each continuation, a multinomial logistic head predicts the four joint
outcomes of first-answer correctness and continuation-answer correctness. A ridge
head predicts incremental tokens. Select the largest positive predicted
`P(rescue) - P(regression) - lambda * incremental_tokens / 1000`; otherwise accept.
This identity is standard expected-utility reasoning, **not a new theorem**.

Features available at the decision are the frozen MiniLM question embedding,
three lexical counts, and first-response mean decoder log-probability, length,
parse validity, and truncation. Training-only PCA reduces the embedding to 16
coordinates; scaling also fits only on training observations. No second response,
thinking output, or gold answer enters the deployed decision interface.

## Closest work and the novelty boundary

- [ReASC, ACL Findings 2026](https://aclanthology.org/2026.findings-acl.1085/)
  already gates single-sample acceptance and accumulates confidence-weighted
  evidence. A confidence gate before another sample is not our contribution.
- [Learning When to Sample](https://arxiv.org/abs/2603.08999) already learns
  whether a completed trajectory warrants further sampling.
- [Pandora's Router](https://arxiv.org/abs/2608.20316) already prices optional
  information before routing. “Value of information” is not a novelty claim.
- [DART's author implementation](https://github.com/js-lee-AI/DART) contains
  separate SC and SC-Budget routers. Our new SC comparator uses two initial
  drafts, a third on disagreement, majority acceptance, and thinking otherwise.
  The matched 512-answer/2,048-reasoning caps, decoder settings, and numerical
  parser are our adaptations; invalid parsed answers never establish consensus.
  This is not a full SC-Budget reproduction.

The testable distinction is **action-dependent rescue and regression under
correlated errors from the same model, with actual stochastic continuation costs**.
Superiority and originality remain unestablished. A gain over confidence alone
would be insufficient: the method must also compete with direct gain regression,
DART, and stronger adaptive consistency methods. The joint-probability
parameterization may offer no benefit at all; preserve that result if so.

If an edge survives, the more substantial next contribution is learning these
rare rescue/regression regions with fewer acquired traces: choose question,
continuation, and repeat jointly by expected policy improvement per token. That
requires comparison with ordinary uncertainty acquisition and targeted-error
acquisition. It is a later hypothesis, not an implemented contribution here.

## Frozen development protocol

- Train on the existing 100-question calibrated pilot, two samples per mode.
- Tune on the existing 100 validation questions, including the previous
  diagnostic. These questions already informed design and are explicitly
  development data now; they are not presented as fresh confirmation.
- Reserve 100 previously unused training-pool questions as a fresh diagnostic.
  `protocol.json` records exclusions and exact IDs. Never put these diagnostic
  IDs back into later training. The official 500-question test stays sealed.
- Freeze every model and threshold before generating fresh responses. Collect
  three direct and two thinking samples per diagnostic question: 500 records.
  The third draft enables the stronger DART SC comparator. Both first-draft
  orientations reuse these observations and are averaged within each question.
- Select one regularization setting per learned family at lambda=.05 on tuning
  data. The primary comparison is joint three-action routing minus the strongest
  tuned confidence-continuation baseline in utility at lambda=.05. The latter
  selects a threshold and whether low-confidence cases buy a draft or think.
- Comparators: always-direct, always-thinking, MiniLM/four-ridge, random
  direct/thinking allocation, random optional probes, confidence-to-probe,
  confidence-to-thinking, tuned confidence continuation, DART SC-2 and SC-3,
  and direct gain/cost ridge regression with identical observed features.
- Ablations remove question features, disallow immediate thinking, or omit the
  regression penalty. The last two are fixed-policy knockouts, not separately
  tuned optimal methods.
- Paired bootstrap resamples whole questions, not the correlated orientations.
  Secondary curves/ablations are descriptive, without multiple-comparison
  correction. Intervals do not estimate variation from retraining seeds.

All consumed first drafts, probes, and thinking tokens count toward inference
cost. All 500 cached generations count separately toward actual acquisition
expenditure, including outcomes a replay policy never requested. Historical
training-cache cost is also recorded separately. Token curves exclude CPU
encoding/routing and prompt-prefill costs; cached generation seconds are not an
end-to-end live latency benchmark. Live latency is required before claiming a
runtime improvement. The scoring audit is waived by user instruction, not done.

The current confidence signal is mean log-probability after decoder warping.
It is **not ReASC's bottom-group confidence**. Full ReASC and DART SC-Budget
reproductions remain requirements before broad published-baseline claims;
Qwen3-4B, a second task, and new seed repetitions remain confirmation work.

## Tracking and commands

Study directory: `artifacts/probe/continuation-v1/`.

Launch snapshot, 2026-09-18: models frozen, 103 offline tests passing, process
92189 collecting direct responses under `artifacts/runs/931c0e7a434abe265049`.
The first seven responses succeeded. This snapshot is not live; use the status
and log below for current progress. Fresh diagnostic accuracy has not been
inspected and no advantage is established yet.

```sh
uv run --locked rb probe prepare
HF_HUB_OFFLINE=1 OMP_NUM_THREADS=1 uv run --locked rb probe fit artifacts/probe/continuation-v1
HF_HUB_OFFLINE=1 MPLCONFIGDIR=.cache/matplotlib OMP_NUM_THREADS=1 \
  uv run --locked rb probe run artifacts/probe/continuation-v1
```

`run` resumes completed work and automatically scores and reports after both
generation stages. `status.json` shows the PID/stage; `runs.json` points to the
per-response records; `execution.log` tracks a launched background run.
`models.json` contains frozen models and tuning histories; `protocol.json`
contains the roles, configuration and code fingerprints. Finished outputs are
`report.md`, `report.json`, `curve.csv`, and `accuracy-cost.png`.

Local MPS/FP16 only, with cached Qwen3-1.7B. Limits: 170,000 direct-stage and
530,000 thinking-stage charged tokens; cumulative stage time limits of two and
five hours respectively; ten minutes per job. Expect roughly 4–5 local hours
from earlier throughput, but that is an estimate. The runner reserves maximum
tokens before a job, so it can pause before exhausting a numerical ceiling.
No cloud instance is launched, and cloud expenditure is $0. CPU fitting does
not fine-tune Qwen or MiniLM.

For inference, `reasoning_budget.probe.route_first(model, questions,
first_results, preference)` returns actions 0/1/2 without access to labels or
future responses. The caller must execute and charge requested continuations.
