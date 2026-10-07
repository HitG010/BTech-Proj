# Improving the 1.7B solver: diagnose before training

The larger model here is Qwen3-1.7B. Its direct accuracy is already **84.375%**
on the 64-question development panel, versus 61.719% for 0.6B direct. Its
87.500% thinking accuracy is also higher than 0.6B thinking. The problem is
limited extra benefit from thinking, expensive responses and poor routing.
Do not describe the larger solver as generally less accurate.

At the current lambda .05, 1.7B direct also has higher observed token utility
than the 0.6B parser-aware router: .832350 versus .781867. The respective
generated tokens are 228.01 and 1081.41 per question. A practical future system
comparison must therefore include the larger direct solver as a strong control.
These are paired-development point estimates. Generated tokens alone do not
measure model-size-dependent FLOPs, resident memory or live latency.

## What to improve first

The [cached diagnosis](qwen17-performance-diagnosis.md) identifies three separate
issues. First, thinking fixes only seven direct errors on four questions, while
introducing three errors. Second, confidence escalates 34 times but catches
only one rescue and two harms; another large router trained on four positive
questions is not justified. Third, 18 thinking responses hit the 2048-token
reasoning cap. Nine of 13 both-wrong pairs and all three harms occur in those
cap-hit cells. This is a strong association, not proof that the cap caused the
errors or that additional tokens will fix them.

Use direct acceptance as the current reference operating point. The post-hoc
cap fallback increases confidence-policy accuracy from 83.594% to 85.156% at
the same 682.56 paid tokens, but utility .817434 remains below direct .832350.
The syntax fallback restores one scored answer but also remains below direct
utility. These are diagnostic controls, not deployed or freshly validated rules.

The current sampling settings match the
[official Qwen3-1.7B guidance](https://huggingface.co/Qwen/Qwen3-1.7B).
The card warns against greedy thinking decoding. Keep those settings; a decoder
change is not an established repair. The boxed-answer prompt is already present.
No frozen model, decoder, scorer or label should be changed in place.

## Conditional matched reasoning-cap bridge

This step is now [complete and independently verified](qwen17-cap-bridge-results.md).
One of 18 responses was rescued at 4k, with no harms. The primary 11-question
accuracy gain is 4.55 percentage points, with 1,662.45 extra tokens and a
−.037668 utility difference at lambda .05; its interval includes zero. Keep
2k as the current operating point. No default 4k promotion or additional cap
grid is justified.
The historical preparation proposal below records the original design; the
completed study and its explicit runtime deviations are in the results record.

The next accuracy hypothesis is **2048 versus 4096 reasoning tokens**, with the
same 512 answer cap and 2 closure tokens. Select the current 18 capped cells by
their gold-free cap flag only, not by correctness. They are an enriched
development cohort, not 18 independent fresh questions or a representative
population sample. Rerun a matched old-cap control along with the extended-cap
arm under one frozen backend; do not compare only a new arm with old timing.

Before generation, freeze exact cells, both arms, shared per-cell seeds, model
revision, tokenizer/chat template, unchanged prompt/sampling/v7, score endpoint,
full setup/failure accounting and independent review. The response-only maximum
for 36 jobs is `18 × (2562 + 4610) = 129,096` tokens. A 160k-token/four-hour envelope
is only a proposed upper limit; no collector or bridge has been prepared.
Both arms must finish and exit before any separately authorized scoring of
selected upstream-training references. Do not reopen old references merely to
repeat their scores. Report accuracy change, extra tokens, net utility at the
unchanged lambda and losses as well as rescues. A gain here still needs a fresh
whole-question study before broad claims.

On CUDA, integer seed equality does not establish equivalence with the old MPS
traces. If Kaggle is used, first record the backend and run both bridge arms
there. A local comparison remains the default; free Kaggle training is now an
available option. Preserve the old MPS endpoint and interpret runtime separately.

## When training becomes justified

The completed extended arm still has eight accepted numeric outputs scored
incorrect and three parser-rejected outputs. Use cached error/format diagnosis
to distinguish these cases before freezing a training design. No new reference
fetch, generation, adapter fit or Kaggle action follows automatically from
this result. Training and fresh evaluation retain the boundaries below.

If a matched cap test leaves repeatable mathematical errors, prepare a small
supervised math LoRA experiment on free Kaggle hardware. Keep frozen base-model
weights as the control, and train on a separately approved acquired corpus
with question-group exclusions. Do not train on fresh evaluation, sealed roles
or the 64 development questions and then claim fresh gains on them. Evaluate
direct and thinking modes separately; adapter training changes the solver and
requires new calibration, identity and evaluation protocols.

The [Kaggle readiness plan](kaggle-free-gpu-plan.md) provides a hardware-only
notebook and explains the remaining environment/data pins. No adapter, RL,
training dataset export, login or remote job is launched now. More compute alone
does not supply the data, evaluation or novelty evidence. This is an ordered
test plan, not a claim that cap extension or fine-tuning has improved the model.
