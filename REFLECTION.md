# Reflection

With three months I would spend the first part on a finance-reviewed policy and evidence
model rather than adding more agents. Every mapping, accrual reversal, acquisition and
rate would have an owner, effective date, supporting document and recorded approval.
I would replace the acquisition-note template with structured completion accounts,
add a finance review UI over the JSON proposal queue, and import prior consolidation workings
so opening equity, goodwill and translation reserves can be reconciled directly.

The engine and bounded Claude review agent would sit behind immutable snapshots and
typed reviewer decisions. The implemented agent can inspect evidence and propose
actions, but cannot post a journal or create a rate. An approved change would create
a new candidate run with a visible financial diff, followed by the same validation gates.
Publication would switch an atomic pointer only after a finance reviewer accepts the
run. I would add independent accounting review, property-based tests and a broader
set of acquisition, disposal, impairment and currency scenarios before extending scope.

This prototype would break at scale in several concrete ways. Repeated source lists
grow rapidly; provenance should be stored once as a graph keyed by immutable row IDs.
Whole-file in-memory processing and synchronous recomputation would become costly
across large ledgers. Fixed schemas, one acquisition-note template and hard-coded FY2024
scope cannot absorb new ERPs, ownership changes or different policy periods. A local
folder is neither a concurrent evidence snapshot nor an atomic publication boundary.
There is no persistent decision store, permissions model or workflow for competing
reviewers. Those need deliberate design, not just larger machines.

The underestimated problem is deciding when the available evidence actually supports
a number. An unbalanced journal is easy to reject. A balanced entry with a plausible
description may duplicate an accrual, reverse something never booked, or belong before
acquisition. Even a perfectly balanced TB says nothing about whether the intercompany
counterparty, historical equity or closing rate is correct. Making the system return
`null`, and making that null propagate to the right totals while preserving independent
results, is as much a product requirement as producing statements. A trustworthy product
must make that incompleteness clear enough that a busy CFO cannot mistake passing
mechanical controls for a signable set of accounts.
