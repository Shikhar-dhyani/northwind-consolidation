"""Reconcile April-December to the TB before removing pre-acquisition results."""

from .model import InputError, Posting, ZERO, decimal, sources


def cut_india(inputs, postings):
    monthly = inputs.csv('in_pl_monthly.csv')
    expected_codes = {r['ledger_code'] for r in inputs.local_rows['IN']
                      if inputs.coa[inputs.maps['IN'][r['ledger_code']][0]]['statement'] == 'PL'}
    seen, full, before, after = set(), {}, {}, {}
    for row in monthly:
        code, month = row['ledger_code'], row['month']
        if code not in expected_codes or month not in [f'2024-{m:02}' for m in range(4, 13)]:
            raise InputError(f'{row["_ref"]}: unexpected monthly account/period')
        if (code, month) in seen or row['dr_cr'] not in ('Dr', 'Cr'):
            raise InputError(f'{row["_ref"]}: duplicate month or invalid sign')
        seen.add((code, month))
        value = decimal(row['amount']) * (1 if row['dr_cr'] == 'Dr' else -1)
        full[code] = full.get(code, ZERO) + value
        bucket = before if month < '2024-07' else after
        bucket[code] = bucket.get(code, ZERO) + value
    for code in sorted(expected_codes):
        rows = [r for r in monthly if r['ledger_code'] == code]
        source = [r for r in inputs.local_rows['IN'] if r['ledger_code'] == code]
        refs = sources(tuple(r['_ref'] for r in rows), tuple(r['_ref'] for r in source))
        inputs.audit.check(f'India monthly {code} covers nine months', len(rows) == 9, refs)
        tb = sum((decimal(r['amount']) * (1 if r['dr_cr'] == 'Dr' else -1) for r in source), ZERO)
        inputs.audit.check(f'India monthly {code} ties to TB', full[code] == tb, refs)
    # Remove source YTD PL only. Posted December journals remain post-acquisition.
    result = [p for p in postings if not (p.entity == 'IN' and p.stage == 'source'
                                        and inputs.coa[p.account]['statement'] == 'PL')]
    for row in monthly:
        if row['month'] < '2024-07':
            continue
        group, map_refs = inputs.maps['IN'][row['ledger_code']]
        result.append(Posting('IN', group, decimal(row['amount']) * (1 if row['dr_cr'] == 'Dr' else -1),
                              'INR', sources((row['_ref'],), map_refs,
                              (inputs.coa[group]['_ref'],)), 'period'))
    pre_profit = -sum(before.values(), ZERO)
    pre_refs = tuple(r['_ref'] for r in monthly if r['month'] < '2024-07')
    result.append(Posting('IN', '3200', -pre_profit, 'INR', pre_refs,
                          'period', 'PRE_ACQUISITION'))
    inputs.audit.check('India recut local TB balances',
                       sum((p.amount for p in result if p.entity == 'IN'), ZERO) == ZERO)
    inputs.audit.issue('india_period_cut', pre_refs, pre_profit, 'INR', 'flagged',
                       'April-June profit moved to pre-acquisition net assets; only July-December PL consolidated.')
    return result, pre_profit
