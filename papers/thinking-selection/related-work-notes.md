# Verified literature notes for the empirical manuscript

Primary-source check: 2026-10-09. These notes support drafting from the existing
[outline](../../docs/empirical-paper-outline-2026-10-09.md). They introduce no
experiment, dataset, model download, or external outcome analysis. Literature
claims below describe the cited authors' designs; their numerical results were
not reproduced. This is a targeted comparison, with no systematic-review or
priority claim. Bibliographic entries are in [references.bib](references.bib).

## Draftable related-work prose

Routing research already uses contrastive representations, repeated solver
supervision, and limited-data adaptation. RouterDC learns query/model and
query/query objectives and averages repeated sampled open-ended answers to
construct supervision (`chen2024routerdc`). CSCR adds cost-sensitive selection
in a shared prompt/model space (`shirkavand2025cscr`), while SEMIROUTER studies
sparse supervision and adaptation to new model pools (`wang2026semirouter`).
Our bounded controls examine representation and objective choices under a
specified paid-direct-draft, accept-or-fresh-thinking contract. They are not
faithful replications of those systems, and no external-method superiority is
established. [RouterDC full text](https://arxiv.org/html/2409.19886v1),
[CSCR full text](https://arxiv.org/html/2508.12491v3),
[SEMIROUTER proceedings](https://aclanthology.org/2026.eacl-long.228/).

Adaptive-thinking work also predates this study. Thinkless uses reinforcement
learning to select short or long reasoning (`fang2025thinkless`). DART samples
two direct drafts, uses agreement, and predicts a thinking budget when they
disagree (`lee2026dart`). BEST-Route jointly selects a model and its inference
sample count (`ding2025bestroute`). These differ from learning a two-action
policy after one observed draft; our historical agreement adaptation does not
reproduce full DART. [Thinkless](https://arxiv.org/abs/2505.13379v2),
[DART current record](https://arxiv.org/abs/2606.23181),
[BEST-Route](https://arxiv.org/abs/2506.22716v1).

The closest empirical papers already caution against interpreting routing
headroom as usable action value. Chen separates stochastic single-commit
ceilings from hindsight unions and specifies their coupling and scorer
dependence (`chen2026routingoracle`). Garg and Sagtani examine judge,
truncation, and formatting artifacts together with majority-policy collapse
(`garg2026unsolvability`). Yang et al. hold a solver fixed across collaboration
protocols and distinguish failure-risk prediction from protocol-specific
payoff (`yang2026failureprotocol`). Our narrower addition is a controlled
post-draft comparison with independent response halves, matched representation
controls, and explicitly limited follow-up. These design differences motivate
an empirical contribution; they do not establish method priority or broad
router failure. [Chen v3](https://arxiv.org/html/2607.03436v3),
[Garg and Sagtani v1](https://arxiv.org/html/2605.07395),
[Yang et al. v1](https://arxiv.org/html/2608.14927).

The released CLM provides state/action projection heads on a frozen Qwen3-8B
encoder, requiring the embedding recipe used in training
(`kwok2026clm`, `contrastiveLM2026release`). Our quantized transfer diagnostic
uses those released heads and a control on the same backbone. A failed
transfer recipe cannot establish failure of contrastive representations,
full-precision equivalence, or a quantization cause. The primary release is an
author blog and implementation, whose benchmark claims were not reproduced.
[Official repository](https://github.com/Contrastive-LM/CLM),
[official model card](https://huggingface.co/Contrastive-LM/CLM-v0.1-8B).

## Source and claim inventory

### Dataset, solvers, and representations

- **`cobbe2021gsm8k`** — Karl Cobbe et al., *Training Verifiers to Solve Math
  Word Problems*, arXiv:2110.14168 v2 (2021-11-18). The paper introduces GSM8K
  and studies selecting sampled solutions with a trained verifier. Cite for
  dataset provenance, not for the project's allocation, sealed-role rules, or
  parser. Metadata and abstract verified from the
  [arXiv record](https://arxiv.org/abs/2110.14168v2).
- **`qwen2025qwen3`** — An Yang et al., *Qwen3 Technical Report*,
  arXiv:2505.09388 v1 (2025-05-14). The report describes integrated thinking
  and non-thinking modes and a controllable thinking budget. Cite for model
  family capabilities; exact model revisions, sampler settings, closure
  behavior, and operational caps come from the project's frozen protocols.
  Sixty-author metadata and abstract checked against the
  [primary record](https://arxiv.org/abs/2505.09388v1).
- **`reimers2019sbert`**, **`wang2020minilm`**,
  **`sentencetransformersAllMiniLML6v2`** — Sentence-BERT supplies context for
  sentence embeddings; MiniLM describes base-model distillation. The exact
  `all-MiniLM-L6-v2` release is documented by its model card: 384-dimensional
  sentence vectors, contrastive sentence-pair training, and default truncation
  after 256 word pieces. Therefore the compact encoder is already contrastive
  before the project's small-head objective comparison. Do not cite the base
  MiniLM paper alone as evidence for this release's training recipe. Model
  card publication date is unspecified; the bibliography does not invent one.
  [Sentence-BERT](https://aclanthology.org/D19-1410/),
  [MiniLM v2](https://arxiv.org/abs/2002.10957v2),
  [release model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2).

### Established router and adaptive-compute designs

- **L8 / `chen2024routerdc`** — Shuhao Chen, Weisen Jiang, Baijiong Lin,
  James T. Kwok, and Yu Zhang; NeurIPS 2024, volume 37. Full-text Sections
  3.2–3.4 and 4.1 establish dual contrastive objectives and repeated
  open-ended supervision: scores average ten sampled outputs, using beam
  sampling at temperature .2. Thus neither contrastive routing nor repeated
  solver labels is new here. Its query-to-model choice precedes the selected
  answer; the present policy sees a completed direct draft.
  [Official proceedings](https://proceedings.neurips.cc/paper_files/paper/2024/hash/7a641b8ec86162fc875fb9f6456a542f-Abstract-Conference.html),
  [full text](https://arxiv.org/html/2409.19886v1). The proceedings BibTeX
  endpoint failed; verified author/title/volume/DOI fields were entered directly.
- **L9 / `shirkavand2025cscr`** — Reza Shirkavand, Shangqian Gao, Peiran Yu,
  and Heng Huang; *Cost-Aware Contrastive Routing for LLMs*, arXiv:2508.12491
  v3 (2025-11-24). CSCR is the method's name, expanded as Cost-Spectrum
  Contrastive Routing. It trains prompt/model representations with positives
  based on cost bands, then uses nearest-neighbor selection in a changing
  model pool. A token penalty or shared contrastive space supplies no priority
  claim. Metadata, abstract, and primary HTML checked; no faithful comparator
  was executed. [Record](https://arxiv.org/abs/2508.12491v3),
  [full text](https://arxiv.org/html/2508.12491v3).
- **L10 / `wang2026semirouter`** — Zijie Wang et al., EACL 2026,
  pp. 4910–4921. The paper addresses sparse supervision and adding models
  without retraining its backbone. Its PDF Section 4.2 describes anchor/sparse
  contrastive pairs combined with prediction training. Limited-data routing
  and contrastive adaptation already have direct precedent. The bibliography
  preserves the ACL-supplied author parsing, including `Zihao, Zeng`.
  [Official proceedings and BibTeX](https://aclanthology.org/2026.eacl-long.228/),
  [PDF](https://aclanthology.org/2026.eacl-long.228.pdf).
- **L11 / `lee2026dart`** — Jungseob Lee et al., arXiv:2606.23181 v4
  (2026-10-03). The current abstract specifies two no-think drafts, agreement,
  and entropy-based budget prediction upon disagreement. Exact metadata and
  version are verified; comparison here is abstract-level. The versioned URL
  failed direct retrieval once, while the
  [unversioned current record](https://arxiv.org/abs/2606.23181) exposes v4.
  No claim of reproducing or outperforming full DART is supported.
- **L12 / `fang2025thinkless`**, **L13 / `ding2025bestroute`** — Primary
  abstracts verify RL-based short/long choice and joint model/sample-count
  selection, respectively. Use only these design descriptions. Training-repeat
  allocation and inference sampling are distinct decisions. Their external
  efficiency percentages are not imported into the manuscript.
  [Thinkless v2](https://arxiv.org/abs/2505.13379v2),
  [BEST-Route v1](https://arxiv.org/abs/2506.22716v1).
- **L14 / `kubaty2026earlyexit`** — Piotr Kubaty et al., ICML 2026,
  PMLR 306:61372–61389. The abstract distinguishes classifier calibration from
  useful early-exit computation, proposing a correctness/cost criterion.
  This supports the conceptual boundary between confidence and action value,
  without asserting equivalence between neural early exit and a fresh language
  model solve. Metadata and abstract checked against
  [PMLR](https://proceedings.mlr.press/v306/kubaty26a.html).

### Released CLM and retrieval boundary

**`kwok2026clm`** — Jacky Kwok, Hangoo Kang, Tarun Suresh, Jon Saad-Falcon,
Marco Pavone, Christopher Ré, and Azalia Mirhoseini, 2026. The official GitHub
citation calls it *Contrastive Language Models* and labels it a Notion Blog.
The official model-card citation supplies the subtitle used in the BibTeX.
No arXiv or proceedings record was verified. The author blog returned an
internal retrieval error; the accessible
[repository](https://github.com/Contrastive-LM/CLM) and
[model card](https://huggingface.co/Contrastive-LM/CLM-v0.1-8B) establish the
released heads, frozen Qwen3-8B backbone, bidirectional InfoNCE description,
and required last-token pooling. The card distinguishes released zero-shot
heads from benchmark-specific finetuned heads and states that candidate scores
are relative to the supplied set. **`contrastiveLM2026release`** permits a
direct release-documentation citation. Do not describe this source as a
peer-reviewed paper, cite an invented arXiv ID, or present its benchmark
numbers as independently validated. Upstream mutable documentation is context;
the experiment's recorded asset and implementation pins identify its recipe.

### Closest empirical audits (L15–L17)

| Key and verified version | Primary support and overlap | Specific distinction and manuscript limit |
|---|---|---|
| **L15 / `chen2026routingoracle`** — Teng-Ruei Chen, v3, 2026-09-27 | Sections III–VI and Appendix C separate single-commit ceilings from hindsight unions, specify coupling, and audit scorer, pool, and finite-draw sensitivity. The archive uses 11 models and 30 draws per cell on three tasks. [Full text](https://arxiv.org/html/2607.03436v3). | Our accept-or-think policy is conditioned on a completed draft and evaluates learned actions across question folds and independent response halves. Hindsight gains cannot become deployable ceilings; this manuscript adds no oracle theorem. |
| **L16 / `garg2026unsolvability`** — Saloni Garg and Amit Sagtani, v1, 2026-05-08 | Sections 3, 5, and 8 discuss greedy generation, judge disagreement, truncation, format mismatch, and collapse checks using shuffled labels/random features across six benchmarks. [Full text](https://arxiv.org/html/2605.07395). | Our labels remain frozen while syntax compatibility is reported separately; cap and sparse guard follow-ups are interventions with restricted cohorts/identification. We have not reproduced its artifact decomposition or conducted a human mathematical scoring audit. |
| **L17 / `yang2026failureprotocol`** — Chih-Hsuan Yang et al., v1, 2026-08-14 | Sections 2–5 and Appendices B/C distinguish failure-risk ranking from which fixed-solver collaboration protocol pays. Broader task/solver checks have one deterministic realized outcome per problem/protocol pair. [Full text](https://arxiv.org/html/2608.14927). | Our sampled token-confidence and independent stochastic draw halves differ from its deterministic protocol outcomes and self-assessment probes. We have substantially less task/family breadth. Confidence beating some elaborate routers or fixed-solver routing is already covered. |

L15's current complete title is *What Does a Routing Oracle Measure Under
Stochastic Decoding? Coupling, Scorer Choice, and Single-Commit Ceilings*.
The current arXiv record explicitly states that it supersedes earlier
interpretations; the older “How Much of the Routing Gap Is Real?” title is not
a separate work. L17's complete title includes *Cost-Aware Protocol Routing
Across Reasoning Tasks*. Both versions and author order were checked against
the corresponding arXiv records.

## Unsupported extensions to avoid

- The sources support describing established designs; they do not show that
  the manuscript is the first to study contrastive routing, repeated
  supervision, confidence thresholds, parser effects, cap effects, or
  failure-risk/action-value mismatch.
- The present evidence supports comparisons among specified internal controls.
  It does not compare against a faithful external RouterDC, CSCR, SEMIROUTER,
  Thinkless, BEST-Route, or full DART implementation.
- The scoped paper does not need acquisition-priority or theorem claims.
  Existing G0 retrieval limits for acquisition supplements and the L4 full
  paper remain in their original records; this reference check does not close
  those limits or supersede the failed synthetic-acquisition screen.
- None of the literature checks establishes model pretraining disjointness,
  full-precision/quantized equivalence, causal reasons for a failed recipe, or
  deployment latency under co-resident solver/router execution.

No existing study source, outcome, scorer, reference, protocol, executor, or
model asset was changed or reopened. No tests were run for this writing task.
