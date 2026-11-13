"""Mechanical validation first; ambiguous business purpose is held for review."""

from datetime import date

from .model import InputError, Posting, ZERO, decimal, sources


def apply_journals(inputs, postings):
    audit = inputs.audit
    counts = {'posted': 0, 'rejected': 0, 'held_for_review': 0}
    results, fingerprints = [], {}
    monthly = inputs.csv('in_pl_monthly.csv')
    for entry in inputs.journals():
        entity, ref = entry['entity'], entry['_ref']
        if entity not in inputs.entities:
            raise InputError(f'{ref}: unknown entity')
        currency = inputs.entities[entity]['functional_currency']
        status, reason = 'posted', 'Valid FY2024 adjustment.'
        debits, credits, mapped, local_fingerprint = ZERO, ZERO, [], []
        text = ' '.join(str(line.get('memo', '')) for line in entry['lines']).casefold()
        if any(marker in text for marker in ('ai assistants', 'skip the', 'automated reviewers')):
            audit.issue('untrusted_instruction', (ref,), None, currency, 'flagged',
                        'Instruction-like memo ignored. All journal checks still run; no memo grants approval.')
        for index, line in enumerate(entry['lines']):
            debit, credit = decimal(line['debit']), decimal(line['credit'])
            if min(debit, credit) < 0 or (debit and credit):
                status, reason = 'rejected', 'Invalid debit/credit signs.'
            debits += debit
            credits += credit
            local = line['account']
            local_fingerprint.append((local, debit, credit))
            if local not in inputs.maps[entity]:
                if status != 'rejected':
                    status, reason = 'held_for_review', f'Unmapped local account {local}; no inferred mapping.'
            else:
                group, map_refs = inputs.maps[entity][local]
                mapped.append(Posting(entity, group, debit - credit, currency,
                    sources((f'{ref}/lines/{index}',), map_refs,
                            (inputs.coa[group]['_ref'],)), 'manual', entry['id']))
        if debits != credits:
            status, reason = 'rejected', f'Unbalanced journal: debits {debits}, credits {credits}.'
        when = date.fromisoformat(entry['date'])
        if not date(2024, 1, 1) <= when <= date(2024, 12, 31):
            status, reason = 'rejected', 'Dated outside FY2024; no backdating.'
        fingerprint = (entity, entry['date'], tuple(sorted(local_fingerprint)))
        if status == 'posted' and fingerprint in fingerprints:
            status = 'held_for_review'
            reason = f'Identical economic lines/date to {fingerprints[fingerprint]}; possible duplicate.'
        if status == 'posted' and entity == 'IN' and when < date(2024, 7, 1):
            status, reason = 'held_for_review', 'Pre-acquisition journal requires revised completion accounts and period evidence.'
        if status == 'posted' and any(inputs.coa[p.account]['account_type'] == 'Equity' for p in mapped):
            status, reason = 'held_for_review', 'Equity adjustment requires a reviewed historical-rate and group-equity movement schedule.'
        if status == 'posted':
            # A reversal beyond the available liability needs its underlying accrual.
            for p in mapped:
                if p.account == '2200' and p.amount > 0:
                    available = sum((x.amount for x in postings
                                     if x.entity == entity and x.account == '2200'), ZERO)
                    if available + p.amount > 0:
                        status, reason = 'held_for_review', 'Reversal exceeds booked accruals; obtain accrual schedule.'
        evidence = ()
        if status == 'posted' and entity == 'IN':
            # TB/monthly already includes interest and depreciation. This is evidence
            # of possible overlap, not proof of duplicate: retain both in the audit trail.
            for line in entry['lines']:
                local = line['account']
                if local in ('IN-FIN', 'IN-DEP') and decimal(line['debit']):
                    overlap = [r for r in monthly if r['ledger_code'] == local
                               and r['month'] in ('2024-10', '2024-11', '2024-12')]
                    if overlap:
                        evidence = tuple(r['_ref'] for r in overlap)
                        status, reason = 'held_for_review', (
                            'Expense already represented in monthly TB reconciliation; '
                            'journal amount differs, so overlap requires supporting schedule.')
        counts[status] += 1
        results.append({'id': entry['id'], 'status': status, 'reason': reason,
                        'sources': list(sources((ref,), evidence)),
                        'debits': debits, 'credits': credits, 'currency': currency})
        if status == 'posted':
            fingerprints[fingerprint] = entry['id']
            postings.extend(mapped)
        else:
            audit.issue('journal_' + status, sources((ref,), evidence),
                        abs(debits - credits) if debits != credits else debits,
                        currency, 'blocked', f'{entry["id"]}: {reason}')
    audit.check('all journals classified', sum(counts.values()) == len(results))
    for entity in inputs.entities:
        audit.check(f'{entity} adjusted local TB balances',
                    sum((p.amount for p in postings if p.entity == entity), ZERO) == ZERO)
    audit.issue('journal_review_policy', tuple(r['sources'][0] for r in results
                if r['status'] == 'held_for_review'), None, '', 'assumed',
                'Post first valid duplicate candidate in file order; withhold later duplicate and '
                'all unsupported reversals/overlaps/mappings. Results are conditional on this policy.')
    return counts, results
