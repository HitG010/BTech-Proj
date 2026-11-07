# Framing / positioning / presentation review

Paper: "Learned Deferral Did Not Beat Confidence in a Same-Model Thinking Cascade"
(papers/thinking-selection/short/main.tex, 192 lines; output/main.pdf, 8 pp.)
Reviewer role: workshop PC member, efficient reasoning / LLM cascades. Read-only review.

---

## (a) Mock review

### Summary
The paper studies a two-stage cascade in which a small Qwen3 model first answers
directly and then, if a deferral rule says so, solves the question again from
scratch in thinking mode. Both calls are charged under a linear utility
(accuracy minus lambda x tokens/1000, lambda = 0.05). On 50 GSM8K training
questions with 8 draws per mode (400 paired draft/thinking samples) for
Qwen3-1.7B, a predeclared Ridge learner on question embeddings plus draft
features, and nine later variants (regularized/PCA, small neural objectives,
released contrastive-LM heads, token-level uncertainty quantiles), plus a
simulated two-draft agreement rule, all have lower held-out utility than a
threshold on mean token log-probability. Refitted at 10 lambdas, the learner
loses at all of them. With refit-inclusive bootstrap intervals the learner's
deficit is no longer significant ("missing gain, not demonstrated loss").
Confidence captures ~18% of a hindsight oracle's gain, helps Qwen3-0.6B
(+0.153 utility) but not Qwen3-1.7B. The authors relate the outcome to the
conditions under which Jitkrittum et al. (2023) predict learned post-hoc
deferral should beat confidence.

### Strengths
- S1. Honest, careful negative result. Predeclared criteria, failed gates kept,
  and the distinction between fixed-action and refit-inclusive intervals
  (Table 2) is a genuinely useful methodological point that most routing
  papers ignore.
- S2. Clean decision-theoretic setup (Eq. 1) that charges the draft; the
  linearity argument linking E[G|x,D] to the optimal deferral rule is crisp.
- S3. Repeated draws per question separate question-level from sampling-level
  variation; whole-question bootstrap is the right unit.
- S4. The "why" section (Sec. 4) is the most interesting part: confidently
  wrong drafts in the top bin, 13/30 rescues in mid/high confidence bins,
  thinking cost needing >1/14 rescue rate. This turns a null into insight.
- S5. Solver dependence (0.6B vs 1.7B) is a practically useful finding:
  check that the cascade beats "accept the draft" before tuning a router.
- S6. Novelty claims are appropriately modest; prior work on confidence-gated
  CoT, DART, and cascade theory is acknowledged.

### Weaknesses
- W1. Scale and scope. One dataset (GSM8K, where the 1.7B solver is at 89.5% /
  94.5%), 50 questions, two sub-2B models of one family. 30 rescues in total.
  Reviewers will say "a 391-feature Ridge fitted on 40 questions was never
  going to work"; the paper must pre-empt this by framing the low-data regime
  as the point (per-deployment calibration with tiny labelled sets), not as an
  apology.
- W2. Contribution sentence is buried and defensive (line 46). The reader
  finishes the intro knowing what failed but not what to take away or do.
- W3. Heavy internal jargon: "predeclared learner", "progression criteria",
  "screen", "repeat panel", "two-solver panel", "states", "rescues/harms"
  (used in the abstract before definition), "CPU family", "CLM/raw learned
  family", "refit-inclusive", "numeric-v7", "frozen roles". This reads as a
  lab notebook, not a paper.
- W4. Utility units are never interpreted. "+0.153 utility" and "-0.044" mean
  nothing to a reader until told 1.0 = one correct answer and lambda=0.05
  prices 20,000 output tokens at one answer.
- W5. Related work is thin on the canonical lines a cascade/efficient-reasoning
  reviewer expects: learning-to-defer, selective prediction, LLM confidence
  calibration, self-consistency/adaptive consistency, overthinking/NoThinking,
  compute-optimal test-time scaling, RouteLLM/Hybrid-LLM routers, and
  evaluation-variance literature that motivates refit-inclusive intervals.
- W6. Several key citations (Jitkrittum 2023, Gupta 2024, Lewis-Lim 2026,
  Fanconi 2025) were checked only at abstract level, yet Sec. 4's central
  explanatory paragraph (line 145) rests on Jitkrittum's precise conditions,
  including a "label-noise analogue". Must be verified against full text.
- W7. Table 1 is dense (11 learned rows, implementation-named), lacks the one
  column that explains most of the story (escalation rate), and mixes
  precisions. Figure 1's grey dots are unidentifiable.
