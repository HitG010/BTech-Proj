# Submission and release checklist

Phase 4, steps 14–16 of the
[project review](../../../docs/project-review-and-publication-plan-2026-10-29.md).
These steps need decisions or actions by the authors. Nothing here has been
uploaded, submitted, or released.

## 1. Before anyone else reads it

- [ ] **Authors.** Names, affiliations, contributions, funding, and conflicts.
  Decide whether the supervisor is a co-author.
- [ ] **Endorsement.** Read every claim against the long report. The AI-assistance
  statement must stay.
- [ ] **Read the full texts** of the sources that were checked only at abstract
  level (blocked by the session network policy): Jitkrittum et al. 2023,
  Gupta et al. 2024, Lewis-Lim et al. 2026, Fanconi and van der Schaar 2025,
  and the one-line descriptions of Self-Route, AutoMix, Yue et al., and
  FrugalGPT. What to confirm for each is listed in the
  [reframing record](../cascade-reframing-2026-10-29.md#4-retrieval-limits-and-what-to-read-before-submission).
  Section 4's reading of the Jitkrittum et al. conditions depends on the first.

## 2. Feedback (step 14)

- [ ] Send the PDF to the supervisor and one or two peers. Ask specifically:
  is the main claim clear in one reading; is "missing gain, not demonstrated
  loss" convincing; is Figure 1 readable in print.
- [ ] Record the feedback and revise; keep the long report in sync.

## 3. Venue (step 16)

- [ ] Pick the workshop and confirm its page limit, template, deadline, and
  anonymity rules. The draft uses a plain article layout with no repository
  links in the text, so moving to a venue template is mechanical.
- [ ] For double-blind review, keep the author block anonymous and do not link
  the repository until after review.
- [ ] arXiv: pdfLaTeX, the bundled `.bbl`, categories cs.CL (primary) and cs.LG.
  Do not submit the same results to two archival venues at once.

## 4. Release (step 15)

Decisions needed before anything is made public:

- [ ] **Back up `artifacts/` from the Mac first.** The raw responses and score
  caches behind every number exist only there.
- [ ] **What to release.** Proposed: code, protocols, aggregate reports, and for
  each reported study the cached responses, v7 score sidecars, and
  verification records. Exclude the sealed confirmation allocation, the
  official-test role, and the prepared-but-unrun confirmation.
- [ ] **Licenses.** Code (for example MIT or Apache-2.0); the released
  responses inherit the terms of GSM8K (MIT) and the Qwen3 models
  (Apache-2.0). Check both before choosing a data license.
- [ ] **Archive and DOI.** For example a Zenodo record for the cached data,
  cited from the paper's data statement.
- [ ] **Repository clean-up.** Tag the old branch tips, fast-forward `master`
  to the current branch, and move the long agent log in `AGENTS.md` (which
  contains local machine paths) to a history file before making the
  repository public. These were proposed in the project review and still
  need approval.
- [ ] **Reproduce-from-cache command.** Written: `scripts/reproduce_paper.py`
  ([guide](../../../docs/reproduce-from-cache.md)). Still to do: run `export`
  then `check` on the Mac, confirm every value reproduces, and publish the
  cache file with the release.
