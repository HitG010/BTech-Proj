# Methods and claims review: "Learned Deferral Did Not Beat Confidence in a Same-Model Thinking Cascade"

Reviewed: `papers/thinking-selection/short/main.tex` (192 lines), PDF pp. 1–8, Figure 1 + manifest, against
`manuscript.md` v0.7 and `docs/{deferral-curves-results,confidence-gain-shape-results,token-deferral-results,phase-2-repeat-results,reproduction-report}.md`.
Read-only; no repository file edited.

## Spot checks (all pass unless noted)

| Claim (main.tex line) | Check | Result |
|---|---|---|
| Always direct −0.012, oracle +0.057, learner −0.044 vs confidence (Table 1) | U = acc − .05·tok/1000: .8839, .9529, .8521 vs .8961 | OK |
| Agreement −0.003, lift +1.40† (l.95) | .8926 − .8961; random acc at 597.69 = .90855 | OK |
| "one escalation in fourteen" (l.141) | 1,389.83 thinking tokens × .05/1000 = .0695 | OK |
| Agreement second-draft cost ≈ .011 (l.147) | 221.14 × .05/1000 | OK |
| Oracle share 17.6% (l.141) | .0122/.0690 | OK |
| Refit widening 1.1–1.9× (l.133) | width ratios 1.13–1.93 | OK |
| 0.6B 81.25% at 1,063 tok, +6.2 pts (l.137) | deferral-curves Part A | OK |
| 13 of 30 rescues outside lowest bin; 8 of 12 both-wrong in top bin (l.143) | confidence-gain-shape record | OK |
| "Table 1 lists every rule on the repeat panel" (l.67) | Figure 1A also plots solver-only Ridge, question-only Ridge, training-selected comparator (render_curves.py l.112–120) | **Inconsistent** |
| Confidence definition "post-sampling" (l.55) | backend.py: post-warper (after T, top-k, top-p); token rules use pre-warper | **Ambiguous** |

---

## (a) Mock review

**Summary.** The paper studies a two-stage cascade in which a small Qwen3 model answers directly and a rule decides whether to buy a fresh thinking solve from the same weights, under utility = accuracy − 0.05·tokens/1000. The main evidence is a 50-question × 8-draw GSM8K panel (Qwen3-1.7B), with 5-fold question-held-out cross-fitting and draw-half transfer. A predeclared Ridge learner (391 features) fails 4 of 5 progression criteria. Nine later variants and a simulated two-draft agreement rule all have lower point utility than a confidence threshold. A λ sweep keeps the ordering at every tested cost. Refit-inclusive bootstrap intervals for the learner's contrasts include zero. A 64-question two-solver panel shows that confidence deferral beats accepting the draft for Qwen3-0.6B (+0.153) but not for 1.7B. Post-hoc confidence bins explain the gap descriptively.

**Strengths.**
1. Unusually disciplined: predeclared criteria, frozen protocols, failed criteria reported, and the reference answers kept sealed until each study's responses were complete. The 195/195 reproduction from cache is exemplary.
2. Correct cost accounting for escalation (sunk draft charged). Cost-matched random baseline and oracle give the reader a scale.
3. Refit-inclusive intervals, and the explicit downgrade from "worse" to "missing gain", are rare and commendable.
4. Cascade-theory framing (Jitkrittum et al.) turns a null into an interpretable null.
5. Breadth of the null: capacity, objectives, released representations, token-level quantiles, and agreement.

**Weaknesses.**
1. **Power.** 50 questions, 40 training questions per fold, and 30 rescues concentrated in 14 informative questions (long report Table 2; not stated in the short paper). The learned rules are asked to find about 3 rescue-bearing questions per fold among 40. The null is close to guaranteed by design, and the paper does not own this up front. The title and abstract read as more general than "40 training questions".
2. **The 0.6B headline conflates thinking with deferral.** Always-think already beats accept by +0.128 for 0.6B (long report Table 4: .734211 − .606697). Confidence beats always-think by only +0.025 (.759374 − .734211, no interval). "+0.153, robust to refitting" mostly measures the value of thinking, not of selective deferral. The deferral-specific evidence is the +6.2-point cost-matched lift, which has no interval.
3. **Refit result over-generalized.** Only the predeclared learner was refitted, yet l.133 concludes for "the learned rules". The refit bootstrap also shrinks effects toward zero (−.012 vs −.016; +.002 vs +.012 per the record), which the paper calls "approximate" without saying in which direction. Conversely, against confidence the refit upper bound (+0.008) is below the +0.01 margin. The paper can make a sharper statement than it does.
4. **Oracle definition.** The hindsight oracle sees the realized thinking sample under an arbitrary pairing by sample index. Its "gain" includes thinking's sampling luck that no (x, D)-measurable rule can capture, so "captures only 18%" (abstract) understates confidence relative to achievable headroom.
5. **Fairness of some comparisons.** The CLM families exclude confidence and draft statistics (long report §4.3); the short paper does not say so. The compact neural rules truncate drafts to their last 256 tokens (111 of 400 truncated) and use one seed. The table omits the 4-feature solver-only Ridge, which nests the confidence feature and still loses (−0.030 point). That row is the strongest evidence that the failure is estimation noise rather than features. The training-selected comparator itself loses 0.028 to fixed confidence, which directly shows how noisy selection is with 40 questions. This is informative and unreported.
6. **Selective omissions relative to the long report.** On the 1.7B two-solver panel, agreement *leads* confidence (+0.008, both directions positive). The September studies found agreement best on one 50-question holdout. The long report's key hedge, "the results do not show that deferral is unlearnable" (between-question gain variance .032 [.005, .065]), is absent.
7. **Single dataset near ceiling, possibly contaminated.** The questions are GSM8K *training* rows, which are very likely in Qwen3's training data. This is acknowledged for ceiling but not for contamination.
8. Single λ: adequately addressed by the sweep (point estimates only). The cost accounting (output tokens only) is acknowledged.

