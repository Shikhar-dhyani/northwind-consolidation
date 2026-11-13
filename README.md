# Northwind Group consolidation

Consolidates the trial balances of a three-entity, three-currency group (US parent, UK and India subsidiaries) into GBP group financial statements for the year ended 31 December 2024. Every figure traces back to its source rows.

Take-home submission, bundle ID **NWG-D0BC**.

## Design in one paragraph

All accounting arithmetic is deterministic Python code: parsing, mapping, FX, eliminations, NCI and goodwill. Nothing in the numbers comes from an LLM. Text inside the input data (memos, descriptions) is treated only as data, never as instructions. Each problem found is recorded in `output/issues.json` with its file, line, amount and the action taken (`blocked`, `assumed` or `flagged`). When a figure can't be determined from the inputs, the output is `null` with a reason; no value is estimated. See [ARCHITECTURE.md](ARCHITECTURE.md) for the full design.

## Requirements

- Python 3.11+
- No network access needed

## Setup

```bash
git clone <repo-url> northwind-consolidation
cd northwind-consolidation
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python -m consolidation --data data --out output
```

This writes every required output to `output/`. Runs are deterministic: the same inputs always produce identical files.

## Outputs

| File | Contents |
|---|---|
| `consolidated_tb.csv` | Consolidated trial balance in GBP, with source rows for each balance |
| `balance_sheet.json` | Group balance sheet, including NCI and translation reserve |
| `profit_and_loss.json` | Group P&L, with profit split between owners and NCI |
| `changes_in_equity.json` | Opening to closing equity roll-forward |
| `eliminations.csv` | Every elimination entry and the source rows it eliminates |
| `issues.json` | Every problem found: file, line, amount, action taken |
| `control_figures_sd.json` | The 12 control figures (number, or `null` with a reason) |

## Pipeline

1. **Load:** parse three ERP formats (debit/credit columns, signed balances, amount plus Dr/Cr) into one signed format. Check each trial balance nets to zero.
2. **Map:** map local accounts to the group chart of accounts. Detect suspect mappings, such as a balance-sheet account mapped to a P&L account.
3. **Validate journals:** check the 20 manual journals for balance, period, valid accounts and duplicates, then post, reject or hold each one.
4. **Entity-level FX:** retranslate foreign-currency monetary items at the closing rate. Differences go to account 7300.
5. **Period:** include India's results only from 1 July 2024, using the monthly P&L.
6. **Translate:** convert each entity to GBP. Closing rate for assets and liabilities, average rate for income and expenses, historical rate for equity.
7. **Eliminate:** remove intercompany balances and fees, handling in-transit items. Remove investments against acquired equity.
8. **Goodwill and NCI:** goodwill held in INR and retranslated at the closing rate. NCI measured at its proportionate share of net assets.
9. **Statements and checks:** produce the statements, then run the validation suite before anything is written.

## Repository layout

```
consolidation/     source code
data/              input bundle, unmodified
output/            generated outputs (do not edit by hand)
tests/             unit tests and independent recomputations
transcripts/       unedited AI tool sessions
ARCHITECTURE.md    design document
DECISIONS.md       key design decisions and trade-offs
VALIDATION.md      how correctness was established
REFLECTION.md      one-page reflection
```

## Tests

```bash
pytest
```

## Assumptions

Where the group policies are silent, the choice made is recorded in [DECISIONS.md](DECISIONS.md) and logged as `assumed` in `issues.json`.
