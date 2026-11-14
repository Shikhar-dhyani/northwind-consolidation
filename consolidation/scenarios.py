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


def alternative(inputs, fx, opening, local, postings, india, bank, reports):
    bridge = opening_bridge(inputs, fx, opening)
    if not bridge['agrees_after_rounding']:
        inputs.audit.issue('alternative_bridge_mismatch', tuple(bridge['sources']),
                           bridge['difference_gbp'], 'GBP', 'blocked',
                           'Alternative blocked: opening equity bridge does not agree.')
        return {'status': 'blocked', 'reason': 'Opening bridge no longer agrees; A1 cannot be supported.',
                'opening_equity_bridge': bridge}
    refs = sources(bridge['sources'], *(p.refs for p in postings))
    def known(types):
        return sum((p.amount for p in postings if p.amount is not None
                    and inputs.coa[p.account]['account_type'] in types), ZERO)
    investment = total(postings, entity='US', account='1600')['value']
    assets = known(('Asset',)) - investment
    liabilities = -known(('Liability',))
    # Net historical GBP adjustments cancel in equity under A1 regardless of their
    # gross asset/liability allocation. Gross totals additionally require A1.gross.
    equity = known(('Asset', 'Liability')) - investment
    profit = -known(('Revenue', 'Expense'))
    owners = profit - india['profit_nci']
    us_profit = -sum((p.amount for p in local if p.entity == 'US'
                     and inputs.coa[p.account]['statement'] == 'PL'), ZERO)
    closing, _ = fx.factor('USD', 'GBP', 'closing')
    opening_rate, _ = fx.factor('USD', 'GBP', 'opening')
    average, _ = fx.factor('USD', 'GBP', 'average')
    investment_translation = sum((p.amount for p in postings if p.entry == 'IN_ACQUISITION'
                                  and p.account == '3300'), ZERO)
    total_oci = (bridge['parent_net_equity_usd'] * (closing - opening_rate)
                 + us_profit * (closing - average) + india['india_oci']
                 + india['goodwill_fx'] - investment_translation)
    owners_oci = total_oci - india['nci_fx']
    rolled = (bridge['reported_gbp'] + bridge['difference_gbp'] + profit
              + india['initial_nci'] + total_oci)
    inputs.audit.check('alternative equity independently rolls forward', abs(rolled - equity) < Decimal('1e-24'), refs)
    inputs.audit.check('alternative balance sheet balances', abs(assets - liabilities - equity) < Decimal('1e-24'), refs)
    uses_a2 = bank is None
    if uses_a2:
        reason = ('Closing valuation not determinable from inputs; GBP 23,010.00 carrying '
                  'amount under A2 only; see output/scenarios/alternative_disclosed_assumptions.json.')
        reports['control_explanations.json']['sgd_bank_gbp']['reasons'].append(reason)
        for issue in inputs.audit.issues:
            if issue['code'] == 'unavailable_control_sgd_bank_gbp':
                issue['reason'] += ' ' + reason
    dependencies = {
        'group_profit': ['A2'] if uses_a2 else [],
        'profit_owners': ['A2'] if uses_a2 else [],
        'total_equity': ['A1'] + (['A2'] if uses_a2 else []),
        'total_assets': ['A1', 'A1.gross'] + (['A2'] if uses_a2 else []),
        'translation_reserve_movement': ['A1'],
    }
    values = {'group_profit': profit, 'profit_owners': owners, 'total_assets': assets,
              'total_equity': equity, 'translation_reserve_movement': owners_oci}
    for key, value in values.items():
        if reports['control_figures_sd.json'][key] is None:
            assumptions = '/'.join(dependencies[key]) or 'supplied evidence'
            reason = (f'Not determinable from inputs; GBP {value:,.2f} under {assumptions}; '
                      'see output/scenarios/alternative_disclosed_assumptions.json.')
            reports['control_explanations.json'][key]['reasons'].append(reason)
            for issue in inputs.audit.issues:
                if issue['code'] == 'unavailable_control_' + key:
                    issue['reason'] += ' ' + reason
    inputs.audit.issue('alternative_scenario_assumptions', refs, None, 'GBP', 'assumed',
                       'Alternative only: A1 conditional historical net-equity bridge; A1.gross '
                       'no offsetting historical gross asset/liability adjustments; '
                       + ('A2 SGD carried at GBP 23,010 with no FX adjustment.' if uses_a2
                          else 'A2 not used: supplied SGD closing FX applied.'))
    return {'status': 'alternative_only_not_authoritative', 'currency': 'GBP',
        'assumptions': {
            'A1': 'TB equity represents opening balances; no unreported dividends, capital/reserve '
                  'movements or in-year historical adjustment movements. The historical net adjustment '
                  'is zero within opening-source rounding and remains in GBP. This does not prove zero goodwill.',
            'A1.gross': 'For gross assets/liabilities only, additionally assume no offsetting historical '
                        'asset/liability adjustments, including UK goodwill. Net equity does not need this allocation.',
            'A2': 'If closing SGD FX is missing, carry the bank at booked GBP 23,010 and record no FX '
                  'remeasurement. This is a reporting assumption, not a closing valuation or compliance with policy 3.'},
        'active_assumptions': ['A1', 'A1.gross'] + (['A2'] if uses_a2 else []),
        'opening_equity_bridge': bridge, 'figure_dependencies': dependencies,
        'controls': values, 'sgd_bank_closing_measurement': bank,
        'sgd_bank_reporting_amount': Decimal('23010') if uses_a2 else bank,
        'profit_and_loss': {'group_profit': profit, 'profit_owners': owners, 'profit_nci': india['profit_nci']},
        'balance_sheet': {'total_assets': assets, 'total_liabilities': liabilities, 'total_equity': equity,
                          'residual': assets - liabilities - equity,
                          'rounded_display_residual': assets.quantize(Decimal('.01'))
                              - liabilities.quantize(Decimal('.01')) - equity.quantize(Decimal('.01')),
                          'rounding_note': 'Balance tested before rounding. Independently rounded totals '
                                           'can differ by a penny; no balancing plug is posted.'},
        'changes_in_equity': {'opening_total': bridge['reported_gbp'],
            'opening_source_rounding_difference': bridge['difference_gbp'],
            'opening_source_rounding_difference_unrounded': str(bridge['difference_gbp']),
            'group_profit': profit, 'nci_on_acquisition': india['initial_nci'],
            'total_translation': total_oci, 'owners_translation': owners_oci,
            'nci_translation': india['nci_fx'], 'closing_total': rolled,
            'rollforward_residual': rolled - equity},
        'sources': list(refs)}
