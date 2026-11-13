"""Small accounting primitives. Debits are positive, credits negative."""

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

ZERO = Decimal('0')


class InputError(ValueError):
    """The input cannot safely enter the calculation."""


def decimal(value: str) -> Decimal:
    try:
        result = Decimal(value)
    except (InvalidOperation, TypeError) as exc:
        raise InputError(f'Invalid decimal: {value!r}') from exc
    if not result.is_finite():
        raise InputError('Non-finite amounts are forbidden')
    return result


def sources(*groups):
    return tuple(sorted({ref for group in groups for ref in group}))


@dataclass
class Posting:
    entity: str
    account: str
    amount: Decimal | None
    currency: str
    refs: tuple[str, ...]
    stage: str = 'source'
    entry: str = ''
    reasons: tuple[str, ...] = ()


@dataclass
class Audit:
    issues: list[dict] = field(default_factory=list)
    checks: list[dict] = field(default_factory=list)

    def issue(self, code, refs, amount, currency, action, reason, *, at=None):
        ref = at or next(iter(refs), 'data:1')
        file, location = ref.split(':', 1)
        self.issues.append({
            'id': f'I{len(self.issues) + 1:03d}', 'code': code,
            'file': file, 'line': int(location.split('#')[0]),
            'sources': list(refs), 'amount_affected': amount,
            'currency': currency, 'action': action, 'reason': reason,
        })

    def check(self, name, passed, refs=(), detail=''):
        self.checks.append({'name': name, 'passed': bool(passed),
                            'sources': list(refs), 'detail': detail})
        if not passed:
            raise InputError(f'Control failed: {name}. {detail}')


def total(postings, *, account=None, entity=None):
    selected = [p for p in postings if (account is None or p.account == account)
                and (entity is None or p.entity == entity)]
    reasons = sources(*(p.reasons for p in selected))
    refs = sources(*(p.refs for p in selected))
    known = sum((p.amount for p in selected if p.amount is not None), ZERO)
    return {'value': None if any(p.amount is None for p in selected) else known,
            'known_postings': known, 'reasons': list(reasons), 'sources': list(refs)}
