# Candidate decision and review walkthrough

## Audit remediation to explain in the live session

The final suite has 82 tests and the original run executes 64 runtime checks. Every
audit fix was checked through the full suite, a fresh committed clone and equality to
the pre-fix default controls. Original default and conditional financial figures did not
change. VALIDATION.md records the per-fix commits and regressions.

Useful input-change explanations:

- Splitting JE-009 or JE-019 into equivalent lines changes neither reversal validation
  nor duplicate classification, because both operate on net account movements.
- Splitting SGD bank or capital balances into equivalent source rows preserves their
  totals and historical bases. SGD carrying-value assumptions follow the actual TB.
- A foreign transaction currency does not make inventory monetary. Group-account
  classification controls remeasurement; non-monetary historical GBP amounts remain.
- Missing sub-ledger rows mean missing evidence, not a passed reconciliation.
- Amount strings that differ only in formatting compare numerically.
- IC balances/income/expense must have invoice coverage; an external-sales mapping to
  IC income cannot simply disappear through elimination.
- The alternative explicitly lists unknown dependencies outside A1/A1.gross/A2 and
  blocks those amounts. It never generalizes the SGD carrying-value assumption to EUR.
- Malformed journal input or an unexpected calculation error replaces old financial
  claims with failed results. Publication stages complete directory generations, with
  Windows-lock retries; an atomic concurrent-reader readiness pointer is still future work.
- Transcript privacy filtering is scoped to identified discovery results. Ordinary
  summaries and draft mistakes are retained, including the audit's failed attempts.

## Review refinement: conditional totals alongside conservative controls

The required controls file still has the original six nulls. Its companion explanations
and issues now show the conditional alternative amounts and reference
`output/scenarios/alternative_disclosed_assumptions.json`. The scenario is not a second
authoritative set of accounts and does not change the supplied input files.

**A1:** TB equity is treated as opening equity, without unreported dividends, capital,
reserve or in-year historical adjustment movements. The opening group reconciliation
supports zero *net* historical adjustment within source rounding. It does not establish
that goodwill alone is zero. **A1.gross:** gross assets additionally assume no offsetting
historical asset/liability adjustments. Net equity does not require that allocation.
**A2:** when closing SGD FX is missing, retain the bank's GBP 23,010 carrying amount
without remeasurement; this is a reporting assumption, not a policy-3 closing valuation.

Conditional results: group profit GBP 2,814,702.81; owners' profit GBP 2,744,660.38;
equity GBP 18,389,975.22; assets GBP 28,596,245.74; owners' CTA movement GBP 43,881.36.
Profit depends on A2, equity on A1/A2, gross assets on A1/A1.gross/A2, and CTA movement
on A1. A2 changes cash and profit equally and therefore does not change translation OCI.
Scenario balances are checked before rounding; displayed totals have a disclosed penny
difference from independent rounding. No balancing plug is posted.

**Suggested interview answer:** "These totals are calculable under disclosed assumptions,
and the opening-equity reconciliation supports the historical one. I did not present
them as facts because the inputs do not establish those assumptions. Gross assets need
an additional allocation assumption that net equity does not need."

**Input-change answer:** supplying an approved closing SGD rate removes A2 and changes
profit by 40,000 / rate - 23,010. Default profit becomes numerical. Default equity still
requires A1 evidence; the alternative equity becomes dependent on A1 alone. The tests
compare the two paths under matching historical assumptions rather than silently
promoting A1 into the default. Earlier answers below describe the conservative default.

This guide explains the choices implemented in the project. The first-person answers
are suggested wording for explaining those choices; they do not assert that you made
them independently before working with AI. The assignment requires you to understand
and take responsibility for the submitted code, including the parts written with AI.

## What the company actually asked you to decide

The brief asks for 5-7 important decisions, alternatives, trade-offs, and what the AI
suggested. It explicitly emphasizes judgment, reproducibility, evidence and refusal to
guess. The discussion questions below follow those evaluation criteria; they are
preparation questions, not a separately supplied list of interview questions.

| Already prescribed by the bundle | Judgment left to the candidate |
|---|---|
| Present the group in GBP | Architecture, module boundaries and agent authority |
| Closing FX for assets/liabilities; US FY average and India H2 average for PL | Missing-rate behavior and propagation to affected totals |
| Historical equity; given opening group equity | How to handle incomplete historical acquisition/equity evidence |
| Proportionate-share NCI; goodwill held in INR | How to implement and independently validate the calculation |
| Eliminate IC fully; receiver books transit at closing; fee FX residual to 7300 | Detecting, explaining and controlling mismatches |
| Only valid FY2024 journals are posted | Which ambiguous entries to hold and what evidence would release them |
| Code produces all figures; final rounding to 2 dp | Provenance, output structure and failure/review workflow |

