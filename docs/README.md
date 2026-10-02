# Research map

Start here if you are new to this repository. This page is an index: it says what
the project asks, which study answered which question, where each result lives,
and how the code is laid out. It adds no results of its own. Every number below is
copied from the linked study document, which remains authoritative.

Snapshot: 2026-10-03. The active implementation branch is
`codex/research-data-efficiency`, based on `research/router-studies` at
`15a4d2d`, with the prior research handoff checkpointed at `1b67fbc`.
The [research roadmap](research-roadmap.md) defines the current phases and gates;
the [first Phase 1 record](phase-1-evidence-repair.md) records the correction,
and [checkpoint 2](phase-1-protocol-reconciliation.md) records protocol integration
and legacy reproduction. [Checkpoint 3](phase-1-bridge.md) freezes the disjoint
roles and defines the paired generation bridge. Current offline verification:
the full 500-test suite plus two independent accounting tests pass; actual bridge collection and endpoint verification are complete,
with all six engineering gates passed. The [parser preflight](parser-preflight.md)
adds opt-in v7 while preserving the primary bridge's frozen v5 results.
The [repeat-panel protocol](phase-2-repeat-panel.md) is frozen: 50 disjoint
questions, 800 jobs, independent draw halves, question-held-out diagnostics and
deferred reference answers. All **800 responses are complete** after
[runtime recovery](phase-2-runtime-recovery.md) with Docker running. The
[results and post-hoc diagnosis](phase-2-repeat-results.md) report four failed
progression gates out of five; acquisition scaling remains stopped. The frozen
analysis reproduced exactly, and all 2,319 protected originals are unchanged.
Separate gold-free triage found five presentation candidates among 27 rejected
answers. Fixed-policy bounds show that these cases cannot reverse the observed
combined-versus-baseline comparison; the bounded parser compatibility preflight
has since completed with one narrow formatting repair.
The [October checkpoint and contrastive-router review](contrastive-router-review-2026-10-02.md)
adds bounded confidence/capacity and draft-representation controls, followed by
an optional released-CLM probe and a separately locked fresh signal test.
The [bounded feasibility results](phase-2-router-feasibility-results.md) are now
complete: 1,035 Ridge and 600 compact neural fits, with both exploratory screens
failed. All eight representation/objective families have negative average
point differences versus confidence. The [parser compatibility preflight](phase-2-parser-compatibility.md)
repairs one narrow formatting case without changing primary labels. The full
500-test suite plus two independent accounting tests pass; 33,600 reported
decisions were verified and all protected originals preserved. The subsequent
[local released-CLM preflight and power review](local-clm-and-power-results.md)
are complete: actual released heads with a 4-bit 8B encoder pass ten synthetic
engineering inputs at 4.95 GiB peak MLX allocation. Task routing quality remains
untested in that engineering stage. The subsequent
[cached CLM diagnostic](phase-2-clm-probe-results.md) completes 402 encodings,
450 Ridge/75 PCA fits and independent verification of 20,000 decisions; every
exploratory screen fails. Calibrated CLM averages −.033262 utility vs confidence,
with the raw encoder control also negative. Preserve the additive correction
for 75 conditional bootstrap intervals; primary averaged intervals are unchanged.
The [broader signal design](broader-signal-design.md) proposes a
diagnostic panel only; new generation/scaling remain unstarted. Contrastive
routing itself is not a new contribution. The latest user preference is local
experiments with Docker kept running.

## 1. The question

Qwen3 models have two inference modes: **direct** (non-thinking; a short answer,
sometimes with brief working) and **thinking** (a long hidden reasoning trace,
then an answer). Thinking is usually more accurate but costs 5–7× the generated
tokens. The project asks:

1. Can a cheap **router** decide, per question, whether thinking is worth its cost?
2. Can the training data for that router be collected with fewer generated tokens
   than sampling every question the same number of times? This was the original
   candidate contribution: **cost-aware acquisition**.

The solver is always frozen (Qwen3-1.7B, pinned revision). Only the router is learned.
Utility is `correct − λ · charged_tokens / 1000`, with λ = 0.05 as the preselected
primary preference: five accuracy points are worth 1,000 generated tokens.

## 2. Where things stand

- On GSM8K with Qwen3-1.7B, thinking beats direct by 4–10 points across studies
  once answers are not truncated. Most questions are answered correctly by both
  modes (73 of 100 in pilot v2, with both samples right in both modes). A mode
  difference shows up on only 15–23% of questions.
