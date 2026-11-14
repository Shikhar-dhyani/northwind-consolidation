from decimal import Decimal as D, localcontext
from pathlib import Path
import json
import shutil
import pytest

from consolidation.accounting import prior_equity
from consolidation.fx import FxBook
from consolidation.inputs import Inputs
from consolidation.model import Audit
from consolidation.scenarios import opening_bridge
from consolidation.pipeline import run

DATA = Path(__file__).resolve().parents[1] / 'data'


def test_opening_bridge_is_conditional_and_preserves_subpenny_difference():
    with localcontext() as ctx:
        ctx.prec = 40
        inputs = Inputs(DATA, Audit())
        inputs.load()
        bridge = opening_bridge(inputs, FxBook(inputs), prior_equity(inputs))
        expected = D('14799373.43') / D('1.273') + D('2641510')
        assert bridge['reconstructed_gbp'] == expected
        assert bridge['reported_gbp'] == D('14267097.93')
        assert bridge['agrees_after_rounding']
        assert D(bridge['difference_gbp_unrounded']) == expected - D('14267097.93')
        assert bridge['difference_gbp'] != 0
        assert 'does not identify goodwill' in bridge['interpretation']
        assert bridge['sources']


def scenario(out):
    return json.loads((out / 'scenarios/alternative_disclosed_assumptions.json').read_text(), parse_float=D)


def test_alternative_is_separate_balanced_and_has_per_figure_dependencies(tmp_path):
    controls = run(DATA, tmp_path / 'out')
    result = scenario(tmp_path / 'out')
    assert controls['group_profit'] is None
    assert result['controls']['group_profit'] == D('2814702.81')
    assert result['balance_sheet']['residual'] == 0
    assert result['changes_in_equity']['rollforward_residual'] == 0
    assert result['figure_dependencies']['total_equity'] == ['A1', 'A2']
    assert result['figure_dependencies']['total_assets'] == ['A1', 'A1.gross', 'A2']
    assert result['figure_dependencies']['translation_reserve_movement'] == ['A1']
    assert result['sgd_bank_closing_measurement'] is None
    reasons = json.loads((tmp_path / 'out/control_explanations.json').read_text())
    assert '2,814,702.81' in ' '.join(reasons['group_profit']['reasons'])


@pytest.mark.parametrize('rate', ['2.0000', None])
def test_actual_sgd_fx_removes_a2_and_converges_under_same_a1(tmp_path, rate):
    bundle = tmp_path / 'data'
    shutil.copytree(DATA, bundle)
    baseline = run(bundle, tmp_path / 'before')
    before = scenario(tmp_path / 'before')
    with localcontext() as ctx:
        ctx.prec = 40
        actual_rate = D(rate) if rate else D('40000') / D('23010')
        with (bundle / 'fx_rates.csv').open('a') as stream:
            stream.write(f'GBP,SGD,closing,{actual_rate},2024-12-31,SGD per 1 GBP\n')
        actual = run(bundle, tmp_path / 'after')
        after = scenario(tmp_path / 'after')
        delta = D('40000') / actual_rate - D('23010')
        us = (D('19040000') - D('16895000') - D('288750')) / D('1.278')
        uk = (D('9850000') - sum(map(D, ('5120000', '1625000', '310000', '290000',
              '490707.72', '640000', '330000', '6800', '22000', '9400'))) + D('26000')
              - (D('629840') / D('1.253') - D('490707.72')) - D('10160') / D('1.253'))
        independent = us + uk + D('37750000') / (D('1.284') * D('83.95'))
        assert abs(actual['group_profit'] - independent - delta) < D('1e-24')
        assert actual['total_equity'] is None  # A1 is still not established by SGD FX.
        assert baseline['group_profit'] is None
        assert after['controls']['group_profit'] == actual['group_profit'].quantize(D('.01'))
        assert 'A2' not in after['active_assumptions']
        assert after['figure_dependencies']['total_equity'] == ['A1']
        assert abs(after['controls']['total_equity'] - before['controls']['total_equity'] - delta) < D('.011')
        assert after['controls']['translation_reserve_movement'] == before['controls']['translation_reserve_movement']


def test_failed_bridge_blocks_alternative_instead_of_inventing_a_residual(tmp_path):
    bundle = tmp_path / 'data'
    shutil.copytree(DATA, bundle)
    path = bundle / 'prior_year_group.csv'
    path.write_text(path.read_text().replace('12604747.93', '12604847.93'))
    run(bundle, tmp_path / 'out')
    assert scenario(tmp_path / 'out')['status'] == 'blocked'
