from decimal import Decimal, localcontext
from pathlib import Path

import pytest

from consolidation.fx import FxBook, MissingRate
from consolidation.inputs import Inputs
from consolidation.journals import apply_journals
from consolidation.model import Audit, total
from consolidation.periods import cut_india

DATA = Path(__file__).resolve().parents[1] / 'data'


def load():
    inputs = Inputs(DATA, Audit())
    return inputs, inputs.load()


def test_signs_mapping_and_duplicate_rows():
    inputs, rows = load()
    for entity in ('US', 'UK', 'IN'):
        assert total(rows, entity=entity)['value'] == 0
    assert total(rows, entity='UK', account='6100')['value'] == Decimal('1625000')
    assert total(rows, entity='UK', account='2300')['value'] == -180000
    assert total(rows, entity='UK', account='4100')['value'] == -9850000
    mismatches = [i for i in inputs.audit.issues if i['code'] == 'subledger_mismatch']
    assert [i['amount_affected'] for i in mismatches] == [45000, 45000]


def test_journal_security_and_business_review():
    inputs, rows = load()
    counts, decisions = apply_journals(inputs, rows)
    assert counts == {'posted': 13, 'rejected': 2, 'held_for_review': 5}
    statuses = {d['id']: d['status'] for d in decisions}
    assert statuses['JE-006'] == statuses['JE-017'] == 'rejected'
    assert statuses['JE-014'] == 'posted'
    assert statuses['JE-019'] == statuses['JE-020'] == 'held_for_review'
    assert any(i['code'] == 'untrusted_instruction' for i in inputs.audit.issues)


def test_period_cut_preserves_adjustments():
    inputs, rows = load()
    apply_journals(inputs, rows)
    rows, pre_profit = cut_india(inputs, rows)
    assert pre_profit == 18000000
    assert -sum(p.amount for p in rows if p.entity == 'IN' and inputs.coa[p.account]['statement'] == 'PL') == 37750000
    assert total(rows, entity='IN')['value'] == 0


def test_fx_direction_and_rate_types():
    inputs, _ = load()
    with localcontext() as ctx:
        ctx.prec = 40
        rates = FxBook(inputs)
        amount, refs = rates.convert(Decimal('107281860'), 'INR', 'GBP', 'closing')
        assert abs(amount - Decimal('1000000')) < Decimal('1e-30')
        assert len(refs) == 2
        with pytest.raises(MissingRate):
            rates.factor('SGD', 'GBP', 'closing')
