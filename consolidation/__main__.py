import argparse
import json
from pathlib import Path
import sys

from .model import InputError
from .pipeline import run


def main():
    parser = argparse.ArgumentParser(description='Deterministic Northwind FY2024 consolidation')
    parser.add_argument('--data', type=Path, default=Path('data'))
    parser.add_argument('--out', type=Path, default=Path('output'))
    parser.add_argument('--review', choices=('off', 'offline', 'live'), default='offline',
                        help='offline rules baseline (default), live Azure Claude tool loop, or off')
    args = parser.parse_args()
    try:
        controls = run(args.data, args.out, review_mode=args.review)
    except InputError as exc:
        print(f'Blocked: {exc}', file=sys.stderr)
        return 2
    missing = sum(value is None for value in controls.values())
    print(f'Wrote outputs to {args.out}. {missing} control figures blocked; see issues.json.')
    review = json.loads((args.out / 'review_report.json').read_text(encoding='utf-8'))
    print(f'Review: {review["mode"]}, {review["status"]}; see review_report.json and agent_trace.json.')
    if review['status'] == 'failed':
        print(review['error'], file=sys.stderr)
        return 3
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
