# Northwind Group consolidation

Deterministic Python consolidation into GBP for the year ended 31 December 2024.
Take-home bundle **NWG-D0BC**; candidate initials **sd**. Original brief: [assignment](assignment/AI_Agentic_Engineer_TakeHome_v2.pdf).

The supplied inputs do **not** support complete signed-off statements. The program
writes all requested files, calculates supported figures, and propagates missing inputs
as `null` with reasons. It never substitutes a guessed exchange rate or acquisition reserve.

## Setup and run

Python **3.11+**. Runtime uses only the standard library; no credentials, API, or network
are needed. From a fresh clone:

```bash
git clone https://github.com/Shikhar-dhyani/northwind-consolidation.git
cd northwind-consolidation
python -m consolidation --data data --out output
```

For the validation suite:

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
```

Outputs are generated under `output/`, ignored by Git, and never edited manually.
Exit code **0** means the run completed, possibly with disclosed blocked figures;
check the statement `status` and `issues.json`. Exit code **2** means a fatal input or
control failure. Fatal failures replace the named output files with blocked results,
so an earlier run's figures are not left behind.

The engine stages complete financial generations and publishes them by directory
renames. It refuses to clear unrelated nonempty directories. Successful runs retain
source-hashed PDF attachments but discard older submission archives; rebuild the archive
after rerunning the engine. Windows rename locks have bounded retries. A persistent
swap failure invalidates named financial files if they remain writable; process death
or a wholly unwritable filesystem still needs operator recovery.

Audit remediation is covered by **57 tests**, per-fix fresh-clone verification and
unchanged default controls. See the cleaned summary and fix commits in VALIDATION.md.

## Current results

| Control | GBP, unless a count |
|---|---:|
| Group revenue | 28,301,607.81 |
| Profit attributable to NCI | 70,042.43 |
| Closing NCI | 1,334,335.55 |
| Closing goodwill on the India acquisition | 1,375,815.07 |
| Journals posted / rejected / held | 13 / 2 / 5 |

Group profit, owners' profit and the SGD bank balance are unknown because the closing
SGD rate is missing. Total assets, total equity and group translation reserve movement
also require the UK acquisition/elimination history and opening-equity reconciliation.
Results are conditional on the documented journal holds and mapping/transit assumptions.
The India goodwill control is distinct from total group goodwill, which is blocked.

## Outputs and interpretation

The conservative required outputs are accompanied by
`output/scenarios/alternative_disclosed_assumptions.json`. It shows the conditional
opening-equity bridge, assumptions A1/A2 and the extra gross-allocation condition
A1.gross, per-figure dependencies, alternative statements and balance/roll-forward
checks. Default null reasons include the conditional value and scenario path.
See the review updates in DECISIONS.md, VALIDATION.md and CANDIDATE_GUIDE.md.

| File | Contents |
|---|---|
| `consolidated_tb.csv` | Group-account balances, status, reasons and source rows |
| `balance_sheet.json` | Assets, liabilities, equity before current profit, current profit and totals |
| `profit_and_loss.json` | P&L accounts and owners/NCI attribution |
| `changes_in_equity.json` | Opening balances, supported movements and blocked closing totals |
| `eliminations.csv` | Posted elimination lines and clearly marked held UK lines |
| `issues.json` | File, physical line, amount, currency, action and reason |
| `control_figures_sd.json` | Exactly the 12 appendix keys |
| `control_explanations.json` | Reasons and source references for those controls |
| `journal_decisions.json` | Individual journal dispositions with evidence |
| `ledger_postings.csv` | Contribution-level GBP postings for tracing a balance |
| `validation.json` | Executed mechanical controls and their results |
| `input_manifest.json` | SHA-256 of each input used by the run |

Control scalars are JSON numbers or `null`. The two appendix breakdowns,
`intercompany_difference` and `journals`, contain numeric components. Keeping reasons
in a companion file preserves the exact control-key contract. An unknown CSV amount
is an empty field with `status=blocked` or an explicit reason; it is never zero.

Debits are positive and credits negative in the TB and postings. Statements use positive
income, expense, liability and equity amounts, with signed contra assets. Current-year
profit remains unclosed in the TB and is included once in balance-sheet total equity.
`known_postings` columns show sums of available postings, **not** substitute balances:
they may include carrying values and investments awaiting adjustment/elimination.
No balanced consolidated TB or completed equity roll-forward is claimed while blocked.

Trace a control through `control_explanations.json`, its statement account, the matching
`ledger_postings.csv` contributions, and the original `data/file:line` references. JSON
references also contain a JSON pointer to the journal/line. Rate rows accompany each
conversion. [ARCHITECTURE.md](ARCHITECTURE.md) explains the accounting stages.

## Review material

- [Architecture](ARCHITECTURE.md): six short pages in Markdown.
- [Decisions](DECISIONS.md): seven choices, alternatives and AI involvement.
- [Validation](VALIDATION.md): independent calculations, mutation tests and actual AI fixes.
- [Reflection](REFLECTION.md): one-page reflection.
- [Transcripts](transcripts/README.md): current session export and explicit coverage limitations.
- [Candidate guide](CANDIDATE_GUIDE.md): decision context, alternatives, rationale, journal/control answers and reviewer Q&A.
- [Review runbook](REVIEW_RUNBOOK.md): a 45-minute walkthrough and input-change examples.
- [Clarifications](CLARIFICATIONS.md): missing evidence, current treatment and what would change.
- [Submission](SUBMISSION.md): deliverable checklist and archive-building instructions.
- [Email draft](SUBMISSION_EMAIL.md): prepared text for the original assignment email thread.

Both known contributing conversations are represented: the original Claude planning
text supplied by the candidate and the Codex implementation record. The current Codex
turn is captured through a stated snapshot boundary; refreshing after it ends includes
the final records. The Claude text is preserved without reconstructed roles/tool output.
No submission email has been sent. Keep the full Git history; do not squash it.

## Scope

This is a reviewable prototype for the supplied Northwind FY2024 scope, not a general
consolidation product. Entity ownership/dates, supported ERP schemas, date-specific FX
and policy rules are explicit. Changed ownership, fair values or policy text require
reviewed code/configuration. No live LLM runs in the accounting path. See the reflection
for limitations and the architecture for a production agent topology.