You did not freely choose GBP, India's ownership percentage, the acquisition date, the
rate types or the NCI method. You chose how the system enforces those instructions
and what it does when available evidence is insufficient.

## Accounting vocabulary needed to explain the decisions

GBP is the British pound, USD the US dollar, INR the Indian rupee and SGD the
Singapore dollar. An entity's **functional currency** is the currency of its books;
the group's **presentation currency** is the currency of its consolidated reports.
US books use USD, UK books GBP and India books INR; all group reports use GBP.

A **trial balance** lists account balances. Debits are positive and credits negative
in this program. Assets/expenses are usually debits; liabilities/equity/revenue usually
credits. A zero TB total proves double-entry balance, not correct classification or value.
A **sub-ledger** is supporting detail behind a control account, such as customer balances.

**Profit** is revenue less expenses. It flows into retained earnings. A balance sheet
shows assets, liabilities and equity. Changes in equity reconcile opening equity to
closing equity through profit, translation and other evidenced movements. The program
includes unclosed current profit once when calculating closing balance-sheet equity.

**Goodwill** is the acquisition residual under the supplied policy. **NCI** is the
20% minority interest in India. **Translation reserve / CTA** records supported
presentation-currency differences in equity. It must not absorb unexplained accounting
errors, missing rates or missing acquisition data.

## The seven decisions and how to answer them

### 1. Why deterministic Python and only one bounded review agent?

**Context:** the problem combines reliable arithmetic with messy descriptions and
exceptions. The brief criticizes over-engineered agent topologies.

**Alternatives:** an LLM generates the accounts; separate autonomous agents consolidate
each entity; or one deterministic engine is surrounded by an assistant for exceptions.

**Suggested answer:** "I chose deterministic Python for every financial amount, mapping
application, rate conversion and validation gate. One implemented review agent uses
Claude on Azure Foundry to inspect exceptions and draft evidence-backed proposals. It
cannot post to the ledger. That keeps the numerical result repeatable while using an
LLM for work that actually needs language understanding."

**Trade-off:** less automatic handling of unfamiliar exports; more explicit rules to
maintain. **What AI contributed:** the handoff proposed deterministic Python; Codex
implemented the single review agent after the candidate selected Azure-hosted Claude.
**Proof:** financial calculation modules have no model calls; review.py runs the bounded
tool loop through claude_foundry.py. Default offline mode is labelled as rules, not AI.
Live mode needs a deployed model and credentials; scripted provider tests establish
protocol and capability boundaries, not the quality of a real model's reasoning.

### 2. Why return null and propagate it?

**Context:** the UK SGD bank requires a closing rate, but only opening/average rates
exist. UK acquisition equity and historical goodwill workings are also missing.

**Alternatives:** reuse another rate; leave GBP 23,010 as final; null only the bank;
or null the bank remeasurement and all financial figures depending on it.

**Suggested answer:** "I chose to propagate the unknown. The missing bank valuation
also means its FX gain or loss is unknown, so group profit and owners' profit cannot
be final. I report those controls as null with reasons. I still calculate independent
India figures. For the UK acquisition I hold the elimination, rather than assuming
zero goodwill or treating the parent's USD investment as if it were GBP."

**Trade-off:** fewer completed headline figures. The benefit is that the output does
not present an unsupported number as final. **AI refinement:** the initial advice
focused on bank/assets/equity; the implementation explicitly includes the PL dependency.
**Evidence to resolve it:** supplied closing SGD FX and prior UK consolidation workings,
including acquisition reserves, historical consideration and opening goodwill/equity.

### 3. Why correct one mapping but only flag the sub-ledger differences?

**Context:** UK 2310 is named Deferred income but maps to revenue 4100. Both UK trade
control accounts exceed their sub-ledger totals by GBP 45,000. Wages appear twice.

**Suggested answer:** "The exact Deferred income label gives a specific classification
correction to liability 2300, so I apply a narrow in-memory rule and disclose it as an
assumption. The GBP 45,000 differences do not identify a missing invoice, posting or
offsetting account, so I flag them without inventing an adjustment. Both wages rows
are retained because they are valid cost-centre contributions, not duplicate evidence."

