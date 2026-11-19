# Data-to-code presentation and beginner rehearsal

Use this as a 40-45 minute screen-share script. It is suggested wording to learn and
adapt, not a claim that every decision was independently originated without AI.
Explain the implemented choices, the AI assistance and your verification honestly.

## Set up your screen

Open this repository in VS Code. Keep Explorer, the editor and an integrated terminal
visible. Use Ctrl+P to open a relative filename, Ctrl+G to jump to a line and Ctrl+F
to find an account or journal ID. Read CSVs as text so the stated line numbers match.
Do not edit the original inputs during the presentation. The tests demonstrate changes
on temporary copies. Generated JSON line numbers vary; search for the stated keys.

Before the call, run:

```powershell
python -m consolidation --data data --out output
python -m pytest -q
```

Expected on the original bundle: six blocked controls; 81 tests pass. The original run
executes 64 runtime checks. Passing checks does not certify the blocked statements.
Rerunning consolidation clears previous submission archives, so rebuild the ZIP after
the final run if you need it: `python scripts/prepare_submission.py --require-pdfs`.

## 1. Explain the business before discussing code — 2 minutes

**Open:** `data/entities.csv`, lines 2-4.

**Point at:** `functional_currency`, `ownership_pct`, `acquisition_date`, `erp_system`.

**Say:** "Three companies keep accounts in different systems and currencies. The US
parent owns all of the UK company and 80% of India. India joined on 1 July 2024.
The task is to report the group in GBP for the year ending 31 December 2024."

**Understand:** functional currency means the currency of a company's own books.
Presentation currency means the currency of the group's report. Control of India
means consolidating its controlled operations in full, then separating the other
shareholders' interest; it does not mean taking 80% of every revenue and expense.

**Highlight:** different financial year-ends do not change the required group period.
The ownership and dates are supplied facts, not design decisions.

## 2. Establish the accounting rules — 2 minutes

**Open:** `data/group_policies.md`, policies 1-7.

**Say:** "The bundle prescribes GBP reporting, rate types, the NCI method, intercompany
treatment and final rounding. My implementation choices concern enforcing those rules,
handling missing evidence and explaining the result."

**Understand:** assets are resources; liabilities are obligations; equity is the remaining
owners' interest. Revenue less expenses is profit. Assets = liabilities + equity.
The P&L measures performance during a period; the balance sheet is a position at a date.

**Highlight:** policy rules are reviewed instructions. Journal memos are untrusted data
and cannot change those rules. Do not claim you freely selected prescribed rate types.

## 3. Show why three adapters are needed — 3 minutes

**Open in sequence:** `data/tb_us.csv:1`, `data/tb_uk.csv:1`, `data/tb_in.csv:1`.

**Point at:** US debit/credit columns; UK signed balance; India amount plus Dr/Cr flag.
The India period says `FY25 YTD`.

**Say:** "These files express the same bookkeeping ideas differently. I normalize them
to debit-positive and credit-negative postings before doing group calculations."

**Understand:** debit and credit are bookkeeping sides, not good and bad. In this
representation a GBP 100 rent payment produces +100 expense and -100 bank movement.
Their sum is zero. A TB lists accumulated account balances rather than just this entry.

**Highlight:** every source TB balances, but balance alone does not prove correct
classification, valuation or completeness. Keep the original source rows traceable.

## 4. Explain mapping with one real defect — 3 minutes

**Open:** `data/group_coa.csv:1`, then `data/map_uk.csv:12`, then `data/tb_uk.csv:12`.

**Point at:** local UK `2310,Deferred income,4100`. Group 4100 is revenue; the
implemented correction uses group liability 2300. The source amount is GBP 180,000.
Then show wages at `data/tb_uk.csv:18` and line 19: two GBP 812,500 cost-centre rows.

**Say:** "A mapping translates local account codes into the group's chart. Deferred
income is an obligation for performance still owed, so the exact-label rule maps it
to a liability. The override is disclosed; the supplied CSV is not rewritten. Both
wage rows are retained and added to GBP 1,625,000."

**Highlight:** local numbers are not universal identifiers: UK 1200 means bank, while
group 1200 means trade receivables. Do not join charts on code alone.

