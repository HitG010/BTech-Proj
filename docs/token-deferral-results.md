# Token-level deferral check: results

Run on the Mac on 2026-10-30 under the frozen
[protocol](token-deferral-protocol.md); the generated
[report](token-deferral-report.md) is the authoritative output. This is a
**post-hoc, exploratory** analysis of the reused 50-question repeat panel. It
generated no response and opened no reference answer.

## Integrity

- **Extraction fidelity passed.** Teacher-forced pre-warper mean log
  probabilities match the recorded values with median absolute difference
  0.000139 and maximum 0.001055, against a 0.02 tolerance (share within
  tolerance 1.0). Prompt and answer token counts and decoded text matched for
  all 400 drafts. The post-warper diagnostic had 4 tokens in 4 drafts fall
  outside the recomputed top-p support, as expected from float16 differences
  near the cutoff; post-warper values were not used as features.
- **The comparator is the paper's.** `execute` reproduced every historical
  accept, escalate, confidence, solver-only, and combined decision from the
  primary repeat report before comparing rules. The confidence policy's
  four-draw averages, 92.75% accuracy at 628.47 tokens per state, equal
  Table 3 of the manuscript.
- The recorded confidence's pooled positive-gain AUROC, .7050, matches the
  earlier CLM signal audit (.705045).

## Readings

| Rule | Mean utility difference vs confidence [90%] | A→B | B→A | Screen |
|---|---|---:|---:|---|
| Learned error score (primary) | −.037093 [−.061320, −.012740] | −.043491 | −.030694 | Fail |
| Minimum-token threshold | −.010236 [−.027213, +.005476] | −.025371 | +.004898 | Fail |
| Token gain Ridge | −.020237 [−.035444, −.007115] | −.032280 | −.008193 | Fail |

Accuracy and tokens per state: learned error score 88.75% at 570.33,
minimum-token threshold 91.00% at 483.20, token gain Ridge 90.00% at 483.21,
against confidence 92.75% at 628.47. The secondary eight-draw differences are
also negative: −.028534, −.014151, and −.023358. **The primary rule fails, and
so do both secondary rules.** For no rule are all leave-one-question-out
averages positive.

## Interpretation

**Better single-feature ranking did not become better held-out decisions.**
Pooled over the 400 states, low token-level quantiles rank incorrect drafts and
positive-gain states slightly better than the recorded confidence. For positive
gain, the 25th percentile scores AUROC .7613 against .7050; for incorrect
drafts, the 10th percentile scores .6445 against .5952. These are in-sample
point values without intervals. Every learned or tuned rule nevertheless lost
utility to confidence on held-out questions. The learned error score did worst.
It fits eleven correlated features to roughly one incorrect draft in ten
training rows (direct accuracy is 89.5%). It also predicts direct errors, not
gain, so it cannot distinguish rescues from pairs that thinking also gets
wrong.

**The length bias that motivated the recipe is not visible in our confidence.**
The recorded mean log probability is nearly uncorrelated with answer length
(Spearman −.0267). The minimum token log probability is length-dependent
(−.3108), because longer answers have more chances to contain one unlikely
token. Gupta et al. describe length bias for sequence-level aggregates in
general; on this panel our length-normalized mean shows little of it, so the
recipe's main motivation is weak here.

**What this closes.** The manuscript previously listed token-level quantile
deferral as an untested recipe. This adapted version is now tested, and it
fails like the capacity, contrastive, and CLM variants. Confidence remains the
strongest tested rule on the repeat panel.

## Limits

This is an adaptation, not a reproduction of Gupta et al.: our quantile set,
logistic and Ridge models, and threshold search are our own choices, and their
full text was not available when the protocol was written. The panel is the
same reused 50 questions, the analysis is post-hoc, and intervals hold fitted
actions fixed. A failure here is evidence against this recipe on this panel,
not against token-level features with more training data or other models.

## Manuscript integration

At the author's request, manuscript v0.6 (1 November 2026) reports this check as
Section 4.4 and three rows of Table 3, and removes the statements that token-level
deferral was untested from the abstract, introduction, related work, discussion,
limitations, and conclusion. Table 1, Section 3.5, and Appendices A and B are
updated. Table 3's new rows and every Section 4.4 value were checked by script
against the generated report. Figure 3 predates the check and does not show it.