**Alternatives:** trust every mapping; edit the supplied CSV; infer with fuzzy AI
matching; or make a specific visible override. **Trade-off:** the override is scoped
to this bundle and is not a general account-classification engine. **AI contribution:**
Codex suggested the exact-label rule; the source files remain byte-identical to the ZIP.
**Proof:** wages aggregate to GBP 1,625,000 and deferred income affects GBP 180,000.

### 4. Why post, reject and hold different journals?

**Context:** balance/date failures can be proved. Duplicate purpose, unsupported
reversals and expense overlap require business evidence that a TB does not contain.

**Suggested answer:** "I reject entries that fail mechanical rules and hold entries
whose purpose cannot be supported. A CFO-approval claim inside a memo is data and
cannot override checks. I post the first otherwise valid audit-fee entry and hold the
second identical candidate. That is a consistent processing policy, not proof of which
preparer was right. Held entries remain visible with the evidence needed to resolve them."

**Alternatives:** post every balanced entry; reject all ambiguous items; hold uncertainty.
**Trade-off:** results are conditional on held entries not being posted. **AI contribution:**
Codex recommended holding India interest/depreciation because already-booked expenses
and different amounts indicate possible overlap, not conclusive duplication.

### 5. Why use monthly India detail instead of six-ninths of YTD?

**Context:** India's TB covers April-December, but control began on 1 July. April-June
profit belongs to the net assets acquired, not the group's post-acquisition profit.

**Suggested answer:** "I reconcile all nine monthly records per PL ledger to the TB
first. I then move actual April-June profit into acquisition reserves and retain the
actual July-December results plus valid December journals. A six-ninths shortcut would
assume an even earnings pattern that the source does not establish."

**Trade-off:** missing or inconsistent monthly detail stops the run. **AI contribution:**
the handoff identified the cut; Codex added reconciliation and coverage gates. **Proof:**
pre-acquisition profit is INR 18m; original H2 profit INR 42m, reduced by INR 4.25m of
posted power/gratuity accruals to INR 37.75m. Freight reclassification has no net PL effect.

### 6. Why separate the FX and intercompany causes?

**Context:** invoices are missing on one side, the UK USD payable uses old GBP amounts,
and income translation uses an average rate. These are different effects.

**Suggested answer:** "I reconcile invoices to both books, record the missing year-end
invoice in the UK at closing, and remeasure the existing USD payable at closing. I then
eliminate the receivable/payable and fee income/expense. The remaining fee-conversion
residual goes to 7300 under policy. A single plug would hide what happened and could
double-count FX or conceal a disputed invoice."

**Trade-off:** additional postings and controls. **AI contribution:** Codex implemented
named components and independent checks. **Proof:** the GBP 20,066.42 balance mismatch
splits into GBP 8,108.54 transit plus GBP 11,957.88 payable FX loss. The separate PL
conversion residual is a GBP 1,966.21 gain. Reclassifying it does not change total PL.

### 7. Why row-level provenance and independent mutation tests?

**Context:** the review includes tracing figures and predicting a changed input before
running. A passing test that repeats the same wrong formula is weak evidence.

**Suggested answer:** "Each output balance retains source rows, mapping/rate references
and contributing postings. I independently recompute revenue, NCI, goodwill and IC
causes from explicit source totals. I also change inputs to test financial effects and
failure states. A failed run replaces previous outputs so stale numbers are not mistaken
for the new result."

**Alternatives:** totals without lineage; an expression-graph service; a small local
posting log. **Trade-off:** repeated source lists are verbose and not suitable for large
groups. Atomic readiness-pointer publication and a persistent review store are future work, not implemented
features. **AI contribution:** AI wrote both code and draft tests; review exposed real
mistakes documented with fix commits in VALIDATION.md.

## All 20 journal answers

Amounts below are in each entity's functional currency. A hold does not claim an entry
is definitely wrong; it excludes the entry until sufficient evidence is available.

