"""Entity FX, invoice matching, translation and acquisition eliminations."""

from dataclasses import replace
from decimal import Decimal
import re

from .fx import MissingRate
from .model import InputError, Posting, ZERO, decimal, sources, total


def retranslate_uk(inputs, fx, postings):
    bank_value = None
    for row in inputs.local_rows['UK']:
        currency = row['txn_currency']
        if currency == 'GBP':
            continue
        if not row['txn_amount']:
            raise InputError(f'{row["_ref"]}: missing monetary transaction amount')
        group, map_refs = inputs.maps['UK'][row['nominal_code']]
        refs = sources((row['_ref'],), map_refs)
        carrying = decimal(row['balance'])
        try:
            translated, rate_refs = fx.convert(decimal(row['txn_amount']), currency, 'GBP', 'closing')
            delta = translated - carrying
            refs = sources(refs, rate_refs)
            reasons = ()
            inputs.audit.issue('monetary_retranslation', refs, delta, 'GBP', 'flagged',
                               f'{currency} monetary balance retranslated at closing; counterpart to 7300.',
                               at=row['_ref'])
            if currency == 'SGD' and group == '1100':
                bank_value = (bank_value if bank_value is not None else ZERO) + translated
        except MissingRate as exc:
            delta = None
            reasons = (str(exc),)
            inputs.audit.issue('missing_closing_rate', refs, carrying, 'GBP', 'blocked',
                               f'{exc}; bank and FX expense unknown. No use of average/opening as closing.',
                               at=row['_ref'])
        postings.append(Posting('UK', group, delta, 'GBP', refs, 'entity_fx', currency, reasons))
        postings.append(Posting('UK', '7300', -delta if delta is not None else None,
                                'GBP', refs, 'entity_fx', currency, reasons))
    return bank_value


def record_transit(inputs, fx, postings):
    rows = inputs.csv('intercompany.csv')
    keyed = {}
    for row in rows:
        key = (row['reporting_entity'], row['doc_ref'])
        if key in keyed:
            raise InputError(f'{row["_ref"]}: duplicate intercompany invoice')
        if (row['reporting_entity'], row['counterparty']) not in (('US', 'UK'), ('UK', 'US')):
            raise InputError('Prototype only supports supplied US/UK management fees')
        if row['doc_currency'] != 'USD' or not '2024-01-01' <= row['doc_date'] <= '2024-12-31':
            raise InputError('Unsupported intercompany currency or period')
        keyed[key] = row
    us = [r for r in rows if r['reporting_entity'] == 'US']
    uk = [r for r in rows if r['reporting_entity'] == 'UK']
    us_total = sum((decimal(r['doc_amount']) for r in us), ZERO)
    uk_booked = sum((decimal(r['booked_amount']) for r in uk), ZERO)
    uk_foreign = sum((decimal(r['doc_amount']) for r in uk), ZERO)
    refs = tuple(r['_ref'] for r in rows)
    inputs.audit.check('US invoices tie to IC receivable and income',
        us_total == total(postings, entity='US', account='1250')['value']
        == -total(postings, entity='US', account='4200')['value'], refs)
    # Compare original UK carrying amount, before monetary retranslation.
    uk_source = [p for p in postings if p.entity == 'UK' and p.stage == 'source']
    inputs.audit.check('UK invoices tie to booked payable and expense',
        uk_booked == -total(uk_source, account='2150')['value']
        == total(uk_source, account='6300')['value'], refs)
    uk_tb_foreign = sum((decimal(r['txn_amount']) for r in inputs.local_rows['UK']
                         if r['nominal_code'] == '2150'), ZERO)
    inputs.audit.check('UK foreign IC amount ties to invoices', uk_foreign == -uk_tb_foreign, refs)
    transit = ZERO
    transit_refs = []
    for row in uk:
        if row['booked_currency'] != 'GBP':
            raise InputError(f'{row["_ref"]}: unsupported UK invoice booked currency')
        other = keyed.get(('US', row['doc_ref']))
        if other is None or any(row[k] != other[k] for k in ('doc_currency', 'doc_amount', 'doc_date')):
            raise InputError(f'{row["_ref"]}: unmatched/disputed UK invoice')
    for row in us:
        if row['booked_currency'] != 'USD' or decimal(row['booked_amount']) != decimal(row['doc_amount']):
            raise InputError('US intercompany booking disagrees with invoice')
        if ('UK', row['doc_ref']) not in keyed:
            if row['doc_date'] != '2024-12-31':
                raise InputError('Unmatched invoice not demonstrably a year-end item in transit')
            value, rate_refs = fx.convert(decimal(row['doc_amount']), 'USD', 'GBP', 'closing')
            evidence = sources((row['_ref'],), rate_refs)
            transit_refs.extend(evidence)
            transit += value
            postings.extend([
                Posting('UK', '6300', value, 'GBP', evidence, 'transit', row['doc_ref']),
                Posting('UK', '2150', -value, 'GBP', evidence, 'transit', row['doc_ref']),
            ])
            inputs.audit.issue('invoice_in_transit', evidence, value, 'GBP', 'assumed',
                               'US year-end invoice absent from UK; record receiving expense/payable at closing rate.',
                               at=row['_ref'])
    receiver_closing, closing_refs = fx.convert(uk_foreign, 'USD', 'GBP', 'closing')
    sender_closing, _ = fx.convert(us_total, 'USD', 'GBP', 'closing')
    causes = {'initial_balance_difference': sender_closing - uk_booked,
              'invoice_in_transit': transit,
              'payable_retranslation_loss': receiver_closing - uk_booked,
              'balance_residual_after_resolution': sender_closing - receiver_closing - transit}
    inputs.audit.check('IC balance difference explained',
        abs(causes['balance_residual_after_resolution']) < Decimal('1e-25'), refs)
    return causes, sources(refs, tuple(transit_refs), closing_refs)