- **Routers that see only the question** (MiniLM embeddings with ridge, retrieval,
  or decision-focused heads) have not beaten random allocation at the same token cost.
- **Routers that see a first direct draft** (confidence gates, draft agreement as in
  DART, and the project's continuation router) are cheaper than always-thinking
  at similar accuracy. Between those methods, no difference is statistically established.
- The project's continuation router beats tuned confidence by +0.008 utility
  (95% CI −0.020 to +0.044): inconclusive. Detecting an effect that size needs
  about 3,000 fresh questions.
- A 3,100-question confirmation is **prepared but not started**. The latest
  [CPU router development result](router-dev-results.md) tested a shared
  correctness model on cached traces. It improved on refitted learned routers,
  but at the preselected cost preference tuned confidence matched its accuracy
  at lower token cost. A high-accuracy region is exploratory. The prepared
  125–142-hour confirmation remains for the unchanged earlier router.
- The official 500-question GSM8K test split has never been generated or scored.
- The new 50-question repeat panel rejects progression for the predeclared
  combined learner. Its four-draw average utility difference versus the
  training-selected baseline is −0.0162 (90% CI −0.0333 to −0.0006). The
  eight-draw secondary analysis favors tuned confidence: 92.5% accuracy at
  466.9 tokens, versus combined 89% at 799.5. These are diagnostic results,
  not independent confirmation. See [Phase 2 results](phase-2-repeat-results.md).
- The human scoring audit was waived by the user on 2026-09-18. Every
  audit so far is an agent review.

## 3. Two lines of work: read this before comparing numbers

The project diverged after commit `03380a9`. Both historical lines fixed the same pilot v1
truncation problem, independently and with **different protocols**.

| | router-studies lineage (this directory) | `research/pilot-v2` worktree |
|---|---|---|
| Location | `BTechProj/` | `BTechProj-pilot-v2/` (git worktree) |
| Dates | 2026-09-13 → 2026-09-22 | 2026-09-09 → 2026-09-10 |
| Git lineage | Active `codex/research-data-efficiency`; base `15a4d2d`; handoff checkpoint `1b67fbc`; studies 2–8 committed in `5519867` | HEAD `6c7903c` |
| Prompt | original boxed-answer instruction | Qwen3 model-card math prompt |
| Reasoning / answer tokens | 2,048 / 512 | 4,096 / 1,024 |
| Forced-closure text | `</think>\n\n` | Qwen3 report budget phrase |
| EOS ids | tokenizer default only | both checkpoint EOS ids |
| Direct confidence | post-warper mean log-prob | post-warper **and** raw-logit |
| Studies | calibration, routing, learnability, continuation, power, confirmation | pilot v2 feasibility report |
| Tests | 113 pass | 89 pass |

**Scorer names collide.** `numeric-v3` and `numeric-v4` mean different parsers on
the two lines:

- On `research/router-studies`, v3 adds repeating decimals and v4 stops Markdown headings from
  being read as `####` answers.
- On the branch, v3 strips LaTeX decoration and v4 stops prose after an answer
  label from being read as a claim.

Scores labelled `numeric-v4` are therefore not comparable across lines. The active
branch now merges the parser fixes as `numeric-v5`, with a source digest and
versioned caches. Their historical generation settings still differ.

The active `qwen3-boxed-budget-v3` protocol ports the full EOS list, raw-logit
confidence, configurable closure, incremental ledger, consecutive-failure policy,
and source provenance separate from run identity. Each new response identifies
its producing session/code; frozen-study readers reject mixed implementations.
The prompt, 2,048/512 research caps, closure, and original confidence signal are
retained. See [checkpoint 2](phase-1-protocol-reconciliation.md) for the exact
configuration. New role manifests are frozen; the 25-question generation bridge
completed 200/200 responses and passed all six engineering gates. All 100 matched
cells have identical token sequences across protocols on these inputs. See
[checkpoint 3](phase-1-bridge.md) for results and the unexercised new-EOS path,
conservative scoring limitation, and Phase 2 preflight. That scoring issue is now
resolved by separate v7 extraction: zero changes on 900 historical responses,
and only the duplicated final-180 case changes in the 200 bridge responses.
The separate sensitivity is 82% direct / 94% thinking; the v5 primary bridge
remains 80% / 94%. See [parser preflight](parser-preflight.md).

## 4. Study timeline

Every row is a completed or prepared study. The artifact paths are local and
ignored by Git.

| # | Study | Question it answered | Result | Doc · artifact |
|---|---|---|---|---|
| 0 | Smoke | Does the pipeline run end to end? | 20/20 records; direct 10/10, thinking 7/10 (3 truncated) | [verification](verification.md) · `runs/63d94a10…` |
| 1 | Pilot v1 | Direct vs thinking on 100 GSM8K, 2 samples each | Direct 63%, thinking 46% (−17 pp). **A protocol artifact**: 168 of 182 failures were truncated at 256 answer tokens | [pilot-results](pilot-results.md) · `runs/af1f1e56…` |
| 1b | Pilot v2 *(branch)* | Same questions, protocol v2 | Direct 83.5%, thinking 93.0%, +10 pp [3, 16]; oracle 96%; confidence AUROC 0.83 | branch `docs/pilot-v2-report.md` · `runs/f73a5665…` |
| 2 | Answer-cap calibration | Which answer allowance removes truncation? | 25 questions: 256 → 60/46%, 512 → 72/88%, 1,024 → 72/88%. 512 frozen | [calibration-results](calibration-results.md) · `calibration/answer-cap-v1` |
| 3 | Calibrated pilot | Full 100 questions at 512 answer tokens | Direct 84%, thinking 92%, 1.5% truncation per mode | [routing-learnability](routing-learnability.md) · `runs/d00485799…` |
| 4 | Routing learnability | Can a MiniLM/ridge question-only router beat random? | Ridge +0.24 pp over cost-matched random [−2.58, +3.13]; DART-SC-2 +1.55 pp [−1.18, +4.36]. Neither reliable | [routing-learnability](routing-learnability.md) · `routing/e1dd7627…` |
| 5 | Stronger routers | Do retrieval or decision-focused heads fix it on disjoint data? | Decision head beats ridge on utility (+0.040 [0.007, 0.078]) but thinks on 1/50 questions, no better than always-direct. DART-SC-2: 95% at 759 tokens | [stronger-router-study](stronger-router-study.md) · `learnability/baselines-v1` |
| 6 | Continuation routing | After one direct draft: accept, buy a second draft, or think now? | Joint 88.0% at 728 tokens; gain-ridge 89.0% at 877; confidence 86.5% at 592; always-thinking 89.5% at 1,414. Primary +0.008 [−0.020, +0.044]: inconclusive | [continuation-study](continuation-study.md) · `probe/continuation-v1` |
| 7 | Power analysis | How many fresh questions would confirm study 6? | 3,029 for 80% power; about 122–139 local hours | [confirmation-design](confirmation-design.md) · `probe/continuation-v1/power-analysis.md` |
| 8 | Frozen confirmation | Confirm the unchanged router on 3,100 fresh questions | **Prepared, not started** (15,500 responses in 31 batches) | [confirmation-design](confirmation-design.md) · `confirmation/frozen-router-v1` |
| 9 | Shared-correctness CPU development | Does a coherent first-correctness model improve continuation decisions? | At λ=.05: 90.25% at 622 tokens; confidence also 90.25% at 589.4. Secondary high-accuracy lead remains exploratory | [router-dev-results](router-dev-results.md) · corrected `router-dev/shared-base-v2`; v1 preserved |
| 10 | Evidence repair | Is standalone thinking charged correctly? | Corrected to 91.50% at 1,430.69 tokens; all six other policies unchanged; no solver generation | [Phase 1 record](phase-1-evidence-repair.md) |
| 11 | Protocol reconciliation | Can new collection be consistent and historical artifacts preserved? | 195 offline tests; 900 records and 14 artifacts preserved; zero gold-free parser differences; real bridge pending | [Checkpoint 2](phase-1-protocol-reconciliation.md) |
| 12 | Paired protocol bridge | Does v3 pass the engineering screen on 25 new training questions? | 200/200 completed; all gates pass; 100/100 matched token sequences; direct 80%, thinking 94% in both arms; finite v3 direct confidence 50/50 | [Checkpoint 3](phase-1-bridge.md) · `research/data-efficiency-v1/bridge-v1` |
| 13 | Parser preflight | Can final sections distinguish intermediate boxes without losing valid cached answers? | V6 rejected for 44 prose regressions; v7 changes only one duplicated bridge case across 1,100 records. Separate sensitivity 82%/94%; primary v5 unchanged | [Parser preflight](parser-preflight.md) · `research/data-efficiency-v1/parser-v7-preflight-v1` |
| 14 | Repeat-panel study | Does repeated supervision support useful routing on independent draws and unseen questions? | 800/800 complete; four of five progression gates fail; four-draw average utility difference −0.0162; acquisition scaling stopped | [Phase 2 results](phase-2-repeat-results.md) · [Protocol](phase-2-repeat-panel.md) · [Runtime recovery](phase-2-runtime-recovery.md) · `research/data-efficiency-v1/repeat-panel-v1` |
| 15 | Post-hoc signal diagnosis | Is the failed learner missing useful escalation opportunities? | Combined full8 captures 5 positive-gain pairs in 174 escalations; confidence captures 16 in 58; no new candidate fitting or generation | [Separate development diagnosis](phase-2-repeat-results.md) · `research/data-efficiency-v1/repeat-diagnosis-v1` |
| — | Active roadmap | What should come next? | Protocol repair, supervision diagnosis, then gated data-efficient acquisition; defer study 8 | [research roadmap](research-roadmap.md) |

### Run registry (`artifacts/runs/`)

| Run | Study | Questions × samples | Caps (reasoning/answer) |
|---|---|---|---|
| `0cfc724c…`, `0d73cf0f…`, `6aee51ca…` | offline fake-backend checks | 10 fixtures × 1 | — |
| `0d1ecd02…` | abandoned first smoke (partial, 8 records) | fixtures | 2,048 / 256 |
| `63d94a10…` | smoke (0) | 10 × 1 | 2,048 / 256 |
| `af1f1e56…` | pilot v1 (1) | 100 × 2 | 2,048 / 256 |
| `2116b22f…`, `f73a5665…` | branch smoke v2, pilot v2 (1b) | 10 × 1, 100 × 2 | 4,096 / 1,024 |
| `d883ad97…`, `b819354d…` | calibration arms (2) | 25 × 2 | 2,048 / 512 and 1,024 |
| `d00485799…` | calibrated pilot (3); training data for 4 and 6 | 100 × 2 | 2,048 / 512 |
| `49622886…`, `bf2834fe…`, `12ea5bac…` | stronger routers (5): train, tune, diagnostic | 50 × 1, 50 × 2, 50 × 2 | 2,048 / 512 |
| `931c0e7a…`, `c79bba43…` | continuation diagnostic (6): direct ×3, thinking ×2 | 100 fresh | 2,048 / 512 |

`artifacts/routing/115f6c7e…` is an earlier version of study 4. No document refers
to it, and `e1dd7627…` supersedes it.

## 5. Code map

All code is in `src/reasoning_budget/`, with one CLI entry point, `rb`
(`cli.py`). Data flows: config → questions → jobs → generation records → scores →
reports → router studies.

| Layer | Module | Role | CLI |
|---|---|---|---|
| Infrastructure | `config.py` | Strict YAML schema; unknown keys rejected | — |
| | `storage.py` | Canonical hashing, atomic writes, checksum envelopes, run locks | — |
| | `records.py` | Gold-free dataclasses: `Question`, `GenerationJob`, `GenerationResult`, `ScoredResult` | — |
| Data | `data.py` | Frozen disjoint GSM8K splits (100 pilot / 400 train / 100 val / 500 test); gold kept in a separate file | `rb prepare` |
| Generation | `backend.py` | Batch-one Transformers backend with a two-stage (reasoning, answer) protocol and forced closure; fake backend for tests | `rb doctor` |
| | `runner.py` | Resumable jobs, per-job seeds, token/time reservations, attempt ledger | `rb smoke`, `rb generate` |
| Scoring & reporting | `scoring.py` | Exact rational numeric parser that never sees gold | `rb score` |
| | `scoring_v7.py` | Opt-in final-section parser; complete frozen bridge or synthetic fixtures only | `python -m reasoning_budget.scoring_v7` |
| | `scoring_v6.py` | Rejected numeric-only candidate retained for provenance; v7 also reuses structural helpers | Do not select for new studies |
| Phase 2 | `research_repeat.py` | Frozen repeat role, jobs, budgets, source/endpoint guards and deferred selected-only v7 scoring | `python -m reasoning_budget.research_repeat …` |
| | `repeat_stats.py` | Nested question-fold diagnostics, independent draw halves, acquisition accounting and scaling gates | Via repeat `analyze` |
| | `scripts/diagnose_repeat_signal.py` | CPU-only post-hoc oracle, variance and policy-decision diagnostics from the completed scored endpoint | `.venv/bin/python scripts/diagnose_repeat_signal.py` |
| | `reporting.py` | Whole-question bootstrap, paired differences, audit worksheets, cost projection | `rb report`, `rb audit` |
| Study 2 | `calibration.py` | Answer-cap comparison and confirmation | `rb calibrate …` |
| Study 4 | `controller.py` | MiniLM + lexical features (387 dims); four ridge predictors; portable model | — |
| | `routing.py` | Nested cross-validation on the pilot; baselines (random, confidence, DART-SC-2) | `rb routing` |
| Study 5 | `stronger.py` | Retrieval/shrinkage and regret-weighted logistic routers; training-only PCA | — |
| | `learnability.py` | Frozen train/tune/diagnostic pipeline | `rb learnability …` |
| Study 6 | `probe.py` | Continuation router (accept / probe / think), DART-SC-3, confidence gates | — |
| | `probe_study.py` | Frozen continuation study | `rb probe …` |
| Studies 7–8 | `power.py` | Paired power and sensitivity | `rb power` |
| | `confirmation.py`, `confirmation_stats.py` | Fresh-sample selection, batched collection, paired t-test, Holm correction | `rb confirm …` |

Each study module has a matching `tests/test_<module>.py`. Tests never load Qwen
or use a GPU.

## 6. Reading order

1. This page.
2. [pilot-results](pilot-results.md): how a token cap can reverse a conclusion.
3. [calibration-results](calibration-results.md): how the protocol was fixed.
4. [routing-learnability](routing-learnability.md), then
   [stronger-router-study](stronger-router-study.md): why question-only routing
   has not worked yet.
5. [continuation-study](continuation-study.md): the current method and its
   prior-art boundary.
6. [confirmation-design](confirmation-design.md) and
   [router-improvement-research](router-improvement-research.md): the proposed
   router change and its [CPU result](router-dev-results.md).
7. [router-research-proposal](router-research-proposal.md): the literature table
   and the acquisition idea.
8. `../plan.md`: the milestone checklist and dated execution log.
9. `../README.md`: how to run every command.

## 7. Open decisions and hazards

- **Current worktrees.** This directory is on `codex/research-data-efficiency`,
  descended from `research/router-studies`, and the sibling worktree remains on
  `research/pilot-v2`. The prior handoff is checkpointed at `1b67fbc`, while
  generated artifacts stay local and ignored by Git. Recheck branch and
  status before continuing work; the root [AGENTS.md](../AGENTS.md) records the
  layout and the active research handoff.
- **Protocol divergence.** Section 3 describes the historical lineages. The new
  protocol/scorer identities are implemented; their real generation bridge is
  complete with all engineering gates passed. Exact observed agreement on the
  bridge does not justify pooling other historical protocols or claiming global
  equivalence. Use pinned legacy code to reproduce earlier frozen studies.
- **Task headroom.** Both lines found that GSM8K leaves little room between
  cheap confidence routing and the per-question oracle. The branch recommended
  adding a set with a wider thinking gap (numeric MATH, GSM-Plus, or procedural
  tasks). The router-studies line has not yet acted on this.
- **Label-noise ceiling check.** The branch plan gates the acquisition idea on
  training with 1-sample versus 8-sample labels. This check has not been run.
- **Compute.** Batch-one MPS runs at about 23 tokens/s. The branch plan's
  batched vLLM backend has not been built.
- **Missing baselines.** Full DART SC-Budget and full ReASC have not been
  reproduced. The current comparators are labelled adaptations.

## 8. Glossary

| Term | Meaning here |
|---|---|
| Direct / thinking | Qwen3 chat template with `enable_thinking=False` / `True` |
| Forced closure | Reasoning reached its token limit, so the closure text was inserted and the answer stage continued |
| Answer truncation | The answer stage hit its cap; always scored incorrect |
| Charged tokens | Generated plus inserted tokens, summed over every call a policy makes |
| λ (cost preference) | Accuracy points traded per 1,000 charged tokens; primary λ = 0.05 |
| Cost-matched random | Random direct/thinking allocation with the same expected token cost as the policy being compared |
| Oracle | Picks the better mode per question from the same noisy samples; optimistic, not a deployable ceiling |
| Orientation | Which of two cached direct drafts plays "first draft"; both are averaged within a question and never counted as separate questions |
| Rescue / regression | A continuation turns a wrong first answer right / a right first answer wrong |
| DART-SC-2 / SC-3 | Local adaptations of DART's agreement router: two drafts, then think on disagreement / a third-draft majority vote first |
| Development vs diagnostic vs test | Development data may be reused for design. A diagnostic is fresh once, then becomes development. The official test is sealed |
