# Validation evidence

## Final agent audit - 20 November 2026

Audit of the Messages client, tool capabilities, evidence retrieval, proposal gate,
failure publication and packaging reproduced three additional source-integrity gaps.
Regression tests failed before fix c3de623 and passed after it:

- A file could change between hashing its bytes and reopening it for an excerpt.
  Evidence is now decoded from the exact byte snapshot whose hash was verified.
- The chart used to validate proposed account codes was reread without checking its
  manifest hash. The review broker now constructs its chart from verified bytes.
- A source could change after model inspection but before proposal submission.
  Submission now rechecks every input against the accounting run manifest before
  accepting any proposals. This does not claim OS-level immutable snapshot locking.

The suite now contains 85 cases: the original 62 plus 23 agent cases. All 14 original
audit probes were rerun; default controls remain equal to the frozen baseline.
The credentialed model evidence from 19 November is preserved unedited with its
original code provenance. This audit did not make extra billable model calls; the new
guards are verified by adversarial source-edit tests and clean-clone execution.

## Agent extension - 19 November 2026

Credentialed live evidence is in transcripts/runtime_claude/. Azure accepted the local
key and configured claude-sonnet-4-6 model. The completed run used 18 model responses
and queued 11 proposals, with unchanged financial controls. Both earlier unsuccessful
attempts are retained: retrieval consumed all 20 steps, then final generation exceeded
the original 30-second timeout. Fix 159c290 reserves the last three steps for submission
and corrections; fix 68144fa allows 90 seconds and avoids automatic timeout retries.
The regression suite now has 85 cases. The model wrongly asked for a UK acquisition
date already supplied in entities.csv; this prose error is recorded, not rewritten.

Commit 94ae9b8 adds one evidence-review agent and the Azure Foundry Claude Messages
adapter. The original 62 test cases are retained; 23 agent cases bring the suite to 85.
Financial runtime checks remain 64 because advisory review is separately validated.
Default financial controls are compared against the frozen original baseline.

tests/test_review.py exercises both the deterministic offline broker and the live loop
with a scripted Messages-protocol test double. The adversarial fixture tries to post
JE-006 and cite invented evidence; both are rejected, feedback is returned, and corrected
proposals are queued. Input manifest checks reject changed source bytes; tools reject
arbitrary file access. Tests cover context/step boundaries, configuration absence,
finite JSON, nullable mapping validation, HTTP authentication error redaction and
bounded transient retries. All proposals remain pending human review, and financial
artifact hashes do not change when the agent runs.

Provider-request encoding and mocked response handling are tested independently of
the agent loop. These fixtures are not model-quality certification. The separate
credentialed smoke test and its raw traces establish live operation. No live success is
inferred from offline mode. CLI exit 3 reports review failure while retaining accounting results;
accounting failure skips review and replaces stale agent artifacts with blocked outputs.

## Audit remediation - final verification

Re-audit on 15 November 2026 checked the original brief, accounting and publication
paths, transcript export, packaging, required filenames, decision count and PDF page
limits. All 14 original audit probes were rerun and their outcomes reviewed alongside
the regression suite. The additional packaging defect below was fixed; no numerical
regression was found in these checks. Original source hashes and default controls match.

**85 tests pass; 64 runtime checks pass on the original bundle.** After every fix,
the full suite was run, the committed repository was cloned into a new temporary
directory, the suite and one-command consolidation were run there, and the resulting
12-key control JSON was compared with a frozen pre-fix baseline. Every comparison
matched. The original six conservative nulls and all numerical default figures remain
unchanged; the alternative's original conditional amounts are unchanged too.

The cleaned audit summary below is submission evidence. Raw audit reports, mutation
outputs and per-fix clone helpers remain under ignored tmp/ and are not packaged.
The original 14 audit probes were rerun after remediation; their corrected outcomes
are covered by committed regression tests, including test_transcript_export.py.

