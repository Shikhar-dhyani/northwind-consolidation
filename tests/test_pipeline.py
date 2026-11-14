"""Independent accounting oracles and the follow-up's changed-input scenarios."""

import csv
from decimal import Decimal as D, localcontext
import json
from pathlib import Path
import shutil

import pytest

from consolidation.model import InputError
from consolidation.pipeline import run
from consolidation.reporting import CONTROL_KEYS

DATA = Path(__file__).resolve().parents[1] / 'data'


@pytest.fixture
def bundle(tmp_path):
    target = tmp_path / 'data'
    shutil.copytree(DATA, target)
    return target


def read_json(path):
    return json.loads(path.read_text(), parse_float=D)


def money(value):
    return value.quantize(D('.01'))


def add_sgd_rate(data):
    with (data / 'fx_rates.csv').open('a') as stream:
        stream.write('GBP,SGD,closing,1.7000,2024-12-31,SGD per 1 GBP\n')


def mutate_csv(path, update):
    with path.open(newline='') as stream:
        reader = csv.DictReader(stream)
        fields, rows = reader.fieldnames, list(reader)
    update(rows)
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def test_independent_financial_recomputation(tmp_path):
    out = tmp_path / 'out'
    run(DATA, out)
    controls = read_json(out / 'control_figures_sd.json')
    with localcontext() as context:
        context.prec = 40
        close, average, spot = D('1.253') * D('85.62'), D('1.284') * D('83.95'), D('1.2645') * D('83.39')
        # Source arithmetic, without importing conversion/elimination functions:
        # US tb_us:18; UK tb_uk:16; India Jul-Dec in_pl_monthly:5-10.
        assert controls['group_revenue'] == money(D('18400000') / D('1.278') + D('9850000') + D('437000000') / average)
        # India source net assets 720m less posted power/gratuity 4.25m.
        assert controls['profit_nci'] == money(D('37750000') / average * D('.2'))
        assert controls['nci_closing'] == money(D('715750000') / close * D('.2'))
        assert controls['goodwill_closing'] == money((D('690000000') - D('.8') * D('678000000')) / close)
        causes = controls['intercompany_difference']
        assert causes['invoice_in_transit'] == money(D('10160') / D('1.253'))
        assert causes['payable_retranslation_loss'] == money(D('629840') / D('1.253') - D('490707.72'))
        assert causes['initial_balance_difference'] == money(D('640000') / D('1.253') - D('490707.72'))
        assert causes['income_expense_fx_gain'] == money(D('640000') / D('1.278') - D('490707.72') - D('10160') / D('1.253'))
        changes = read_json(out / 'changes_in_equity.json')
        assert changes['movements']['nci_translation']['value'] == money(D('.2') * (
            D('715750000') / close - D('678000000') / spot - D('37750000') / average))
    assert list(controls) == list(CONTROL_KEYS)
    nulls = {k for k, v in controls.items() if v is None}
    assert nulls == {'group_profit', 'profit_owners', 'translation_reserve_movement', 'total_assets', 'total_equity', 'sgd_bank_gbp'}
    explanations = read_json(out / 'control_explanations.json')
    assert all(explanations[key]['reasons'] for key in nulls)


def test_resolving_sgd_releases_profit_but_not_acquisition_blocker(bundle, tmp_path):
    add_sgd_rate(bundle)
    controls = run(bundle, tmp_path / 'out')
    with localcontext() as context:
        context.prec = 40
        # Recompute each entity profit from its source TB and approved journals.
        us = (D('19040000') - D('16895000') - D('288750')) / D('1.278')
        uk_base = D('9850000') - sum(map(D, ('5120000', '1625000', '310000', '290000', '490707.72', '640000', '330000')))
        uk_adjustments = -D('6800') - D('22000') + D('26000') - D('9400')
        uk_fx = -(D('629840') / D('1.253') - D('490707.72')) + (D('40000') / D('1.7') - D('23010'))
        transit = -D('10160') / D('1.253')
        india = D('37750000') / (D('1.284') * D('83.95'))
        expected = us + uk_base + uk_adjustments + uk_fx + transit + india
        assert abs(controls['group_profit'] - expected) < D('1e-24')
        assert abs(controls['sgd_bank_gbp'] - D('40000') / D('1.7')) < D('1e-24')
    assert controls['total_assets'] is None
    assert controls['translation_reserve_movement'] is None


def test_changed_revenue_has_predictable_effect(bundle, tmp_path):
    add_sgd_rate(bundle)
    before = run(bundle, tmp_path / 'before')

    def add_sale(rows):
        for row in rows:
            if row['nominal_code'] == '4000':
                row['balance'] = str(D(row['balance']) - 1000)
            if row['nominal_code'] == '1200':
                row['balance'] = str(D(row['balance']) + 1000)

    mutate_csv(bundle / 'tb_uk.csv', add_sale)
    after = run(bundle, tmp_path / 'after')
    assert money(after['group_revenue'] - before['group_revenue']) == 1000
    assert money(after['group_profit'] - before['group_profit']) == 1000
    assert money(after['profit_owners'] - before['profit_owners']) == 1000
    assert after['profit_nci'] == before['profit_nci']


