"""Disclosed alternatives; never replace the authoritative control figures."""

from decimal import Decimal

from .model import ZERO, sources, total


def opening_bridge(inputs, fx, opening):
    rows = inputs.local_rows
    us = {r['account_code']: r for r in rows['US']}
    uk = {r['nominal_code']: r for r in rows['UK']}
    def usd_credit(code):
        return Decimal(us[code]['credit']) - Decimal(us[code]['debit'])
    base = usd_credit('3100') + usd_credit('3200') - Decimal(us['1600']['debit'])
    parent, rates = fx.convert(base, 'USD', 'GBP', 'opening')
    uk_equity = -sum((Decimal(uk[c]['balance']) for c in ('3000', '3200')), ZERO)
    reported = sum((v for v, refs in opening.values()), ZERO)
    reconstructed = parent + uk_equity
    difference = reconstructed - reported
    refs = sources(tuple(us[c]['_ref'] for c in ('3100', '3200', '1600')),
                   tuple(uk[c]['_ref'] for c in ('3000', '3200')), rates,
                   *(refs for v, refs in opening.values()))
    return {'parent_net_equity_usd': base, 'parent_net_equity_gbp': parent,
            'uk_equity_gbp': uk_equity, 'reconstructed_gbp': reconstructed,
            'reported_gbp': reported, 'difference_gbp': difference,
            'reconstructed_gbp_unrounded': str(reconstructed),
            'difference_gbp_unrounded': str(difference),
            'agrees_after_rounding': reconstructed.quantize(Decimal('.01')) == reported,
            'sources': list(refs),
            'interpretation': 'Conditional on A1: the net historical adjustment is zero within '
                'source rounding. This does not identify goodwill or gross asset/liability adjustments.'}
