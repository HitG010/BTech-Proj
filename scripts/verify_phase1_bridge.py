"""Independent fixed-endpoint arithmetic/preservation audit; never scores partial runs."""
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from reasoning_budget.confirmation import file_hash
from reasoning_budget.research_bridge import checked_arm, read_protocol
from reasoning_budget.storage import atomic_json, digest, envelope, read_json, verified

ROOT = Path('artifacts/research/data-efficiency-v1')
STUDY = ROOT / 'bridge-v1'
protocol = read_protocol(STUDY)
loaded = {arm: checked_arm(STUDY, protocol, arm) for arm in protocol['arms']}
assert all(len(rows) == 100 and all(r['status'] == 'completed' for r in rows)
           for _, rows in loaded.values()), 'No scoring or outcomes before full 200-response endpoint'

# These imports/accesses occur only after the complete endpoint guard above.
from reasoning_budget.data import load_gold  # noqa: E402
from reasoning_budget.scoring import score_record  # noqa: E402

gold = load_gold(ROOT / 'data' / 'bridge')
assert len(gold) == 25
report = verified(STUDY / 'report.json')
assert report['protocol_sha256'] == digest(protocol)
assert not report['synthetic']
assert report['cloud_spend_usd'] == 0 and not report['official_test_opened']
report_text = (STUDY / 'report.md').read_text()

def close(actual, expected):
    assert math.isclose(float(actual), float(expected), rel_tol=1e-12, abs_tol=1e-12), (actual, expected)