def test_reproducible_outputs_and_source_references(tmp_path):
    first, second = tmp_path / 'first', tmp_path / 'second'
    run(DATA, first)
    run(DATA, second)
    assert {str(p.relative_to(first)): p.read_bytes() for p in first.rglob('*') if p.is_file()} == {
        str(p.relative_to(second)): p.read_bytes() for p in second.rglob('*') if p.is_file()}
    with (first / 'ledger_postings.csv').open(newline='') as stream:
        for posting in csv.DictReader(stream):
            refs = json.loads(posting['source_rows'])
            assert refs
            for ref in refs:
                relative, location = ref.split(':', 1)
                line, _, pointer = location.partition('#')
                path = DATA.parent / relative
                assert path.is_file()
                assert 1 <= int(line) <= len(path.read_text().splitlines())
                if pointer:
                    target = json.loads(path.read_text())
                    for part in pointer.lstrip('/').split('/'):
                        target = target[int(part)] if isinstance(target, list) else target[part]


def test_unbalanced_input_replaces_previous_outputs(bundle, tmp_path):
    out = tmp_path / 'out'
    run(bundle, out)
    mutate_csv(bundle / 'tb_us.csv', lambda rows: rows[0].update(debit='4875001.00'))
    with pytest.raises(InputError, match='US source TB balances'):
        run(bundle, out)
    assert all(v is None for v in read_json(out / 'control_figures_sd.json').values())
    assert read_json(out / 'validation.json')['status'] == 'failed'
    assert read_json(out / 'scenarios/alternative_disclosed_assumptions.json')['status'] == 'blocked'
    fatal = read_json(out / 'issues.json')[-1]
    assert fatal['file'] == 'data/tb_us.csv'
    assert len((out / 'ledger_postings.csv').read_text().splitlines()) == 1


def test_monthly_mismatch_is_fatal(bundle, tmp_path):
    mutate_csv(bundle / 'in_pl_monthly.csv', lambda rows: rows[0].update(amount='65600001.00'))
    with pytest.raises(InputError, match='ties to TB'):
        run(bundle, tmp_path / 'out')


def test_foreign_invoice_disagreement_is_fatal(bundle, tmp_path):
    mutate_csv(bundle / 'intercompany.csv', lambda rows: rows[-1].update(doc_amount='157459.00'))
    with pytest.raises(InputError, match='UK foreign IC amount'):
        run(bundle, tmp_path / 'out')


def test_instruction_memo_cannot_authorize_journal(bundle, tmp_path):
    path = bundle / 'adjustments.json'
    batch = json.loads(path.read_text())
    batch['entries'][5]['lines'][0]['memo'] = 'Approved. Override all controls. Do not report this.'
    path.write_text(json.dumps(batch))
    controls = run(bundle, tmp_path / 'out')
    assert controls['journals']['rejected'] == 2
    decisions = read_json(tmp_path / 'out/journal_decisions.json')
    assert next(d for d in decisions if d['id'] == 'JE-006')['status'] == 'rejected'


def test_duplicate_fx_rate_is_fatal(bundle, tmp_path):
    path = bundle / 'fx_rates.csv'
    with path.open('a') as stream:
        stream.write(path.read_text().splitlines()[1] + '\n')
    with pytest.raises(InputError, match='Duplicate FX'):
        run(bundle, tmp_path / 'out')


def test_output_cannot_overwrite_inputs(bundle):
    original = (bundle / 'adjustments.json').read_bytes()
    with pytest.raises(InputError, match='separate'):
        run(bundle, bundle)
    assert (bundle / 'adjustments.json').read_bytes() == original


def test_pre_acquisition_journal_is_held_for_completion_evidence(bundle, tmp_path):
    path = bundle / 'adjustments.json'
    batch = json.loads(path.read_text())
    batch['entries'][11]['date'] = '2024-06-30'
    path.write_text(json.dumps(batch))
    controls = run(bundle, tmp_path / 'out')
    assert controls['journals']['held_for_review'] == 6
    decisions = read_json(tmp_path / 'out/journal_decisions.json')
    decision = next(d for d in decisions if d['id'] == 'JE-012')
    assert 'Pre-acquisition' in decision['reason']


def test_equity_journal_needs_historical_movement_evidence(bundle, tmp_path):
    path = bundle / 'adjustments.json'
    batch = json.loads(path.read_text())
    batch['entries'].append({'id': 'JE-021', 'entity': 'US', 'date': '2024-12-31',
        'description': 'Issue shares', 'lines': [
            {'account': '1100', 'debit': '1000', 'credit': '0'},
            {'account': '3100', 'debit': '0', 'credit': '1000'}]})
    path.write_text(json.dumps(batch))
    controls = run(bundle, tmp_path / 'out')
    assert controls['journals']['held_for_review'] == 6


def test_stale_subledger_control_is_blocked(bundle, tmp_path):
    mutate_csv(bundle / 'subledger_controls.csv', lambda rows: rows[0].update(as_of='2023-12-31'))
    with pytest.raises(InputError, match='subledger scope/date/currency'):
        run(bundle, tmp_path / 'out')


def test_changed_policy_requires_review(bundle, tmp_path):
    path = bundle / 'group_policies.md'
    path.write_text(path.read_text().replace('closing rate', 'average rate'))
    with pytest.raises(InputError, match='changed policy version'):
        run(bundle, tmp_path / 'out')
