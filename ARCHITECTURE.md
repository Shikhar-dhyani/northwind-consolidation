# Northwind consolidation architecture

Bundle NWG-D0BC | FY ended 31 December 2024 | Python standard-library prototype

## Page 1 of 6 - Scope and topology

The system produces reproducible GBP consolidation workings and statements for the
US parent, wholly owned UK subsidiary and 80%-owned India subsidiary acquired on
1 July 2024. It distinguishes a completed calculation from complete financial evidence.
The current bundle produces partial statements: SGD closing FX and UK acquisition
history are missing. Neither a balanced input TB nor passing tests removes those gaps.

The prototype is one deterministic orchestrator (`pipeline.py`) calling small modules:

```text
Immutable bundle -> ERP adapters -> mapping and source controls -> journal gate
 -> entity monetary FX -> invoice transit -> India period cut -> GBP translation
 -> intercompany and India acquisition eliminations -> statements -> checks -> output
```

One implemented **case-review agent** surrounds this engine. Live mode uses Claude on
Azure Foundry through the Messages API. It selects cases, retrieves bounded evidence,
and submits proposals through four tools: get_case, read_evidence, get_control and
submit_review. Local validation rejects unseen citations, forbidden actions and incomplete
case coverage; errors return to the model for correction within 20 steps. No write,
shell, arbitrary-file or network tool is exposed to the model.

Default offline mode is an explicitly labelled rules baseline through the same broker,
not a simulated LLM. Live mode requires local credentials and a deployed model name.
The agent earns its place by explaining ambiguous exceptions and drafting evidence
requests. Accounting arithmetic and dispositions remain deterministic. All proposals
await human review; supported input corrections require a complete accounting rerun.

<div style="page-break-after: always;"></div>

## Page 2 of 6 - Input contract and trust boundary

Original `data/` bytes are committed, protected from Git line-ending conversion and
checked against hashes taken directly from the ZIP. Each run also hashes its actual
inputs, allowing reviewers to work on a copied, modified bundle without rewriting the
original. No network source fills a gap. No free-text field can change execution rules.
The implemented policy version is hash-checked; changed policy prose blocks for review.

Adapters normalize US debit/credit columns, UK signed balances, and India amount plus
Dr/Cr into signed postings. Codes remain strings, preserving UK `0030` and `0031`.
UK wages cost-centre rows both survive and aggregate. Duplicate metadata keys are
rejected before dictionary creation. Account types and statement classifications are
checked, and each entity TB must balance before processing and after valid journals.

Mappings are explicit inputs. The narrow correction for the exact label `Deferred income`
changes the supplied UK 2310 mapping from revenue to liability 2300 in memory. It is an
`assumed` issue, not an invisible repair; the source file is unchanged. Other unmapped
TB accounts stop the run; an unmapped journal is held. An unused mapping is disclosed.
The UK debtor and creditor sub-ledgers each differ from the source TB by GBP 45,000.
These remain flagged rather than becoming invented adjusting journals.

JE-006's memo requests bypassing controls. It is retained as evidence, flagged as
instruction-like text and ignored as authority. Its USD 1,200 imbalance rejects it.
Detection uses a limited marker list; containment is unconditional, even for wording
the marker list misses. The agent receives source text as untrusted quoted evidence.
Its tools enforce capability and citation boundaries even if it follows an injected memo.

<div style="page-break-after: always;"></div>

## Page 3 of 6 - Journals, periods and currencies

Journals are classified once, with sources and reasons. The engine rejects unbalanced
or out-of-period entries. It posts the first otherwise valid duplicate candidate in file
order, holding later identical lines/date; thus JE-014 posts and JE-019 is held. JE-009's
reversal exceeds available accruals; JE-016 has no mapping. India interest/depreciation
entries are held because the monthly TB already contains those expense categories and
no supporting schedule distinguishes a true-up from overlap. Different amounts do not
prove duplication. This review policy is disclosed and makes the results conditional.
Schema validation rejects malformed or empty journal structures. Reversal checks and
duplicate fingerprints operate on net account movements, independent of line splits.

India's April-December monthly detail must cover every PL ledger/month and reconcile
exactly to the source TB. April-June profit moves into pre-acquisition reserves; only
July-December source PL enters group profit. Valid December manual journals survive
the cut. Completion equity must reconcile to both the note and the period-cut ledger.

All arithmetic uses `Decimal` at 40 significant digits. GBP/USD means USD per GBP;
GBP/INR closing is 1.2530 x 85.62. Reverse conversions and at most two same-type legs
are allowed; FX type, quotation, positive value and as-of period are checked. There is
no fallback to another date or rate type. Currency identity uses a factor of one.

Entity-level monetary FX comes before presentation translation. UK USD payables are
remeasured at closing with the difference in 7300. Missing SGD closing FX creates
unknown bank-adjustment and PL counterpart legs; it therefore blocks group profit as
well as cash. Presentation translation uses closing for assets/liabilities, FY average
for US PL, H2 average for India PL and historical equity bases where supported. The
supplied opening parent share capital is used directly in GBP. Group opening reserves
cannot be treated as the parent's standalone historical retained earnings.
Monetary status is explicit by group account: cash/receivables/payables differ from
inventory/PPE/prepayments/deferred income despite broad shared Asset/Liability types.

<div style="page-break-after: always;"></div>

## Page 4 of 6 - Eliminations and minority ownership

