"""Strict ERP adapters; source files are never rewritten."""

import csv
import hashlib
import json
from pathlib import Path

from .model import Audit, InputError, Posting, ZERO, decimal, sources


class Inputs:
    def __init__(self, root: Path, audit: Audit):
        self.root, self.audit = root, audit

    def csv(self, name):
        with (self.root / name).open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.DictReader(stream)
            if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
                raise InputError(f'{name}: missing or duplicate headers')
            result = []
            previous_line = reader.line_num
            for row in reader:
                if None in row or any(v is None for v in row.values()):
                    raise InputError(f'{name}:{previous_line + 1}: invalid column count')
                row['_ref'] = f'data/{name}:{previous_line + 1}'
                result.append(row)
                previous_line = reader.line_num
            return result

    def journals(self):
        text = (self.root / 'adjustments.json').read_text(encoding='utf-8-sig')
        batch = json.loads(text)
        if not isinstance(batch, dict) or not isinstance(batch.get('entries'), list):
            raise InputError('data/adjustments.json:1: entries must be a list')
        entries = batch['entries']
        ids = set()
        for index, entry in enumerate(entries):
            ref = f'data/adjustments.json:1#/entries/{index}'
            if not isinstance(entry, dict) or any(not isinstance(entry.get(k), str) or not entry[k]
                    for k in ('id', 'entity', 'date')):
                raise InputError(f'{ref}: journal needs string id/entity/date')
            if not isinstance(entry.get('lines'), list) or not entry['lines']:
                raise InputError(f'{ref}: journal lines must be a nonempty list')
            for leg in entry['lines']:
                if not isinstance(leg, dict) or not isinstance(leg.get('account'), str) or not leg['account']:
                    raise InputError(f'{ref}: journal line needs an account')
                for amount in ('debit', 'credit'):
                    decimal(leg.get(amount))
            if entry['id'] in ids:
                raise InputError('Duplicate journal id')
            ids.add(entry['id'])
            needle = f'"id": "{entry["id"]}"'
            position = text.find(needle)
            # JSON pointer remains authoritative if whitespace formatting changes.
            line = text.count('\n', 0, position) + 1 if position >= 0 else 1
            entry['_ref'] = f'data/adjustments.json:{line}#/entries/{index}'
        return entries

    def unique(self, name, key):
        result = {}
        for row in self.csv(name):
            if row[key] in result:
                raise InputError(f'{row["_ref"]}: duplicate {key} {row[key]}')
            result[row[key]] = row
        return result

    def load(self):
        # Rules below implement this reviewed policy version, not arbitrary prose.
        policy = self.root / 'group_policies.md'
        if hashlib.sha256(policy.read_bytes()).hexdigest() != '00888e755e03b2b275bb9b77b5e71916a26b2a23cfda4dffd1dbd47447cc05d4':
            raise InputError('data/group_policies.md:1: changed policy version requires reviewed implementation')
        self.entities = self.unique('entities.csv', 'entity_id')
        expected = {'US': ('USD', '', ''), 'UK': ('GBP', '100', '2016-03-01'),
                    'IN': ('INR', '80', '2024-07-01')}
        if set(self.entities) != set(expected):
            raise InputError('This prototype supports the three supplied Northwind entities')
        for entity, values in expected.items():
            row = self.entities[entity]
            if (row['functional_currency'], row['ownership_pct'], row['acquisition_date']) != values:
                raise InputError(f'{entity}: changed scope/ownership requires reviewed configuration')
            if row['tb_file'] != f'tb_{entity.lower()}.csv':
                raise InputError(f'{row["_ref"]}: unsupported TB filename')
        self.coa = self.unique('group_coa.csv', 'account_code')
        for code, row in self.coa.items():
            expected_statement = 'PL' if row['account_type'] in ('Revenue', 'Expense') else 'BS'
            if row['account_type'] not in ('Asset', 'Liability', 'Equity', 'Revenue', 'Expense') or row['statement'] != expected_statement:
                raise InputError(f'{row["_ref"]}: inconsistent account type/statement for {code}')
        self.maps = {'US': {code: (code, ()) for code in self.coa}}
        mapping_issues = {}
        for entity, name in [('UK', 'map_uk.csv'), ('IN', 'map_in.csv')]:
            self.maps[entity] = {}
            for row in self.csv(name):
                code, group = row['local_code'], row['group_code']
                if code in self.maps[entity] or group not in self.coa:
                    raise InputError(f'{row["_ref"]}: duplicate or invalid mapping')
                # Narrow, explainable correction: exact chart label, no fuzzy inference.
                if row['local_name'] == 'Deferred income' and group != '2300':
                    mapping_issues[(entity, code)] = self.audit.issue('mapping_classification', (row['_ref'],), ZERO, 'GBP',
                                     'assumed', 'Exact Deferred income label mapped to revenue; '
                                     'override to liability 2300, preserving the source file.')
                    group = '2300'
                self.maps[entity][code] = (group, (row['_ref'],))
        postings = []
        self.local_rows = {}
        for entity in ('US', 'UK', 'IN'):
            rows = self.csv(self.entities[entity]['tb_file'])
            self.local_rows[entity] = rows
            used, counts, local_refs = set(), {}, {}
            entity_posts = []
            for row in rows:
                code = row[{'US': 'account_code', 'UK': 'nominal_code', 'IN': 'ledger_code'}[entity]]
                if entity == 'US':
                    debit, credit = decimal(row['debit']), decimal(row['credit'])
                    if min(debit, credit) < 0 or (debit and credit):
                        raise InputError(f'{row["_ref"]}: invalid debit/credit')
                    amount = debit - credit
                elif entity == 'UK':
                    amount = decimal(row['balance'])
                else:
                    if row['dr_cr'] not in ('Dr', 'Cr') or decimal(row['amount']) < 0:
                        raise InputError(f'{row["_ref"]}: invalid Dr/Cr amount')
                    if row['period'] != 'FY25 YTD':
                        raise InputError('Unsupported India TB reporting period')
                    amount = decimal(row['amount']) * (1 if row['dr_cr'] == 'Dr' else -1)
                if code not in self.maps[entity]:
                    raise InputError(f'{row["_ref"]}: unmapped account {code}')
                group, map_refs = self.maps[entity][code]
                used.add(code)
                counts[code] = counts.get(code, 0) + 1
                local_refs.setdefault(code, []).append(row['_ref'])
                entity_posts.append(Posting(entity, group, amount,
                    self.entities[entity]['functional_currency'],
                    sources((row['_ref'],), map_refs, (self.coa[group]['_ref'],))))
                correction = mapping_issues.get((entity, code))
                if correction is not None:
                    correction['amount_affected'] += abs(amount)
                    correction['sources'] = list(sources(correction['sources'], (row['_ref'],)))
            refs = sources(*(p.refs for p in entity_posts))
            self.audit.check(f'{entity} source TB balances',
                             sum((p.amount for p in entity_posts), ZERO) == ZERO, refs)
            for code, count in counts.items():
                if count > 1:
                    self.audit.issue('repeated_local_account',
                        tuple(local_refs[code]),
                        sum((p.amount for p in entity_posts if p.account == self.maps[entity][code][0]), ZERO),
                        self.entities[entity]['functional_currency'], 'flagged',
                        f'{code}: {count} source rows retained and aggregated; no last-row overwrite.')
            for code in sorted(set(self.maps[entity]) - used):
                if entity != 'US':
                    self.audit.issue('unused_mapping', self.maps[entity][code][1], ZERO,
                                     self.entities[entity]['functional_currency'], 'flagged',
                                     f'Mapped local account {code} does not appear in the TB.')
            postings.extend(entity_posts)
        self.subledger_controls(postings)
        return postings

    def subledger_controls(self, postings):
        ledgers = {'Accounts receivable (trade)': '1200', 'Accounts payable (trade)': '2100'}
        seen = set()
        for row in self.csv('subledger_controls.csv'):
            if (row['entity_id'] not in self.entities or row['ledger'] not in ledgers
                    or row['as_of'] != '2024-12-31'
                    or row['currency'] != self.entities[row['entity_id']]['functional_currency']):
                raise InputError(f'{row["_ref"]}: unsupported subledger scope/date/currency')
            account = ledgers[row['ledger']]
            key = (row['entity_id'], account)
            if key in seen:
                raise InputError(f'{row["_ref"]}: duplicate subledger control')
            seen.add(key)
            selected = [p for p in postings if p.entity == row['entity_id'] and p.account == account]
            tb = abs(sum((p.amount for p in selected), ZERO))
            difference = tb - decimal(row['control_total'])
            refs = sources((row['_ref'],), *(p.refs for p in selected))
            if difference:
                self.audit.issue('subledger_mismatch', refs, difference, row['currency'], 'flagged',
                                 'Compare before journals. Preserve the balanced TB; no unsupported adjustment.',
                                 at=row['_ref'])
            else:
                self.audit.check(f'{row["entity_id"]} {account} subledger agrees', True, refs)
        for entity, metadata in self.entities.items():
            for ledger, account in ledgers.items():
                if (entity, account) in seen:
                    continue
                selected = [p for p in postings if p.entity == entity and p.account == account]
                refs = sources(('data/subledger_controls.csv:1',), *(p.refs for p in selected))
                amount = abs(sum((p.amount for p in selected), ZERO))
                self.audit.issue('subledger_missing_evidence', refs, amount,
                    metadata['functional_currency'], 'flagged',
                    f'{entity} {ledger}: missing sub-ledger total; reconciliation was not performed. '
                    'Amount affected is the TB carrying balance, not an estimated discrepancy.',
                    at='data/subledger_controls.csv:1')