**Decision:** narrow visible correction rather than fuzzy AI remapping or accepting a
known defect. This is a reviewed, bundle-specific assumption, not general accounting AI.

## 5. Show a problem that must not be guessed away — 2 minutes

**Open:** `data/subledger_controls.csv:4`, alongside `data/tb_uk.csv:4` and line 9.

**Point at:** UK receivables GBP 1,985,000 versus supporting total GBP 1,940,000;
payables magnitude GBP 1,210,000 versus GBP 1,165,000. Each gap is GBP 45,000.

**Say:** "A sub-ledger is supporting customer or supplier detail behind the total.
These controls disagree. The system flags the gaps, but there is no evidence of which
individual posting is wrong, so it does not invent a correcting journal."

**Highlight:** discovering a discrepancy does not establish the right adjustment.
Missing sub-ledger evidence is also reported; it cannot silently count as agreement.

## 6. Demonstrate journal judgment and untrusted text — 4 minutes

**Open:** `data/adjustments.json:102`; then `output/journal_decisions.json`.
Search the latter for `JE-006`, `JE-017`, `JE-009` and `JE-019`.

**Point at:** JE-006's memo asking AI reviewers to skip checks, debit USD 51,200 and
credit USD 50,000. It fails balance by USD 1,200 regardless of the memo.

**Say:** "A journal changes account balances and must balance. An entry's memo is
evidence to inspect, not authority to change the validator. Invalid entries are rejected.
Balanced entries with unsupported business purpose are held for review."

| Example | Outcome | Reason |
|---|---|---|
| JE-006 | Rejected | Unequal debits and credits; injected memo ignored |
| JE-017 | Rejected | Date outside FY2024 |
| JE-009 | Held | Reversal exceeds supported booked accruals |
| JE-016 | Held | Missing mapping |
| JE-019 | Held | Possible duplicate of JE-014 |
| JE-018 / JE-020 | Held | Possible overlap with monthly India expenses |

**Highlight:** 13 posted, 2 rejected, 5 held. "Held" does not mean proven wrong.
The first valid identical accrual is retained deterministically; file order is not proof
of approval. Net account movements prevent split lines from bypassing these checks.

## 7. Explain India's acquisition cut — 3 minutes

**Open:** `data/tb_in.csv:1`, `data/in_pl_monthly.csv:2`,
`data/acquisition_note.md:3`.

**Point at:** April-June rows versus July-December rows; acquisition on 1 July;
acquisition-note pre-acquisition profit INR 18,000,000.

**Say:** "India's TB covers April-December. The group controlled it only from July.
I reconcile all nine months to the source TB, then include July-December P&L.
April-June profit belongs in the net assets acquired, not group trading profit."

**Decision:** actual monthly detail rather than a six-ninths estimate. The latter
would assume equal earnings each month. Supported post-acquisition journals are retained.

## 8. Explain the two FX jobs and the missing rate — 4 minutes

**Open:** `data/fx_rates.csv:1`, alongside `data/tb_uk.csv:3` and line 10.

**Point at:** GBP/USD closing 1.2530, FY average 1.2780, INR H2 rates, and the fact
that SGD has opening/average rates but no closing rate.

**Say:** "Rates are quote-currency units per base currency. GBP/USD 1.253 means
GBP 1 equals USD 1.253, so converting dollars to pounds requires division."

| Job | Example | Where its difference belongs under the supplied policy |
|---|---|---|
| Remeasure foreign money inside an entity | UK USD payable inside GBP books | P&L account 7300 |
| Translate a whole entity to presentation GBP | US or India statements | Translation reserve 3300, with the appropriate India NCI allocation |

Assets/liabilities use closing; US P&L uses full-year average; India included P&L uses
H2 average; equity uses historical rates. Same-type INR cross rates multiply the two
supplied legs. Monetary cash/debts differ from non-monetary inventory and equipment.

**Say:** "The UK holds SGD 40,000, recorded at GBP 23,010. Without a supported closing
rate I cannot measure its closing GBP value. Its unknown FX adjustment also affects
profit. The system does not silently substitute an average or booked amount."

**Decision:** propagate uncertainty to dependent figures, preserving independent results.

