# Confidence–gain shape audit: results

Run on the Mac on 2026-10-30 under the frozen
[protocol](confidence-gain-shape-protocol.md); the generated
[report](confidence-gain-shape-report.md) is the authoritative output. This is
a **post-hoc, descriptive** analysis of reused development panels. It fits no
model, chooses no threshold, and changes no criterion or endpoint.

## Integrity

- The only runtime field that differs from collection is `platform` (a macOS
  update). All cached inputs were verified by hash, as the protocol's deviation
  section specifies.
- The bin totals reproduce the published counts: on the repeat panel, 30
  rescues, 10 harms, and 12 both-wrong pairs, with 89.5% direct and 94.5%
  thinking accuracy; on the two-solver panel, 61.7% direct and 80.5% thinking
  accuracy for Qwen3-0.6B and 84.375% and 87.5% for Qwen3-1.7B.

## Readings under the fixed rule

| Panel | Reading | Pooled Spearman [90%] | Between questions | Within questions |
|---|---|---|---|---|
| Repeat, Qwen3-1.7B (50 × 8) | Inconclusive | +.1553 [−.0021, +.2975] | −.0348 [−.3007, +.2447] | −.0555 [−.1584, +.0476] |
| Two-solver, Qwen3-0.6B (64 × 2) | Consistent | −.1931 [−.3572, −.0251] | −.2801 [−.4648, −.0782] | −.1776 [−.3724, +.0278] |
| Two-solver, Qwen3-1.7B (64 × 2) | Inconsistent | +.3439 [+.1612, +.4994] | +.3943 [+.1814, +.5768] | +.0759 [−.1404, +.2840] |

## What the bins show

**Qwen3-0.6B: lower confidence goes with higher gain.** Mean gain falls in
every step from the lowest-confidence bin (+.4221 [+.1920, +.6260]) to the
highest (−.1271 [−.2982, +.0253]), with no monotonicity violation. The two
lowest bins hold 23 of 32 rescues. The between-question correlation is clearly
negative: confidence tracks which questions benefit. The best in-sample
threshold escalates 66.4% of states and captures 71.8% of the hindsight
oracle's gain. Here the threshold premise holds, which fits the published
+.152677 utility of confidence over accepting the draft.

**Qwen3-1.7B, repeat panel: only the lowest tail benefits.** The lowest-
confidence fifth is the only bin with positive mean gain (+.0806,
[−.0158, +.1757]) and holds 17 of 30 rescues. Bins 2–5 all have negative mean
gain. The highest-confidence bin holds 8 of the 12 both-wrong pairs, and its
direct accuracy drops to 86.3% from 93.8–97.5% in bins 2–4. These are
confidently wrong drafts that thinking also fails to fix. The best in-sample
threshold escalates 11.7% of states and captures 32.9% of the oracle's gain
(.022675 versus .068956 per state). Thirteen rescues lie outside the lowest
bin, where the cost of thinking outweighs them.

**Qwen3-1.7B, two-solver panel: no threshold helps.** The two highest bins are
all correct in both modes, so their gain is only the thinking cost (−.0525).
The two lowest bins hold 10 of the 13 both-wrong pairs, against 5 rescues and
3 harms, and the longest thinking (1,799.8 and 1,557.2 mean tokens). Even
in-sample, the best confidence threshold escalates nothing. This fits the
published −.030540 utility of confidence relative to accepting the draft.

**Reading the pooled correlation.** Most 1.7B states have both responses
correct, and for those the gain is just \(-0.05\,C_T/1000\). Thinking runs
longer after low-confidence drafts on all three panels (repeat: 1,638.0 tokens
in bin 1 versus 1,154.2 in bin 5), so among these states the gain rises with
confidence. The positive pooled correlations for 1.7B therefore largely reflect
thinking length, not harms. The bins and escalation curves answer the
threshold question more directly.

## Answer to the question

Lower confidence goes with higher expected gain for Qwen3-0.6B, but not in
general for Qwen3-1.7B. For the stronger solver, low confidence often marks
hard questions where thinking also fails and runs longest, and some failures
are confidently wrong. A threshold can then capture at most the lowest tail
(repeat panel) or nothing (two-solver panel). This gives a descriptive reason
for the solver contrast in the manuscript's Table 4. It also shows that the
1.7B oracle headroom is spread across confidence levels where thinking's cost
dominates.

## Limits

These panels were used to design earlier studies; this audit is post-hoc. The
escalation-curve values are in-sample and optimistic. Intervals are
whole-question bootstrap summaries without simultaneous coverage. The two
solvers share the same 64 questions. Bins of 25–26 states on the two-solver
panel are small. Neither the "label noise" analogy nor any causal mechanism is
tested; the both-wrong pattern also differs between the two 1.7B panels
(highest-confidence bin on the repeat panel, lowest bins on the two-solver
panel).