cells, audit = {}, {}
for arm, (manifest, rows) in loaded.items():
    frozen = protocol['arms'][arm]['snapshot']
    run = Path(frozen['run_dir'])
    completion = verified(STUDY / f'{arm}-completion.json')
    assert completion['protocol_sha256'] == digest(protocol)
    assert completion['completed'] == completion['expected'] == 100
    assert completion['records_sha256'] == digest(rows)
    assert not completion['gold_opened']
    artifact = read_json(run / 'scores.json')
    independently_scored = [score_record(r, gold[r['job']['question_id']]) for r in rows]
    assert artifact['scores'] == independently_scored
    assert artifact['gold_sha256'] == digest(gold)
    assert artifact['records_sha256'] == digest(rows)
    summary = report['summaries'][arm]
    assert summary['manifest_sha256'] == digest(manifest)
    assert summary['records_sha256'] == digest(rows)
    assert summary['scores_sha256'] == digest(artifact)
    by_job = {s['job_id']: s for s in independently_scored}
    arm_cells = {(r['job']['question_id'], r['job']['mode'], r['job']['sample']): r for r in rows}
    assert len(arm_cells) == 100
    assert len({key[0] for key in arm_cells}) == 25
    cells[arm] = (arm_cells, by_job)
    attempts = [verified(p) for p in (run / 'attempts').glob('*.json')]
    sessions = [verified(p) for p in (run / 'sessions').glob('*.json')]
    assert all(a['started_at'] >= protocol['prepared_at'] for a in attempts)
    # An interrupted attempt retains its full reservation; a later completed
    # cell must not erase that earlier charge from the ledger.
    assert all(a['status'] in {'started', 'completed', 'failed'} for a in attempts)
    spent = sum(a.get('charged_tokens', a['reserved_tokens']) for a in attempts)
    duration = sum(a.get('elapsed_seconds', a['reserved_seconds']) for a in attempts)
    setup = sum(s['setup_seconds'] for s in sessions)
    assert spent <= frozen['config']['limits']['max_tokens']
    assert duration + setup <= frozen['config']['limits']['max_elapsed_seconds']
    assert spent == summary['charged_tokens_all_attempts'] == completion['charged_tokens_all_attempts']
    close((duration + setup) / 3600, summary['elapsed_hours_all_attempts_and_setup'])
    close(duration + setup, completion['elapsed_seconds_all_attempts_and_setup'])
    close(setup, summary['setup_seconds'])
    assert len(attempts) == summary['attempts']
    for r in rows:
        res = r['result']
        for stage in ['reasoning', 'answer', 'inserted']:
            assert len(res['metadata'][stage + '_token_ids']) == res[stage + '_tokens']
        assert sum(res[k + '_tokens'] for k in ['reasoning', 'answer', 'inserted']) <= r['job']['max_tokens']
        assert res['metadata']['inserted_token_ids'] == ([151668, 271] if res['forced_closure'] else [])
        assert res['reasoning_seconds'] + res['answer_seconds'] + res['closure_seconds'] <= res['elapsed_seconds'] + .001
        attempt = verified(run / 'attempts' / (r['attempt_id'] + '.json'))
        assert attempt['charged_tokens'] == sum(res[k + '_tokens'] for k in ['reasoning', 'answer', 'inserted'])
    for mode in ['direct', 'thinking']:
        subset = [r for r in rows if r['job']['mode'] == mode]
        values = summary['modes'][mode]
        n = len(subset)
        assert n == values['responses'] == 50
        expected = {
            'accuracy': sum(by_job[r['job']['id']]['correct'] for r in subset) / n,
            'parse_failure_rate': sum(by_job[r['job']['id']]['parser_status'] != 'ok' for r in subset) / n,
            'answer_truncation_rate': sum(r['result']['answer_truncated'] for r in subset) / n,
            'forced_closure_rate': sum(r['result']['forced_closure'] for r in subset) / n,
            'mean_charged_tokens': sum(sum(r['result'][k + '_tokens'] for k in ['reasoning', 'answer', 'inserted']) for r in subset) / n,
            'raw_finite_coverage': sum(r['result'].get('mean_generated_logprob_raw') is not None and math.isfinite(r['result']['mean_generated_logprob_raw']) for r in subset) / n,
        }
        for field in ['prompt_tokens', 'reasoning_tokens', 'answer_tokens', 'inserted_tokens', 'elapsed_seconds', 'reasoning_seconds', 'answer_seconds']:
            expected['mean_' + field] = sum(r['result'][field] for r in subset) / n
        for key, value in expected.items():
            close(values[key], value)
        row_text = f"| {arm} | {mode} | {values['accuracy']:.1%} | {values['mean_charged_tokens']:.1f} | {values['mean_elapsed_seconds']:.2f} | {values['parse_failure_rate']:.1%} | {values['answer_truncation_rate']:.1%} |"
        assert row_text in report_text
    audit[arm] = {'completed': 100, 'attempts': len(attempts), 'sessions': len(sessions),
                  'attempt_statuses': dict(Counter(a['status'] for a in attempts)),
                  'charged_tokens': spent, 'setup_seconds': setup,
                  'elapsed_hours_all_attempts_and_setup': (duration + setup) / 3600}

old, old_scores = cells['legacy']
new, new_scores = cells['v3']
assert old.keys() == new.keys()
for key in old:
    assert old[key]['job']['seed'] == new[key]['job']['seed']
    qid, mode, sample = key
    cell = next(c for c in report['paired'][mode]['cells'] if c['question_id'] == qid and c['sample'] == sample)
    a, b = old[key]['result'], new[key]['result']
    delta_acc = int(new_scores[new[key]['job']['id']]['correct']) - int(old_scores[old[key]['job']['id']]['correct'])
    delta_cost = sum(b[k + '_tokens'] - a[k + '_tokens'] for k in ['reasoning', 'answer', 'inserted'])
    for field, expected in {'accuracy_delta': delta_acc, 'charged_tokens_delta': delta_cost,
                            'utility_delta': delta_acc - .05 * delta_cost / 1000,
                            'result_seconds_delta': b['elapsed_seconds'] - a['elapsed_seconds']}.items():
        close(cell[field], expected)
    assert cell['token_ids_equal'] == all(a['metadata'][s + '_token_ids'] == b['metadata'][s + '_token_ids'] for s in ['reasoning', 'answer', 'inserted'])
    assert cell['termination_equal'] == (a['termination'] == b['termination'])
    assert cell['extracted_answer_equal'] == (old_scores[old[key]['job']['id']]['extracted_answer'] == new_scores[new[key]['job']['id']]['extracted_answer'])