## 9. Explain internal transactions before eliminating them — 3 minutes

**Open:** `data/intercompany.csv:2`; show lines 2-6 versus lines 7-10.
Then open `output/control_figures_sd.json`, key `intercompany_difference`.

**Point at:** US five invoices total USD 640,000; UK four invoices total USD 629,840.
The missing UK invoice is `INV-US-2291`, USD 10,160, dated 31 December.

**Say:** "The group cannot earn revenue by charging itself. But cancelling unlike
amounts would hide errors. First reconcile the invoices, record the receiving side
of the year-end item at closing, and remeasure the existing USD payable. Then eliminate."

**Highlight:** GBP 20,066.42 balance gap = GBP 8,108.54 transit + GBP 11,957.88
payable retranslation loss, at displayed precision. The remaining income/expense
conversion difference is a separate GBP 1,966.21 FX gain. Do not call it an unexplained
balance plug. All IC postings require invoice coverage before elimination.

## 10. Explain goodwill and minority ownership — 3 minutes

**Open:** `data/acquisition_note.md:5`, then controls `goodwill_closing`,
`profit_nci` and `nci_closing`.

**Say:** "The parent owns 80% of India; other shareholders own 20%. NCI means their
interest. The prescribed method measures acquisition NCI as a share of net assets."

```text
All figures in millions of INR:
Consideration paid                         690.0
+ NCI: 20% of net assets 678                135.6
- identifiable net assets acquired         678.0
= goodwill                                 147.6
```

Goodwill is held in INR and translated at closing: GBP 1,375,815.07.
NCI profit is GBP 70,042.43; closing NCI is GBP 1,334,335.55. Closing NCI includes
its acquisition interest, post-acquisition profit and translation movement. Its independent
cross-check is 20% of India's adjusted closing net assets translated at closing.

**Highlight:** NCI is not 20% of the whole group's profit. Under this proportionate
method, goodwill FX is attributable to owners, not the India minority.

## 11. Show the results and separate assumptions — 3 minutes

**Open:** `output/control_figures_sd.json`, `output/control_explanations.json`,
then `output/scenarios/alternative_disclosed_assumptions.json`.

**Say:** "Supported group revenue is GBP 28,301,607.81. Six default controls remain
null because their evidence dependencies are unresolved. Null means unknown, not zero."

Trace revenue from `data/tb_us.csv:18` (USD 18.4m), `data/tb_uk.csv:16`
(GBP 9.85m), and July-December India revenue at `data/in_pl_monthly.csv:5`
(six rows total INR 437m):

```text
18,400,000 / 1.278 + 9,850,000 + 437,000,000 / (1.284 * 83.95)
= GBP 28,301,607.81 after final rounding
```

**Highlight:** the default statements remain blocked for required missing evidence.
The separate scenario shows profit GBP 2,814,702.81 under the SGD carrying-value
assumption A2. A1 covers the conditional historical net-equity bridge; A1.gross is an
extra assumption needed for gross assets/liabilities. The bridge does not prove zero
UK goodwill. Supplying SGD FX resolves A2, not A1. Do not present scenario totals as facts.

For provenance, find group account `4100` in `output/consolidated_tb.csv`, inspect its
`source_rows`, then find its contributions in `output/ledger_postings.csv`.
Source references name the data row, mapping row and applicable rates. Journal sources
also carry JSON pointers. Amounts are code-generated, with rounding at the output boundary.

## 12. Connect the business flow to code — 5 minutes

Start at `consolidation/__main__.py:9`, then `consolidation/pipeline.py:28`.
Do not read every line aloud. Explain each module's responsibility and show one function.