Intercompany invoices are keyed by reporting entity and document reference, checked
against local TB balances and counterpart data. The US year-end invoice absent from
the UK is recorded as receiver expense/payable at closing under group policy. The
GBP 20,066.42 initial mismatch in the comparison comprises GBP 8,108.54 in transit
and GBP 11,957.88 payable retranslation. Reconciled receivables/payables eliminate in
full. Fee income and expense eliminate in full, with their GBP 1,966.21 conversion
residual reclassified to a gain in 7300. This reclassification does not change total PL.
The monetary payable retranslation is a separate loss, not that fee-conversion residual.
Numeric invoice formats compare as Decimal. All entities' IC postings, including manual
entries, require invoice coverage before any account is cleared through elimination.

The acquisition note is parsed using a narrow, checked template. Changed ownership,
completion date or fair-value wording stops for review. Consideration must reconcile
to the parent's USD investment within its original half-cent rounding tolerance.
India goodwill is INR 690m - 80% x INR 678m = INR 147.6m; it is recognized at
acquisition spot and retranslated at closing. Goodwill FX belongs entirely to owners.

India's entity translation difference is closing net assets minus acquisition net assets
translated at spot minus H2 profit translated at H2 average. NCI receives 20% of that
difference and 20% of post-acquisition profit, not 20% of goodwill. Opening acquisition
NCI plus profit plus translation independently reconciles to 20% of adjusted closing net
assets at closing FX. A separately named investment translation component reconciles
the parent's closing-translated investment to its acquisition-date elimination basis.

UK acquisition reserves and historical consideration/goodwill history are unavailable.
The UK elimination is held; empty amount markers block affected group accounts instead
of posting a guessed balancing adjustment. India goodwill is still a calculable control;
total group goodwill is not. Consolidated equity and the group CTA are not residual plugs.

<div style="page-break-after: always;"></div>

## Page 5 of 6 - Provenance and output semantics

Every posting carries an entity, account, signed GBP amount, stage, entry identifier and
source references. CSV references use physical file lines. Journal references add JSON
pointers so reformatting the JSON does not destroy identity. Converted contributions
also cite the actual FX rows, and mappings cite their chart rows. Acquisition and NCI
workings include completion-note, monthly, TB and rate evidence. Output amounts are
rounded once, at serialization, to 2 dp using half-up rounding.

An auditor starts at `control_explanations.json` or a statement account, follows the
source list and `ledger_postings.csv` contributions, inspects the relevant source rows,
then re-runs the named accounting stage. `eliminations.csv` shows both sides of each
posted elimination and separately identifies held lines. `journal_decisions.json` explains
excluded journal amounts. `input_manifest.json` identifies the exact files behind the run.
The ledger is a contribution log, not a general symbolic expression graph; the small,
versioned functions supply the formulas. A production system would store typed formula
nodes and immutable run/decision IDs for more efficient interactive drill-down.

An unknown scalar is `null` with a reason and sources in a companion object. Affected
TB CSV fields are empty and marked blocked. The controls file retains exactly the 12
required keys, with numeric components for the two required breakdowns. A partial
posting sum is labelled `known_postings`; it can contain unadjusted carrying amounts
and is never presented as the missing consolidated amount. Unknown dependencies
propagate through profit, equity and totals, without wiping out independent India figures.

Statements state `partial_blocked`. Current PL remains unclosed in the TB; reporting
includes it exactly once in total equity. No assertion that the consolidated TB balances,
or that opening-to-closing group equity reconciles, is made while required evidence is
absent. The missing SGD rate and UK history are explicit review requests, not estimates.

<div style="page-break-after: always;"></div>

## Page 6 of 6 - Validation, correction and operational limits

The loop is ingest -> validate -> compute -> reconcile -> publish. A fatal schema,
unbalanced source, inconsistent monthly detail, disputed invoice or acquisition control
stops calculation, writes blocked outputs and returns exit code 2. A reviewable gap
preserves independent results, records an issue, and returns code 0 with blocked status.
Corrections change code or reviewed input/configuration, then rerun the whole engine;
no generated figure is edited. The tests preserve discovered failure cases.

Controls include local TB balance, monthly/TB ties, completion equity, consideration,
invoice/TB ties, explained IC differences, balanced elimination journals, cleared IC and
India investment accounts, and the NCI roll-forward. Independently derived financial
oracles and input mutations test accounting effects, not merely implementation branches.
Adding a supplied SGD closing rate releases group profit but leaves acquisition blockers.
In that resolved-rate scenario, a GBP 1,000 UK cash sale increases revenue and owners' profit by GBP 1,000,
with no NCI effect. Full details and genuine AI-error fix commits are in VALIDATION.md.

The engine has no autonomous self-correction that silently modifies financial evidence.
The agent proposes; a finance reviewer obtains evidence and corrects reviewed inputs;
the engine validates a complete rerun. Invalid tool proposals receive corrective feedback.
There is no model-authorized journal, rate, approval or financial output overwrite.

Financial files are written into a temporary generation, then published using directory
renames. Caught errors publish failed outputs; unrelated directories are protected.
Windows rename locks have bounded retries and a failure-file invalidation fallback.
The directory may briefly be unavailable between renames. Process termination or an
unwritable filesystem still requires recovery. PDFs survive successful runs; archives
are rebuilt. There is no review UI, persistent decision store, policy language, concurrent
input snapshot lock or atomically exchanged readiness pointer. Production needs immutable
runs, an atomic ready pointer and access control. review_report.json holds pending
proposals; agent_trace.json records calls, evidence, tool rejections and model usage.
Sources are checked against the run manifest. API requests have 30-second timeouts,
three bounded attempts for transient failures, token/context limits and no redirects.
Review failure preserves financial results, records failure and gives CLI exit code 3.
At scale, stream/partition ledger data and normalize provenance rather than repeating
large source lists. The Claude planning conversation is preserved as supplied by the
candidate; the Codex record includes completed turns and the active turn through its
snapshot boundary. Refresh it after the active turn closes to include its final records.
