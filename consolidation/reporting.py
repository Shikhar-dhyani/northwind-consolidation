"""Stable output serialization. Decimal arithmetic ends at this boundary."""

import csv
import hashlib
import json
import re
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from .model import ZERO, sources, total

CONTROL_KEYS = ('group_revenue', 'group_profit', 'profit_owners', 'profit_nci',
                'nci_closing', 'goodwill_closing', 'translation_reserve_movement',
                'total_assets', 'total_equity', 'intercompany_difference',
                'sgd_bank_gbp', 'journals')


def rounded(value):
    if isinstance(value, Decimal):
        return float(value.quantize(Decimal('.01'), rounding=ROUND_HALF_UP))
    if isinstance(value, dict):
        return {k: rounded(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [rounded(v) for v in value]
    return value


def metric(value, refs=(), reasons=()):
    return {'value': value, 'reasons': list(reasons), 'sources': list(refs)}


def negate(value):
    return {**value, 'value': -value['value'] if value['value'] is not None else None,
            'known_postings': -value['known_postings']}


def subset(postings, coa, types):
    return [p for p in postings if coa[p.account]['account_type'] in types]


def build_reports(inputs, postings, opening, india, bank, counts, causes, ic_refs):
    accounts = {code: total(postings, account=code) for code in inputs.coa}
    pl = subset(postings, inputs.coa, ('Revenue', 'Expense'))
    profit = negate(total(pl))
    revenue = negate(total([p for p in pl if p.account == '4100']))
    assets = total(subset(postings, inputs.coa, ('Asset',)))
    liabilities = negate(total(subset(postings, inputs.coa, ('Liability',))))
    # Current-year PL is unclosed in the trial balance. Include it in closing equity.
    equity = negate(total(subset(postings, inputs.coa, ('Equity', 'Revenue', 'Expense'))))
    owners = metric(None if profit['value'] is None else profit['value'] - india['profit_nci'],
                    sources(profit['sources'], india['sources']), profit['reasons'])
    controls = dict(zip(CONTROL_KEYS, (
        revenue['value'], profit['value'], owners['value'], india['profit_nci'],
        india['nci_closing'], india['goodwill_closing'], None,
        assets['value'], equity['value'], causes, bank, counts,
    )))
    unknown_reserve = 'Group translation reserve depends on unresolved UK acquisition and opening-equity reconciliation.'
    explanations = {
        'group_revenue': revenue, 'group_profit': profit, 'profit_owners': owners,
        'profit_nci': metric(india['profit_nci'], india['sources']),
        'nci_closing': metric(india['nci_closing'], india['sources']),
        'goodwill_closing': metric(india['goodwill_closing'], india['sources']),
        'translation_reserve_movement': metric(None, accounts['3300']['sources'], (unknown_reserve,)),
        'total_assets': assets, 'total_equity': equity,
        'intercompany_difference': metric(causes, sources(ic_refs,
            *(p.refs for p in postings if p.entry == 'IC_INCOME'))),
        'sgd_bank_gbp': metric(bank, sources(*(p.refs for p in postings if p.entry == 'SGD')),
                             ('Missing closing GBP/SGD or same-type cross.',) if bank is None else ()),
        'journals': metric(counts, tuple(r['_ref'] for r in inputs.journals())),
    }
    for key in CONTROL_KEYS:
        if controls[key] is None:
            item = explanations[key]
            inputs.audit.issue('unavailable_control_' + key, tuple(item['sources']), None,
                               'GBP', 'blocked', '; '.join(item['reasons']))
    meta = {'period_end': '2024-12-31', 'presentation_currency': 'GBP',
            'status': 'partial_blocked',
            'basis': 'Conditional on documented journal holds and mapping/transit assumptions; see issues.json.',
            'sign_convention': 'Statement amounts positive for income, expenses, assets, liabilities and equity; contra balances negative.'}
    bs = {**meta, 'assets': {c: a for c, a in accounts.items() if inputs.coa[c]['account_type'] == 'Asset'},
          'liabilities': {c: negate(a) for c, a in accounts.items() if inputs.coa[c]['account_type'] == 'Liability'},
          'equity_before_current_profit': {c: negate(a) for c, a in accounts.items() if inputs.coa[c]['account_type'] == 'Equity'},
          'current_year_profit': profit, 'total_assets': assets,
          'total_liabilities': liabilities, 'total_equity': equity,
          'equation_check': metric(None, (), ('Cannot assert assets = liabilities + equity while inputs are missing.',))}
    pnl = {**meta, 'accounts': {c: negate(a) if inputs.coa[c]['account_type'] == 'Revenue' else a
                              for c, a in accounts.items() if inputs.coa[c]['statement'] == 'PL'},
           'group_revenue': revenue, 'group_profit': profit,
           'profit_owners': owners, 'profit_nci': metric(india['profit_nci'], india['sources'])}
    changes = {**meta,
        'opening': {c: metric(v, refs) for c, (v, refs) in opening.items()},
        'movements': {'profit_owners': owners, 'profit_nci': metric(india['profit_nci'], india['sources']),
                      'nci_on_acquisition': metric(india['initial_nci'], india['sources']),
                      'nci_translation': metric(india['nci_fx'], india['sources']),
                      'owners_translation': metric(None, accounts['3300']['sources'], (unknown_reserve,)),
                      'india_goodwill_translation_owners': metric(india['goodwill_fx'], india['sources'])},
        'closing': {'nci': metric(india['nci_closing'], india['sources']),
                    'owners': metric(None, equity['sources'], equity['reasons']), 'total_equity': equity},
        'note': 'Goodwill translation is a component of owners translation, not an additional movement. '
                'No dividends or capital movements are supplied; the roll-forward remains blocked.'}
    return {'control_figures_sd.json': controls, 'control_explanations.json': explanations,
            'balance_sheet.json': bs, 'profit_and_loss.json': pnl, 'changes_in_equity.json': changes}, accounts


def write_json(path, value):
    path.write_text(json.dumps(rounded(value), indent=2, ensure_ascii=False, allow_nan=False) + '\n', encoding='utf-8')


def write_csv(path, fields, rows):
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        for row in rows:
            writer.writerow({k: ('' if v is None else format(v.quantize(Decimal('.01'), rounding=ROUND_HALF_UP), '.2f')
                                 if isinstance(v, Decimal) else json.dumps(v, ensure_ascii=False)
                                 if isinstance(v, (list, tuple, dict)) else v) for k, v in row.items()})


def emit(out: Path, inputs, reports, accounts, postings, eliminations, journals):
    out.mkdir(parents=True, exist_ok=True)
    for name, report in reports.items():
        write_json(out / name, report)
    write_json(out / 'issues.json', inputs.audit.issues)
    write_json(out / 'validation.json', {'checks': inputs.audit.checks,
        'status': 'checks_passed_with_disclosed_blockers',
        'note': 'Passing mechanical checks does not certify blocked statements.'})
    write_json(out / 'journal_decisions.json', journals)
    write_csv(out / 'consolidated_tb.csv', ['account', 'name', 'balance_gbp', 'status',
        'known_postings_gbp', 'reasons', 'source_rows'], [
        {'account': code, 'name': inputs.coa[code]['account_name'], 'balance_gbp': item['value'],
         'status': 'blocked' if item['value'] is None else 'computed',
         'known_postings_gbp': item['known_postings'], 'reasons': item['reasons'], 'source_rows': item['sources']}
        for code, item in sorted(accounts.items())])
    fields = ['entry', 'entity', 'account', 'stage', 'signed_gbp', 'debit_gbp', 'credit_gbp', 'reasons', 'source_rows']
    def rows(items):
        for p in items:
            yield {'entry': p.entry, 'entity': p.entity, 'account': p.account, 'stage': p.stage,
                   'signed_gbp': p.amount, 'debit_gbp': max(p.amount, ZERO) if p.amount is not None else None,
                   'credit_gbp': max(-p.amount, ZERO) if p.amount is not None else None,
                   'reasons': list(p.reasons), 'source_rows': list(p.refs)}
    write_csv(out / 'eliminations.csv', fields, rows(eliminations))
    write_csv(out / 'ledger_postings.csv', fields, rows(postings))
    write_json(out / 'input_manifest.json', {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(inputs.root.iterdir()) if p.is_file()})


def emit_failure(out, audit, error):
    """Replace all financial outputs on failure; never leave a previous good run."""
    out.mkdir(parents=True, exist_ok=True)
    reason = f'Input/control failure: {error}'
    refs = getattr(error, 'refs', ())
    if not refs:
        found = re.search(r'data/[\w.]+:\d+', str(error))
        filename = getattr(error, 'filename', None)
        refs = (found[0] if found else f'data/{Path(filename).name}:1'
                if filename else 'data/entities.csv:1',)
    primary = next((ref for ref in refs if '/tb_' in ref), refs[0])
    audit.issue('fatal_input_control', refs, None, '', 'blocked', reason, at=primary)
    for name in ('balance_sheet.json', 'profit_and_loss.json', 'changes_in_equity.json'):
        write_json(out / name, {'status': 'blocked', 'reason': reason})
    write_json(out / 'control_figures_sd.json', {key: None for key in CONTROL_KEYS})
    write_json(out / 'control_explanations.json', {key: metric(None, (), (reason,)) for key in CONTROL_KEYS})
    write_json(out / 'issues.json', audit.issues)
    write_json(out / 'validation.json', {'status': 'failed', 'reason': reason, 'checks': audit.checks})
    write_json(out / 'journal_decisions.json', [])
    write_json(out / 'input_manifest.json', {})
    write_csv(out / 'consolidated_tb.csv', ['account', 'balance_gbp', 'status', 'reasons', 'source_rows'], [])
    for name in ('eliminations.csv', 'ledger_postings.csv'):
        write_csv(out / name, ['entry', 'account', 'signed_gbp', 'source_rows'], [])