**Questions for authors.**
1. What is confidence minus always-think for 0.6B, with an interval? Does selective deferral beat the better constant policy?
2. Of the 30 rescues, how many distinct questions contribute? What is the learners' performance on just those questions?
3. Is "confidence" the post-warper mean (after T=0.7, top-k 20, top-p 0.8)? Why not the raw log probability, which you also record? Do the token-level AUROCs (pre-warper) and confidence (post-warper) compare like with like?
4. What is the utility of a question-level oracle that knows Y_D and the per-question mean thinking accuracy from the 8 draws?
5. Why were the sealed confirmation allocations not used? Presumably the predeclared gate. Saying so would strengthen the paper.
6. With the margin of +0.01, can you state a non-superiority result against confidence from the refit upper bound?

**Scores.**
- Soundness 3/4: honest and careful, but underpowered, and two claims are over-generalized.
- Presentation 3/4: dense but clear. One methods sentence is wrong (l.59). Table/figure mismatch.
- Contribution 2/4: a well-executed negative result in a narrow, near-ceiling setting. The novelty is in rigor, not in the idea.
- **Overall: 6/10 at a workshop** (weak accept; acceptance likely, roughly 60–70% after P0 fixes). **3/10 at a main conference** (reject; roughly 5–10%). A main-track paper would need a second dataset with real headroom and several hundred training questions. That requires new data collection, and it is essential for that venue only.
- Confidence: 4/5.

---

## (b) Prioritized fix list

### P0 — must fix before submission (all text-only)

1. **Evaluation design sentence is wrong (l.59).** "A rule trains on one half of the training questions and is evaluated on the other half of the held-out questions" describes a question split that does not exist. Replace with: "A rule trains on one draw half (A or B) of the 40 training questions and is evaluated on the other draw half of the 10 held-out questions, in both directions…"
2. **"Table 1 lists every rule" is false (l.67, Table 1 l.76–97).** Figure 1A plots three more rules. Add rows for the training-selected comparator (90.25%, 683.06, −0.028†, lift −0.91), solver-only Ridge (89.75%, 621.67, −0.030†, −1.19), and question-only Ridge (88.75%, 794.10, −0.048†, −2.81). These values are in deferral-curves-results; mark points derived from accuracy and tokens with †. If space forbids, change l.67 to "lists the rules discussed" and note the three in the Figure 1 caption. Adding the rows is preferred: solver-only nests confidence and still loses, which pre-empts the "391 features on 40 questions" objection.
3. **0.6B gain conflates thinking with deferral (l.28, l.44, l.135–137, Table 2 row 4).** Add: "Always thinking already gains +0.128 over accepting the draft. Confidence deferral adds +0.025 over always thinking (point estimate; no interval) and lies 6.2 points above cost-matched random." Retitle §3.4 "Thinking and confidence deferral pay for the smaller solver". Abstract: "It clearly helps Qwen3-0.6B" → "It beats accepting the draft for Qwen3-0.6B, mostly because thinking itself pays there, but not for Qwen3-1.7B". (Optional, not needed for a workshop: a frozen-protocol refit interval for confidence − always-think from the cache.)
4. **The refit conclusion is generalized beyond what was refitted (l.43, l.133).** l.133: "the learned rules did not deliver…; the data do not show that they are worse" → "the predeclared learner did not deliver…; the data do not show that it is worse than confidence. The later variants were not refitted; their fixed-action intervals (Table 1) would widen too, so we do not read them as demonstrated losses." Intro bullet l.43: scope it to "the predeclared learner".

### P1 — should fix