def prior_equity(inputs):
    result = {}
    for row in inputs.csv('prior_year_group.csv'):
        if row['as_of'] != '2023-12-31' or row['group_account'] in result:
            raise InputError('Invalid opening group equity')
        result[row['group_account']] = (decimal(row['amount_gbp']), (row['_ref'],))
    if set(result) != {'3100', '3200', '3300', '3400'}:
        raise InputError('Incomplete opening group equity')
    return result


def translate(inputs, fx, local, opening):
    translated = []
    for p in local:
        kind = 'h2_average' if p.entity == 'IN' else 'average'
        statement = inputs.coa[p.account]
        if statement['account_type'] in ('Asset', 'Liability'):
            kind = 'closing'
        elif statement['account_type'] == 'Equity':
            if p.entity == 'US' and p.account == '3100':
                translated.append(replace(p, amount=-opening['3100'][0], currency='GBP',
                                          refs=sources(p.refs, opening['3100'][1]), stage='translation'))
                continue
            if p.entity == 'US':
                # Group opening reserves are authoritative; parent opening reserves
                # alone do not have a supplied historical GBP carrying amount.
                translated.append(replace(p, amount=None, currency='GBP', stage='translation',
                    refs=sources(p.refs, opening['3200'][1]), reasons=(
                        'Parent retained earnings historical GBP basis not separable from supplied group opening equity.',)))
                continue
            kind = 'spot' if p.entity == 'IN' else 'closing'
        if p.amount is None:
            translated.append(replace(p, currency='GBP'))
            continue
        value, rate_refs = fx.convert(p.amount, p.currency, 'GBP', kind)
        translated.append(replace(p, amount=value, currency='GBP', stage=p.stage + ':gbp',
                                  refs=sources(p.refs, rate_refs)))
    india_pre_cta = total(translated, entity='IN')
    india_oci = india_pre_cta['value']
    translated.append(Posting('IN', '3300', -india_oci, 'GBP',
        tuple(india_pre_cta['sources']), 'translation', 'IN_CTA'))
    us = total(translated, entity='US')
    translated.append(Posting('US', '3300', None, 'GBP', tuple(us['sources']),
        'translation', 'US_CTA', ('Group opening equity must be reconciled after unresolved UK acquisition elimination.',)))
    return translated, india_oci


