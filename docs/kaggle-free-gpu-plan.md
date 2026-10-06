# Free Kaggle compute: conditional training plan

The user has authorized free Kaggle GPU compute as an optional training
resource. This updates the earlier local-only preference for that option;
paid cloud/API work remains unauthorized. Docker stays running locally.
No login, upload, remote execution, model download or training has occurred.

The current scalar baseline refit and cached 1.7B diagnosis need no GPU.
First test the 1.7B reasoning-cap hypothesis under its own matched protocol.
If residual model-capability errors justify training, consider a bounded math
LoRA adapter with the original weights kept as a control. The training corpus,
held-out questions, prompts/modes, loss, adapter settings, seeds, compute cap and
evaluation protocol must freeze first. The 64 development questions cannot
serve as fresh evidence for a trained solver or router.

[PEFT's official guide](https://huggingface.co/docs/peft/main/en/quicktour)
describes training a small number of adapter parameters while keeping the base
weights fixed. That makes LoRA a plausible resource option, not an established
accuracy improvement or a new contribution. Mixing direct and thinking examples
needs separate evaluation of both modes; improving one may degrade the other.
A trained adapter is a new solver identity and requires fresh calibration and
comparison. Do not attach it to frozen completed study identities.

## Hardware and account boundary

[Kaggle GPU guidance](https://www.kaggle.com/docs/efficient-gpu-usage) describes
free GPUs and a weekly quota of 30 hours or sometimes more, subject to demand
and resources. This is not a promise about this account's remaining allocation.
[Notebook documentation](https://www.kaggle.com/docs/notebooks) lists P100 and
T4x2 options, 12-hour CPU/GPU sessions and 20 GB saved working output. Check the
actual device and quota before choosing a batch size or training budget. There
is no reason to connect a paid Colab account for this project.

The [readiness notebook](../notebooks/kaggle-free-gpu-readiness.ipynb) is ready
for review. It records GPU names/memory, CUDA, Python and package versions;
it performs no installs, model loading, data access or training. Its single code
cell was syntax-checked locally. It has not been run on Kaggle and does not
verify account eligibility or remote capacity. Keep Internet off for that check.

Do not assume Kaggle's CUDA environment is the same as the frozen local MPS
environment. Pin actual dependencies and precision after preflight; a matched
backend comparison must precede pooling CUDA and MPS solver results. Identical
integer seeds across backends do not establish identical stochastic outputs.

## Export boundary

Use a private notebook and a separately private dataset when an acquired
training export is actually needed. [Dataset documentation](https://www.kaggle.com/docs/datasets)
describes privacy and collaborator controls; notebook visibility is a separate
setting. Export an explicit manifest of permitted training records and code
with source/data checksums. Keep sealed validation/confirmation/test outcomes,
unclaimed reserve rows, credentials and whole project artifacts/cache out of
that package. Save adapter weights, logs and accounting for local independent
evaluation. This is a ready environment check and a conditional training plan,
not a launched or configured training experiment.
