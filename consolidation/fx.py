"""A rate is units of quote per base. Never mix rate types or dates."""

from .model import InputError, decimal, sources


class MissingRate(InputError):
    pass


class FxBook:
    def __init__(self, inputs):
        self.edges = {}
        dates = {'opening': '2023-12-31', 'closing': '2024-12-31',
                 'average': 'FY2024', 'h2_average': '2024-07-01 to 2024-12-31',
                 'spot': '2024-07-01'}
        for row in inputs.csv('fx_rates.csv'):
            kind = row['rate_type']
            if kind not in dates or row['as_of'] != dates[kind]:
                raise InputError(f'{row["_ref"]}: unsupported FX type/date')
            rate = decimal(row['rate'])
            if rate <= 0:
                raise InputError('FX rates must be positive')
            base, quote = row['base_currency'], row['quote_currency']
            if row['convention'] != f'{quote} per 1 {base}':
                raise InputError('Unexpected FX quotation convention')
            key = (base, quote, kind)
            if key in self.edges or (quote, base, kind) in self.edges:
                raise InputError('Duplicate FX pair/type')
            self.edges[key] = (rate, (row['_ref'],))
            self.edges[(quote, base, kind)] = (1 / rate, (row['_ref'],))

    def factor(self, source, target, kind):
        if source == target:
            return decimal('1'), ()
        key = (source, target, kind)
        if key in self.edges:
            return self.edges[key]
        # Policies permit a two-leg same-type cross, not arbitrary graph inference.
        candidates = []
        for (base, via, edge_kind), (left, left_refs) in self.edges.items():
            right = self.edges.get((via, target, kind))
            if base == source and edge_kind == kind and right:
                candidates.append((left * right[0], sources(left_refs, right[1])))
        if len(candidates) == 1:
            return candidates[0]
        raise MissingRate(f'No unambiguous {kind} rate {source}->{target}')

    def convert(self, amount, source, target, kind):
        factor, refs = self.factor(source, target, kind)
        return amount * factor, refs
