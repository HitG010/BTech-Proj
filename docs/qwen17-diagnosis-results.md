# 1.7B diagnosis: verified results and the next improvement test

The separately frozen descriptive audit is complete. Source `9bc9ac7`, plan
`7c7c62b1…72592`, report `558a8486…05d79`, independent review `c77eafcf…b27ac`.
All 2,652 study files and source pins remain unchanged. The review reproduces
all 128 paired cells, cap/category counts, six fixed-policy tables and optimistic
parser bounds from cached scores. No fitting, generation, rescoring, reference
access or label change occurred.

| Recorded policy | Accuracy | Generated tokens/question | Utility at lambda .05 |
|---|---:|---:|---:|
| Accept direct |84.375%|228.01|.832350|
| Think after every draft |87.500%|1586.79|.795661|
| Frozen confidence |83.594%|682.56|.801809|
| Confidence OR direct parser rejection |83.594%|720.50|.799913|
| Post-thinking syntax fallback |84.375%|682.56|.809622|
| Post-thinking cap fallback |85.156%|682.56|.817434|

Both fallback variants return the existing draft only when it parses and the
chosen thinking response is rejected or forcibly closed, respectively. The
entire thinking cost remains charged. These are post-hoc diagnostic rules;
neither is a freshly validated improvement or a deployed policy. All recorded
policy utilities remain below accepting direct.

Thinking rescues seven cells on four questions, harms three on two questions,
and leaves thirteen both-wrong cells on seven questions. Confidence escalates
34 times but selects only one rescue and two harms. Another high-capacity router
trained on these four positive-gain groups is not justified.

The reasoning cap is a plausible engineering bottleneck. **18 cells on 11
question groups** hit forced closure at 2,048 tokens. **12/18** thinking outputs
in that set are scored wrong, compared with **4/110** uncapped outputs. Cap hits
include nine of thirteen both-wrong cells, all three harms, and one rescue.
Harder questions or unproductive reasoning could cause this association; more
tokens are not guaranteed to fix it. The current sampling parameters match
the [official Qwen card](https://huggingface.co/Qwen/Qwen3-1.7B), which warns
against greedy thinking decoding.

The next controlled test is a separately frozen, paired 2,048-versus-4,096
reasoning-cap bridge on the cap-triggered development cells. Keep an old-cap
control, identical model/prompt/sampling, matched seeds and explicit extra-token
charges. At most36 responses reserve129,096 tokens before setup/failure buffer.
No such bridge has been prepared or started. It needs a new complete endpoint
and selected-training-reference policy; it cannot invoke the completed scorer
or claim whole-population gains from this enriched cohort.

The larger direct model is also a strong practical cross-size baseline for the
0.6B routing project. Its current accuracy and token utility exceed the smaller
parser-aware router's point estimates. Model-size-dependent FLOPs, memory and
live latency still need measurement; raw generated tokens are not the entire
compute cost.

If a matched cap test leaves repeatable capability errors, the user-approved
free Kaggle option can support a separately specified math LoRA study. The
[hardware notebook](../notebooks/kaggle-free-gpu-readiness.ipynb) is ready but
unexecuted. No upload, login, training or model download has occurred. Base-model
and adapter identities, training exclusions and fresh evaluation must remain
separate. See the [ordered improvement plan](qwen17-improvement-plan.md).
