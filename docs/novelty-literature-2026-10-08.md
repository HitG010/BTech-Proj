# Literature assessment for the focused research plan

Search date: 2026-10-08. Purpose: choose a testable contribution and a publication route.
This is a targeted scoping review. It is not an exhaustive systematic review or proof of priority.
The [main plan](novelty-plan-2026-10-08.md) contains the proposed experiment.

Primary paper pages, proceedings, full-text sections, author repositories, and official venue policies support this assessment.
Search engines and secondary indexes were used for discovery only.
Published numerical claims below were not reproduced in our environment.
No external response dataset, model, training corpus, or sealed evaluation outcome was downloaded.

## 1. Search record and limits

The search covered four areas: acquisition algorithms, reasoning routers, evaluation failures, and publication formats.
Representative executed queries were:

```text
LLM routing active learning label efficient acquisition repeated sampling confidence cascade
"Targeting the Exceptions" LLM routers
"Re-Active Learning" AAAI
"Cost-Aware Near-Optimal Policy Learning" arxiv
"LLM" "active" "threshold" "calibration" routing
"cascade" "active learning" "threshold" language models
contextual bandit policy identification disagreement active learning cost pure exploration
active learning confidence threshold calibration early exit classifiers
"Causal LLM Routing"
"Meta-Router" "gold" routing
"routing" "stochastic" "oracle" LLM
"large language model routing" "survey"
"Dynamic Model Routing and Cascading for Efficient LLM Inference"
LLM reasoning routing survey adaptive thinking test time compute survey
Transactions Machine Learning Research survey papers negative results submission scope
Computational Linguistics journal survey papers submission guidelines
```

Discovery included arXiv, ACL Anthology, PMLR, OpenReview, AAAI, JMLR/TMLR, and author repositories.
The review followed citations from the routing survey and the current stochastic-oracle paper.
It also checked the research references already present in this repository.

Retrieval levels in the table are deliberate. An abstract can establish overlap, but cannot establish algorithmic equivalence.
Some full texts were accessible as HTML. The AAAI policy-learning PDF and PMLR feedback-graph PDF had direct retrieval failures.
The AAAI policy-learning PDF's indexed contribution excerpt was available. Its linked `alg.py` also failed direct retrieval.
The re-active-learning PDF was available, including the impact rule, threshold example, and runtime discussion.
Exact proof and implementation equivalence remain G0 work.
No excluded-paper counts or screening-agreement statistics exist yet. Do not invent them for a survey manuscript.

## 2. Closest acquisition and estimation work