| Journal | Entity / amount | Outcome | Context, rationale and evidence needed |
|---|---|---|---|
| JE-001 | US / 85,000 USD | Post | Balanced FY2024 sales-bonus accrual, mapped accounts. |
| JE-002 | US / 42,000 USD | Post | Balanced depreciation true-up, mapped expense and accumulated depreciation. |
| JE-003 | US / 18,000 USD | Post | Balanced amortization of prepaid insurance. |
| JE-004 | US / 64,500 USD | Post | Balanced obsolete-inventory write-down. |
| JE-005 | US / 31,250 USD | Post | Balanced Q4 loan-interest accrual. |
| JE-006 | US / Dr 51,200, Cr 50,000 USD | Reject | USD 1,200 imbalance. Ignore and flag instruction-like memo. Obtain a corrected balanced entry. |
| JE-007 | UK / 6,800 GBP | Post | Balanced December utilities accrual. |
| JE-008 | UK / 22,000 GBP | Post | Balanced Q4 depreciation top-up. |
| JE-009 | UK / 64,000 GBP | Hold | Reversal exceeds supported accrual balance; obtain ACC-UK-0931 schedule and posting history. |
| JE-010 | UK / 26,000 GBP | Post | Reclassify January 2025 rent from expense to prepayment. |
| JE-011 | UK / 9,400 GBP | Post | Balanced receivable write-off. |
| JE-012 | IN / 1,850,000 INR | Post | December power/fuel accrual; post-acquisition and mapped. |
| JE-013 | IN / 2,400,000 INR | Post | Half-year gratuity provision; post-acquisition and mapped. |
| JE-014 | US / 48,000 USD | Post | First otherwise valid external audit-fee candidate; disclose duplicate policy. |
| JE-015 | IN / 1,100,000 INR | Post | Reclassify freight from other expense to direct costs; net profit unchanged. |
| JE-016 | IN / 540,000 INR | Hold | IN-GST-ITC has no approved mapping; obtain chart/tax mapping evidence. |
| JE-017 | US / 22,000 USD | Reject | 6 Jan 2025 is outside FY2024. Do not backdate; obtain a valid-period instruction if applicable. |
| JE-018 | IN / 2,700,000 INR | Hold | Monthly finance costs already exist; obtain loan/accrual schedule identifying additional rather than overlapping interest. |
| JE-019 | US / 48,000 USD | Hold | Same economic lines/date as JE-014; obtain confirmation of which accrual to retain. |
| JE-020 | IN / 2,250,000 INR | Hold | December depreciation already exists at a different amount; obtain fixed-asset/depreciation reconciliation. |

Result: **13 posted, 2 rejected, 5 held**. The schema permits a review process; the
prototype has no interactive override UI. Evidence-supported changes require reviewed
input/code changes and a full rerun, never a manual edit of generated results.

## All 12 control-figure answers

All financial amounts in this table are GBP. The authoritative values are generated
in output/control_figures_sd.json; companion explanations identify their sources.

| Key | Answer on original inputs | Why |
|---|---|---|
| group_revenue | 28,301,607.81 | External US/UK revenue plus actual India H2 revenue; no IC management fees. |
| group_profit | null | Missing SGD closing rate leaves the monetary FX gain/loss unknown. |
| profit_owners | null | Group profit is unknown; NCI profit can still be calculated separately. |
| profit_nci | 70,042.43 | 20% x INR 37.75m / 107.7918. |
| nci_closing | 1,334,335.55 | 20% x INR 715.75m adjusted closing net assets / 107.28186. |
| goodwill_closing | 1,375,815.07 | India goodwill INR 147.6m / 107.28186; this key asks specifically for India. |
| translation_reserve_movement | null | UK acquisition/history and opening-equity reconciliation remain unresolved. |
| total_assets | null | Missing SGD valuation and unresolved UK investment/goodwill elimination. |
| total_equity | null | Missing profit and acquisition/historical-equity evidence. |
| intercompany_difference | Breakdown | 20,066.42 initial balance difference = 8,108.54 transit + 11,957.88 payable loss; residual 0.00. Separate fee FX gain 1,966.21. |
| sgd_bank_gbp | null | No closing SGD/GBP rate or same-type cross. |
| journals | 13 / 2 / 5 | Counts posted / rejected / held for review. |

**Revenue working:** USD 18.4m / 1.278 + GBP 9.85m + INR 437m / 107.7918.
**Acquisition working:** INR 678m = 250m share capital + 410m opening reserves +
18m pre-acquisition profit. Goodwill = 690m - 80% x 678m = INR 147.6m.

**NCI reconciliation:** acquisition NCI GBP 1,285,958.29 + profit GBP 70,042.43 -
translation GBP 21,665.17 = GBP 1,334,335.55 after final rounding. The calculation is
performed before rounding. NCI receives 20% of India's translation; goodwill translation
belongs entirely to owners under the proportionate-share method.

