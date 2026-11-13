# Seven decisions

These document the implementation choices made with Codex. They do not assert a
separate human accounting approval. Every assumption affecting results is also logged.

## 1. Deterministic accounting, one review agent in the product design

**Options:** LLM-generated statements; autonomous agents per entity; one deterministic
pipeline with an exception-review assistant. **Choice:** the last option; no runtime LLM
in the prototype. **Trade-off:** more explicit accounting code and less flexibility for
unseen exports, in exchange for reproducibility and explainable arithmetic. **AI:** the
handoff proposed deterministic Python; Codex adopted it and proposed a single review
agent for the full product. No autonomous ledger authority was added.

## 2. Missing evidence propagates as unknown

**Options:** reuse the SGD opening/average rate; carry the bank unadjusted as final;
null only the bank; propagate unknowns. **Choice:** unknown bank adjustment and its
7300 counterpart block profit/cash and dependent totals. UK acquisition history also
blocks the investment/equity elimination and total group goodwill. India-only controls
remain calculable. **Trade-off:** fewer headline figures, but no false precision. Partial
posting sums are explicitly non-authoritative. **AI:** Codex extended the handoff's
suggested SGD null to its PL and total dependencies; adopted. It did not assume zero
UK goodwill or use group opening reserves as parent-only historical reserves.

## 3. Repair one mapping visibly; preserve source data

**Options:** edit map_uk.csv; accept all mappings; fuzzy remapping; a narrow override.
**Choice:** the exact `Deferred income` label maps to 2300, with an `assumed` issue.
Keep both wage cost-centre rows. Record unused mappings and GBP 45,000 sub-ledger
differences without invented adjustments. **Trade-off:** the rule is bundle-specific and
needs review for another chart. **AI:** Codex proposed the exact-label rule rather than
a model similarity score; adopted. The initial Git scaffolding missed byte-preserving
attributes, which were added after conversion warnings exposed the problem.

## 4. Mechanical rejection versus business review

**Options:** post every balanced journal; reject all questionable entries; hold uncertain
purpose while posting supported entries. **Choice:** 13 posted, 2 rejected, 5 held.
JE-006 fails balance regardless of its memo; JE-017 fails period. JE-014 posts first,
JE-019 is held as a possible duplicate. JE-009, JE-016, JE-018 and JE-020 need evidence.
**Trade-off:** the results depend on the queue disposition. File-order selection is
deterministic, not proof that the first audit accrual is the correct one. **AI:** Codex
proposed holding overlapping India expenses because different monthly/journal amounts
do not prove duplication; adopted and disclosed as a review policy.

## 5. Reconcile periods before translating

**Options:** take India's entire FY25 YTD profit; multiply by six-ninths; use reconciled
monthly detail. **Choice:** reconcile all nine months per PL ledger, move April-June
profit into acquisition reserves, retain H2 source PL and valid December journals.
Translate H2 PL at H2 average and closing net assets at closing. **Trade-off:** absent or
inconsistent detail is fatal, even if a pro-rata estimate seems plausible. **AI:** the
handoff suggested the monthly split; Codex retained it and added coverage and tie tests.

## 6. Separate invoice transit, monetary FX and presentation FX

**Options:** plug the net IC difference; eliminate at one rate; explain distinct causes.
**Choice:** match invoices and reconcile local totals, book the missing year-end invoice
in the UK at closing, remeasure the existing USD payable, then eliminate balances.
The remaining fee-income/expense conversion difference goes to 7300. India NCI shares
entity translation while goodwill FX belongs to owners. **Trade-off:** more workings,
but the effects can be defended independently. **AI:** Codex proposed separate named
postings and an independent NCI closing-net-assets oracle; adopted. No UK elimination
plug was accepted.

## 7. Contribution provenance and testable failure states

**Options:** source filenames only; a large expression-graph service; a local posting log
with row/pointer/rate references. **Choice:** the local log plus input hashes and companion
control explanations. A fatal run overwrites the named outputs with blocked results;
mutations test this explicitly. **Trade-off:** verbose repeated source lists and no atomic
publication or persistent override UI. **AI:** Codex initially chose an issue's first sorted
source as its primary location and silently indexed duplicate metadata; review tests
exposed both mistakes. Explicit primary locations and uniqueness checks replaced them.
