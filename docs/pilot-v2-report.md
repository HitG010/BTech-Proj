# Pilot v2 feasibility report

Run `f73a5665230cd83a7f12` (`configs/pilot_v2.yaml`), Qwen3-1.7B at commit `70d244cc…`,
Mac M2 Pro, MPS fp16, batch one. 100 GSM8K pilot questions × 2 samples × 2 modes,
400/400 jobs complete, 4.93 hours including setup, 410,462 charged tokens, cloud
billing $0. Scorer `numeric-v4`. Written 2026-09-10 on branch `research/pilot-v2`.

**Status: provisional.** The agent pre-screen found no scorer defect
(`docs/pilot-v2-prescreen.md`), but the 50-row human audit in the run's `audit.json`
has not been done. The protocol requires it before any number here is treated as
accepted.

## 1. Summary and recommendation

- **Pipeline: go.** Protocol v2 removes the v1 artifact. No answer of the 400 was cut
  short except three on questions the model treats as contradictory; every response
  ended naturally; the scorer handled every format the model produced.
- **Compute: go only with a batched engine.** At the observed lengths the full
  programme for one model is about 13 million generated tokens: 157 local hours for
  the 1.7B model and an assumed 394 for the 4B. At a 2,000 tokens/s cloud scenario that
  is 1.8 and 4.6 GPU-hours, about $6.4 at $1/hour. The vLLM backend in `plan.md` must
  exist before the training cache is generated.
- **Headroom on GSM8K with Qwen3-1.7B: too small to carry the accuracy claim.**
  Thinking beats direct by 10 points (83.5% versus 93.0%, interval [3, 16] points),
  and the per-question oracle reaches 96.0%. But a free confidence signal already
  closes the gap: routing on the direct answer's log-probability reaches 93.0% while
  sending 40% of questions to thinking (in-sample threshold, so optimistic). That
  leaves at most three points between the strongest cheap baseline and the oracle,
  below the four-point minimum detectable difference on the 500-question test set.
  A learned controller can still win on **cost** (it decides from the question alone
  and never pays for the direct answer it would discard), and that comparison is
  well powered because token counts have low variance. The acquisition method's
  effect, a second-order improvement to the controller, is unlikely to be detectable
  on GSM8K alone.
- **Recommendation for the supervisor:** keep GSM8K as one setting, reframe the primary
  metric as tokens at matched accuracy (the accuracy–cost curve), and add a setting
  with a wider thinking gap before Milestone D: the numeric-answer subset of MATH or
  GSM-Plus (the Qwen3 report gives 1.7B MATH-500 thinking 93.4 versus non-thinking
  73.0), or promote the procedural tasks with tunable difficulty from confirmation to
  primary. Enlarge the training pool so the breadth baseline exists.
- **Forced closure: 7.0% against the 5% gate.** Recommend keeping 4,096 reasoning tokens
  and reporting the rate. The 14 exceedances concentrate on five questions the model
  finds contradictory, seven of the 14 still scored correct after the budget phrase,
  and direct mode fails the same questions. Testing 8,192 is cheap once a cloud backend
  exists; on the Mac it would add hours for a tail the model cannot resolve.

## 2. Protocol v2 as run

Prompt suffix "Please reason step by step, and put your final answer within
\boxed{}." for both modes; direct is Qwen3 non-thinking mode with natural working;
4,096 reasoning tokens then 1,024 answer tokens; forced closure inserts the Qwen3
report's budget phrase (23 tokens); decoding per model card; both EOS ids; post-warper
and raw-logit mean log-probability stored for direct answers.

## 3. Results

| Mode | Accuracy | Untruncated accuracy | Truncated at 1,024 | Forced closure at 4,096 | Generated tokens mean / p90 / max | Seconds mean / p90 | Tokens per second |
|---|---:|---:|---:|---:|---:|---:|---:|
| Direct | 83.5% (167/200) | 84.3% | 2 | 0 | 301 / 420 / 1,024 | 12.9 / 18.4 | 23.3 |
| Thinking | 93.0% (186/200) | 93.5% | 1 | 14 (7.0%) | 1,751 / 3,646 / 5,143 | 75.6 / 155.1 | 23.2 |

Thinking costs 5.8× the tokens and 5.8× the time of direct per response. Parser
statuses: direct 195 ok, 2 conflicting (hedged boxes), 1 invalid (two quantities boxed),
2 incomplete; thinking 199 ok, 1 incomplete.

Paired thinking minus direct accuracy: **+0.10**, whole-question bootstrap 95% interval
**[0.03, 0.16]** (2,000 draws, seed 20260909). Pilot v1 had shown -0.17 under the
truncating protocol; the sign reversal is entirely the protocol change.

Per-question outcome matrix (direct correct of 2, thinking correct of 2):

| Direct | Thinking | Questions |
|---:|---:|---:|
| 2 | 2 | 73 |
| 1 | 2 | 9 |
| 0 | 2 | 7 |
| 2 | 1 | 4 |
| 0 | 1 | 2 |
| 1 | 1 | 2 |
| 0 | 0 | 2 |
| 2 | 0 | 1 |

Thinking is better on 18 questions, direct on 5, equal on 77; the decision-relevant
fraction is 23%. Within-mode sample disagreement: direct 11%, thinking 8%. Both
modes always wrong on 2 questions; both always right on 73.

Direct-answer confidence as a predictor of correctness (200 answers): AUROC 0.82 for
the post-warper mean log-probability and 0.83 for the raw-logit version; the raw
value was below the post-warper value on every row, as renormalisation predicts.