def eliminate_intercompany(inputs, translated, causes):
    selected = {code: total(translated, account=code) for code in ('1250', '2150', '4200', '6300')}
    refs = sources(*(v['sources'] for v in selected.values()))
    inputs.audit.check('retranslated IC balances agree',
        abs(selected['1250']['value'] + selected['2150']['value']) < Decimal('1e-25'), refs)
    journal = []
    for code, value in selected.items():
        journal.append(Posting('GROUP', code, -value['value'], 'GBP', tuple(value['sources']),
                               'elimination', 'IC_BALANCE' if code in ('1250', '2150') else 'IC_INCOME'))
    difference = -selected['4200']['value'] - selected['6300']['value']
    journal.append(Posting('GROUP', '7300', -difference, 'GBP', refs, 'elimination', 'IC_INCOME'))
    causes['income_expense_fx_gain'] = difference
    for entry in ('IC_BALANCE', 'IC_INCOME'):
        inputs.audit.check(f'{entry} journal balances',
            abs(sum((p.amount for p in journal if p.entry == entry), ZERO)) < Decimal('1e-25'), refs)
    translated.extend(journal)
    return journal


def acquisition(inputs):
    text = (inputs.root / 'acquisition_note.md').read_text(encoding='utf-8-sig')
    patterns = {
        'consideration': r'Consideration:\*\* INR ([\d,]+)',
        'capital': r'\| Equity share capital \| ([\d,]+) \|',
        'reserves': r'\| Reserves and surplus at 1 April 2024 \| ([\d,]+) \|',
        'pre_profit': r'\| Profit for 1 April to 30 June 2024 \| ([\d,]+) \|',
        'net_assets': r'\| \*\*Net assets at completion\*\* \| \*\*([\d,]+)\*\* \|',
    }
    result, refs = {}, []
    for key, pattern in patterns.items():
        matches = list(re.finditer(pattern, text))
        if len(matches) != 1:
            raise InputError(f'Acquisition note: ambiguous/missing {key}')
        match = matches[0]
        result[key] = decimal(match[1].replace(',', ''))
        refs.append(f'data/acquisition_note.md:{text.count(chr(10), 0, match.start()) + 1}')
    if '**Completion date:** 1 July 2024' not in text or '**Interest acquired:** 80%' not in text:
        raise InputError('Acquisition scope/date requires review')
    if 'Fair values of identifiable assets and liabilities equal their book values.' not in text:
        raise InputError('Fair value basis requires review')
    return result, tuple(refs)


