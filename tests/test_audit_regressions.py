import json
import csv
import shutil
from decimal import Decimal as D
from pathlib import Path
from unittest.mock import patch

import pytest

from consolidation.model import InputError
from consolidation.pipeline import run
from tests.test_pipeline import mutate_csv, add_sgd_rate, read_json

DATA = Path(__file__).resolve().parents[1] / 'data'


@pytest.fixture
def bundle(tmp_path):
    folder = tmp_path / 'data'
    shutil.copytree(DATA, folder)
    return folder


def journals(bundle, mutate):
    path = bundle / 'adjustments.json'
    batch = json.loads(path.read_text())
    mutate(batch)
    path.write_text(json.dumps(batch))


@pytest.mark.parametrize('change', ['lines_null', 'entries_null', 'empty_lines'])
def test_malformed_journals_replace_all_old_results(bundle, tmp_path, change):
    out = tmp_path / 'out'
    run(bundle, out)
    (out / 'obsolete.txt').write_text('stale')
    def mutate(batch):
        if change == 'entries_null':
            batch['entries'] = None
        else:
            batch['entries'][0]['lines'] = None if change == 'lines_null' else []
    journals(bundle, mutate)
    with pytest.raises(InputError):
        run(bundle, out)
    assert not (out / 'obsolete.txt').exists()
    assert all(v is None for v in read_json(out / 'control_figures_sd.json').values())
    assert read_json(out / 'validation.json')['status'] == 'failed'


def test_unexpected_error_after_partial_staging_never_publishes_partial_files(bundle, tmp_path):
    out = tmp_path / 'out'
    run(bundle, out)
    def broken_emit(stage, *args):
        (stage / 'incomplete.json').write_text('{')
        raise TypeError('simulated unexpected serialization failure')
    with patch('consolidation.pipeline.emit', broken_emit), pytest.raises(InputError):
        run(bundle, out)
    assert not (out / 'incomplete.json').exists()
    assert read_json(out / 'validation.json')['status'] == 'failed'


def test_publication_refuses_to_clear_unrelated_directory(bundle, tmp_path):
    out = tmp_path / 'user-files'
    out.mkdir()
    note = out / 'notes.txt'
    note.write_text('keep')
    with pytest.raises(InputError, match='not a recognized'):
        run(bundle, out)
    assert note.read_text() == 'keep'


def test_sgd_control_sums_equivalent_split_rows(bundle, tmp_path):
    add_sgd_rate(bundle)
    def split(rows):
        rows[1].update(txn_amount='20000.00', balance='11505.00')
        rows.append(dict(rows[1]))
    mutate_csv(bundle / 'tb_uk.csv', split)
    controls = run(bundle, tmp_path / 'out')
    assert abs(controls['sgd_bank_gbp'] - D('40000') / D('1.7')) < D('1e-20')
    alternative = read_json(tmp_path / 'out/scenarios/alternative_disclosed_assumptions.json')
    assert alternative['sgd_bank_reporting_amount'] == D('23529.41')


def test_split_accrual_reversal_is_still_held(bundle, tmp_path):
    def split(batch):
        entry = batch['entries'][8]
        debit = dict(entry['lines'][0], debit='32000.00')
        entry['lines'] = [debit, dict(debit), entry['lines'][1]]
    journals(bundle, split)
    controls = run(bundle, tmp_path / 'out')
    assert controls['journals'] == {'posted': 13, 'rejected': 2, 'held_for_review': 5}
    decisions = read_json(tmp_path / 'out/journal_decisions.json')
    assert next(d for d in decisions if d['id'] == 'JE-009')['status'] == 'held_for_review'


def test_split_audit_fee_remains_a_duplicate_candidate(bundle, tmp_path):
    def split(batch):
        entry = batch['entries'][18]
        debit = dict(entry['lines'][0], debit='24000.00')
        entry['lines'] = [debit, dict(debit), entry['lines'][1]]
    journals(bundle, split)
    controls = run(bundle, tmp_path / 'out')
    assert controls['journals'] == {'posted': 13, 'rejected': 2, 'held_for_review': 5}
    decisions = read_json(tmp_path / 'out/journal_decisions.json')
    assert next(d for d in decisions if d['id'] == 'JE-019')['status'] == 'held_for_review'


def test_scenario_bank_carrying_value_and_disclosure_follow_source(bundle, tmp_path):
    def update(rows):
        rows[1]['balance'] = '24010.00'
        rows[0]['balance'] = '1239000.00'
    mutate_csv(bundle / 'tb_uk.csv', update)
    run(bundle, tmp_path / 'out')
    alternative = read_json(tmp_path / 'out/scenarios/alternative_disclosed_assumptions.json')
    assert alternative['sgd_bank_reporting_amount'] == 24010
    assert '24,010.00' in alternative['assumptions']['A2']
    explanations = read_json(tmp_path / 'out/control_explanations.json')
    assert '24,010.00' in ' '.join(explanations['sgd_bank_gbp']['reasons'])


@pytest.mark.parametrize('local_code', ['1001', '1103', '0030', '2310'])
def test_nonmonetary_foreign_transactions_keep_historical_gbp(bundle, tmp_path, local_code):
    def mark_foreign(rows):
        row = next(r for r in rows if r['nominal_code'] == local_code)
        row.update(txn_currency='USD', txn_amount='800000.00')
    mutate_csv(bundle / 'tb_uk.csv', mark_foreign)
    run(bundle, tmp_path / 'out')
    result = read_json(tmp_path / 'out/scenarios/alternative_disclosed_assumptions.json')
    assert result['controls']['group_profit'] == D('2814702.81')
    issues = read_json(tmp_path / 'out/issues.json')
    assert any(i['code'] == 'nonmonetary_historical_carrying' for i in issues)


def test_invoice_matching_ignores_equivalent_decimal_format(bundle, tmp_path):
    mutate_csv(bundle / 'intercompany.csv', lambda rows: rows[-1].update(doc_amount='157460.0'))
    controls = run(bundle, tmp_path / 'out')
    assert controls['group_revenue'].quantize(D('.01')) == D('28301607.81')
    assert abs(controls['intercompany_difference']['balance_residual_after_resolution']) < D('1e-24')