- W8. Audit residue: "Draft, 2 November 2026", "Cloud and API experiment
  spending was zero", token tallies (App. C), scorer version names, the
  parser-guard/allowance follow-ups (App. B) unrelated to the main question.

### Scores
- Contribution: 2 / 4 (useful, well-executed null in a narrow setting; no new
  method, small n, one dataset).
- Presentation: 2.5 / 4 (rigorous and honest, but jargon-dense; main claim not
  readable in one pass; would be 3 after P0/P1 fixes).
- Overall: 5 / 10 as is (borderline); 6 / 10 after P0/P1 fixes at a
  negative-results or efficient-reasoning workshop.
- Likelihood: workshop (negative-results / efficient reasoning) ~55-65% after
  fixes; main conference (NeurIPS/ICLR/ACL main) <5% without at least a
  second dataset (e.g., MATH-500 or a harder GSM variant) and a larger
  question pool.

### Questions a reviewer will ask
1. Is the learner's failure just n=40 training questions vs 391 features? Show
   a learning curve (1/2/4/8 draws exist already) or a features-only-of-draft
   learner as the primary comparison in the main text.
2. Why must the thinking call ignore the draft? (Design choice; one sentence
   of motivation: it isolates deferral from revision.)
3. How was the confidence threshold chosen? (Within training; say so in the
   Rules paragraph, not only in the appendix.)
4. Would P(True)/verbalized confidence or self-consistency change the picture?
   (Acknowledge in Limitations.)
5. What does lambda=0.05 correspond to in dollars or latency?

---

## (b) Prioritized fix list (main.tex line numbers)

### P0 — must fix before submission

P0-1. Abstract, line 28: lead with question + takeaway; cut jargon. Replace the
first two sentences with:

> Hybrid reasoning models such as Qwen3 can answer directly or think first,
> so a cheap policy is to draft an answer directly and pay for a thinking
> solve only when the draft looks unreliable. We ask whether a learned
> deferral rule chooses those escalations better than the standard baseline,
> a threshold on the draft's token-level confidence, when the utility charges
> for both calls.

