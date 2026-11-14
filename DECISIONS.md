# Seven decisions

These document the implementation choices made with Codex. They do not assert a
separate human accounting approval. Every assumption affecting results is also logged.
The context and rationale below explain the choices implemented in this submission;
the suggested first-person interview answers are in CANDIDATE_GUIDE.md.

## 1. Deterministic accounting, one review agent in the product design

**Context:** the brief asks for correct, reproducible financial figures and expressly
criticizes both frontier-model arithmetic and excessive agent counts. **Why this choice:**
arithmetic and control decisions need repeatable rules; language understanding is useful
for exceptions. One review agent around a small engine is easier to audit and explain.

**Options:** LLM-generated statements; autonomous agents per entity; one deterministic
pipeline with an exception-review assistant. **Choice:** the last option; no runtime LLM
in the prototype. **Trade-off:** more explicit accounting code and less flexibility for
unseen exports, in exchange for reproducibility and explainable arithmetic. **AI:** the
handoff proposed deterministic Python; Codex adopted it and proposed a single review
agent for the full product. No autonomous ledger authority was added.

## 2. Missing evidence propagates as unknown

**Review refinement:** retain conservative controls as the default and publish a separate
`output/scenarios/alternative_disclosed_assumptions.json`. The opening-equity bridge
supports a zero *net* historical adjustment within source rounding under A1: TB equity
represents opening balances, with no unreported capital/dividend/reserve or historical
adjustment movements. It does not establish zero UK goodwill alone. A1.gross additionally
assumes no offsetting historical gross asset/liability adjustments, and is needed only
for gross totals. A2 carries SGD at GBP 23,010 without FX remeasurement when closing FX
is missing; this is a reporting assumption, not a closing valuation under policy 3.
Profit needs A2; equity needs A1/A2; assets need A1/A1.gross/A2; owners' translation
movement needs A1 but not A2. Supplying SGD FX removes A2, not A1. Default null reasons
now include the conditional value and the scenario path. No default control is replaced.

**AI involvement in the refinement:** the candidate supplied the bridge and suggested
reducing nulls, then qualified the inference after discussion. Codex retained the
conservative default and implemented the explicitly labelled alternative and tests.

**Context:** the bank holds SGD 40,000 at a GBP 23,010 carrying value, without a closing
rate. UK acquisition workings are also absent. **Why this choice:** an unknown bank
remeasurement changes both assets and FX profit. Keeping headline profit would imply
that unknown gain/loss is zero. Blocking all dependent figures preserves that uncertainty
while allowing independent India figures to remain useful.

**Options:** reuse the SGD opening/average rate; carry the bank unadjusted as final;
null only the bank; propagate unknowns. **Choice:** unknown bank adjustment and its
7300 counterpart block profit/cash and dependent totals. UK acquisition history also
blocks the investment/equity elimination and total group goodwill. India-only controls
remain calculable. **Trade-off:** fewer headline figures, but no false precision. Partial
posting sums are explicitly non-authoritative. **AI:** Codex extended the handoff's
suggested SGD null to its PL and total dependencies; adopted. It did not assume zero
UK goodwill or use group opening reserves as parent-only historical reserves.

## 3. Repair one mapping visibly; preserve source data

**Context:** UK deferred income is mapped to revenue, wages have two cost-centre rows,
and sub-ledgers disagree with a balanced TB. **Why this choice:** an exact-label mapping
defect has a specific supported correction; a GBP 45,000 reconciliation difference has
no evidenced adjusting entry. The two conditions require different actions.

**Options:** edit map_uk.csv; accept all mappings; fuzzy remapping; a narrow override.
**Choice:** the exact `Deferred income` label maps to 2300, with an `assumed` issue.
Keep both wage cost-centre rows. Record unused mappings and GBP 45,000 sub-ledger
differences without invented adjustments. **Trade-off:** the rule is bundle-specific and
needs review for another chart. **AI:** Codex proposed the exact-label rule rather than
a model similarity score; adopted. The initial Git scaffolding missed byte-preserving
attributes, which were added after conversion warnings exposed the problem.

## 4. Mechanical rejection versus business review

**Context:** some entries are demonstrably invalid, while others are balanced but lack
evidence of distinct business events. **Why this choice:** rejection is appropriate when
a rule fails; a hold preserves an unresolved question without inventing an answer. The
first audit accrual is selected consistently, with no assertion that file order proves approval.

**Options:** post every balanced journal; reject all questionable entries; hold uncertain
purpose while posting supported entries. **Choice:** 13 posted, 2 rejected, 5 held.
JE-006 fails balance regardless of its memo; JE-017 fails period. JE-014 posts first,
JE-019 is held as a possible duplicate. JE-009, JE-016, JE-018 and JE-020 need evidence.
**Trade-off:** the results depend on the queue disposition. File-order selection is
deterministic, not proof that the first audit accrual is the correct one. **AI:** Codex
proposed holding overlapping India expenses because different monthly/journal amounts
do not prove duplication; adopted and disclosed as a review policy.

## 5. Reconcile periods before translating

**Context:** India's FY25 YTD means April-December, but group control began in July.
**Why this choice:** monthly detail supplies the actual pre/post split. Multiplying nine
months by six-ninths would assume uniform earnings and misclassify acquisition reserves.

**Options:** take India's entire FY25 YTD profit; multiply by six-ninths; use reconciled
monthly detail. **Choice:** reconcile all nine months per PL ledger, move April-June
profit into acquisition reserves, retain H2 source PL and valid December journals.
Translate H2 PL at H2 average and closing net assets at closing. **Trade-off:** absent or
inconsistent detail is fatal, even if a pro-rata estimate seems plausible. **AI:** the
handoff suggested the monthly split; Codex retained it and added coverage and tie tests.

## 6. Separate invoice transit, monetary FX and presentation FX

**Context:** the IC balances disagree because one invoice is absent and the UK USD
payable still carries historical amounts; PL also uses an average rate. **Why this choice:**
one net plug would hide different causes and could double-count or misallocate FX.
Separate postings prove which discrepancy was resolved and where each effect belongs.

**Options:** plug the net IC difference; eliminate at one rate; explain distinct causes.
**Choice:** match invoices and reconcile local totals, book the missing year-end invoice
in the UK at closing, remeasure the existing USD payable, then eliminate balances.
The remaining fee-income/expense conversion difference goes to 7300. India NCI shares
entity translation while goodwill FX belongs to owners. **Trade-off:** more workings,
but the effects can be defended independently. **AI:** Codex proposed separate named
postings and an independent NCI closing-net-assets oracle; adopted. No UK elimination
plug was accepted.

## 7. Contribution provenance and testable failure states

**Context:** reviewers must trace a figure and predict a changed input before rerunning.
**Why this choice:** source rows, rate rows, journal decisions and input hashes make the
computation inspectable. Independent calculations and deliberate input mutations expose
errors that a self-consistent but wrong implementation could otherwise miss.

**Options:** source filenames only; a large expression-graph service; a local posting log
with row/pointer/rate references. **Choice:** the local log plus input hashes and companion
control explanations. A fatal run overwrites the named outputs with blocked results;
mutations test this explicitly. **Trade-off:** verbose repeated source lists and no atomic
publication or persistent override UI. **AI:** Codex initially chose an issue's first sorted
source as its primary location and silently indexed duplicate metadata; review tests
exposed both mistakes. Explicit primary locations and uniqueness checks replaced them.
