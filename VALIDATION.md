# Validation evidence

Run `python -m pytest -q`, then `python -m consolidation --data data --out output`.
Tests use temporary copies when changing inputs. The committed source bundle is never
edited. Runtime uses Decimal at precision 40; two-place rounding happens at output only.
Passing controls validate the supported workings, not the blocked financial statements.

## Coded controls

- Three source TBs balance; posted journals balance and leave adjusted local TBs balanced.
- Sign formats, mapping targets, duplicate metadata, statement classification and FX
  quotation/type/date/positivity are checked. Missing closing FX never falls back.
- Journals have one posted/rejected/held disposition. Balance/period override any memo.
  Duplicates, absent mappings, excessive reversals and expense overlap have explicit holds.
- Every India PL ledger has nine unique monthly records and ties exactly to the source
  YTD TB. The H2 recut balances and reconciles to acquisition equity.
- Acquisition note totals, pre-acquisition profit, capital/reserves and the parent's rounded
  USD consideration agree. No fair-value assumption is inferred from missing evidence.
- US and UK invoices tie to booked TB balances, foreign payable amount and fee PL.
  Counterpart disagreements block. Transit plus payable FX explains the balance difference.
- Each posted elimination balances at precision tolerance, IC and India investment
  accounts clear, and NCI closes to 20% of adjusted closing India net assets.
- Repeated runs are byte-identical. Every posting source file/line and JSON pointer is
  resolved in tests. Original input bytes match ZIP-derived hashes, including line endings.

There are 50 executed runtime controls for the original bundle. Neither a final balanced
group TB nor an assets/equity equation is claimed: unavailable values block those checks.
The statement status, issues and explanations are part of the result, not incidental logs.

## Independent calculations

`tests/test_pipeline.py` derives these from explicit source totals, without calling the
pipeline's FX, period, goodwill or elimination helpers. Let C = 1.2530 x 85.62 =
107.28186 INR/GBP, A = 1.2840 x 83.95 = 107.7918, and S = 1.2645 x 83.39 =
105.446655. These are closing, H2 average and acquisition spot respectively.

| Figure | Independent working | Reported GBP |
|---|---|---:|
| Revenue | 18.4m USD / 1.278 + 9.85m GBP + 437m INR / A | 28,301,607.81 |
| India pre-acquisition profit | April-June monthly revenue less expenses, INR | 18,000,000 INR |
| India H2 profit after posted journals | 42m - 1.85m - 2.4m, INR | 37,750,000 INR |
| NCI profit | 20% x 37.75m / A | 70,042.43 |
| Closing NCI | 20% x (720m - 4.25m) / C | 1,334,335.55 |
| India goodwill | (690m - 80% x 678m) / C | 1,375,815.07 |
| NCI on acquisition | 20% x 678m / S | 1,285,958.29 |
| NCI translation | 20% x (715.75m / C - 678m / S - 37.75m / A) | -21,665.17 |
| Invoice in transit | 10,160 USD / 1.253 | 8,108.54 |
| Payable retranslation loss | 629,840 USD / 1.253 - 490,707.72 GBP | 11,957.88 |
| Initial IC balance difference | 640,000 USD / 1.253 - 490,707.72 GBP | 20,066.42 |
| Fee-conversion FX gain | 640,000 USD / 1.278 - 490,707.72 - 10,160 / 1.253 | 1,966.21 |

NCI acquisition + profit + translation agrees before rounding to closing NCI. India
goodwill translation is wholly allocated to owners. The fee-conversion gain is separate
from the payable loss; the elimination reclassifies PL and does not create group profit.

Group profit, owners' profit, total assets/equity, group translation movement and SGD bank
are null in the original run. Reasons and source references are in
`output/control_explanations.json` and `output/issues.json`. The known-posting sums are
not independent estimates of those unknowns. Total group goodwill remains blocked,
while the specifically requested India goodwill control is calculated.

## Changed-input and failure evidence

- Add a **test-only** supplied GBP/SGD closing rate of 1.7000: bank becomes 40,000 /
  1.7. Profit is independently recomputed from all three source TBs, posted journals,
  entity FX and transit. Owners' profit becomes calculable; UK acquisition blockers stay.
  This rate is never inserted in the original inputs or used as an estimate.
- Add a balanced GBP 1,000 UK cash sale after that scenario: revenue, group profit
  and owners' profit each increase GBP 1,000; NCI is unchanged.
- Change one USD debit by 1: source balance fails, exit 2, previous financial files are
  replaced by null/blocked files and prior ledger/elimination rows disappear.
- Change one India monthly amount: monthly/TB reconciliation fails.
- Change a counterpart invoice amount: the foreign IC reconciliation fails.
- Reword the injected memo to claim approval: JE-006 remains rejected on numbers.
- Duplicate an entity, chart key or FX rate: block rather than silently overwrite.
- Use the data directory as output: refuse before writing any input bytes.
- Change policy prose: reject the unsupported policy version rather than silently applying old rules.

## Three actual AI mistakes and their fixes

These happened during implementation; they are not invented accounting errors or
deliberately planted defects. The earlier commits and failed test output remain in history
and the session transcript.

| AI mistake | Evidence and fix | Fix commit |
|---|---|---|
| Initial scaffolding did not protect original source bytes from Git text conversion. | Git warned of line-ending conversion on input files. Added `.gitattributes` with `-text` for originals, re-indexed source bytes and added ZIP-derived hash verification. | `3308a2f` |
| Primary issue file/line was taken from the first lexically sorted dependency, which sometimes identified `group_coa.csv` rather than the bad source. | `test_issue_locations.py` failed on both sub-ledger differences. Added explicit primary locations while preserving the full dependency set. | `2363599` |
| Entity and chart dictionary comprehensions silently overwrote duplicate input keys. | Both parametrized cases in `test_metadata.py` failed to raise. Added checked uniqueness before indexing and retained regression cases. | `b6bee12` |

## Limits to the evidence

The accounting rules are checked against this supplied policy and scope, not externally
certified. Exact-label remapping and held-journal dispositions need finance review.
The parser is deliberately narrow for acquisition prose. Group opening reserves cannot
stand in for a missing UK acquisition history or the parent's historical equity basis.
The current export covers the visible Codex session through its last snapshot; earlier
planning sessions still require their full original exports before submission.