Then also: define "rescue" inline ("thinking fixes 30 of 400 wrong-or-right
drafts" -> "thinking fixes 30 of 400 drafts and breaks 10"); replace "nine
later variants (capacity and objective changes, released contrastive
representations, and token-level uncertainty)" with "nine follow-up variants";
replace "the evidence shows a missing gain rather than a demonstrated loss"
with "the learner fails to beat confidence, but is not reliably worse";
harmonize "18%" with 17.6% (line 141) and "under a fifth" (line 164) — pick
"18%" everywhere. End the abstract on a takeaway, e.g. "Confidence is a strong
baseline for same-model thinking cascades; whether the cascade pays at all
depends more on the solver than on the deferral rule."

P0-2. Contribution paragraph, line 46: replace with:

> None of the ingredients is new: confidence-gated thinking
> \citep{lewislim2026confidencegated}, post-hoc deferral after an observed
> draft \citep{jitkrittum2023cascade,gupta2024lmcascades}, agreement-based
> routing \citep{yue2024motcascade,lee2026dart}, and learned routers
> (Section~\ref{sec:related}) all precede this work. Our contribution is a
> controlled test of learned deferral in the case where both stages are the
> same small hybrid model, with repeated draws per question, held-out
> questions, a utility that charges the draft, intervals that include
> refitting variance, and every predeclared criterion reported. The answer is
> a calibrated negative: confidence was not beaten, consistent with cascade
> theory's account of when learned deferral should help, and the larger
> practical lever was whether thinking pays for the solver at all.

P0-3. Verify, from full text, every claim attributed to Jitkrittum et al.
(lines 35, 55, 145, 152), Gupta et al. (lines 35, 145, 152), Lewis-Lim et al.
(lines 35, 154) and Fanconi & van der Schaar (line 152). Line 145's "closest
analogue of label noise" argument must be rewritten or cut if the paper's
label-noise case is not about both models failing. (Already on the checklist;
it is P0 because Sec. 4's main explanation depends on it.)

P0-4. Interpret the utility scale once, in Setup after Eq. 1 (line 55): "Utility
is measured in correct answers per question: +0.01 is one extra correct answer
per hundred questions, and lambda = 0.05 prices 20,000 output tokens at one
correct answer." Without this, every number in Tables 1-2 is opaque.

P0-5. Define vocabulary once and use plain names (lines 41, 57, 59, 61, 69,
Table 1-2, Fig. 1):
- "repeat panel" -> "main panel (Qwen3-1.7B, 50 questions x 8 draws)";
  "two-solver panel" -> "solver-comparison panel (64 questions x 2 draws)".
- "state" -> "draft-thinking pair" (define at line 59).
- "rescue"/"harm" -> define at line 67 or earlier: draft wrong & thinking
  right / the reverse.
- "progression criteria", "screen" -> "success criteria".
- "refit-inclusive" -> "intervals that include refitting" (keep the term only
  as a parenthetical label).
- "predeclared learner (combined Ridge)" in Table 1 vs "Combined learner" in
  Fig. 1 legend -> use "Predeclared learner" in both.
- Line 41/abstract: "nine later learned variants" is inaccurate — zero-shot
  CLM and the minimum-token threshold are not learned on this data. Use
  "follow-up rules".

P0-6. Line 59, evaluation protocol, is hard to parse ("trains on one half of
the training questions and is evaluated on the other half of the held-out
questions"; "half" means draws). Replace with: "Rules are fitted on draws 0-3
of the training questions and evaluated on draws 4-7 of the held-out
questions, and vice versa; we report the average."

P0-7. Remove submission-incompatible residue: line 22 "Draft, 2 November 2026"
(use \date{}); line 21 anonymous author block per venue rules; line 166 "Cloud
and API experiment spending was zero" (move to the repository README or cut;
keep the AI-assistance sentence verbatim).

### P1 — strongly recommended

P1-1. Pre-empt the "40 questions vs 391 features" objection (line 143 already
says it; promote to intro/Sec. 3.1). Add one sentence in the intro framing the
low-data regime as the realistic deployment case, and point to the 1/2/4-draw
conditions (App. A, line 177) as a learning-curve check if those numbers are
in the long report.

P1-2. Table 1 (lines 71-98): add an "Escalated %" column (confidence 25%,
oracle 7.5%, learner 40.5%, agreement 8.5% from line 69/141); round tokens to
integers and accuracy to one decimal (89.5, not 89.50%); rename
"Regularized/compressed (CPU family)" -> "Ridge, strong penalty + PCA";
"CLM/raw learned family" -> describe or merge; group rows into "Learned,
question+draft features", "Learned, contrastive-LM features", "Token-level",
"Agreement". Move "Always think" utility interval in or mark as baseline.

P1-3. Figure 1 (line 106): legible in print (fonts ~7-8 pt at full width, ok)
but (i) grey dots are unidentifiable — label the 2-3 relevant ones
(min-token, zero-shot CLM) or drop them and keep agreement; (ii) the oracle
square forces wide y-ranges, compressing the curves — consider an arrow/inset
marker at the top edge; (iii) legend "λ=.05" -> "λ = 0.05"; (iv) x-label
"Output tokens per state" -> "Output tokens per question (incl. draft)".
Caption line 107: cut "Values are post-hoc, on reused development panels, and
carry no intervals" to "No intervals shown; see Tables 1-2."

P1-4. Related work (lines 149-156): add the missing lines (list below) in ~8-10
lines; replace line 156's "precede our use of repeated labels and contrastive
representations" with a sentence that says what those routers do and how this
setting differs (single model, post-draft decision).

P1-5. Bibliography fixes (references.bib):
- qwen2025qwen3: 60+ author list costs ~9 lines of page budget; use
  "Yang, An and others" or "{Qwen Team}".
- lewislim2026confidencegated: year 2026 with arXiv 2510.21007 (Oct 2025) —
  either year 2025 or add the 2026 venue that justifies 2026.
- chen2023frugalgpt: I believe FrugalGPT appeared in TMLR (2024); check and
  cite the archival version.
- fanconi2025cascaded: NeurIPS 2025 claim unverified; no volume/pages; confirm.
- ding2025bestroute: I believe it appeared at ICML 2025 (unverified); check.
- fang2025thinkless: may have a NeurIPS 2025 version (unverified); check.
- sentencetransformersAllMiniLML6v2: no year; also cite reimers2019sbert and
  wang2020minilm (already in the bib, unused) at line 61.
- kwok2026clm: blog/notion URL with a 7-author list that cannot be checked;
  cite the model card (contrastiveLM2026release, in bib, unused) alongside it.
- kubaty2026earlyexit is in the bib but uncited (harmless; remove if unused).
- Inconsistent URL policy (v1/v3 pinned arXiv URLs vs proceedings); fine,
  but prefer proceedings DOIs where they exist.

P1-6. Cut or shrink Appendix B (lines 181-186): the parser guard and
reasoning-allowance follow-ups are off-question; keep one sentence in
Limitations (line 160 already has it) and drop the appendix. Shrink Appendix C
(line 190) to the protocol-freezing sentence; token tallies are audit detail.

P1-7. Add to Limitations (line 160): no verbalized/P(True) or sampling-based
confidence baselines; thinking call does not see the draft (design choice,
not the only cascade).

### P2 — polish

P2-1. Line 33: "costs several times as many output tokens" -> give the number
(221 vs 1,611 tokens, ~7x).
P2-2. Line 55: "mean post-sampling token log probability" — "post-sampling"
is unclear; say "mean log-probability of the sampled draft tokens".
P2-3. Line 57: "frozen numeric answer scorer (numeric-v7)" -> "a fixed numeric
answer-matching scorer"; "GSM8K training rows assigned to frozen roles" ->
"questions drawn from the GSM8K training split".
P2-4. Line 102: "The single cost preference of the original studies therefore
does not explain the result" -> "The result is not an artifact of lambda."
P2-5. Line 133: "The fold assignment does not drive the signs" — fine; keep.
P2-6. Section 3 subsection titles are good claim-style headings; make Sec. 4
paragraph titles parallel (all claims).
P2-7. Line 147: "Agreement is priced out" — good; add the escalation-rate
number for agreement for symmetry with confidence (line 141).
P2-8. Use \lambda consistently (\lam macro is fine) and "lambda = 0.05" in
figure legend.
P2-9. Page budget: main text ends at page 6 top; references take ~1.5 pp
(Qwen3 author list). After cuts, there is room for a 3-4 line "Practical
takeaways" paragraph before the Conclusion (check whether cascade beats
accept; use confidence; learned rules need more rescues than you have).
P2-10. Consider a tiny schematic (draft -> rule -> think) only if the venue
allows 8+ pages; not necessary.

### Missing related work a reviewer will expect
Confident these exist (title, first author, year); details marked
"(unverified)" where I am not sure of venue or exact title.

Cascades / deferral / routing
- Varshney & Baral, "Model Cascading: Towards Jointly Improving Efficiency and
  Accuracy of NLP Systems", EMNLP 2022.
- Madras, Pitassi & Zemel, "Predict Responsibly: Improving Fairness and
  Accuracy by Learning to Defer", NeurIPS 2018.
- Mozannar & Sontag, "Consistent Estimators for Learning to Defer to an
  Expert", ICML 2020.
- Narasimhan et al., "Post-hoc Estimators for Learning to Defer to an Expert",
  NeurIPS 2022.
- Wang, Kondratyuk et al., "Wisdom of Committees: An Overlooked Approach to
  Faster and More Accurate Models", ICLR 2022 (confidence-based cascades of
  ensembles).