| Audit defect | Corrected behavior and regression evidence | Fix commit |
|---|---|---|
| Malformed journals left stale results; empty journals could post | Validate journal structure/amount types; stage complete output generations. Null/empty entry structures and an unexpected mid-write TypeError publish failed results with null controls and remove stale financial artifacts. Unrelated output directories are refused. | 07fedcc |
| SGD scalar returned only the last row | Aggregate all SGD cash rows. Two equivalent SGD 20,000 rows at synthetic rate 1.7 produce the same GBP 23,529.41 control as one SGD 40,000 row. | 122aeaa |
| Split reversal bypassed liability check | Check the journal's net movement per account. Two GBP 32,000 debits still hold JE-009 and do not create a debit accrual balance. | 3c84634 |
| Split audit fee bypassed duplicate check | Fingerprint net local-account movements by entity and parsed date. Split lines and equivalent ISO date formatting still match JE-014 and remain held. | 4ab6c05, 01e26e4 |
| Scenario hard-coded GBP 23,010 | Derive carrying value from source SGD cash rows and use it in the amount and all disclosures. A changed GBP 24,010 book value is reported consistently. | a1ee2d2 |
| Foreign non-monetary accounts were remeasured | Explicit group-account monetary classification. Inventory, prepayments, PPE and deferred income with foreign transaction metadata retain their recorded functional-GBP values. | 789b8cd |
| Transcript redaction suppressed arbitrary summaries | Redact private title/summary values only in identified chat-discovery results; ordinary financial summaries and AI mistakes remain. Test both privacy and preservation, including nested JSON. | e786672 |
| Equivalent invoice numeric strings disagreed | Compare document amounts as Decimal; 157460.0 and 157460.00 reconcile identically. | 152a578 |
| Missing sub-ledgers silently removed checks | Report missing evidence per required entity/ledger and reject duplicate controls. Removing both UK rows produces two missing-evidence issues. | 042b014 |
| Alternative dropped unknown FX outside A2 | Explicitly list unquantified dependencies and block alternative amounts when unknowns are not covered by A1/A1.gross/A2. Missing EUR FX is not silently treated as zero under the SGD assumption. | 7a49005 |
| Mapping external sales to IC could eliminate them | Require invoice coverage for every entity's IC balances/income/expense, including manual journals. Unsupported UK 4200 income or additional unbacked 6300 expense blocks before elimination. | 604dab2 |
| Repeated capital rows distorted historical bases | Aggregate opening-bridge rows and translate parent historical capital once with all source refs. Equivalent US/UK capital splits retain the same bridge and scenario equity. | b2d284f |
| Windows scanner locks could transiently prevent publication | Bounded directory-rename retries; persistent swap failure invalidates existing named financial results if individual files remain writable. Both transient and persistent lock cases are simulated. | 5f9287f |
| Refreshing the Codex export overwrote reviewed Claude coverage metadata | Preserve the single-session registry and provenance across refreshes. Separate regressions verify that only unrelated sidebar labels are redacted from Claude UI results, preserving the assignment messages and mistakes. | 6c3a419 |
| Packaging checked the initial Claude text but omitted the later excerpt hash | Verify both source records before packaging. Tests cover unchanged excerpts, modified excerpts and a missing excerpt file. | 7c961a8 |

Directory publication uses staged generations and directory renames rather than writing
the financial files into the live directory one by one. On Windows it is not an atomic
ready-pointer exchange: readers may briefly find the directory unavailable between
renames. Process termination or an unwritable filesystem can still prevent publication;
the program cannot guarantee a failure record when the OS denies all writes. These
limits are distinct from the now-tested malformed-input and stale-success defects.

No synthetic rate or mutated input from the regression tests is inserted into the original bundle.

## Disclosed scenario review update

Original inputs retain the same six default null controls.
The separate alternative contributes two of the 64 runtime checks:
an unrounded balance-sheet equation and an independently calculated equity roll-forward.

The opening bridge is GBP 14,267,097.92615868028279654359780047132757 against
GBP 14,267,097.93 reported opening equity. The difference is
GBP -0.00384131971720345640219952867243, retained as an unrounded audit string rather
than silently discarded. Under A1 the *net* historical adjustment is zero within source
rounding. Gross allocations and goodwill are not identified by that equality.

Under A1/A1.gross/A2, the alternative reports:

| Figure | GBP | Dependencies |
|---|---:|---|
| Group profit | 2,814,702.81 | A2 |
| Owners' profit | 2,744,660.38 | A2 |
| Total equity | 18,389,975.22 | A1/A2 |
| Total assets | 28,596,245.74 | A1/A1.gross/A2 |
| Owners' translation reserve movement | 43,881.36 | A1 |

The GBP 0.01 displayed balance difference results from independently rounding each total; no plug is posted.
Reserve 3300 movement is owners-only: GBP 43,881.36 excludes India's NCI translation loss of GBP 21,665.17 in account 3400.
Independent NCI bridge: GBP 1,285,958.29 acquisition NCI + GBP 70,042.43 H2 profit - GBP 21,665.17 translation = GBP 1,334,335.55 closing NCI (computed before rounding).

The gross-scenario liabilities are GBP 10,206,270.51. Assets minus liabilities minus
equity is zero before rounding; independently rounded displayed totals differ by GBP
0.01, explicitly disclosed without a plug. The separate equity bridge uses parent
opening net equity FX, parent profit closing-versus-average FX, India translation,
goodwill translation and investment translation, plus acquisition NCI. The opening
sub-penny difference is a separate source-rounding movement, not disguised as CTA.

Tests supply closing SGD rates in copied inputs, including a rate reproducing the booked
GBP 23,010. A2 disappears; scenario and default profit converge, and the profit/equity
change is 40,000 / rate - 23,010 under the same A1. Default equity remains null because
SGD FX does not establish historical A1. Changing opening reserves by GBP 100 blocks
the alternative rather than generating a residual. Fatal runs also overwrite stale
scenario output. Scenario fields and sources are deterministic across repeated runs.

The default accounting interpretation is unchanged.

Run `python -m pytest -q`, then `python -m consolidation --data data --out output`.
Tests use temporary copies when changing inputs. The committed source bundle is never
edited. Runtime uses Decimal at precision 40; two-place rounding happens at output only.
Passing controls validate the supported workings, not the blocked financial statements.

Final local verification: **85 tests passed** on Windows with Python 3.14.3, including
a fresh local Git clone, source-byte integrity, and the one-command output run. The CI
workflow is configured for Python 3.11 and 3.14 on Linux; no remote CI run is claimed.

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

There are 64 executed runtime controls for the original bundle. Neither a final balanced
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
The supplied Claude planning text is captured verbatim with a SHA-256 and provenance.
Its session identifier is recorded in transcripts/SESSIONS.json.
The Codex export preserves visible records through its snapshot boundary, with completed
turns counted. Its completion flag now follows actual session events rather than always
remaining false. Privacy tests cover unrelated chat metadata returned by discovery.