5. **Margin and bias of the refit intervals (l.117 caption, l.133).** Add: "Refit bootstrap means are shrunk toward zero (−0.012 vs −0.016), so these intervals lean toward including zero. Against confidence, the upper bound +0.008 lies below the +0.01 margin, so a gain of that size is approximately excluded. Against the training-selected comparator (upper +0.021) it is not."
6. **Effective sample size (l.67, l.160).** Add "The 30 rescues and 10 harms fall in 14 of the 50 questions." In the Limitations, state that each fold trains on about 40 questions, of which only a handful carry rescues.
7. **Oracle caveat (l.28, l.141, l.164).** Add at l.141: "The oracle sees the realized thinking outcome under an arbitrary draw pairing, so part of its gain is thinking's sampling luck that no rule using only the question and draft can capture; the 17.6% share is a lower bound against achievable headroom." Abstract: "only 18% of the hindsight oracle's gain" → "18% of a hindsight oracle's gain (an upper bound no deployable rule can reach)".
8. **Confidence definition and threshold selection (l.55).** "mean post-sampling token log probability" → "mean log probability of the draft's tokens under the sampling distribution (after temperature, top-k and top-p), with the threshold chosen on training questions only". At l.145, note that the token-level quantiles use pre-warper probabilities.
9. **Fairness disclosures (l.61 or l.179).** Add that the CLM families exclude confidence and draft statistics, that compact neural rules see only the last 256 draft tokens (111 of 400 truncated), and that they used one seed. Add that the training-selected comparator itself trails confidence by 0.028, which shows selection noise at 40 questions.
10. **Restore omitted findings (l.137, l.160, §4).**
    - l.137: "for Qwen3-1.7B it leads confidence by +0.008 (both directions positive, below the +0.01 screen) but trails accepting the draft by 0.023".
    - Limitations: "Earlier development studies on other questions gave mixed results for agreement."
    - End of §4 or the Conclusion, from the long report: "post-hoc between-question gain variance is positive, so the results do not show that deferral is unlearnable; they show these rules did not exploit it from 40 training questions".
11. **Agreement omitted from the random-line sentence (l.102).** "Among the later variants, only…" → add "; two-draft agreement lies 1.40 points above it". The long report (manuscript.md l.251, "Among the Table 3 rows") has the same omission; fix it there in a separate version.
12. **Calibrate the statistical verbs.**
    - l.28, l.44: "lower confidence predicts higher deferral gain" → "is associated with".
    - §3.2 title (l.100): → "The point ordering holds at every tested cost".
    - l.164: "Confidence was the best deferral rule we tested" → "Confidence had the highest point utility among the rules we tested on the main panel, but its own gain over accepting the 1.7B draft (+0.012) is indistinguishable from zero".
    - Title: consider adding scope, e.g. "…in a Small Same-Model Thinking Cascade on GSM8K".
13. **Limitations additions (l.160).**
    - GSM8K training rows may be in Qwen3's pretraining data.
    - 90% intervals, with no multiplicity adjustment across about 12 contrasts.
    - One prompt and one decoding configuration.
    - Tokens from different model sizes are not equal compute.
14. **Availability, ethics, and anonymity (l.21–22, l.166, l.190).**
    - Add a code/data availability paragraph: what will be released, the cache SHA-256, the one-command 195-check reproduction, and an anonymized link.
    - Add a one-line ethics/impact statement: GSM8K (MIT) and Qwen3 (Apache-2.0), no human subjects, low misuse risk.
    - Remove "Draft, 2 November 2026".
    - Make "accompanying technical report" anonymous-safe.
    - Optionally note that, per the predeclared gate, no rule progressed, so the sealed confirmation sets were not spent.

### P2 — nice to have

15. l.41: "nine later learned variants" → "nine later variants" (zero-shot CLM and the minimum-token threshold are not trained).
16. l.145: "rank errors slightly better (positive-gain AUROC…)" → "rank positive-gain states slightly better".
17. l.41 / l.177: say that the five criteria are related decisions, not independent tests. Note that the failed reproducibility criterion (+0.0116 [−0.017, +0.048]) is itself evidence that question-level gain is hard to predict. This could serve as a lead explanation in §4.
18. l.46 claims "repeated draws" as a contribution, but the 1/2/4-draw results (mixed signs) are not shown. Add one appendix sentence.
19. l.133: explain that fold-repartition ranges reflect assignment variation only, not sampling, so excluding zero there is not significance.
20. l.186: note that the appendix uses 95% intervals while the body uses 90%.
21. Optional cache-only analyses, each under its own frozen protocol; none is essential for a workshop:
    - a question-level oracle using the 8 thinking draws;
    - a threshold on the raw (pre-warper) confidence;
    - a refit interval for 0.6B confidence − always-think.
22. Essential only for a main-track venue: a second dataset with real headroom (for example MATH-level problems) and at least a few hundred training questions. This needs new local data collection under a new frozen plan.