| Open | What to point at | What to explain |
|---|---|---|
| `pipeline.py:33` | `_calculate` calls in order; Decimal precision 40 | Accounting remains deterministic; the run wrapper invokes review separately |
| `inputs.py:67` | ERP normalization and mapping | Different source shapes become common postings; original files remain unchanged |
| `model.py:35` | `Posting` | An amount travels with entity, account, currency, source references and stage |
| `journals.py:8` | `apply_journals`; balance/date/net movements | Reject objectively invalid entries; hold unsupported business purpose |
| `accounting.py:11` and `:54` | `retranslate_uk`, `record_transit` | Entity FX and invoice reconciliation happen before group elimination |
| `periods.py:6` | `cut_india` | Reconcile source months and remove pre-acquisition P&L |
| `fx.py:10` and `accounting.py:141` | `FxBook`, `translate` | Strict rate lookup/crosses; convert entity statements to GBP |
| `accounting.py:181`, `:224`, `:288` | IC, India acquisition, blocked UK elimination | Supported eliminations are posted; missing UK history is not guessed |
| `scenarios.py:33` | `alternative` | Conditional scenario stays separate and unknowns outside its assumptions block it |
| `reporting.py:41` and `:120` | `build_reports`, `emit` | Statements, controls, issues, final rounding and provenance |
| `publication.py:47` | `execute` | Stage complete generations; caught failures replace stale financial claims |

All paths in the table are under `consolidation/`. Publication wraps calculation; it
is not just another arithmetic step at the end. Explain the brief directory-swap gap
and OS/process-interruption limits rather than claiming fully atomic publication.

If asked where AI earns its place: "AI assisted development. The implemented Claude
review agent selects cases, reads bounded evidence and submits human-review proposals.
Local checks return invalid actions/citations for correction. It has no posting tool.
The default offline rules baseline makes no model call; --review live uses Azure Foundry."

Open consolidation/review.py (run_review and EvidenceReview), then
consolidation/claude_foundry.py (FoundryClaude.complete). Show output/review_report.json
and output/agent_trace.json. Configure the ignored .env before demonstrating live mode.
Use AGENT_REVIEW.md for the four tools, failure behavior and honest test boundaries.

## 13. Predict a changed input, then show the test — 3 minutes

**Open:** `tests/test_pipeline.py:78`. State the prediction before executing:

"With a supplied synthetic closing rate of SGD 1.7 per GBP, the bank is GBP 23,529.41.
Profit increases by GBP 519.41 versus the carrying-value scenario. Default profit becomes
numerical, but default equity still needs historical UK evidence."

```powershell
python -m pytest tests/test_pipeline.py -q -k resolving_sgd
python -m pytest tests/test_audit_regressions.py -q -k split_accrual
```

For the second test, predict: "Splitting JE-009 into equivalent debit lines still leaves
the same excessive net reversal; it remains held." The tests use copied data. A passing
test means its assertions held; open those assertions to demonstrate the actual evidence.
Never add the synthetic FX rate to the original bundle as though the company supplied it.

## 14. Close with evidence, AI corrections and future work — 2 minutes

**Open:** `VALIDATION.md`, then `REFLECTION.md`. Show the genuine AI-error table and
one actual fix commit; distinguish original mistakes from later audit refinements.

**Say:** "Checks cover source balance, monthly reconciliation, invoices, eliminations,
NCI and predictable changed-input effects. Independent calculations check selected
figures rather than only testing the code against itself. AI mistakes and fixes are recorded."

"The prototype is deliberately scoped to this bundle. With more time I would build
immutable input snapshots, typed finance approvals, a review queue, normalized provenance
and stronger publication/concurrency controls before scaling the number of entities."

## Rehearsal and questions to practise

For each stop explain: **input -> rule -> decision -> output -> proof**.
First rehearse data steps without code. Next rehearse the pipeline map. Finally practise
the changed-input prediction without reading the answer. Use the script as prompts,
not text to memorize word for word.

- Why can a balanced TB still be wrong? Show the deferred-income mapping.
- Why are customer receivables assets? They are amounts customers owe for earned sales;
  earning revenue need not coincide with collecting cash.
- Why hold a balanced journal? Equal debits/credits do not prove a distinct valid event.
- Why are there six nulls rather than six coding failures? Follow the missing-rate and
  historical-evidence dependencies; independent controls remain available.
- Why not 80% of India's sales? Consolidation includes controlled operations in full,
  with the minority share identified separately in profit and equity.
- What would you ask finance? Approved closing SGD FX; UK historical consolidation
  workings; supporting schedules for held journals and the sub-ledger gaps.
- What did you decide versus follow? Refer back to prescribed policies and the seven
  documented implementation choices in DECISIONS.md, with accurate AI attribution.
