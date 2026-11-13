import argparse
from pathlib import Path
import sys

from .model import InputError
from .pipeline import run


def main():
    parser = argparse.ArgumentParser(description='Deterministic Northwind FY2024 consolidation')
    parser.add_argument('--data', type=Path, default=Path('data'))
    parser.add_argument('--out', type=Path, default=Path('output'))
    args = parser.parse_args()
    try:
        controls = run(args.data, args.out)
    except InputError as exc:
        print(f'Blocked: {exc}', file=sys.stderr)
        return 2
    missing = sum(value is None for value in controls.values())
    print(f'Wrote outputs to {args.out}. {missing} control figures blocked; see issues.json.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
