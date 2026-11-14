from decimal import Decimal as D, localcontext
from pathlib import Path

from consolidation.accounting import prior_equity
from consolidation.fx import FxBook
from consolidation.inputs import Inputs
from consolidation.model import Audit
from consolidation.scenarios import opening_bridge

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