- Ding et al., "Hybrid LLM: Cost-Efficient and Quality-Aware Query Routing",
  ICLR 2024.
- Ong et al., "RouteLLM: Learning to Route LLMs with Preference Data", 2024
  (ICLR 2025 version, unverified).
- Hu et al., "RouterBench: A Benchmark for Multi-LLM Routing System", 2024.
- Dekoninck et al., "A Unified Approach to Routing and Cascading for LLMs",
  2024 (venue unverified).
- Narasimhan et al., "Faster Cascades via Speculative Decoding", 2024
  (ICLR 2025, unverified).

Adaptive / budgeted thinking
- Ma, He, Snell, Griggs, Min & Zaharia, "Reasoning Models Can Be Effective
  Without Thinking", 2025 (NoThinking; directly relevant).
- Chen et al., "Do NOT Think That Much for 2+3=? On the Overthinking of
  o1-like LLMs", 2024.
- Snell et al., "Scaling LLM Test-Time Compute Optimally can be More Effective
  than Scaling Model Parameters", 2024 (difficulty-predicted compute
  allocation).
- Damani et al., "Learning How Hard to Think: Input-Adaptive Allocation of LM
  Computation", 2024 (ICLR 2025, unverified).
- Muennighoff et al., "s1: Simple Test-Time Scaling", 2025 (budget forcing,
  relevant to the reasoning-allowance follow-up).
- Han et al., "Token-Budget-Aware LLM Reasoning", 2024.
- Zhang et al., "AdaptThink: Reasoning Models Can Learn When to Think", 2025
  (unverified authors).