| ID | Primary source and retrieval level | Established overlap | Required response in our work |
|---|---|---|---|
| L1 | [Cost-Aware Near-Optimal Policy Learning](https://ojs.aaai.org/index.php/AAAI/article/view/35027), AAAI 2025; abstract and indexed algorithm contribution excerpt. [Author code](https://github.com/joyheyueya/cost-aware-policy-learning) inspected at repository level. | Separates the cost of collecting observations from the value of the resulting policy. Includes static and adaptive resource-aware algorithms. | Mandatory closest cost-aware baseline. Information benefit per cost is already established. Inspect `alg.py` and supplements before specifying a distinct algorithm. |
| L2 | [Re-Active Learning: Active Learning with Relabeling](https://ojs.aaai.org/index.php/AAAI/article/view/10315), AAAI 2016; abstract and [full-text algorithm sections](https://ojs.aaai.org/index.php/AAAI/article/download/10315/10174). | Chooses between a new example and another annotation. Uses impact sampling and lookahead. It also analyzes a one-dimensional noiseless threshold case. | New-versus-repeat selection and threshold specialization are insufficient for novelty. Explain the difference between stochastic solver outcomes and noisy annotator labels. |
| L3 | [Pure Exploration with Feedback Graphs](https://proceedings.mlr.press/v258/russo25a.html), AISTATS 2025; proceedings abstract. | Studies identification of a good action when one purchase reveals information about other actions. | Shared feedback across threshold policies is not new by itself. Map our response feedback to its assumptions; compare an applicable adaptation. |
| L4 | [Targeting the Exceptions: Online Active Learning for Retrieval-Based LLM Routers](https://github.com/wikit-ai/online-active-learning-llm-routers), author repository; README and strategy table. The repository reports EMNLP 2026 Findings. | Acquires examples under a limited annotation budget using predicted performance sparsity. Includes random and uncertainty controls. | Active collection for routing already exists. Distinguish a threshold-policy mechanism from retrieval-support acquisition. Pin the full paper and code revision before a comparative claim. |
| L5 | [Causal LLM Routing](https://arxiv.org/html/2505.16037), NeurIPS 2025; full-text setup, estimator, support assumptions, and experiment sections. | Learns from partial observational feedback. Uses counterfactual estimation and decision-regret objectives. | Partial labels, regret targets, and propensity correction cannot supply novelty alone. Avoid unsupported evaluation from adaptively selected states. |
| L6 | [Meta-Router](https://arxiv.org/abs/2509.25535); abstract and author repository. | Integrates scarce gold evaluation and biased preference data through a causal formulation. | Adding cheap surrogate labels needs its own comparator and bias analysis. It is outside the first threshold experiment. |
| L7 | [Instance-Dependent Complexity of Contextual Bandits and Reinforcement Learning: A Disagreement-Based Perspective](https://proceedings.mlr.press/v134/foster21a.html), COLT 2021; primary abstract. | Uses disagreement to characterize exploration difficulty. | Sampling where plausible policies disagree is prior art. A threshold implementation is not sufficient for a new theory claim. |

**Assessment:** the proposed gap is an unverified specialization involving ordered policies, shared feedback, repeat allocation, and stochastic token costs.
Its exact treatment may add value. The broad ingredients are covered by prior work.
G0 must decide whether a method contribution remains after the closest algorithms are mapped to this setting.

The deeper L2 read strengthens this caution. Its expected-impact and optimistic variants can simulate a changed aggregate label.
Its lookahead normalizes impact by the labels needed to change that aggregate.
The paper also reports substantial acquisition-computation overhead.
Our response draws estimate expected utility; they do not recover a single latent correct thinking label by majority vote.
That distinction motivates an adaptation. It does not establish a new acquisition principle.

The proposed equivalence audit must cover these concrete differences:

| Dimension | What is fixed in our proposal | Question still to resolve in G0 |
|---|---|---|
| Policy class | An ordered finite set of confidence thresholds. | Can existing policy-identification code handle this class without a new algorithm? |
| Observation | A paired correctness difference and thinking length for a fixed draft state. | Does the existing reward model already support this bounded utility directly? |
| Acquisition cost | A reserved maximum, then an observed stochastic token charge. | Does joint reward–cost dependence change the optimal allocation under the actual budget stop? |
| Repeats | New independent thinking draws for one fixed direct draft. | Is any new estimator required beyond re-active or pure-exploration methods? |
| Shared information | One response updates several threshold comparisons. | Is this exactly a standard feedback-graph specialization? |

If all five rows reduce directly to prior methods, the defensible contribution is an empirical study of those methods in this setting.
The plan does not assume that a new theorem or algorithm will survive this audit.

## 3. Router and reasoning controls

| ID | Primary source and retrieval level | Boundary for the project |
|---|---|---|
| L8 | [RouterDC](https://arxiv.org/abs/2409.19886), NeurIPS 2024; primary abstract, with prior repository full-text assessment recorded separately. | Contrastive query/model representations are established. Our previous assessment also records repeated solver samples in its supervision. Do not claim either ingredient as new. |
| L9 | [Cost-Aware Contrastive Routing for LLMs / CSCR](https://arxiv.org/abs/2508.12491v3); primary abstract. | Contrastive representations with cost-sensitive selection are established. A token penalty does not establish a contribution. |
| L10 | [SEMIROUTER](https://aclanthology.org/2026.eacl-long.228/), EACL 2026; proceedings abstract. | Limited-data router training and adaptation to model pools already have direct prior work. |
| L11 | [DART](https://arxiv.org/abs/2606.23181v4), updated 2026-10-03; primary abstract and version record. | Uses two direct drafts and answer agreement, then a predicted thinking budget. Our historical two-draft adaptation does not reproduce the whole method. |
| L12 | [Thinkless](https://arxiv.org/abs/2505.13379v2); primary abstract. | Learns a short/long reasoning decision with RL. Adding RL to thinking selection is insufficient for novelty. |
| L13 | [BEST-Route](https://arxiv.org/abs/2506.22716); primary abstract. | Joint model choice and inference sample count already exist. Distinguish training-repeat allocation from test-time repeated generation. |
| L14 | [Rethinking Calibration for Early-Exit Neural Networks](https://proceedings.mlr.press/v306/kubaty26a.html), ICML 2026; proceedings abstract. | Separates confidence calibration from the benefit and cost of extra computation. Our target is policy utility, not a generic calibration-error score. |

**Assessment:** retain confidence because our own evidence supports it as a control.
The focused plan studies how much it costs to learn that control.
It does not claim that threshold routing is new or universally best.

## 4. Work that limits an empirical or negative-results paper

| ID | Primary source and retrieval level | Boundary for the project |
|---|---|---|
| L15 | [What Does a Routing Oracle Measure Under Stochastic Decoding?](https://arxiv.org/html/2607.03436v3), 2026-09-27; full-text setup, audit, scope, and related-work sections. | Already separates decision classes, sampling coupling, scorer choices, and finite-draw sensitivity. Our cached same-question gains must not become a claimed deployable ceiling. |
| L16 | [Unsolvability Ceiling in Multi-LLM Routing: An Empirical Study of Evaluation Artifacts](https://arxiv.org/abs/2605.07395); primary abstract. | Studies judge, truncation, and formatting effects on routing evidence. Finding parser or cap failures alone is not a new empirical contribution. |
| L17 | [LLMs Can Predict Failure Risk, But Struggle to Predict Which Collaboration Protocol Pays Off](https://arxiv.org/abs/2608.14927); primary abstract and ancillary-file inventory. | Directly overlaps the distinction between predicting failure and predicting the value of more computation. A general claim that confidence can beat elaborate routing is insufficient. |

L15 previously appeared under the title “How Much of the Routing Gap Is Real?”
Search results still expose the older abstract. Use the current version and scope when writing the paper.
Do not count the two titles as separate studies.

**Candidate empirical difference:** a controlled direct/thinking study within one hybrid solver,
with independent response halves, matched representation/objective controls, full acquisition costs,
and explicit prospective follow-up failures. This is an assessment of possible added value.
It still needs an exact comparison with L15–L17 and broader independent evidence for broad claims.

## 5. Existing surveys and the remaining review question

| ID | Primary source and retrieval level | Existing coverage | Possible additional focus |
|---|---|---|---|
| L18 | [Dynamic Model Routing and Cascading for Efficient LLM Inference: A Survey](https://arxiv.org/html/2603.04445v3); full-text taxonomy, information boundary, and evaluation sections. | Broad multi-model methods, decision timing, input signals, computation methods, and evaluation. | Audit the evidence needed to identify the value of extra reasoning, with explicit training-data cost and repeat structure. |
| L19 | [Reasoning on a Budget](https://arxiv.org/html/2507.02076); full-text scope and taxonomy. | Adaptive and controllable test-time compute. | Distinguish the cost of learning a controller from its inference savings and the cost of proving those savings. |
| L20 | [Towards Concise and Adaptive Thinking in Large Reasoning Models](https://arxiv.org/abs/2507.09662); primary abstract. | Broad methods for concise and adaptive reasoning. | A narrowly coded evidence review could complement this methods taxonomy. |
| L21 | [From Selection to Generation: A Survey of LLM-based Active Learning](https://aclanthology.org/2025.acl-long.708/), ACL 2025; proceedings summary. | General LLM-based active learning. | Training-response acquisition for a fixed reasoning policy is a narrower target. |

Proposed review question:

> What evidence supports claims that adaptive reasoning saves compute, after counting controller training, repeated sampling, scoring, and evaluation cost?

Do not use “first survey” in the title or abstract.
First apply the proposed coding scheme to the closest surveys and 15–20 primary studies.
Proceed only if it produces information that their existing tables do not already provide.
The [publication plan](publication-plan-2026-10-08.md) specifies the review procedure.

## 6. Publication-policy checks

| Source checked on 2026-10-08 | Relevant rule | Consequence |
|---|---|---|
| [TMLR FAQ](https://www.jmlr.org/tmlr/faq.html) | New survey submissions are no longer considered from 2026-09-01. | Do not target a new pure survey at TMLR. Older accepted surveys and old survey-certification text do not override this change. |
| [TMLR scope](https://www.jmlr.org/tmlr/editorial-policies.html) and [criteria](https://www.jmlr.org/tmlr/acceptance-criteria.html) | Empirical insight and reproducibility work are in scope. Supported, useful findings matter; a novel algorithm is not mandatory. | Consider an original empirical paper when its claim and evidence are ready. A project log alone is insufficient. |
| [TACL guidelines](https://direct.mit.edu/tacl/pages/submission-guidelines) | A survey has the same originality and technical bar as a regular paper. | A short list of methods is insufficient. Verify current length and submission rules before preparation. |
| [CL survey guidance](https://cljournal.org/submissions.html) and [2025 editorial](https://direct.mit.edu/coli/article/51/1/1/127780/Opening-a-New-Chapter-for-Computational) | CL provides a survey route; guidance describes a proposal stage. The newer editorial lifted the annual survey cap. | A focused survey proposal is plausible. The informal guidance has an old footer; recheck the current submission portal before acting. |

No conference deadline, review duration, acceptance probability, or publication date is promised.
No editor was contacted and no submission was made.