Scoring thinking by the reasoning's own last stated answer instead of the final
response would give 93.5% instead of 93.0%: in two responses the reasoning had the
gold answer and the final response lost it, in one the final response corrected the
reasoning. The protocol keeps the final response.

## 4. Headroom

| Policy on the 100 pilot questions | Accuracy | Mean tokens per question |
|---|---:|---:|
| Always direct | 83.5% | 301 |
| Random 40% to thinking (mean of 200 draws) | 87.5% | about 880 |
| Confidence routing, raw log-prob, 40% to thinking (in-sample threshold) | 93.0% | 1,016 + 0.4 × 301 for the discarded direct answers = about 1,140 |
| Always thinking | 93.0% | 1,751 |
| Oracle best mode per question (same samples) | 96.0% | n/a |

Confidence routing at 20% to thinking already gives 90.5% at about 760 tokens. These
thresholds were chosen on the same 100 questions, so the curve is an upper bound on
what a held-out threshold achieves; the point stands that the cheapest baseline sits
within three points of the oracle. A learned controller's structural advantage is
that it never generates the direct answer for questions it routes, saving those 301
tokens; that is the quantity to measure.

## 5. Power

Per-question paired-difference SD between thinking and direct is 0.33. At 500 test
questions the standard error is 0.015 and the minimum detectable difference at 80%
power and two-sided 5% is about **0.04**. Two policies that agree on most questions
have a smaller SD, so about three points is the practical floor for detecting an
accuracy difference between a learned controller and confidence routing. Token
differences of 10% are detectable with far fewer questions.

## 6. Cost projection

Basis: observed mean tokens per response (direct 301, thinking 1,751) and 23 tokens/s
on the Mac; the 4B slowdown of 2.5× and the 2,000 tokens/s cloud figure are
assumptions to be replaced by measurement.

| Component | Responses per mode | Tokens | Local hours 1.7B | Local hours 4B (assumed) | Cloud hours 1.7B | Cloud hours 4B (assumed) |
|---|---:|---:|---:|---:|---:|---:|
| Training cache 400 × 8 pairs | 3,200 | 6.57 M | 78.7 | 196.8 | 0.91 | 2.28 |
| Validation 100 × 2 | 200 | 0.41 M | 4.9 | 12.3 | 0.06 | 0.14 |
| GSM8K test 500 × 2 | 1,000 | 2.05 M | 24.6 | 61.5 | 0.29 | 0.71 |
| SVAMP 500 × 2 | 1,000 | 2.05 M | 24.6 | 61.5 | 0.29 | 0.71 |
| Procedural 500 × 2 | 1,000 | 2.05 M | 24.6 | 61.5 | 0.29 | 0.71 |
| Total per model | | 13.13 M | 157.4 | 393.6 | 1.82 | 4.56 |

At $1/hour the cloud scenario is $6.4 for both models; a 4× pessimistic throughput
still fits the $50 main-experiment allocation. The batch-one Transformers backend is
not an option for anything beyond pilots. Adding a harder task set or a breadth pool
scales these figures linearly.

## 7. Scorer and audit status

`numeric-v4` fixed two defects found on this branch (LaTeX-decorated boxes; prose
after an answer label read as a claim). Rescoring pilot v1 under v3 and v4 flipped no
correctness value. The agent pre-screen read all 47 incorrect responses, all 14 flagged
rows and 30 random correct ones and found no scorer defect. The human audit is
pending: run `rb report` after filling `audit.json` with a named reviewer; the
report's acceptance flag depends on it.

Dataset notes for the audit: three pilot questions have gold answers that depend on a
reading the model rarely takes ("2 132 contracts", "2 times less than half", Roman's
coins). They inflate the both-wrong cell and should be reported, not "fixed".

## 8. Decisions requested from the supervisor

1. Task mix for Milestone D: GSM8K alone, GSM8K plus a numeric-answer MATH or GSM-Plus
   set, or procedural tasks promoted to primary. Recommendation: add one wider-gap set.
2. Primary metric: accuracy at matched training budget (as proposed) versus tokens at
   matched accuracy or accuracy–cost curve area. Recommendation: the latter, with
   accuracy reported alongside.
3. Reasoning allowance: keep 4,096 and report forced closure, or test 8,192 on cloud.
   Recommendation: keep 4,096 for now.
4. Breadth pool: enlarge the candidate training pool (for example 1,500 GSM8K train
   questions) so acquisition strategies can choose between new questions and repeats.
5. Cloud access timing: the vLLM backend is the next engineering item and needs a GPU
   to validate against the Transformers backend.

## 9. Protocol to freeze before Milestone D

Everything in section 2, plus: scorer `numeric-v4`; final-response scoring; forced
closure counted as a thinking outcome at its actual token cost; two samples per
question for evaluation; whole-question bootstrap; the frozen split manifest tracked
in version control. Deferred designs (vLLM backend, breadth pool, ceiling check,
procedural probe) are specified in `plan.md`.

## 10. Reproduction

```sh
uv run --locked rb generate --config configs/pilot_v2.yaml
uv run --locked rb report artifacts/runs/f73a5665230cd83a7f12 --hourly-rate 1
uv run --locked rb analyze artifacts/runs/f73a5665230cd83a7f12 --cloud-tokens-per-second 2000 --hourly-rate 1
uv run --locked rb audit artifacts/runs/f73a5665230cd83a7f12 --count 50
```

The confidence-routing and reasoning-claim figures in sections 3 and 4 come from a
one-off script over the run's records; they will be folded into `rb analyze` when the
baselines are implemented.