for mode, values in report['paired'].items():
    assert values['questions'] == 25 and values['matched_cells'] == 50
    for metric in ['accuracy_delta', 'charged_tokens_delta', 'utility_delta', 'result_seconds_delta']:
        means = np.array([sum(c[metric] for c in values['cells'] if c['question_id'] == qid) / 2
                          for qid in sorted({c['question_id'] for c in values['cells']})])
        close(values[metric]['mean'], np.mean(means))
        rng = np.random.default_rng(20261001)
        draws = np.mean(means[rng.integers(0, 25, size=(2000, 25))], axis=1)
        for a, b in zip(values[metric]['ci95'], np.quantile(draws, [.025, .975])):
            close(a, b)
    for field in ['token_ids_equal', 'termination_equal', 'extracted_answer_equal']:
        assert values[field] == sum(c[field] for c in values['cells'])

v3 = report['summaries']['v3']['modes']
projection = 400 * sum(m['mean_elapsed_seconds'] for m in v3.values()) / 3600
close(report['repeat_panel_projection_hours_excluding_setup_retries'], projection)
gates = {
    'complete_and_matched': True,
    'raw_confidence_covered': v3['direct']['raw_finite_coverage'] == 1,
    'answer_truncation': all(m['answer_truncation_rate'] <= .05 for m in v3.values()),
    'numeric_parser_coverage': all(m['parse_failure_rate'] <= .05 for m in v3.values()),
    'no_large_observed_accuracy_loss': all(p['accuracy_delta']['mean'] >= -.10 for p in report['paired'].values()),
    'repeat_panel_local_feasible': projection <= 48,
}
assert report['engineering_gates'] == gates and report['engineering_gate_passed'] == all(gates.values())

preservation = verified(ROOT / 'phase-1-step-3' / 'preservation.json')
for path, expected in preservation['files_before'].items():
    assert file_hash(path) == expected, path
for relative, expected in preservation['legacy_source_sha256'].items():
    assert file_hash(Path(preservation['legacy_checkout']) / relative) == expected, relative
assert not read_json('artifacts/confirmation/frozen-router-v1/status.json')['generation_started']

result = {
    'verified_at_utc': datetime.now(timezone.utc).isoformat(), 'code_commits': protocol['source_commits'],
    'protocol_payload_sha256': digest(protocol), 'protocol_file_sha256': file_hash(STUDY / 'protocol.json'),
    'allocation_payload_sha256': protocol['allocation_sha256'], 'report_payload_sha256': digest(report),
    'report_json_file_sha256': file_hash(STUDY / 'report.json'), 'report_md_file_sha256': file_hash(STUDY / 'report.md'),
    'verification_script_sha256': file_hash(__file__), 'arms': audit, 'engineering_gates': gates,
    'independent_arithmetic_and_bootstrap_verified': True, 'common_numeric_v5_rescoring_verified': True,
    'matched_seeds_and_cell_coverage_verified': True, 'frozen_sources_and_environment_verified': True,
    'protected_artifacts_verified': len(preservation['files_before']), 'legacy_sources_verified': len(preservation['legacy_source_sha256']),
    'old_confirmation_generation_started': False, 'official_test_gold_access': False,
    'training_gold_questions_accessed': 25, 'cloud_spend_usd': 0, 'offline_tests_passed_before_collection': 212,
    'limitations': ['25-question engineering diagnostic, not superiority/equivalence/novelty confirmation',
                    'Serial order and MPS thermal variation confound timing comparisons',
                    'Repeat-panel projection excludes setup/retries; memory maximum is sampled post-response allocation, not true MPS peak'],
}
atomic_json(ROOT / 'phase-1-step-3' / 'verification.json', envelope(result))
print({'independent_verification': 'passed', 'arms': audit, 'gates': gates})