def eliminate_india(inputs, fx, local, translated, pre_profit, india_oci):
    note, note_refs = acquisition(inputs)
    ownership = decimal(inputs.entities['IN']['ownership_pct']) / 100
    minority = 1 - ownership
    inputs.audit.check('acquisition net assets reconcile',
        note['capital'] + note['reserves'] + note['pre_profit'] == note['net_assets'], note_refs)
    inputs.audit.check('acquisition pre-profit matches monthly', pre_profit == note['pre_profit'], note_refs)
    inputs.audit.check('India acquisition equity matches TB',
        -total(local, entity='IN', account='3100')['value'] == note['capital'] and
        -total(local, entity='IN', account='3200')['value'] == note['reserves'] + pre_profit, note_refs)
    expected_usd, spot_refs = fx.convert(note['consideration'], 'INR', 'USD', 'spot')
    investment = total(local, entity='US', account='1610')
    inputs.audit.check('India consideration reconciles to parent investment',
        abs(investment['value'] - expected_usd) <= Decimal('.005'), investment['sources'])
    refs = sources(note_refs, spot_refs, investment['sources'],
                   *(p.refs for p in local if p.entity == 'IN'))
    gw_inr = note['consideration'] + minority * note['net_assets'] - note['net_assets']
    gw_spot, spot_refs = fx.convert(gw_inr, 'INR', 'GBP', 'spot')
    gw_close, close_refs = fx.convert(gw_inr, 'INR', 'GBP', 'closing')
    initial_nci, _ = fx.convert(minority * note['net_assets'], 'INR', 'GBP', 'spot')
    profit_inr = -sum((p.amount for p in local if p.entity == 'IN'
                       and inputs.coa[p.account]['statement'] == 'PL'), ZERO)
    profit_gbp, average_refs = fx.convert(profit_inr, 'INR', 'GBP', 'h2_average')
    profit_nci, nci_oci = minority * profit_gbp, minority * india_oci
    net_assets_inr = sum((p.amount for p in local if p.entity == 'IN'
        and inputs.coa[p.account]['account_type'] in ('Asset', 'Liability')), ZERO)
    nci_close, _ = fx.convert(minority * net_assets_inr, 'INR', 'GBP', 'closing')
    refs = sources(refs, spot_refs, close_refs, average_refs)
    journal = []
    for code in ('3100', '3200'):
        value = total(translated, entity='IN', account=code)
        journal.append(Posting('GROUP', code, -value['value'], 'GBP',
                               sources(refs, value['sources']), 'elimination', 'IN_ACQUISITION'))
    inv = total(translated, entity='US', account='1610')
    journal.extend([
        Posting('GROUP', '1700', gw_spot, 'GBP', refs, 'elimination', 'IN_ACQUISITION'),
        Posting('GROUP', '1610', -inv['value'], 'GBP', refs, 'elimination', 'IN_ACQUISITION'),
        Posting('GROUP', '3400', -initial_nci, 'GBP', refs, 'elimination', 'IN_ACQUISITION'),
    ])
    # Difference between parent investment translated at closing and acquisition at
    # spot is a separately named investment translation component, not goodwill.
    investment_translation = -sum((p.amount for p in journal), ZERO)
    journal.append(Posting('GROUP', '3300', investment_translation, 'GBP', refs,
                           'elimination', 'IN_ACQUISITION'))
    journal.extend([
        Posting('GROUP', '1700', gw_close - gw_spot, 'GBP', refs, 'elimination', 'IN_GOODWILL_FX'),
        Posting('GROUP', '3300', gw_spot - gw_close, 'GBP', refs, 'elimination', 'IN_GOODWILL_FX'),
        Posting('GROUP', '3200', profit_nci, 'GBP', refs, 'elimination', 'IN_NCI_PROFIT'),
        Posting('GROUP', '3400', -profit_nci, 'GBP', refs, 'elimination', 'IN_NCI_PROFIT'),
        Posting('GROUP', '3300', nci_oci, 'GBP', refs, 'elimination', 'IN_NCI_FX'),
        Posting('GROUP', '3400', -nci_oci, 'GBP', refs, 'elimination', 'IN_NCI_FX'),
    ])
    inputs.audit.check('India NCI roll-forward equals closing net asset share',
        abs(initial_nci + profit_nci + nci_oci - nci_close) < Decimal('1e-25'), refs)
    for entry in sorted({p.entry for p in journal}):
        inputs.audit.check(f'{entry} balances', abs(sum((p.amount for p in journal
                          if p.entry == entry), ZERO)) < Decimal('1e-25'), refs)
    translated.extend(journal)
    return {'goodwill_inr': gw_inr, 'goodwill_closing': gw_close, 'goodwill_fx': gw_close - gw_spot,
            'initial_nci': initial_nci, 'profit_nci': profit_nci, 'nci_fx': nci_oci,
            'nci_closing': nci_close, 'india_profit': profit_gbp,
            'india_oci': india_oci, 'sources': list(refs)}, journal


def block_uk_acquisition(inputs, translated):
    investment = total(translated, entity='US', account='1600')
    uk_equity = [p for p in translated if p.entity == 'UK' and p.account in ('3100', '3200')]
    refs = sources(investment['sources'], *(p.refs for p in uk_equity))
    reason = ('UK acquisition reserves, historical consideration GBP basis and any opening goodwill '
              'are absent. Investment elimination held; group assets/equity/CTA cannot be finalized.')
    inputs.audit.issue('uk_acquisition_incomplete', refs, investment['value'], 'GBP', 'blocked', reason)
    # Unknown adjustment markers prevent uneliminated legal balances being passed
    # off as consolidated figures. No guessed balancing entry is posted.
    markers = [Posting('GROUP', code, None, 'GBP', refs, 'held_elimination',
                       'UK_ACQUISITION', (reason,)) for code in ('1600', '1700', '3100', '3200', '3300')]
    translated.extend(markers)
    return markers