- Sui et al., "Stop Overthinking: A Survey on Efficient Reasoning for Large
  Language Models", 2025.

Self-consistency / agreement
- Wang et al., "Self-Consistency Improves Chain of Thought Reasoning in
  Language Models", ICLR 2023.
- Aggarwal et al., "Let's Sample Step by Step: Adaptive-Consistency for
  Efficient Reasoning and Coding with LLMs", EMNLP 2023.
- Li et al., "Escape Sky-high Cost: Early-stopping Self-Consistency for
  Multi-step Reasoning", ICLR 2024.

Selective prediction / confidence and calibration
- Geifman & El-Yaniv, "Selective Classification for Deep Neural Networks",
  NeurIPS 2017.
- Kamath, Jia & Liang, "Selective Question Answering under Domain Shift",
  ACL 2020.
- Guo et al., "On Calibration of Modern Neural Networks", ICML 2017.
- Kadavath et al., "Language Models (Mostly) Know What They Know", 2022.
- Kuhn, Gal & Farquhar, "Semantic Uncertainty: Linguistic Invariances for
  Uncertainty Estimation in Natural Language Generation", ICLR 2023.
- Xiong et al., "Can LLMs Express Their Uncertainty? An Empirical Evaluation
  of Confidence Elicitation in LLMs", ICLR 2024.
- Malinin & Gales, "Uncertainty Estimation in Autoregressive Structured
  Prediction", ICLR 2021 (length-normalized sequence confidence).

Evaluation variance (supports the refit-inclusive interval point)
- Bouthillier et al., "Accounting for Variance in Machine Learning
  Benchmarks", MLSys 2021.
- Bates, Hastie & Tibshirani, "Cross-validation: What Does It Estimate and
  How Well Does It Do It?", JASA 2024 (arXiv 2021).
- Nadeau & Bengio, "Inference for the Generalization Error", Machine Learning
  2003.
- Dodge et al., "Show Your Work: Improved Reporting of Experimental Results",
  EMNLP 2019.

Dataset caveat
- Mirzadeh et al., "GSM-Symbolic: Understanding the Limitations of
  Mathematical Reasoning in Large Language Models", 2024 (GSM8K saturation /
  contamination; supports the near-ceiling limitation).

### Title alternatives
1. Is Confidence Enough to Decide When a Small Model Should Think?
2. Learning When to Think Did Not Beat Confidence: A Negative Result for
   Same-Model Reasoning Cascades
3. Draft First, Think If Unsure: Confidence Remains Hard to Beat in a
   Same-Model Cascade
4. Confidence Is a Strong Baseline for Deferring to Thinking Mode
5. When Does Learned Deferral to Thinking Pay? A Small-Scale Negative Result
   on GSM8K

(2 or 3 keep the negative-result honesty of the current title while reading
as a finding rather than a lab report. Avoid any title implying novelty of the
cascade or the confidence rule.)

---

## (c) Venue recommendation

1. Best fit: "Insights from Negative Results in NLP" workshop (co-located with
   ACL/NAACL/EMNLP; archival in the ACL Anthology). Short-paper format
   (typically 4 pp + unlimited refs/appendix; verify the call). Requires:
   compress to 4 pages (drop App. B/C, move Sec. 3.3 detail to appendix),
   ACL template, Limitations section (already present), anonymity.
2. Strong alternative: "I Can't Believe It's Not Better" (ICBINB) workshop,
   usually at NeurIPS or ICLR; non-archival, values exactly the "why did the
   expected gain not appear" analysis in Sec. 4. Requires: venue template,
   usually 4-8 pp, emphasis on the explanatory section.
3. Topical: an efficient-reasoning / test-time-compute workshop at ICLR 2027
   or NeurIPS 2027 (names and dates vary each year; verify). Non-archival
   workshops allow later journal submission. Requires: stronger positioning
   against NoThinking, overthinking, and adaptive-thinking routers; a
   practical-takeaway paragraph.
4. Not recommended now: ACL/EMNLP Findings short or TMLR. Both would ask for a
   second dataset (e.g., MATH-500 or a harder GSM variant), more questions,
   and at least one larger model; TMLR would accept a negative result whose
   claims are well supported, but 50 questions / one dataset will draw
   "insufficient evidence for the general claim" unless the title and claims
   are scoped tightly to the tested setting.
5. arXiv preprint first is fine (checklist already plans it); avoid
   simultaneous archival submissions.
