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


def test_missing_subledger_rows_are_reported_as_missing_evidence(bundle, tmp_path):
    mutate_csv(bundle / 'subledger_controls.csv',
        lambda rows: rows.__setitem__(slice(None), [r for r in rows if r['entity_id'] != 'UK']))
    run(bundle, tmp_path / 'out')
    missing = [i for i in read_json(tmp_path / 'out/issues.json') if i['code'] == 'subledger_missing_evidence']
    assert len(missing) == 2
    assert {i['amount_affected'] for i in missing} == {1985000, 1210000}
    assert all(i['file'] == 'data/subledger_controls.csv' for i in missing)


def test_duplicate_subledger_control_cannot_be_counted_twice(bundle, tmp_path):
    mutate_csv(bundle / 'subledger_controls.csv', lambda rows: rows.append(dict(rows[0])))
    with pytest.raises(InputError, match='duplicate subledger control'):
        run(bundle, tmp_path / 'out')


def test_alternative_lists_unknown_fx_not_covered_by_sgd_bank_assumption(bundle, tmp_path):
    mutate_csv(bundle / 'tb_uk.csv', lambda rows: rows[1].update(txn_currency='EUR'))
    controls = run(bundle, tmp_path / 'out')
    assert controls['group_profit'] is None
    result = read_json(tmp_path / 'out/scenarios/alternative_disclosed_assumptions.json')
    assert result['status'] == 'blocked_unquantified_dependencies'
    assert {d['source_currency'] for d in result['unquantified_dependencies']} == {'EUR'}
    assert all(value is None for value in result['controls'].values())
    assert any(i['code'] == 'alternative_unquantified_dependency' for i in read_json(tmp_path / 'out/issues.json'))


def test_mapping_external_sales_to_ic_income_is_blocked_by_invoice_coverage(bundle, tmp_path):
    mutate_csv(bundle / 'map_uk.csv', lambda rows:
        next(r for r in rows if r['local_code'] == '4000').update(group_code='4200'))
    with pytest.raises(InputError, match='UK 4200 IC invoice coverage'):
        run(bundle, tmp_path / 'out')
    assert read_json(tmp_path / 'out/control_figures_sd.json')['group_revenue'] is None


def test_unbacked_manual_ic_expense_is_not_swept_into_elimination(bundle, tmp_path):
    journals(bundle, lambda batch: batch['entries'][6]['lines'][0].update(account='8210'))
    with pytest.raises(InputError, match='UK 6300 IC invoice coverage'):
        run(bundle, tmp_path / 'out')


@pytest.mark.parametrize('entity', ['US', 'UK'])
def test_repeated_capital_rows_preserve_bridge_and_translate_historical_base_once(bundle, tmp_path, entity):
    def split(rows):
        code_field, code, amount_field = ('account_code', '3100', 'credit') if entity == 'US' else ('nominal_code', '3000', 'balance')
        row = next(r for r in rows if r[code_field] == code)
        row[amount_field] = str(D(row[amount_field]) / 2)
        rows.append(dict(row))
    mutate_csv(bundle / f'tb_{entity.lower()}.csv', split)
    run(bundle, tmp_path / 'out')
    scenario = read_json(tmp_path / 'out/scenarios/alternative_disclosed_assumptions.json')
    assert scenario['opening_equity_bridge']['agrees_after_rounding']
    assert scenario['controls']['group_profit'] == D('2814702.81')
    assert scenario['controls']['total_equity'] == D('18389975.22')
    with (tmp_path / 'out/ledger_postings.csv').open(newline='') as stream:
        capital = [p for p in csv.DictReader(stream) if p['entity'] == 'US' and p['account'] == '3100']
    assert sum((D(p['signed_gbp']) for p in capital), D(0)) == -1250000


def test_transient_directory_rename_lock_is_retried(bundle, tmp_path):
    original = Path.rename
    denied = 0
    def temporarily_locked(path, target):
        nonlocal denied
        if path.name == 'results' and denied < 2:
            denied += 1
            raise PermissionError('simulated transient scanner lock')
        return original(path, target)
    with patch.object(Path, 'rename', temporarily_locked), patch('consolidation.publication.time.sleep'):
        run(bundle, tmp_path / 'out')
    assert denied == 2
    assert read_json(tmp_path / 'out/validation.json')['status'] == 'checks_passed_with_disclosed_blockers'


def test_persistent_directory_lock_invalidates_existing_financial_results(bundle, tmp_path):
    out = tmp_path / 'out'
    run(bundle, out)
    original = Path.rename
    def locked(path, target):
        if path.name in ('results', 'failure'):
            raise PermissionError('simulated persistent directory lock')
        return original(path, target)
    with patch.object(Path, 'rename', locked), patch('consolidation.publication.time.sleep'), pytest.raises(InputError):
        run(bundle, out)
    assert read_json(out / 'validation.json')['status'] == 'failed'
    assert all(v is None for v in read_json(out / 'control_figures_sd.json').values())


def test_equivalent_iso_date_format_does_not_bypass_duplicate_detection(bundle, tmp_path):
    journals(bundle, lambda batch: batch['entries'][18].update(date='20241231'))
    controls = run(bundle, tmp_path / 'out')
    assert controls['journals'] == {'posted': 13, 'rejected': 2, 'held_for_review': 5}