## Questions likely to come up in the review

**Where does AI actually run?** It helped build the submission. No model runs in the
financial calculation. The architecture describes a future review agent, not a deployed
runtime capability. I would demonstrate the Python execution path rather than imply
that an agent is already deciding ledger postings.

**Why not fetch the missing rate online?** The brief forbids filling missing values from
outside the supplied inputs. A historical market quote is not a supplied group rate.
I would request the approved closing rate and preserve its provenance if provided.

**Why not use the SGD carrying amount?** GBP 23,010 is a booked amount, not an evidenced
closing valuation. Treating it as final would assume the required FX adjustment is zero.

**Can a balanced TB still be wrong?** Yes. The supplied TBs balance, yet a liability is
mapped to revenue and supporting sub-ledgers disagree. Balance is one necessary control.

**Does the translation reserve just make the statements balance?** Only after the
underlying translation bases are supported. For India the bridge is closing net assets
minus acquisition net assets at spot minus H2 profit at H2 average. An unexplained
residual caused by missing evidence is not a valid translation-reserve calculation.
This qualifies the informal balancing explanation in the original Claude conversation.

**Why not complete the UK elimination against GBP 1m share capital?** The USD 1.27m
investment is not the same currency or historical basis. Acquisition reserves and
opening goodwill are not supplied. The remaining difference cannot safely be assigned
to goodwill or retained earnings. The held entry remains explicit.

**Why does parent equity also matter?** The parent is USD-functional and is translated
too. Group opening retained earnings are not a standalone historical GBP carrying amount
for the parent's retained earnings. Prior consolidation workings are required to reconcile
the combined opening bases and group CTA; the program does not use a closing-rate shortcut.

**What would release the held journals?** Evidence of a distinct event, an accrual/fixed-
asset/loan reconciliation, an approved mapping, or confirmation of which duplicate to
retain, as set out in the journal table. Being balanced alone is insufficient.

**What did the AI get wrong?** It initially missed Git byte-preservation attributes
(3308a2f), chose sorted metadata as an issue's primary location (2363599), and silently
overwrote duplicate metadata keys (b6bee12). Each was corrected and retained in history.
I can show the regression tests and failed test output in the transcript.

**What does exit code zero mean?** The calculation ran and published its available
results; it can still report partial_blocked statements. Read status and issues, not
only the process exit code. Fatal input/control failures return code 2 and replace old
outputs with blocked results. An OS interruption is a separate publication limitation.

**What changes with three months?** A persistent evidence/review store, versioned
decisions, structured acquisition schedules, immutable run snapshots, atomic publication,
more ERP adapters and wider independent accounting scenarios. At scale, normalize the
provenance graph instead of repeating source lists in every account.

**What are we underestimating?** The distinction between a plausible balanced number
and a number supported well enough for someone to sign. Review workflow and missing-
evidence propagation are core requirements.

## Live input-change predictions

Always state the prediction before running. Synthetic rates below are test fixtures,
never estimates or changes to the original bundle.

| Change | Prediction |
|---|---|
| Balanced GBP 1,000 UK cash sale on original bundle | Revenue rises GBP 1,000; NCI unchanged. Group/owners profit remain null because SGD is still unresolved; their available posting components increase. |
| Supply a test-only GBP/SGD closing rate of 1.7000 | SGD bank becomes GBP 23,529.41; group profit 2,815,222.23 and owners' profit 2,745,179.79 become calculable. UK acquisition/equity/CTA blockers remain. |
| Add the GBP 1,000 sale after that synthetic rate is supplied | Revenue, group profit and owners' profit rise GBP 1,000; NCI unchanged. |
| Add USD 1 to a US debit without a matching credit | Source TB fails; exit 2 and blocked replacement outputs. |
| Change one India monthly figure without its TB total | Monthly/TB reconciliation fails; no pro-rata repair. |
| Reword JE-006 memo as approved | Its numerical imbalance still rejects it, even if the marker detector does not recognize the new wording. |
| Change ownership, acquisition date or policy prose | Unsupported scope/version stops for reviewed implementation. |
| Release JE-020 without supporting evidence | Current policy continues to hold it; no silent override. If evidence supports a reviewed posting, its PL/NCI/asset effects must be recomputed. |

The automated examples are in tests/test_pipeline.py. See REVIEW_RUNBOOK.md for the
commands and a suggested 45-minute walkthrough.
