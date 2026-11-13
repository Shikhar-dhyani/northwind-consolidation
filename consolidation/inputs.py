"""Strict ERP adapters; source files are never rewritten."""

import csv
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
        entries = json.loads(text)['entries']
        ids = set()
        for index, entry in enumerate(entries):
            if entry['id'] in ids:
                raise InputError('Duplicate journal id')
            ids.add(entry['id'])
            needle = f'"id": "{entry["id"]}"'
            position = text.find(needle)
            # JSON pointer remains authoritative if whitespace formatting changes.
            line = text.count('\n', 0, position) + 1 if position >= 0 else 1
            entry['_ref'] = f'data/adjustments.json:{line}#/entries/{index}'
        return entries

    def load(self):
        self.entities = {r['entity_id']: r for r in self.csv('entities.csv')}
        expected = {'US': ('USD', '', ''), 'UK': ('GBP', '100', '2016-03-01'),
                    'IN': ('INR', '80', '2024-07-01')}
        if set(self.entities) != set(expected):
            raise InputError('This prototype supports the three supplied Northwind entities')
        for entity, values in expected.items():
            row = self.entities[entity]
            if (row['functional_currency'], row['ownership_pct'], row['acquisition_date']) != values:
                raise InputError(f'{entity}: changed scope/ownership requires reviewed configuration')
        self.coa = {r['account_code']: r for r in self.csv('group_coa.csv')}
        self.maps = {'US': {code: (code, ()) for code in self.coa}}
        for entity, name in [('UK', 'map_uk.csv'), ('IN', 'map_in.csv')]:
            self.maps[entity] = {}
            for row in self.csv(name):
                code, group = row['local_code'], row['group_code']
                if code in self.maps[entity] or group not in self.coa:
                    raise InputError(f'{row["_ref"]}: duplicate or invalid mapping')
                # Narrow, explainable correction: exact chart label, no fuzzy inference.
                if row['local_name'] == 'Deferred income' and group != '2300':
                    self.audit.issue('mapping_classification', (row['_ref'],), None, 'GBP',
                                     'assumed', 'Exact Deferred income label mapped to revenue; '
                                     'override to liability 2300, preserving the source file.')
                    group = '2300'
                self.maps[entity][code] = (group, (row['_ref'],))
        postings = []
        self.local_rows = {}
        for entity in ('US', 'UK', 'IN'):
            rows = self.csv(self.entities[entity]['tb_file'])
            self.local_rows[entity] = rows
            used, counts = set(), {}
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
                entity_posts.append(Posting(entity, group, amount,
                    self.entities[entity]['functional_currency'],
                    sources((row['_ref'],), map_refs, (self.coa[group]['_ref'],))))
            refs = sources(*(p.refs for p in entity_posts))
            self.audit.check(f'{entity} source TB balances',
                             sum((p.amount for p in entity_posts), ZERO) == ZERO, refs)
            for code, count in counts.items():
                if count > 1:
                    self.audit.issue('repeated_local_account',
                        tuple(r['_ref'] for r in rows if r.get('nominal_code') == code),
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
        for row in self.csv('subledger_controls.csv'):
            account = '1200' if row['ledger'] == 'Accounts receivable (trade)' else '2100'
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
